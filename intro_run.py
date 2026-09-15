#!/usr/bin/env python3
"""intro_run.py - the full sre-intro rail: gated blend VOs -> clipwords -> A-look renders
(wallet-aware) -> lipsync (trim past the window) -> drift gate -> assemble the ~80s master
AND the shots 1+4+6 social trim. Idempotent end to end: safe to re-run after any interrupt."""
import sys, json, time, shutil, subprocess, pathlib, urllib.request
sys.path.insert(0, r"C:\Users\Cory\.neuron-vault")
from secrets_vault import get
HERE = pathlib.Path(__file__).resolve().parent
AD = "sre-intro"; D = HERE / AD
LOOK = "3251701b3e1bf0ba5550dc958b8e6430"          # CORY-neutral-A
NUDGES = [("personas/cory-neutral-B.png", "Cory neutral-B (fully neutral)")]
H = {"x-api-key": get("HEYGEN_API_KEY"), "Accept": "application/json"}

def wallet():
    req = urllib.request.Request("https://api.heygen.com/v3/users/me", headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        return float(json.loads(r.read().decode())["data"]["wallet"]["remaining_balance"])

def run(args, tag):
    r = subprocess.run([sys.executable, "-u"] + args, capture_output=True, text=True, cwd=HERE)
    out = r.stdout + r.stderr
    (HERE / f"intro_{tag}.log").write_text(out, encoding="utf-8")
    return out

def ensure_afford():
    for _ in range(40):
        w = wallet()
        if w >= 7.0:
            return w
        if 5.0 <= w < 7.0 and NUDGES:
            still, name = NUDGES.pop(0)
            print(f"wallet {w:.2f} dead zone -> $1 nudge look: {name}", flush=True)
            run(["make_avatar.py", still, name], "nudge")
        else:
            print(f"wallet {w:.2f} - waiting for auto-reload", flush=True)
            time.sleep(30)
    raise SystemExit("wallet stalled")

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip())

# ---- 1) VOs (gated) + clipwords -------------------------------------------------
from faster_whisper import WhisperModel
wm = None
for i in (1, 2, 3, 4, 5, 6):
    vo = D / f"shot{i}_vo.mp3"
    if not vo.is_file():
        print(f"== VO shot {i}", flush=True)
        out = run(["make_vo.py", AD, str(i), "--takes=4"], f"vo_s{i}")
        if not vo.is_file():
            print(out[-600:], flush=True); raise SystemExit(f"VO s{i} failed the gate")
    cw = D / f"shot{i}_clipwords.json"
    if not cw.is_file():
        wm = wm or WhisperModel("small", device="cpu", compute_type="int8")
        segs, _ = wm.transcribe(str(vo), word_timestamps=True, vad_filter=True)
        words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)}
                 for s in segs for w in (s.words or [])]
        cw.write_text(json.dumps(words, indent=0))
        print(f"== clipwords shot {i}: {len(words)} words, VO {dur(vo):.2f}s", flush=True)

# ---- 2) render + sync -----------------------------------------------------------
for i in (1, 2, 3, 4, 5, 6):
    blend = D / f"shot{i}_blend.mp4"
    if blend.is_file() and blend.stat().st_mtime > (D / f"shot{i}_vo.mp3").stat().st_mtime:
        print(f"== shot {i} already synced, skipping", flush=True); continue
    clip, vo = D / f"shot{i}_cinematic.mp4", D / f"shot{i}_vo.mp3"
    # resume on the CINEMATIC, not just the blend (2026-08-28): a completed re-render was
    # thrown away because this loop only skipped when the blend existed, and the plain
    # resubmit re-attached to a zombie job under the original idempotency key.
    if clip.is_file() and time.time() - clip.stat().st_mtime < 12 * 3600:
        print(f"== shot {i}: fresh cinematic on disk, skipping render", flush=True)
    else:
        w = ensure_afford()
        print(f"== shot {i}: render (wallet {w:.2f})", flush=True)
        out = run(["render_shot.py", AD, str(i), f"--look={LOOK}"], f"s{i}_render")
        if "DOWNLOADED" not in out:
            print(out[-500:], flush=True); raise SystemExit(f"s{i} render failed")
    gap = (dur(clip) - dur(vo)) / dur(clip)
    trim = ["--trim"] if (gap > 0.14 or dur(vo) > dur(clip) - 0.4) else []
    print(f"== shot {i}: lipsync (gap {gap:.1%}{' -> trim' if trim else ''})", flush=True)
    out = run(["lipsync_shot.py", AD, str(i), "precision"] + trim, f"s{i}_sync")
    if "DOWNLOADED" not in out:
        print(out[-500:], flush=True); raise SystemExit(f"s{i} lipsync failed")
    blend.write_bytes((D / f"shot{i}_synced_precision.mp4").read_bytes())
    print(f"== shot {i}: done (wallet {wallet():.2f})", flush=True)

