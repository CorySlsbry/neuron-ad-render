#!/usr/bin/env python3
"""intro_partial.py - do everything that does NOT need shot 6's VO: render+sync shots 1-5,
render shot 6's clip. The scheduled full intro_run.py then only owes s6's VO+sync+assembly."""
import sys, json, time, subprocess, pathlib, urllib.request
sys.path.insert(0, r"C:\Users\you\.neuron-vault")
from secrets_vault import get
HERE = pathlib.Path(__file__).resolve().parent
AD = "sre-intro"; D = HERE / AD
LOOK = "3251701b3e1bf0ba5550dc958b8e6430"
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
        if w >= 7.0: return w
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

for i in (1, 2, 3, 4, 5, 6):
    clip = D / f"shot{i}_cinematic.mp4"
    if not clip.is_file() or clip.stat().st_mtime < time.time() - 6 * 3600:
        w = ensure_afford()
        print(f"== shot {i}: render (wallet {w:.2f})", flush=True)
        out = run(["render_shot.py", AD, str(i), f"--look={LOOK}"], f"s{i}_render")
        if "DOWNLOADED" not in out:
            print(out[-400:], flush=True); raise SystemExit(f"s{i} render failed")
    vo = D / f"shot{i}_vo.mp3"
    if not vo.is_file():
        print(f"== shot {i}: no VO yet (deferred to the post-reset run)", flush=True); continue
    blend = D / f"shot{i}_blend.mp4"
    if blend.is_file() and blend.stat().st_mtime > vo.stat().st_mtime:
        print(f"== shot {i}: already synced", flush=True); continue
    gap = (dur(clip) - dur(vo)) / dur(clip)
    trim = ["--trim"] if (gap > 0.14 or dur(vo) > dur(clip) - 0.4) else []
    print(f"== shot {i}: lipsync (gap {gap:.1%}{' -> fit' if trim else ''})", flush=True)
    out = run(["lipsync_shot.py", AD, str(i), "precision"] + trim, f"s{i}_sync")
    if "DOWNLOADED" not in out:
        print(out[-400:], flush=True); raise SystemExit(f"s{i} lipsync failed")
    blend.write_bytes((D / f"shot{i}_synced_precision.mp4").read_bytes())
    print(f"== shot {i}: synced (wallet {wallet():.2f})", flush=True)
print("PARTIAL DONE  wallet:", wallet(), flush=True)
