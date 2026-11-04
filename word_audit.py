#!/usr/bin/env python3
"""word_audit.py - ADVISORY listening aid. ⚠ NOT A GATE - it FAILED its own regression test.

It could not catch the real case: "scredshit" scores 0.70 string-similarity against "spreadsheet",
above any threshold that does not also flag every normal word. Detecting a mispronunciation needs
PHONETIC distance (metaphone), and no phonetic library is installed on this box. Until one is:
  PREVENTION is the gate -> the LANDMINE list in the script validator (avoid sheet-words etc).
  A HUMAN EAR is the gate -> Cory caught this; whisper AND Gemini both normalised it away.
What this tool IS good for: printing what each script word sounds like IN ISOLATION, which is the
one technique that did expose the truth once we knew where to look.


Why this exists (Cory 2026-08-22): Seedance said "scredshit" for "spreadsheet" and BOTH whisper and
Gemini transcribed the full sentence as "...No spreadsheet, no guessing" - an ASR with context
normalizes a mangled word back to the word it expects. Cory heard it in the finished ad.

⛔ The load-bearing detail (a first version of this file got it wrong and passed the known-bad take):
compare the audio against the **SCRIPT** word, never against the transcript. The transcript is the
thing that is already wrong. So: align transcript -> script, take each SCRIPT word's aligned time
span, cut THAT span out, transcribe it alone, and ask "does this sound like what we wrote?"

Usage: python word_audit.py <ad> [shot ...] [--src=sts|native] [--min-len=5] [--thresh=0.6]
Exit 1 if any word is suspect (a flagged word is a reroll, not a debate).
"""
import sys, json, re, pathlib, subprocess, difflib
from faster_whisper import WhisperModel

STOP = {"about","after","again","alone","already","always","another","before","being","below","between",
        "could","every","first","going","might","never","other","right","shall","since","their","there",
        "these","thing","think","those","through","under","until","where","which","while","would"}
HERE = pathlib.Path(__file__).resolve().parent
ad = sys.argv[1]
shots = [int(a) for a in sys.argv[2:] if a.isdigit()] or [1, 2, 3]
src_kind = next((a.split("=")[1] for a in sys.argv if a.startswith("--src=")), "sts")
MIN_LEN = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--min-len=")), "5"))
THRESH = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--thresh=")), "0.6"))
d = HERE/ad; qa = d/"qa"; qa.mkdir(exist_ok=True)
SHOTS = json.loads((HERE/"shots.json").read_text(encoding="utf-8"))[ad]
model = WhisperModel("small", device="cpu", compute_type="int8")
# ASR writes numerals; the script writes words. Not a mispronunciation - normalise both ways.
NUMWORD = {"zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7",
           "eight":"8","nine":"9","ten":"10","eleven":"11","twelve":"12","thirty":"30","forty":"40"}
def norm(s):
    t = re.sub(r"[^a-z0-9']", "", s.lower())
    return NUMWORD.get(t, t)
sim = lambda a, b: difflib.SequenceMatcher(a=a, b=b).ratio()

bad_total = 0
for n in shots:
    wf = d/f"shot{n}_clipwords.json"
    audio = d/(f"shot{n}_sts.mp3" if src_kind == "sts" else f"shot{n}_native.wav")
    if not (wf.exists() and audio.exists()):
        print(f"shot{n}: missing {wf.name if not wf.exists() else audio.name}"); continue
    heard_words = json.loads(wf.read_text())
    script = [w for w in re.findall(r"[A-Za-z']+", SHOTS[n-1]["dialogue"])]
    a = [norm(w["w"]) for w in heard_words]; b = [norm(w) for w in script]
    # map each SCRIPT word -> the time span of the transcript word(s) aligned to it
    spans = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal" or (tag == "replace" and (i2 - i1) == (j2 - j1)):
            for k in range(i2 - i1): spans[j1 + k] = (heard_words[i1 + k]["s"], heard_words[i1 + k]["e"])
        elif tag == "replace":  # unequal swap: the whole heard span covers the whole script run
            s0, e0 = heard_words[i1]["s"], heard_words[i2 - 1]["e"]
            for j in range(j1, j2): spans[j] = (s0, e0)
    flagged = []; checked = 0
    for j, tok in enumerate(script):
        t = norm(tok)
        if len(t) < MIN_LEN or t in STOP: continue
        checked += 1
        if j not in spans:
            # ⛔ A script word the transcript could not align to is the MOST suspect word, not a
            # skippable one - that is precisely what a mangled pronunciation looks like. (The first
            # version of this gate skipped these and passed the take Cory caught by ear.)
            flagged.append((tok, "<no aligned audio - transcript never produced this word>", 0.0,
                            spans.get(j - 1, (0.0, 0.0))[1]))
            continue
        s, e = spans[j]; s = max(0.0, s - 0.12); e = e + 0.12
        clip = qa/f"_wa_{n}.wav"
        subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{s:.2f}","-to",f"{e:.2f}","-i",str(audio),
                        "-ar","16000","-ac","1",str(clip)], check=True)
        segs, _ = model.transcribe(str(clip), vad_filter=False, beam_size=5)
        hd = " ".join(x.text for x in segs).strip().strip(".,!?").lower()
        score = max([sim(t, norm(hd))] + [sim(t, norm(p)) for p in hd.split()] or [0])
        if score < THRESH: flagged.append((tok, hd, round(score, 2), s))
    if flagged:
        bad_total += len(flagged)
        print(f"shot{n}: {len(flagged)} SUSPECT of {checked} script words checked")
        for tok, hd, score, t in flagged:
            print(f"   [!] {t:5.2f}s  script '{tok}'  ->  isolated audio sounds like '{hd}'  (match {score})")
    else:
        print(f"shot{n}: clean ({checked} script words isolated and verified)")
try: (qa/f"_wa_{shots[-1]}.wav").unlink()
except Exception: pass
print(f"\n{'FAIL - reroll the flagged shot(s)' if bad_total else 'PASS - every script word verified in isolation'}")
sys.exit(1 if bad_total else 0)
