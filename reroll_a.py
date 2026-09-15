#!/usr/bin/env python3
"""reroll_a.py - re-render both guide reels' 6 shots on the CORY-neutral-A look, reusing the
gated VOs, with wallet-aware sequencing (dead-zone $5-7 nudged by $1 look registrations of the
B/C option photos - useful backups, the render_with_wallet pattern). Then lipsync each (trim
when the gap beats the 15% window), signature-verify drift, and assemble both reels."""
import sys, json, time, subprocess, pathlib, urllib.request
sys.path.insert(0, r"C:\Users\Cory\.neuron-vault")
from secrets_vault import get
HERE = pathlib.Path(__file__).resolve().parent
LOOK = "3251701b3e1bf0ba5550dc958b8e6430"          # CORY-neutral-A
NUDGES = [("personas/cory-neutral-C.png", "Cory neutral-C (lips parted)"),
          ("personas/cory-neutral-B.png", "Cory neutral-B (fully neutral)")]
H = {"x-api-key": get("HEYGEN_API_KEY"), "Accept": "application/json"}

def wallet():
    req = urllib.request.Request("https://api.heygen.com/v3/users/me", headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        return float(json.loads(r.read().decode())["data"]["wallet"]["remaining_balance"])

def run(args, tag):
    r = subprocess.run([sys.executable, "-u"] + args, capture_output=True, text=True, cwd=HERE)
    out = r.stdout + r.stderr
    (HERE / f"reroll_{tag}.log").write_text(out, encoding="utf-8")
    return out

def ensure_afford():
    for _ in range(40):                             # up to ~20 min of waiting on a reload
        w = wallet()
        if w >= 7.0:
            return w
        if 5.0 <= w < 7.0 and NUDGES:
            still, name = NUDGES.pop(0)
            print(f"wallet {w:.2f} in dead zone -> $1 nudge look: {name}", flush=True)
            out = run(["make_avatar.py", still, name], "nudge")
            print("  " + "".join(l for l in out.splitlines(True) if l.startswith(("LOOK_ID", "WALLET"))), flush=True)
        else:
            print(f"wallet {w:.2f} - waiting for auto-reload", flush=True)
            time.sleep(30)
    raise SystemExit("wallet never recovered - stalled")

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip())

results = {}
for ad in ("sre-seller", "sre-buyer"):
    for i in (1, 2, 3):
        w = ensure_afford()
        print(f"== {ad} s{i}: render (wallet {w:.2f})", flush=True)
        out = run(["render_shot.py", ad, str(i), f"--look={LOOK}"], f"{ad}_s{i}_render")
        if "DOWNLOADED" not in out:
            print(out[-500:], flush=True); raise SystemExit(f"{ad} s{i} render failed")
        clip, vo = HERE / ad / f"shot{i}_cinematic.mp4", HERE / ad / f"shot{i}_vo.mp3"
        gap = (dur(clip) - dur(vo)) / dur(clip)
        trim = ["--trim"] if gap > 0.14 else []
        print(f"== {ad} s{i}: lipsync (gap {gap:.1%}{' -> trim' if trim else ''})", flush=True)
        out = run(["lipsync_shot.py", ad, str(i), "precision"] + trim, f"{ad}_s{i}_sync")
        if "DOWNLOADED" not in out:
            print(out[-500:], flush=True); raise SystemExit(f"{ad} s{i} lipsync failed")
        # lipsync_shot writes shotN_synced_precision.mp4; assemble --clips=blend reads shotN_blend.mp4
        sp = HERE / ad / f"shot{i}_synced_precision.mp4"
        (HERE / ad / f"shot{i}_blend.mp4").write_bytes(sp.read_bytes())
        results[f"{ad}-s{i}"] = "ok"
        print(f"== {ad} s{i}: done (wallet {wallet():.2f})", flush=True)

# drift signature gate on all 6
print("== drift verification", flush=True)
import difflib
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
def words(p):
    segs, _ = m.transcribe(str(p), word_timestamps=True, vad_filter=True)
    return [{"w": w.word.strip().lower().strip(".,!?'"), "s": round(w.start, 2)}
            for s in segs for w in (s.words or [])]
for ad in ("sre-seller", "sre-buyer"):
    for i in (1, 2, 3):
        wav = HERE / ad / f"shot{i}_check.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(HERE / ad / f"shot{i}_blend.mp4"),
                        "-map", "0:a:0", "-ac", "1", "-ar", "44100", str(wav)], check=True)
        a, b = words(HERE / ad / f"shot{i}_vo.mp3"), words(wav)
        sm = difflib.SequenceMatcher(a=[x["w"] for x in a], b=[x["w"] for x in b], autojunk=False)
        dd = [(a[i1 + k]["w"], abs(a[i1 + k]["s"] - b[j1 + k]["s"]))
              for t, i1, i2, j1, j2 in sm.get_opcodes() if t == "equal" for k in range(i2 - i1)]
        drifts = [x[1] for x in dd]
        spikes = [f"{w}:{v:.2f}" for w, v in dd if v > 0.15]
        vd, rd = dur(HERE / ad / f"shot{i}_vo.mp3"), dur(wav)
        sig = "JITTER-OK" if abs(vd - rd) < 0.35 and len(spikes) <= 2 else ("CLEAN" if not spikes else "DESYNC?")
        if not drifts: sig = "NO-MATCH!"
        print(f"{ad} s{i}: {len(dd)}/{len(a)} words, max {max(drifts) if drifts else -1:.2f}s, "
              f"spikes {spikes or 'none'}, dur {vd:.2f}/{rd:.2f} -> {sig}", flush=True)
        wav.unlink(missing_ok=True)

# assemble both
for ad in ("sre-seller", "sre-buyer"):
    out = run(["assemble.py", ad, "--clips=blend", "--words=clip"], f"{ad}_assemble")
    fin = [l for l in out.splitlines() if l.startswith("FINAL")]
    print(fin[-1] if fin else out[-300:], flush=True)
    f = HERE / ad / f"{ad}_neuron_ad_v1.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f),
                    "-vf", "select='not(mod(n\\,floor(36*30/9)))',scale=270:-1,tile=3x3",
                    "-frames:v", "1", str(HERE / ad / "qa_sheet_v2.png")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-3", "-i", str(f),
                    "-vf", "fps=2,scale=270:-1,tile=6x1", "-frames:v", "1",
                    str(HERE / ad / "qa_tail_v2.png")], check=True)
print("ALL DONE  wallet:", wallet(), flush=True)
