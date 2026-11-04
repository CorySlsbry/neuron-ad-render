"""Submit the 3 shots of an ad with HeyGen wallet awareness: the wallet auto-reloads (+$30) only when
it dips BELOW $5, but a $7 shot is refused (402) at $5-$6.99. So after shot 2 we may sit at ~$6 and
stall. If that happens we make a SMALL USEFUL spend to cross the threshold (a P1 wardrobe look for the
coming med-spa ad, then a short speed lip-sync), wait for the reload, and submit shot 3."""
import sys, json, time, subprocess, urllib.request, pathlib, base64, hashlib
sys.path.insert(0, r"C:\Users\you\.neuron-vault")
from secrets_vault import get
H = {"x-api-key": get("HEYGEN_API_KEY"), "Accept": "application/json", "Content-Type": "application/json"}
ad = sys.argv[1]; HERE = pathlib.Path(__file__).resolve().parent
def call(method, url, data=None, headers=None):
    h = dict(H); h.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:300]
def wallet():
    s, d = call("GET", "https://api.heygen.com/v3/users/me"); return float(d["data"]["wallet"]["remaining_balance"]) if s == 200 else -1
def submit(n):
    r = subprocess.run([sys.executable, "-u", "render_shot.py", ad, str(n)], capture_output=True, text=True, cwd=HERE)
    out = (r.stdout + r.stderr); ok = "DOWNLOADED" in out
    pathlib.Path(HERE/f"{ad}_shot{n}.log").write_text(out, encoding="utf-8")
    return ok, out
print("wallet start:", wallet(), flush=True)
# shots 1 and 2 in parallel (each render_shot.py submits+polls+downloads)
procs = {n: subprocess.Popen([sys.executable, "-u", "render_shot.py", ad, str(n)], stdout=open(HERE/f"{ad}_shot{n}.log", "w"), stderr=subprocess.STDOUT, cwd=HERE) for n in (1, 2)}
time.sleep(45)   # both submissions (and their $7 charges) have happened by now
w = wallet(); print("wallet after S1+S2 submit:", w, flush=True)
if w < 7.0:
    print("wallet cannot cover shot 3 - making a small useful spend to trip the $5 auto-reload", flush=True)
    # (a) P1 wardrobe look for the med-spa ad: prompt avatar with the P1 hero as reference (~$1)
    ref = pathlib.Path(__file__).resolve().parent / "personas" / "P1-the-operator.png"
    s, d = call("POST", "https://api.heygen.com/v3/avatars",
                {"type": "prompt", "name": "Neuron P1 Operator - med spa wardrobe",
                 "prompt": "The same woman as the reference photo: early thirties, dark blonde hair loosely pinned up, now wearing a clean white collarless tunic top "
                           "(med-spa / aesthetics clinic front-of-house), small stud earrings, soft natural makeup, warm confident half-smile, bright clinic interior softly out of focus. "
                           "Head-and-shoulders portrait, 9:16, photoreal, no text or logos.",
                 "reference_images": [{"type": "base64", "data": base64.b64encode(ref.read_bytes()).decode(), "media_type": "image/jpeg"}],   # HeyGen wants media_type (not mime_type) - 400 otherwise
                 "aspect_ratio": "9:16"}, {"Idempotency-Key": "neuron-p1-medspa-look-" + hashlib.sha1(ref.read_bytes()).hexdigest()[:10]})
    print("P1 med-spa look:", s, json.dumps(d)[:300] if isinstance(d, dict) else d, flush=True)
    time.sleep(8); w = wallet(); print("wallet:", w, flush=True)
    # (b) short speed lip-syncs until we dip under $5 (each ~$0.0333/s); uses the auto S1 clip + its Hope STS audio (a real quality probe of speed mode)
    tries = 0
    while w >= 5.0 and tries < 4:
        tries += 1
        vid = HERE/"auto"/"shot1_sts.mp4"; aud = HERE/"auto"/"shot1_sts.mp3"
        # upload both as assets
        def upload(p, mime):
            import uuid
            b = "----neuron" + uuid.uuid4().hex
            body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{p.name}\"\r\nContent-Type: {mime}\r\n\r\n").encode() + p.read_bytes() + f"\r\n--{b}--\r\n".encode()
            req = urllib.request.Request("https://api.heygen.com/v3/assets", data=body, headers={"x-api-key": H["x-api-key"], "Content-Type": f"multipart/form-data; boundary={b}"}, method="POST")
            with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read().decode())["data"]["asset_id"]
        va, aa = upload(vid, "video/mp4"), upload(aud, "audio/mpeg")
        s, d = call("POST", "https://api.heygen.com/v3/lipsyncs", {"video": {"type": "asset_id", "asset_id": va}, "audio": {"type": "asset_id", "asset_id": aa}, "mode": "speed", "title": f"probe-speed-lipsync-{tries}"},
                    {"Idempotency-Key": f"neuron-probe-speed-{tries}-{int(time.time())}"})
        print("speed lipsync probe:", s, json.dumps(d)[:200] if isinstance(d, dict) else d, flush=True)
        time.sleep(10); w = wallet(); print("wallet:", w, flush=True)
    # wait for the reload
    t0 = time.time()
    while w < 7.0 and time.time() - t0 < 240:
        time.sleep(15); w = wallet(); print("waiting for auto-reload... wallet:", w, flush=True)
ok3, out3 = submit(3) if w >= 7.0 else (False, "SKIPPED: wallet still below $7")
print("shot3:", "DOWNLOADED" if ok3 else out3[-300:], flush=True)
for n, p in procs.items():
    p.wait(); print(f"shot{n} process exit {p.returncode}", flush=True)
print("wallet end:", wallet(), flush=True)
r = subprocess.run([sys.executable, "voicecheck.py", ad], capture_output=True, text=True, cwd=HERE); print(r.stdout[-1500:])