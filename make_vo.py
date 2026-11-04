#!/usr/bin/env python3
"""make_vo.py - THE BLEND for one shot's VO, with the isolated-word gate built in.
Usage: python make_vo.py <ad_key> <shot_idx> [--takes=3] [--style=0.35] [--stab=0.5]
Flow: shots.json dialogue -> Gemini "Charon" TTS (gemini-3.1-flash-tts-preview) -> ElevenLabs
Speech-to-Speech into Cory's clone (REDACTED_ID) -> gate: full-sentence match PLUS
isolated per-word cuts (a +/-0.15s span transcribed ALONE - full-sentence ASR normalizes
mispronunciations like "spreadshit"->"spreadsheet"; only the isolated cut exposes them).
First take that passes the gate wins -> shotN_vo.mp3. Non-deterministic, so N takes.
"""
import sys, json, base64, struct, pathlib, subprocess, urllib.request, uuid, re, difflib
HERE = pathlib.Path(__file__).resolve().parent
def env_val(path, key):
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith(key + "="): return s.split("=", 1)[1].strip().strip('"').strip("'")
# keys come from the encrypted neuron vault (2026-09-15: the legacy Content Engine\.env no longer exists)
sys.path.insert(0, r"C:\Users\you\.neuron-vault")
from secrets_vault import get as _vault_get
GEM_KEY, EL_KEY = _vault_get("GEMINI_API_KEY"), _vault_get("ELEVENLABS_API_KEY")
if not GEM_KEY or not EL_KEY:
    sys.exit("make_vo: GEMINI_API_KEY / ELEVENLABS_API_KEY missing from the vault (vault_cli.py set NAME)")
CLONE = "REDACTED_ID"

ad, idx = sys.argv[1], int(sys.argv[2])
takes = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--takes=")), "3"))
style = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--style=")), "0.35"))
stab = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--stab=")), "0.5"))
script = json.loads((HERE/"shots.json").read_text(encoding="utf-8"))[ad][idx-1]["dialogue"]
d = HERE/ad; d.mkdir(exist_ok=True)

def norm(w): return re.sub(r"[^a-z']", "", w.lower())
STOP = {"a","an","the","in","on","of","to","it","and","or","you","your","my","is","for","with","before"}

