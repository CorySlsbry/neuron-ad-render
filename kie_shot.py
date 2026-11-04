#!/usr/bin/env python3
"""kie_shot.py - image-to-video (and faceless text-to-video) through Kie.ai, as a drop-in alternative to HeyGen
cinematic_avatar for the persona rail. Clean-room: written from Kie.ai's own API docs (docs.kie.ai), not from any
third-party script. stdlib only (urllib). Every dollar is gated IN CODE before a task is created.

Shot mode (the rail):
  python kie_shot.py <ad> <i> --still=personas/<still>.png [--model=seedance15|kling3|auto] [--retry=N] [--dry]
    reads shots.json[ad][i-1] (prompt/dialogue/duration) and <ad>/shot<i>_vo.mp3 (the gated VO sets the length),
    derives a MOTION prompt (identity + set come from the still; no spoken line - the lipsync stage adds the VO),
    uploads the still (Kie's free 24h host), creates the task, polls, downloads
      <ad>/shot<i>_cinematic.mp4   and writes   <ad>/shot<i>_result.json  (HeyGen-shaped `data` + a `kie` block)
    and prints the same `DOWNLOADED <path> <KB> KB` line the drivers grep.
Faceless mode (B-roll / brand shorts):
  python kie_shot.py --faceless --prompt-file=<txt|md> --out=<mp4> [--seconds=12] [--model=seedance15|kling3|veo31fast]
                     [--still=<png>] [--dry]
Utilities:
  python kie_shot.py --credits            balance
  python kie_shot.py --ledger [--import-blotato]   spend ledger + caps state (import merges ~/faceless/generations/ledger.json)

Spend guard (code, not prose): kie_ledger.json rows at submit and at settle; caps KIE_SESSION_CAP (rolling 24h, $10),
KIE_MONTH_CAP (calendar month, $50), KIE_MAX_TASK_USD ($2.00); balance must cover the estimate; creditsConsumed is
reconciled against the balance delta. Local idempotency: <dir>/.kie_tasks.json keyed by sha1(model|prompt|still|duration)
(Kie has no idempotency header) - a re-run replays a finished task free and resumes a pending one; --retry=N forces new.
Exit codes: 0 ok · 2 task failed · 3 still running (resumable) · 4 cap · 5 no credits · 6 bad input · 7 upload failed.
"""
import sys, os, re, json, time, math, hashlib, base64, pathlib, datetime, subprocess, urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\you\.neuron-vault")
API = "https://api.kie.ai/api/v1"
UPLOAD_HOSTS = ["https://kieai.redpandaai.co", "https://api.kie.ai"]   # docs disagree; the first answered on 2026-09-15
CREDIT_USD = 0.005                                                        # $5 per 1,000 credits
LEDGER = pathlib.Path(os.environ.get("KIE_LEDGER") or (HERE / "kie_ledger.json"))   # KIE_LEDGER: the selftest's sandbox
ENGINE = pathlib.Path(r"C:\Users\you\.claude\skills\geo-flywheel\references\engine")
POLL_S, POLL_TIMEOUT_S = 15, 1500
# --audio (faceless only, 2026-09-25): Seedance 1.5 Pro makes its own sound (SFX, ambience). Default stays OFF: the
# persona rail's lipsync stage supplies the voice. Part of the task key, so a silent and a sound run never share a replay.
AUDIO = "--audio" in sys.argv

MODELS = {
    # image-to-video, 9:16 1080p, audio OFF (the lipsync stage supplies the VO). Verified fields/prices 2026-09-15.
    "seedance15": {"id": "bytedance/seedance-1.5-pro", "min": 4, "max": 12, "usd_per_s": 0.0375,
                   "build": lambda url, prompt, d: {"prompt": prompt, **({"input_urls": [url]} if url else {}),
                                                    "aspect_ratio": "9:16", "resolution": "1080p", "duration": int(d),
                                                    "generate_audio": AUDIO, "fixed_lens": False}},
    "kling3":     {"id": "kling-3.0/video", "min": 3, "max": 15, "usd_per_s": 0.09,
                   "build": lambda url, prompt, d: {"prompt": prompt, **({"image_urls": [url]} if url else {}),
                                                    "aspect_ratio": "9:16", "mode": "pro", "duration": str(int(d)),
                                                    "sound": False}},
    # faceless B-roll only: 8s max, native audio always on, upstream rejects real faces -> never for Cory shots
    "veo31fast":  {"id": "veo-3-1", "min": 4, "max": 8, "usd_flat": 0.325, "allowed": (4, 6, 8),
                   "build": lambda url, prompt, d: {"prompt": prompt, **({"image_urls": [url]} if url else {}),
                                                    "aspect_ratio": "9:16", "resolution": "1080p", "duration": int(d)}},
}

