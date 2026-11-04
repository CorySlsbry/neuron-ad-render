#!/usr/bin/env python3
"""Voice consistency across the native-audio cinematic shots of one ad.
For each shotN_cinematic.mp4: transcript (did she say the script?), speaking span, and pitch
statistics (librosa.pyin f0 median / IQR) so three generations can be compared for the same voice.
Also writes shotN_clipwords.json (word timings of the clip's own audio) for karaoke captions.
Usage: python voicecheck.py <ad_key>"""
import sys, json, pathlib, subprocess, numpy as np, librosa
from faster_whisper import WhisperModel
HERE = pathlib.Path(__file__).resolve().parent
ad = sys.argv[1]; d = HERE/ad; qa = d/"qa"; qa.mkdir(exist_ok=True)
shots = json.loads((HERE/"shots.json").read_text(encoding="utf-8"))[ad]
m = WhisperModel("small", device="cpu", compute_type="int8")
rows = []
for i, sh in enumerate(shots, 1):
    mp4 = d/f"shot{i}_cinematic.mp4"
    if not mp4.exists(): print(f"shot{i}: (not rendered yet)"); continue
    wav = qa/f"shot{i}_audio.wav"
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(mp4),"-vn","-ac","1","-ar","16000",str(wav)],check=True)
    segs,_ = m.transcribe(str(wav), word_timestamps=True, vad_filter=False, beam_size=5)
    words = [{"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3)} for s in segs for w in (s.words or [])]
    (d/f"shot{i}_clipwords.json").write_text(json.dumps(words, indent=0))
    heard = " ".join(w["w"] for w in words)
    want = sh["dialogue"]
    norm = lambda t: "".join(c for c in t.lower() if c.isalnum() or c == " ").split()
    hw, ww = norm(heard), norm(want)
    match = sum(1 for a, b in zip(hw, ww) if a == b) / max(len(ww), 1)
    y, sr = librosa.load(str(wav), sr=16000)
    f0, vflag, _ = librosa.pyin(y, fmin=80, fmax=400, sr=sr, frame_length=1024)
    f0v = f0[~np.isnan(f0)]
    med = float(np.median(f0v)) if f0v.size else float("nan"); q1, q3 = (np.percentile(f0v, [25, 75]) if f0v.size else (np.nan, np.nan))
    span = (words[0]["s"], words[-1]["e"]) if words else (None, None)
    rows.append((i, len(words), match, span, med, q1, q3))
    print(f"shot{i}: words={len(words):2d} script-match={match:4.0%} span={span[0]}->{span[1]}s  f0 median={med:5.1f}Hz IQR={q1:5.1f}-{q3:5.1f}")
    print(f"   heard: {heard}")
if len(rows) >= 2:
    meds = [r[4] for r in rows]; print(f"\nPITCH SPREAD across shots: {max(meds)-min(meds):.1f} Hz (same speaker typically < ~15 Hz median drift)")