def gemini_tts(text, dest_wav):
    body = {"contents": [{"parts": [{"text": "Read this calmly and warmly, like a trusted friend explaining something, natural conversational pace: " + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Charon"}}}}}
    # model fallback chain (2026-08-27): the preview TTS models carry separate daily quotas.
    # 3.1-flash exhausted mid-run -> fall through to the 2.5 buckets (Charon exists on all;
    # the original blend recipe was validated on 2.5-era Charon, and the STS + word gate
    # judge the OUTPUT, so the source model may vary).
    TTS_MODELS = ["gemini-3.1-flash-tts-preview", "gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts"]
    model = TTS_MODELS[getattr(gemini_tts, "_mi", 0)]
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"x-goog-api-key": GEM_KEY, "Content-Type": "application/json"})
    # 429 backoff (2026-08-27): the preview TTS model rate-limits after bursts of takes.
    # Honor the error's retryDelay when present, else exponential 30/60/120/240s.
    import time as _t
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                j = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and getattr(gemini_tts, "_mi", 0) + 1 < len(TTS_MODELS):
                gemini_tts._mi = getattr(gemini_tts, "_mi", 0) + 1
                print(f"  quota exhausted on {model} - falling back to {TTS_MODELS[gemini_tts._mi]}", flush=True)
                return gemini_tts(text, dest_wav)
            if e.code != 429 or attempt == 4:
                raise
            body = e.read().decode(errors="ignore")
            m = re.search(r'"retryDelay"\s*:\s*"(\d+)', body)
            delay = int(m.group(1)) if m else 30 * (2 ** attempt)
            print(f"  gemini 429 - waiting {delay}s (attempt {attempt + 1}/5)", flush=True)
            _t.sleep(min(delay, 300))
    part = j["candidates"][0]["content"]["parts"][0]["inlineData"]
    pcm = base64.b64decode(part["data"])                     # 24kHz s16le mono
    with open(dest_wav, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36+len(pcm)) + b"WAVEfmt " +
                struct.pack("<IHHIIHH", 16, 1, 1, 24000, 48000, 2, 16) +
                b"data" + struct.pack("<I", len(pcm)) + pcm)

def sts(src_wav, dest_mp3):
    boundary = "----neuron" + uuid.uuid4().hex
    def part(name, value, filename=None, ctype=None):
        h = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"' + (f'; filename="{filename}"' if filename else "") + "\r\n"
        if ctype: h += f"Content-Type: {ctype}\r\n"
        return h.encode() + b"\r\n" + (value if isinstance(value, bytes) else str(value).encode()) + b"\r\n"
    body = (part("audio", src_wav.read_bytes(), src_wav.name, "audio/wav")
            + part("model_id", "eleven_multilingual_sts_v2")
            + part("voice_settings", json.dumps({"stability": stab, "similarity_boost": 0.85, "style": style, "use_speaker_boost": True}))
            + part("remove_background_noise", "true") + f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/speech-to-speech/{CLONE}?output_format=mp3_44100_128",
                                 data=body, method="POST",
                                 headers={"xi-api-key": EL_KEY, "Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=300) as r:
        dest_mp3.write_bytes(r.read())

from faster_whisper import WhisperModel
MODEL = WhisperModel("small", device="cpu", compute_type="int8")

def gate(mp3):
    """Full-sentence match + isolated cuts on content words. Returns (ok, report)."""
    segs, _ = MODEL.transcribe(str(mp3), word_timestamps=True, vad_filter=True)
    words = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in (s.words or [])]
    heard = [norm(w["w"]) for w in words]
    want = [norm(w) for w in script.split()]
    ratio = difflib.SequenceMatcher(a=want, b=heard, autojunk=False).ratio()
    if ratio < 0.92:
        return False, f"full-sentence mismatch ({ratio:.2f}): {' '.join(heard)}"
    hard = []
    for w in words:
        exp = norm(w["w"])
        if exp in STOP or len(exp) <= 3: continue
        cut = mp3.with_suffix(f".cut.wav")
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(mp3),"-ss",f"{max(0,w['s']-0.15):.2f}",
                        "-to",f"{w['e']+0.15:.2f}","-ac","1","-ar","16000",str(cut)], check=True)
        isegs, _ = MODEL.transcribe(str(cut), vad_filter=False)
        toks = [norm(t) for t in "".join(s.text for s in list(isegs)).split() if norm(t)]
        # the cut span often catches a neighboring word's onset, so judge the BEST token:
        # hard fail only when NO token in the cut is close to the expected word (the
        # spreadshit class); empty/fragment reads are cut-boundary noise, not mispronunciation
        if toks:
            best = max(difflib.SequenceMatcher(a=exp, b=t).ratio() for t in toks)
            if best < 0.75:
                hard.append(f"{w['w']} -> heard {toks} at {w['s']:.2f}s")
        cut.unlink(missing_ok=True)
    return (not hard), ("; ".join(hard) if hard else f"clean (sentence {ratio:.2f})")

# brokerage / fair-housing gate BEFORE any synthesis spend (2026-09-15): a line that names the old
# brokerage or trips Fair Housing never becomes audio. re_compliance exit 3 = violation.
_gate = subprocess.run(["python", r"C:\Users\you\.claude\skills\geo-flywheel\references\engine\re_compliance.py",
                        "--kind", "video", "--text", script + " Cory Salisbury, Realtor, Simple Choice Real Estate. Equal Housing Opportunity."],
                       capture_output=True, text=True)
if _gate.returncode != 0:
    print("COMPLIANCE GATE FAILED for the dialogue:\n" + (_gate.stdout + _gate.stderr)[-600:]); sys.exit(3)
print("compliance gate: clean", flush=True)
for t in range(1, takes+1):
    wav = d/f"shot{idx}_charon_t{t}.wav"; mp3 = d/f"shot{idx}_vo_t{t}.mp3"
    gemini_tts(script, wav)
    sts(wav, mp3)
    ok, rep = gate(mp3)
    dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(mp3)],capture_output=True,text=True).stdout.strip())
    print(f"take {t}: {dur:.2f}s  {'PASS' if ok else 'FAIL'}  {rep}")
    if ok:
        final = d/f"shot{idx}_vo.mp3"
        final.write_bytes(mp3.read_bytes())
        print("VO:", final)
        sys.exit(0)
print("NO TAKE PASSED - regenerate with more takes or fix the script's landmine word"); sys.exit(2)