class KieFailed(Exception): pass
class KieStillRunning(Exception): pass

def arg(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)

def _key():
    from secrets_vault import get
    k = get("KIE_API_KEY")
    if not k:
        raise RuntimeError("KIE_API_KEY is not in the vault: run  python C:\\Users\\you\\.neuron-vault\\vault_cli.py set KIE_API_KEY")
    return k

def _req(method, url, body=None, timeout=120, key=None):
    """Bearer request with 429/5xx retry (x4, Retry-After honored); 400/401/402 surface immediately."""
    key = key or _key()
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="ignore")[:300]
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                wait = int(e.headers.get("Retry-After") or 0) or 8 * (attempt + 1)
                print(f"  kie {e.code} - waiting {wait}s", flush=True); time.sleep(wait); continue
            raise RuntimeError(f"kie {method} {url.split('/api/')[-1]} -> HTTP {e.code}: {txt}")
        except urllib.error.URLError as e:
            if attempt < 4:
                time.sleep(8 * (attempt + 1)); continue
            raise RuntimeError(f"kie network error: {e}")

def credits():
    d = _req("GET", f"{API}/chat/credit")
    val = d.get("data")
    if isinstance(val, dict):
        val = val.get("credits", val.get("remaining", val.get("balance", 0)))
    n = float(val or 0)
    return {"credits": n, "usd": round(n * CREDIT_USD, 4)}

# ---------------------------------------------------------------- ledger + caps (the harness law: gates in code)
def ledger_load():
    try: return json.loads(LEDGER.read_text(encoding="utf-8"))
    except Exception: return []

