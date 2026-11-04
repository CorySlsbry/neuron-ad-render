"""sync_drift.py - is the synced clip's audio the VO, in place? Two independent measures per shot:
  1. word-start drift: whisper word times in the VO vs the clip's audio (SequenceMatcher-paired). Repeated words
     ("what" x3) pair the wrong instance and fake 0.3-0.7s spikes, so max drift alone cannot fail a clip.
  2. envelope correlation: 100 Hz RMS envelopes cross-correlated within +/-1 s. r >= 0.95 at |lag| <= 40 ms proves
     the track IS the VO, in place (the 2026-08-28 law: durations -> spike signature -> envelope -> pixels).
Verdict CLEAN = max word drift <= 0.12 s OR envelope passes. Usage:
  python sync_drift.py <ad> [shots...] [--clip=<mp4>] [--vo=<mp3>]   (defaults: <ad>/shot<N>_blend.mp4 vs shot<N>_vo.mp3)
Exit 0 = every shot CLEAN, 1 = a shot is DESYNC."""
import sys, pathlib, subprocess, difflib, array, math
ad = sys.argv[1]
shots = [int(x) for x in sys.argv[2:] if x.isdigit()] or [1]
clip_arg = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--clip=")), None)
vo_arg = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--vo=")), None)
d = pathlib.Path(ad)
SCRATCH = pathlib.Path(r"C:\Users\you\AppData\Local\Temp\claude\C--Users-Cory-Downloads\d2b24766-2a78-4174-8123-67fab27201f8\scratchpad")
SCRATCH.mkdir(parents=True, exist_ok=True)

def pcm(src, rate=8000):
    out = SCRATCH / (pathlib.Path(src).stem + f"_{rate}.pcm")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
                    "-f", "s16le", str(out)], check=True)
    a = array.array("h"); a.frombytes(out.read_bytes()); return a

def envelope(samples, rate=8000, hz=100):
    w = rate // hz; n = len(samples) // w
    return [math.sqrt(sum(float(samples[i*w+j])**2 for j in range(w)) / w) for i in range(n)]

def xcorr(a, b, max_lag):
    def corr(x, y):
        n = min(len(x), len(y)); x, y = x[:n], y[:n]
        mx, my = sum(x)/n, sum(y)/n
        sx = math.sqrt(sum((v-mx)**2 for v in x)); sy = math.sqrt(sum((v-my)**2 for v in y))
        return sum((x[i]-mx)*(y[i]-my) for i in range(n)) / (sx*sy) if sx and sy else 0.0
    best, lag_best = -2.0, 0
    for lag in range(-max_lag, max_lag+1):
        r = corr(a[max(0, lag):], b[max(0, -lag):])
        if r > best: best, lag_best = r, lag
    return best, lag_best

def words(p, m):
    segs, _ = m.transcribe(str(p), word_timestamps=True, vad_filter=True)
    return [{"w": w.word.strip().lower().strip(".,!?'"), "s": round(w.start, 2)} for s in segs for w in (s.words or [])]

from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
fail = 0
for n in shots:
    clip = pathlib.Path(clip_arg) if clip_arg else d / f"shot{n}_blend.mp4"
    vo = pathlib.Path(vo_arg) if vo_arg else d / f"shot{n}_vo.mp3"
    a, b = words(vo, m), words(clip, m)
    sm = difflib.SequenceMatcher(a=[x["w"] for x in a], b=[x["w"] for x in b], autojunk=False)
    diffs = [abs(a[i1+k]["s"] - b[j1+k]["s"]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag == "equal" for k in range(i2-i1)]
    mx = max(diffs) if diffs else 9.9
    r, lag = xcorr(envelope(pcm(vo)), envelope(pcm(clip)), max_lag=100)   # 100 x 10 ms = +/-1 s
    env_ok = r >= 0.95 and abs(lag) * 10 <= 40
    verdict = "CLEAN" if (mx <= 0.12 or env_ok) else "DESYNC"
    fail += verdict == "DESYNC"
    print(f"shot{n}: {len(diffs)}/{len(a)} words matched | max drift {mx:.3f}s | ENVELOPE r={r:.3f} @ {lag*10:+d}ms -> {verdict}")
sys.exit(1 if fail else 0)
