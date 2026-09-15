#!/usr/bin/env python3
"""sts_shot.py - keep Seedance's native (in-sync) performance, swap the VOICE.
Usage: python sts_shot.py <ad_key> <shot_idx> <elevenlabs_voice_id> [--style 0.35] [--stab 0.5]
Flow: extract the clip's audio -> ElevenLabs Speech-to-Speech into the chosen voice (timing-preserving,
the cory-voice "blend" trick) -> mux the new voice back onto the untouched video -> shotN_sts.mp4,
shotN_sts.mp3, shotN_clipwords.json (faster-whisper word timings of the NEW audio, for captions).
Why: HeyGen's lipsync pass drifted out of sync (Cory 2026-08-21, video 2); Seedance's own co-generated
speech is frame-accurate, and STS keeps every word at the same millisecond, so the lips stay right."""
import sys, json, pathlib, subprocess, urllib.request, uuid, re
sys.path.insert(0, r"C:\Users\Cory\.neuron-vault")
HERE = pathlib.Path(__file__).resolve().parent
def env_val(path, key):
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith(key + "="): return s.split("=", 1)[1].strip().strip('"').strip("'")
sys.path.insert(0, r"C:\Users\Cory\.neuron-vault"); from secrets_vault import get as _vault_get
EL_KEY = _vault_get("ELEVENLABS_API_KEY")   # encrypted vault (2026-09-15: the legacy Content Engine\.env is gone)
ad, idx, voice_id = sys.argv[1], int(sys.argv[2]), sys.argv[3]
style = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--style=")), "0.35"))
stab = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--stab=")), "0.5"))
d = HERE/ad
src = d/f"shot{idx}_cinematic.mp4"
wav = d/f"shot{idx}_native.wav"; out_mp3 = d/f"shot{idx}_sts.mp3"; out_mp4 = d/f"shot{idx}_sts.mp4"

def dur(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)],capture_output=True,text=True).stdout.strip())

# 1) native audio out
subprocess.run(["ffmpeg","-v","error","-y","-i",str(src),"-vn","-ac","1","-ar","44100","-c:a","pcm_s16le",str(wav)], check=True)
src_dur = dur(src); print(f"native audio {dur(wav):.2f}s from a {src_dur:.2f}s clip")

# 2) speech-to-speech (multipart)
boundary = "----neuron" + uuid.uuid4().hex
def part(name, value, filename=None, ctype=None):
    h = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"' + (f'; filename="{filename}"' if filename else "") + "\r\n"
    if ctype: h += f"Content-Type: {ctype}\r\n"
    return h.encode() + b"\r\n" + (value if isinstance(value, bytes) else str(value).encode()) + b"\r\n"
body = (part("audio", wav.read_bytes(), wav.name, "audio/wav") + part("model_id", "eleven_multilingual_sts_v2")
        + part("voice_settings", json.dumps({"stability": stab, "similarity_boost": 0.85, "style": style, "use_speaker_boost": True}))
        + part("remove_background_noise", "true") + f"--{boundary}--\r\n".encode())
req = urllib.request.Request(f"https://api.elevenlabs.io/v1/speech-to-speech/{voice_id}?output_format=mp3_44100_128", data=body, method="POST",
                             headers={"xi-api-key": EL_KEY, "Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "audio/mpeg"})
try:
    with urllib.request.urlopen(req, timeout=300) as r: out_mp3.write_bytes(r.read())
except urllib.error.HTTPError as e:
    print("STS FAILED", e.code, e.read().decode()[:400]); sys.exit(1)
sts_dur = dur(out_mp3); print(f"STS audio {sts_dur:.2f}s (delta vs native {sts_dur - dur(wav):+.2f}s)")

# 3) mux the new voice onto the untouched video (video stream copied, so frames are identical)
subprocess.run(["ffmpeg","-v","error","-y","-i",str(src),"-i",str(out_mp3),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
                "-af","apad","-shortest",str(out_mp4)], check=True)
print("muxed:", out_mp4, f"{dur(out_mp4):.2f}s")

# 4) word timings of the NEW audio -> shotN_clipwords.json (what assemble.py --words=clip reads)
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = model.transcribe(str(out_mp3), word_timestamps=True, vad_filter=True)
words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for s in segs for w in (s.words or [])]
(d/f"shot{idx}_clipwords.json").write_text(json.dumps(words, indent=0))
heard = " ".join(w["w"] for w in words)
shots = json.loads((HERE/"shots.json").read_text(encoding="utf-8"))[ad]
want = shots[idx-1]["dialogue"]
norm = lambda t: re.sub(r"[^a-z0-9' ]+", " ", t.lower()).split()
a, b = norm(heard), norm(want); match = sum(1 for w in a if w in set(b)) / max(1, len(b))
print(f"words={len(words)} span 0.0->{words[-1]['e'] if words else 0}s | script-match ~{match*100:.0f}% | heard: {heard}")