def ledger_save(rows):
    tmp = LEDGER.with_name(f"{LEDGER.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    os.replace(tmp, LEDGER)

class _LedgerLock:
    """One writer at a time ACROSS PROCESSES (an O_EXCL lock file; a lock older than 60 s is a dead process's)."""
    def __enter__(self):
        self.path = str(LEDGER) + ".lock"
        deadline = time.time() + 45
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > 60:
                        os.remove(self.path); continue
                except OSError:
                    pass
                if time.time() > deadline: raise RuntimeError("kie ledger lock held for more than 45 s")
                time.sleep(0.03 + (os.getpid() % 7) * 0.01)
    def __exit__(self, *exc):
        os.close(self.fd)
        try: os.remove(self.path)
        except OSError: pass

def ledger_update(fn):
    """MERGE-FROM-DISK before every write: load the ledger as it is NOW, apply fn(rows), replace the file atomically.
    Nine parallel tasks each wrote back the list they had loaded minutes earlier and eight rows were lost (2026-09-20)."""
    with _LedgerLock():
        rows = ledger_load()
        out = fn(rows)
        ledger_save(rows)
        return out

def reserve(est_usd, row):
    """The cap check and the reservation are ONE step under the lock, before any task exists: a parallel launch used to
    pass nine cap checks against an empty ledger. Exit 4 when the caps would be crossed by everything already reserved."""
    caps = {"session": float(os.environ.get("KIE_SESSION_CAP", 10.0)), "month": float(os.environ.get("KIE_MONTH_CAP", 50.0))}
    def fn(rows):
        s, m = ledger_sums(rows)
        if s + est_usd > caps["session"]: return f"CAP: session ${s + est_usd:.2f} > ${caps['session']:.2f}"
        if m + est_usd > caps["month"]: return f"CAP: month ${m + est_usd:.2f} > ${caps['month']:.2f}"
        rows.append(row)
        return None
    refused = ledger_update(fn)
    if refused:
        print(refused + " (reserved rows of other running tasks count)"); sys.exit(4)

def ledger_patch(rid, fields):
    def fn(rows):
        for r in rows:
            if r.get("rid") == rid or (fields.get("_task_id") and r.get("task_id") == fields["_task_id"]):
                r.update({k: v for k, v in fields.items() if not k.startswith("_")})
    ledger_update(fn)

def ledger_sums(rows):
    now = datetime.datetime.now()
    day = (now - datetime.timedelta(hours=24)).isoformat()
    month = now.strftime("%Y-%m")
    live = [r for r in rows if r.get("state") not in ("fail", "refunded")]
    return (sum(r.get("usd", 0) for r in live if r.get("ts", "") >= day),
            sum(r.get("usd", 0) for r in live if r.get("ts", "").startswith(month)))

def guard_caps(est_usd, dry=False):
    caps = {"session": float(os.environ.get("KIE_SESSION_CAP", 10.0)), "month": float(os.environ.get("KIE_MONTH_CAP", 50.0)),
            "task": float(os.environ.get("KIE_MAX_TASK_USD", 2.0))}
    s, m = ledger_sums(ledger_load())
    line = f"session ${s:.2f}/${caps['session']:.0f} | month ${m:.2f}/${caps['month']:.0f}"
    if est_usd > caps["task"]:
        print(f"CAP: task ${est_usd:.2f} > KIE_MAX_TASK_USD ${caps['task']:.2f}"); sys.exit(4)
    if s + est_usd > caps["session"]:
        print(f"CAP: session ${s + est_usd:.2f} > ${caps['session']:.2f} ({line})"); sys.exit(4)
    if m + est_usd > caps["month"]:
        print(f"CAP: month ${m + est_usd:.2f} > ${caps['month']:.2f} ({line})"); sys.exit(4)
    return line

# ---------------------------------------------------------------- helpers
def sha1_file(p):
    return hashlib.sha1(pathlib.Path(p).read_bytes()).hexdigest()

def ffprobe_dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0

def pick_model(need_s, explicit=None):
    if explicit and explicit != "auto":
        if explicit not in MODELS: sys.exit(f"unknown --model {explicit}; choose {', '.join(MODELS)}")
        return explicit
    if need_s <= MODELS["seedance15"]["max"]: return "seedance15"
    if need_s <= MODELS["kling3"]["max"]: return "kling3"
    print(f"SHOT TOO LONG: {need_s}s > 15s - split the line"); sys.exit(6)

def clamp_duration(model, need_s):
    m = MODELS[model]
    d = max(m["min"], min(m["max"], int(math.ceil(need_s))))
    if "allowed" in m:
        d = min([a for a in m["allowed"] if a >= d] or [m["allowed"][-1]])
    return d

def estimate(model, d):
    m = MODELS[model]
    # Seedance with --audio bills double: measured 2026-09-25, 120 credits for 8 s (15 cr/s) against 7.5 cr/s silent
    audio_x = 2 if (AUDIO and model == "seedance15") else 1
    return round(m["usd_flat"] if "usd_flat" in m else d * m["usd_per_s"] * audio_x, 4)

IDENTITY_LOCK = ("Image-to-video from the reference photo: keep this exact person - same face, hair, beard, build and "
                 "clothing - and this exact set, lighting and framing as the first frame. ")
PERFORMANCE = (" He is mid-conversation, speaking to the camera the whole take: continuous natural speech-like mouth "
               "movement, small natural hand gestures, relaxed shoulders, eyes on the lens, a closed resting mouth "
               "between phrases, no exaggerated expressions. One continuous take, no cuts, no morphing, no one else "
               "stepping into frame, no on-screen text, captions or logos.")

def build_motion_prompt(shot):
    """The still carries identity + set, so the motion prompt keeps only scene/camera clauses from the shots.json
    prompt, drops the spoken line (audio is off) and HeyGen-only phrasing, then adds the performance block."""
    if shot.get("motion"):
        return IDENTITY_LOCK + shot["motion"].strip()
    p = shot.get("prompt", "")
    p = re.sub(r'\bsaying:\s*"[^"]*"\s*', "", p)
    p = re.sub(r"Delivering the whole line[^.]*\.\s*", "", p)
    p = re.sub(r"delivering the whole line[^.]*\.\s*", "", p)
    p = re.sub(r"He talks straight to the lens[^.]*\.\s*", "", p)
    p = re.sub(r"His default face between words[^.]*\.\s*", "", p)
    p = re.sub(r"While speaking the mouth moves[^.]*\.\s*", "", p)
    p = re.sub(r"Only after the last word[^.]*\.\s*", "", p)
    p = re.sub(r"After the last word[^.]*\.\s*", "", p)
    p = re.sub(r"Vertical 9:16 documentary-style video\.\s*", "", p)
    p = re.sub(r"\s{2,}", " ", p).strip()
    return IDENTITY_LOCK + p + PERFORMANCE

def upload_still(path):
    raw = pathlib.Path(path).read_bytes()
    mime = "image/png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    body = {"base64Data": f"data:{mime};base64," + base64.b64encode(raw).decode(),
            "uploadPath": "images", "fileName": f"{pathlib.Path(path).stem}-{sha1_file(path)[:8]}.{'png' if mime.endswith('png') else 'jpg'}"}
    last = ""
    for host in UPLOAD_HOSTS:
        try:
            d = _req("POST", f"{host}/api/file-base64-upload", body, timeout=180)
            data = d.get("data") or {}
            url = data.get("fileUrl") or data.get("downloadUrl")
            if url: return url
            last = json.dumps(d)[:200]
        except RuntimeError as e:
            last = str(e)
    print(f"UPLOAD FAILED: {last}"); sys.exit(7)