# ---- 3) drift signature gate ----------------------------------------------------
print("== drift verification", flush=True)
import difflib
wm = wm or WhisperModel("small", device="cpu", compute_type="int8")
def words_of(p):
    segs, _ = wm.transcribe(str(p), word_timestamps=True, vad_filter=True)
    return [{"w": w.word.strip().lower().strip(".,!?'"), "s": round(w.start, 2)}
            for s in segs for w in (s.words or [])]
for i in (1, 2, 3, 4, 5, 6):
    wav = D / f"shot{i}_check.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(D / f"shot{i}_blend.mp4"),
                    "-map", "0:a:0", "-ac", "1", "-ar", "44100", str(wav)], check=True)
    a, b = words_of(D / f"shot{i}_vo.mp3"), words_of(wav)
    sm = difflib.SequenceMatcher(a=[x["w"] for x in a], b=[x["w"] for x in b], autojunk=False)
    dd = [(a[i1 + k]["w"], abs(a[i1 + k]["s"] - b[j1 + k]["s"]))
          for t, i1, i2, j1, j2 in sm.get_opcodes() if t == "equal" for k in range(i2 - i1)]
    spikes = [f"{w}:{v:.2f}" for w, v in dd if v > 0.15]
    vd, rd = dur(D / f"shot{i}_vo.mp3"), dur(wav)
    sig = "JITTER-OK" if abs(vd - rd) < 0.35 and len(spikes) <= 2 else ("CLEAN" if not spikes else "DESYNC?")
    if not dd: sig = "NO-MATCH!"
    print(f"s{i}: {len(dd)}/{len(a)} words, spikes {spikes or 'none'}, dur {vd:.2f}/{rd:.2f} -> {sig}", flush=True)
    wav.unlink(missing_ok=True)

# ---- 4) assemble master + social trim -------------------------------------------
out = run(["assemble.py", AD, "--clips=blend", "--words=clip"], "assemble_master")
print([l for l in out.splitlines() if l.startswith("FINAL")][-1], flush=True)

SOC = HERE / "sre-intro-social"; SOC.mkdir(exist_ok=True)
for n, src in enumerate((1, 4, 6), 1):
    for suffix in ("blend.mp4", "vo.mp3", "clipwords.json"):
        shutil.copy2(D / f"shot{src}_{suffix}", SOC / f"shot{n}_{suffix}")
shots = json.loads((HERE / "shots.json").read_text(encoding="utf-8"))
shots["sre-intro-social"] = [shots[AD][0], shots[AD][3], shots[AD][5]]
(HERE / "shots.json").write_text(json.dumps(shots, indent=1), encoding="utf-8")
out = run(["assemble.py", "sre-intro-social", "--clips=blend", "--words=clip"], "assemble_social")
print([l for l in out.splitlines() if l.startswith("FINAL")][-1], flush=True)

# ---- 5) QA sheets ---------------------------------------------------------------
for adx, secs, grid in ((AD, 80, "4x3"), ("sre-intro-social", 42, "3x2")):
    f = HERE / adx / f"{adx}_neuron_ad_v1.mp4"
    n = int(grid[0]) * int(grid[2])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f),
                    "-vf", f"select='not(mod(n\\,floor({secs}*30/{n})))',scale=270:-1,tile={grid}",
                    "-frames:v", "1", str(HERE / adx / "qa_sheet.png")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-3", "-i", str(f),
                    "-vf", "fps=2,scale=270:-1,tile=6x1", "-frames:v", "1",
                    str(HERE / adx / "qa_tail.png")], check=True)
print("ALL DONE  wallet:", wallet(), flush=True)