def task_key(model_id, prompt, still_sha, d, retry):
    k = hashlib.sha1(f"{model_id}|{prompt}|{still_sha}|{d}{'|audio' if AUDIO else ''}".encode()).hexdigest()[:16]
    return k + (f"-r{retry}" if retry else "")

def tasks_load(tdir):
    p = pathlib.Path(tdir) / ".kie_tasks.json"
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

def tasks_save(tdir, t):
    """MERGE-FROM-DISK under a lock, like the ledger: two renders in one folder each wrote back the dict they had loaded
    at start, and the second write dropped the first task's key (2026-10-16, Seedance 2.5 + Vidu Q4 run in parallel),
    so a re-run would pay again instead of replaying."""
    p = pathlib.Path(tdir) / ".kie_tasks.json"
    lock = str(p) + ".lock"
    deadline = time.time() + 45
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > 60: os.remove(lock); continue
            except OSError:
                pass
            if time.time() > deadline: raise RuntimeError(f"{lock} held for more than 45 s")
            time.sleep(0.05)
    try:
        merged = tasks_load(tdir)
        merged.update(t)
        tmp = p.with_name(f"{p.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(merged, indent=1), encoding="utf-8")
        os.replace(tmp, p)
        t.update(merged)
    finally:
        os.close(fd)
        try: os.remove(lock)
        except OSError: pass

def create_task(model_id, inp):
    d = _req("POST", f"{API}/jobs/createTask", {"model": model_id, "input": inp})
    if d.get("code") not in (200, "200") or not (d.get("data") or {}).get("taskId"):
        raise RuntimeError(f"createTask refused: {json.dumps(d)[:300]}")
    return d["data"]["taskId"]

def poll(task_id, timeout_s=POLL_TIMEOUT_S):
    t0 = time.time(); last_print = 0
    while time.time() - t0 < timeout_s:
        d = _req("GET", f"{API}/jobs/recordInfo?taskId={task_id}")
        data = d.get("data") or {}
        st = data.get("state")
        if st == "success":
            rj = data.get("resultJson")
            rj = json.loads(rj) if isinstance(rj, str) else (rj or {})
            # Seedance/Kling: resultUrls; Veo 3.1: data.result_urls (the 1080p upsample), then data.origin_urls (2026-10-10)
            vd = rj.get("data") or {}
            urls = rj.get("resultUrls") or vd.get("result_urls") or vd.get("origin_urls") or []
            if not urls: raise KieFailed("NO_RESULT_URL", json.dumps(data)[:200])
            return urls[0], float(data.get("creditsConsumed") or 0), data
        if st == "fail":
            raise KieFailed(data.get("failCode") or "GENERATION_FAILED", data.get("failMsg") or "")
        if time.time() - last_print >= 60:
            print(f"  {int(time.time()-t0):4d}s {st or '?'}", flush=True); last_print = time.time()
        time.sleep(POLL_S)
    raise KieStillRunning(task_id)

def download(url, dest):
    dest = pathlib.Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    dur = ffprobe_dur(dest)
    if dur <= 0: raise KieFailed("BAD_DOWNLOAD", f"ffprobe found no duration in {dest}")
    return dur

def lineage_gate(slug, out, ok, detail):
    try:
        sys.path.insert(0, str(ENGINE)); import lineage
        lineage.score(slug, asset_id=lineage.asset_id(str(out)), scorer="gates", score=100 if ok else 0,
                      verdict="PASS" if ok else "FAIL", detail=detail)
    except Exception:
        pass

# ---------------------------------------------------------------- the render (shared by both modes)
def render(*, slug, tdir, out, result_json, model, prompt, still, need_s, retry, dry, extra_result=None, title=""):
    d = clamp_duration(model, need_s)
    m = MODELS[model]
    still_sha = sha1_file(still) if still else "none"
    key = task_key(m["id"], prompt, still_sha, d, retry)
    est = estimate(model, d)
    tasks = tasks_load(tdir); rec = tasks.get(key) or {}
    out = pathlib.Path(out)
    if rec.get("out_sha") and out.is_file() and sha1_file(out) == rec["out_sha"]:
        print(f"DOWNLOADED {out} {out.stat().st_size//1024} KB   (replayed from .kie_tasks.json key {key}, $0)")
        return 0
    capline = guard_caps(est, dry)
    bal = None
    try:
        bal = credits()
    except RuntimeError as e:
        if not dry: raise
        print(f"  (no balance: {str(e)[:80]})")
    balline = f"balance ${bal['usd']:.2f} ({bal['credits']:.0f} cr)" if bal else "balance n/a"
    print(f"ESTIMATE {model} {d}s = ${est:.2f} | {capline} | {balline}")
    if dry:
        print("DRY RUN payload:", json.dumps({"model": m["id"], "input": m["build"]("<still-url>" if still else None, prompt, d)}, indent=1))
        return 0
    if bal and bal["usd"] < est:
        print(f"NO_CREDITS: balance ${bal['usd']:.2f} < estimate ${est:.2f}"); sys.exit(5)
    task_id = rec.get("taskId") if rec.get("state") not in (None, "fail") else None
    rid = hashlib.sha1(f"{os.getpid()}|{time.time()}|{key}".encode()).hexdigest()[:12]
    ts0 = datetime.datetime.now().isoformat(timespec="seconds")
    if not task_id:
        reserve(est, {"rid": rid, "ts": ts0, "slug": slug, "out": str(out), "model": m["id"], "duration": d, "task_id": None,
                      "key": key, "usd": est, "credits": round(est / CREDIT_USD), "state": "reserved",
                      "balance_before": bal["credits"] if bal else None})
        try:
            url = upload_still(still) if still else None        # uploaded right before the task (24h host)
            inp = m["build"](url, prompt, d)
            task_id = create_task(m["id"], inp)
        except BaseException as e:
            ledger_patch(rid, {"state": "fail", "fail": f"create: {str(e)[:160]}"})
            raise
        ledger_patch(rid, {"task_id": task_id, "state": "submitted"})
        tasks[key] = {"taskId": task_id, "state": "submitted", "created": ts0, "model": m["id"], "duration": d}
        tasks_save(tdir, tasks)
        print(f"TASK {task_id}", flush=True)
    else:
        print(f"RESUME {task_id} (key {key})", flush=True)
    try:
        video_url, consumed, data = poll(task_id)
    except KieFailed as e:
        ledger_patch(rid, {"_task_id": task_id, "state": "fail", "fail": f"{e.args[0]}: {e.args[1] if len(e.args) > 1 else ''}"})
        tasks[key]["state"] = "fail"; tasks_save(tdir, tasks)
        print(f"FAILED {e.args[0]} {e.args[1] if len(e.args) > 1 else ''}"); lineage_gate(slug, out, False, {"engine": "kie", "fail": e.args[0]})
        sys.exit(2)
    except KieStillRunning:
        print(f"STILL RUNNING after {POLL_TIMEOUT_S//60} min - task {task_id} kept in .kie_tasks.json; re-run to resume (results live 14 days)")
        sys.exit(3)
    dur = download(video_url, out)
    after = None
    try: after = credits()
    except RuntimeError: pass
    usd = round((consumed or est / CREDIT_USD) * CREDIT_USD, 4)
    reconcile = "ok"
    settled = datetime.datetime.now().isoformat(timespec="seconds")
    # the balance delta only proves THIS task's cost when no other task spent in the same window
    others = sum(1 for r in ledger_load() if r.get("rid") != rid and r.get("task_id") != task_id and r.get("state") != "fail"
                 and r.get("ts", "") <= settled and (r.get("settled") or settled) >= ts0)
    if others:
        reconcile = f"skipped ({others} concurrent task(s) share the balance delta)"
    elif bal and after is not None:
        delta = bal["credits"] - after["credits"]
        if consumed and abs(delta - consumed) > 1: reconcile = f"mismatch (delta {delta:.0f} vs consumed {consumed:.0f})"
    ledger_patch(rid, {"_task_id": task_id, "state": "success", "credits": round(consumed or est / CREDIT_USD), "usd": usd,
                       "balance_after": after["credits"] if after else None, "reconcile": reconcile, "settled": settled})
    tasks[key].update({"state": "success", "resultUrl": video_url, "out": str(out), "out_sha": sha1_file(out)}); tasks_save(tdir, tasks)
    res = {"source": "kie", "data": {"id": task_id, "status": "completed", "video_url": video_url, "duration": round(dur, 2),
                                     "title": title or f"{slug} (kie {model})"},
           "kie": {"model": m["id"], "model_key": model, "task_id": task_id, "state": "success", "credits_consumed": consumed,
                   "usd": usd, "still": str(still) if still else None, "still_sha": still_sha, "prompt": prompt, "duration": d,
                   "key": key, "created": tasks[key].get("created"), "completed": datetime.datetime.now().isoformat(timespec="seconds"),
                   "result_expires": (datetime.datetime.now() + datetime.timedelta(days=14)).date().isoformat(), "reconcile": reconcile}}
    if extra_result: res.update(extra_result)
    pathlib.Path(result_json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"DOWNLOADED {out} {out.stat().st_size//1024} KB")
    if after: print(f"KIE credits after: {after['credits']:.0f} (${after['usd']:.2f})")
    print(f"COST ${usd:.2f} ({round(consumed or est / CREDIT_USD)} cr)" + ("" if reconcile == "ok" else f"  WARN reconcile {reconcile}"))
    lineage_gate(slug, out, True, {"engine": "kie", "model": m["id"], "usd": usd, "duration": round(dur, 2), "reconcile": reconcile})
    return 0

# ---------------------------------------------------------------- CLI
def _selftest_ledger():
    """Eight real processes reserve $0.30 each against a sandbox ledger with a $1.00 session cap: exactly three may get
    in, five must exit 4, and the file must hold exactly three rows (a lost row or a fourth reservation fails it)."""
    import tempfile
    box = pathlib.Path(tempfile.mkdtemp(prefix="kie-ledger-selftest-")) / "ledger.json"
    env = dict(os.environ, KIE_LEDGER=str(box), KIE_SESSION_CAP="1.0", KIE_MONTH_CAP="50")
    procs = [subprocess.Popen([sys.executable, __file__, "--_reserve-probe"], env=env, stdout=subprocess.PIPE, text=True)
             for _ in range(8)]
    codes = [p.wait() for p in procs]
    rows = json.loads(box.read_text(encoding="utf-8")) if box.exists() else []
    ok = codes.count(0) == 3 and codes.count(4) == 5 and len(rows) == 3 and len({r["rid"] for r in rows}) == 3
    print(f"ledger selftest: exits {sorted(codes)}, rows {len(rows)} -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

def main():
    if "--_reserve-probe" in sys.argv:
        rid = hashlib.sha1(f"{os.getpid()}|{time.time()}".encode()).hexdigest()[:12]
        reserve(0.30, {"rid": rid, "ts": datetime.datetime.now().isoformat(timespec="seconds"), "usd": 0.30, "state": "reserved"})
        return 0
    if "--selftest-ledger" in sys.argv:
        return _selftest_ledger()
    if "--credits" in sys.argv:
        print(json.dumps(credits())); return 0
    if "--ledger" in sys.argv:
        rows = ledger_load()
        if "--import-blotato" in sys.argv:
            bl = pathlib.Path(os.environ.get("GENERATIONS_DIR", os.path.expanduser("~/faceless/generations"))) / "ledger.json"
            if bl.is_file():
                have = {(r.get("ts"), r.get("model"), r.get("credits")) for r in rows}
                for b in json.loads(bl.read_text(encoding="utf-8")):
                    row = {"ts": str(b.get("timestamp") or b.get("created") or "")[:19], "slug": "blotato-generate", "model": b.get("model"),
                           "usd": float(b.get("cost_usd") or 0), "credits": float(b.get("cost_credits") or 0), "state": "success", "source": "blotato"}
                    if (row["ts"], row["model"], row["credits"]) not in have: rows.append(row)
                ledger_save(rows)
        s, m = ledger_sums(rows)
        for r in rows[-20:]:
            print(f"{r.get('ts','')} {r.get('state',''):9} {r.get('model',''):32} {r.get('duration','') or '':>3} ${r.get('usd',0):.2f} {r.get('slug','')} {r.get('reconcile','')}")
        print(f"rows {len(rows)} | session(24h) ${s:.2f} | month ${m:.2f}"); return 0
    dry = "--dry" in sys.argv; retry = arg("retry", ""); explicit = arg("model")
    if "--faceless" in sys.argv:
        pf = arg("prompt-file"); out = arg("out"); secs = float(arg("seconds", 12))
        if not pf or not out: sys.exit("faceless mode needs --prompt-file= and --out=")
        prompt = "\n".join(l for l in pathlib.Path(pf).read_text(encoding="utf-8").splitlines() if not l.strip().startswith("#")).strip()
        still = arg("still")
        model = pick_model(secs, explicit or "seedance15")
        outp = pathlib.Path(out)
        return render(slug="kie-faceless", tdir=outp.parent, out=outp, result_json=outp.with_suffix(".json"), model=model,
                      prompt=prompt, still=still, need_s=secs, retry=retry, dry=dry, title=outp.stem)
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(pos) < 2: print(__doc__); return 6
    ad, i = pos[0], int(pos[1])
    shots = json.loads((HERE / "shots.json").read_text(encoding="utf-8"))
    shot = shots[ad][i - 1]
    still = arg("still") or shot.get("still")
    if not still or not pathlib.Path(still).is_file():
        print(f"bad input: --still=<png> required for a Cory shot (got {still})"); sys.exit(6)
    vo = HERE / ad / f"shot{i}_vo.mp3"
    need = math.ceil(ffprobe_dur(vo) + 0.5) if vo.is_file() else int(shot.get("duration", 12))
    model = pick_model(need, explicit or shot.get("kie_model"))
    prompt = build_motion_prompt(shot)
    out = HERE / ad / f"shot{i}_cinematic.mp4"
    return render(slug=ad, tdir=HERE / ad, out=out, result_json=HERE / ad / f"shot{i}_result.json", model=model, prompt=prompt,
                  still=still, need_s=need, retry=retry, dry=dry, title=f"{ad} s{i} (kie {model})")

if __name__ == "__main__":
    sys.exit(main() or 0)
