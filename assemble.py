#!/usr/bin/env python3
"""Assemble one ad from its synced cinematic shots: trim to VO, karaoke captions (ASS/libass),
hard cuts, 3s end card, then the geo-flywheel audio post-pass (Neuron bed + -16 LUFS).

Usage: python assemble.py <ad_key> [--clips synced_precision|synced_speed|cinematic] [--no-audio-pass]

Caption spec (from the Townsquare teardown): heavy italic sans, ALL CAPS, white fill, thick black
outline + soft shadow, 2-3 words per chunk, the SPOKEN word turns orange (karaoke), centered at
~47% of frame height (under the chin, above the platform UI). Word timings come from
shotN_words.json (faster-whisper on the actual VO), so the highlight follows the voice.
"""
import sys, json, re, pathlib, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = pathlib.Path(r"C:\Users\you\.claude\skills\geo-flywheel\references\engine")
W, H, FPS = 1080, 1920, 30
XF = 0.5   # dissolve length from the last shot into the end card
FONT_CAP = r"C:\Windows\Fonts\seguibli.ttf"   # Segoe UI Black Italic - the heavy italic of the reference
FONT_CARD = r"C:\Windows\Fonts\seguibl.ttf"
ACCENT = "F28C28"   # reference orange (RRGGBB)
NEURON_BG = (12, 10, 20); NEURON_ACCENT = (124, 92, 255)
# Per-brand end card + audio lane. Neuron is the default for every ad not listed here.
BRANDS = {
  "_default":   {"lane": "neuron-hq",      "bg": NEURON_BG,     "accent": NEURON_ACCENT,  "l1": "SEE WHERE YOU", "l2": "SHOW UP.",
                 "sub": "It's free.", "url": "neuron-hq.com/free-ai-check", "wordmark": "NEURON HQ"},
  "autoadvisor": {"lane": "auto-advisor",  "bg": (10, 14, 22),  "accent": (77, 163, 255), "l1": "RUN THE BUSINESS.", "l2": "NOT THE PHONES.",
                 "sub": "Start with a free Service-Drive Audit.", "url": "autoadvisorpartners.com", "wordmark": "AUTO ADVISOR"},
  "tbos":       {"lane": "top-builder-ai", "bg": (10, 11, 15),  "accent": (16, 185, 129), "l1": "KNOW WHAT", "l2": "EVERY JOB MADE.",
                 "sub": "Start with the free job-profit report.", "url": "topbuilderai.com", "wordmark": "TOP BUILDER OS"},
  # ⛔ RE compliance (kw-realtor-engine): the card MUST show "Simple Choice Real Estate" (brokerage since
  # 2026-09-05; "KW Westfield" is BANNED by re_compliance.py) + "Equal Housing Opportunity" on screen.
  "salisburyre": {"lane": "salisburyre", "bg": (15, 15, 17), "accent": (206, 1, 31), "l1": "KNOW YOUR NUMBERS", "l2": "BEFORE YOU MOVE.",
                 "sub": "Free toolkit. No pitch.", "url": "salisburyre.com/tools",
                 "wordmark": "CORY SALISBURY, REALTOR - SIMPLE CHOICE REAL ESTATE | EQUAL HOUSING OPPORTUNITY"},
  "sre-seller": {"lane": "salisburyre", "bg": (15, 15, 17), "accent": (206, 1, 31), "l1": "KNOW WHAT YOU'D", "l2": "WALK AWAY WITH.",
                 "sub": "Free ten-page Seller's Guide.", "url": "salisburyre.com/sellers-guide", "wordmark": "CORY SALISBURY, REALTOR - SIMPLE CHOICE REAL ESTATE | EQUAL HOUSING OPPORTUNITY"},
  "sre-buyer":  {"lane": "salisburyre", "bg": (15, 15, 17), "accent": (206, 1, 31), "l1": "BUY THE PAYMENT", "l2": "YOU CAN LIVE WITH.",
                 "sub": "Free ten-page Buyer's Guide.", "url": "salisburyre.com/buyers-guide", "wordmark": "CORY SALISBURY, REALTOR - SIMPLE CHOICE REAL ESTATE | EQUAL HOUSING OPPORTUNITY"},
  "sre-intro":  {"lane": "salisburyre", "bg": (15, 15, 17), "accent": (206, 1, 31), "l1": "KNOW WHO IS", "l2": "IN YOUR CORNER.",
                 "sub": "Free call + free guides.", "url": "salisburyre.com", "wordmark": "CORY SALISBURY, REALTOR - SIMPLE CHOICE REAL ESTATE | EQUAL HOUSING OPPORTUNITY"},
  "sre-intro-social": {"lane": "salisburyre", "bg": (15, 15, 17), "accent": (206, 1, 31), "l1": "KNOW WHO IS", "l2": "IN YOUR CORNER.",
                 "sub": "Free call + free guides.", "url": "salisburyre.com", "wordmark": "CORY SALISBURY, REALTOR - SIMPLE CHOICE REAL ESTATE | EQUAL HOUSING OPPORTUNITY"},
  "sre-walk-ab": {"lane": "salisburyre", "bg": (15, 15, 17), "accent": (206, 1, 31), "l1": "KNOW YOUR NUMBERS", "l2": "BEFORE YOU MOVE.",
                 "sub": "Free toolkit. No pitch.", "url": "salisburyre.com/tools", "wordmark": "CORY SALISBURY, REALTOR - SIMPLE CHOICE REAL ESTATE | EQUAL HOUSING OPPORTUNITY"},
}

ad = sys.argv[1]
clip_kind = next((a.split("=")[1] for a in sys.argv if a.startswith("--clips=")), "synced_precision")
# --words=vo   -> shotN_words.json      (ElevenLabs VO timings; use with synced clips)
# --words=clip -> shotN_clipwords.json  (timings of the clip's OWN audio; use with native cinematic speech)
words_kind = next((a.split("=")[1] for a in sys.argv if a.startswith("--words=")), "vo")
WORDS_FILE = "shot{i}_words.json" if words_kind == "vo" else "shot{i}_clipwords.json"
audio_pass = "--no-audio-pass" not in sys.argv
d = HERE/ad; work = d/"build"; work.mkdir(exist_ok=True)
shots = json.loads((HERE/"shots.json").read_text(encoding="utf-8"))[ad]

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("CMD FAILED:", " ".join(str(c) for c in cmd)[:300]); print(r.stderr[-1500:]); sys.exit(1)
    return r

def probe_dur(p):
    return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)]).stdout.strip())

def ass_color(rrggbb, alpha="00"):  # ASS wants &HAABBGGRR
    r, g, b = rrggbb[0:2], rrggbb[2:4], rrggbb[4:6]
    return f"&H{alpha}{b}{g}{r}"

def chunk_words(words, gap=0.5):
    """2-3 words per chunk, never a 1-word orphan: split at sentence ends / long pauses, then
    balance each sentence into groups of 2-3 (7 words -> 3+2+2, never 3+3+1)."""
    sents, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i+1] if i+1 < len(words) else None
        if re.search(r"[.!?]$", w["w"]) or nxt is None or (nxt["s"] - w["e"]) > gap:
            sents.append(cur); cur = []
    chunks = []
    for s in sents:
        n = len(s)
        if n == 1 and chunks:            # lone word -> glue onto the previous chunk
            chunks[-1].append(s[0]); continue
        k = max(1, -(-n // 3))           # ceil(n/3) groups
        base, extra = divmod(n, k)       # sizes as even as possible, each 2..3
        sizes = [base + (1 if j < extra else 0) for j in range(k)]
        if n >= 2 and min(sizes) < 2:    # e.g. n=4 -> [2,2] not [3,1]
            k += 1; base, extra = divmod(n, k); sizes = [base + (1 if j < extra else 0) for j in range(k)]
        i = 0
        for sz in sizes:
            chunks.append(s[i:i+sz]); i += sz
    return chunks

def script_align(words, dialogue):
    """Keep whisper's TIMINGS but use the SCRIPT's spelling/punctuation for the caption text.
    Whisper writes homophones ('peaked' for 'peeked', 'Web-C types' for 'websites'); the script is the truth.
    Token-aligns the two sequences; unmatched whisper words keep their own text."""
    import difflib
    sw = dialogue.split()
    norm = lambda t: re.sub(r"[^a-z0-9']+", "", t.lower())
    a = [norm(w["w"]) for w in words]; b = [norm(t) for t in sw]
    out = [dict(w) for w in words]; drop = set(); extra = []   # extra = re-timed script words for unequal replaces
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and (i2 - i1) == (j2 - j1)):
            for k in range(i2 - i1): out[i1 + k]["w"] = sw[j1 + k]
        elif tag == "replace":
            # unequal swap ("no scratch hit" for "No spreadsheet", "AutoAdvisor" for "Auto Advisor"):
            # caption the SCRIPT words, spread over the whisper span proportionally to word length.
            s0, e0 = out[i1]["s"], out[i2 - 1]["e"]; span = max(0.12, e0 - s0)
            toks = sw[j1:j2]; tot = sum(len(t) for t in toks) or 1; t = s0
            for tok in toks:
                d = span * len(tok) / tot; extra.append({"w": tok, "s": round(t, 2), "e": round(t + d, 2)}); t += d
            for k in range(i1, i2): drop.add(k)
        elif tag == "delete":
            # whisper heard words the script does not have (a doubled "the one", a filler): never caption
            # them - fold their time into the previous kept word so the karaoke stays continuous.
            for k in range(i1, i2): drop.add(k)
            if i1 > 0: out[i1 - 1]["e"] = max(out[i1 - 1]["e"], out[i2 - 1]["e"])
    kept = [w for k, w in enumerate(out) if k not in drop] + extra
    return sorted(kept, key=lambda w: w["s"])

def load_words(i):
    w = json.loads((d/WORDS_FILE.format(i=i)).read_text())
    return script_align(w, shots[i-1]["dialogue"]) if shots[i-1].get("dialogue") else w

def fmt_t(t):
    t = max(0.0, t); h = int(t//3600); m = int(t%3600//60); s = t%60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass(words, offset, out_path, hold_tail=0.25):
    """One Dialogue event per (chunk, active-word): the chunk stays up, the spoken word is orange."""
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Segoe UI Black,100,{ass_color('FFFFFF')},{ass_color('FFFFFF')},{ass_color('000000')},{ass_color('000000','80')},-1,-1,0,0,100,100,1,0,1,9,4,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    chunks = chunk_words(words)
    for ci, ch in enumerate(chunks):
        ch_end = ch[-1]["e"] + (hold_tail if ci == len(chunks)-1 else 0.0)
        nxt_start = chunks[ci+1][0]["s"] if ci+1 < len(chunks) else None
        # the chunk stays up until the next chunk starts (no gap flicker), capped at +0.6s
        if nxt_start is not None: ch_end = min(nxt_start, ch[-1]["e"] + 0.6)
        for wi, w in enumerate(ch):
            start = w["s"] if wi > 0 else ch[0]["s"]
            end = ch[wi+1]["s"] if wi+1 < len(ch) else ch_end
            if end <= start: end = start + 0.08
            parts = []
            for wj, ww in enumerate(ch):
                txt = ww["w"].upper().replace("{", "").replace("}", "")
                parts.append((f"{{\\c{ass_color(ACCENT)}}}{txt}{{\\c{ass_color('FFFFFF')}}}") if wj == wi else txt)
            text = " ".join(parts)
            lines.append(f"Dialogue: 0,{fmt_t(start+offset)},{fmt_t(end+offset)},Cap,,0,0,0,,{{\\an5\\pos({W//2},{int(H*0.47)})}}{text}")
    out_path.write_text(hdr + "\n".join(lines) + "\n", encoding="utf-8")
    return len(chunks), len(lines)

# ---- 1) normalise + trim each shot to its VO (last word + 0.6s), collect offsets
norm, offsets, t = [], [], 0.0
for i in range(1, len(shots)+1):
    src = d/f"shot{i}_{clip_kind}.mp4"
    if not src.exists(): print("missing clip:", src); sys.exit(1)
    words = load_words(i)   # whisper timings + SCRIPT spelling (homophone-proof captions)
    # Cory 2026-08-21: never cut right on the last word. Internal cuts sit 0.5s after it (a breath),
    # the LAST shot holds 1.0s before the card. If the clip itself ends sooner, freeze its last frame.
    # The last shot holds 1.0s clean, THEN the 0.5s dissolve into the card begins (so the card is
    # fully in 1.5s after the last word) - the dissolve must not eat the hold.
    tail = (1.0 + XF) if i == len(shots) else 0.5
    want = words[-1]["e"] + tail
    have = probe_dur(src)
    dur = min(have, want); extend = max(0.0, want - have)
    out = work/f"n{i}.mp4"
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p"
    if extend > 0.02: vf += f",tpad=stop_mode=clone:stop_duration={extend:.3f}"
    run(["ffmpeg","-v","error","-y","-t",f"{dur:.3f}","-i",str(src),   # -t BEFORE -i: trim the input, let tpad extend the output
         "-map","0:v:0","-map","0:a:0","-sn",   # HeyGen lipsync outputs carry a mov_text subtitle stream; drop it
         "-vf",vf,
         "-c:v","libx264","-preset","medium","-crf","18","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
         "-af",f"apad=whole_dur={dur+extend:.3f}",str(out)])
    offsets.append(t); t += probe_dur(out); norm.append(out)
    print(f"shot{i}: {dur:.2f}s used" + (f" + {extend:.2f}s freeze" if extend > 0.02 else "") + f" (last word {words[-1]['e']:.2f}s, tail {tail}s)  cum {t:.2f}s")

# ---- 2) end card (3s): last frame of the final shot, darkened, with the CTA
last = work/"last.png"
run(["ffmpeg","-v","error","-y","-sseof","-0.1","-i",str(norm[-1]),"-frames:v","1",str(last)])
im = Image.open(last).convert("RGB").resize((W, H))
BR = BRANDS.get(ad, BRANDS["_default"])
plate = Image.new("RGB", (W, H), BR["bg"]); im = Image.blend(im, plate, 0.72)
dr = ImageDraw.Draw(im)
f1 = ImageFont.truetype(FONT_CAP, 124); f2 = ImageFont.truetype(FONT_CARD, 64); f3 = ImageFont.truetype(FONT_CARD, 44)
def center(txt, font, y, fill, outline=None):
    w = dr.textlength(txt, font=font); x = (W - w)/2
    if outline:
        for dx,dy in ((-3,0),(3,0),(0,-3),(0,3),(-3,-3),(3,3),(-3,3),(3,-3)): dr.text((x+dx,y+dy), txt, font=font, fill=outline)
    dr.text((x, y), txt, font=font, fill=fill)
def fit(txt, size, max_w=W-80):   # shrink long card lines (brand lines vary) so nothing clips the frame
    f = ImageFont.truetype(FONT_CAP, size)
    while dr.textlength(txt, font=f) > max_w and size > 60: size -= 4; f = ImageFont.truetype(FONT_CAP, size)
    return f
center(BR["l1"], fit(BR["l1"], 124), 640, (255,255,255), (0,0,0))
center(BR["l2"], fit(BR["l2"], 124), 780, BR["accent"], (0,0,0))
f2s = ImageFont.truetype(FONT_CARD, 64 if dr.textlength(BR["sub"], font=f2) <= W-80 else 50)
center(BR["sub"], f2s, 960, (255,255,255))
center(BR["url"], f2, 1060, (255,255,255))
# wordmark may be multi-part (" | " separated - RE needs brokerage attribution + EHO as their own lines)
wm_lines = [s.strip() for s in BR["wordmark"].split("|")]
wy = 1700 - (len(wm_lines) - 1) * 52
for wl in wm_lines:
    f3w = ImageFont.truetype(FONT_CARD, 44)
    while dr.textlength(wl, font=f3w) > W - 90 and f3w.size > 28:
        f3w = ImageFont.truetype(FONT_CARD, f3w.size - 2)
    center(wl, f3w, wy, (200, 200, 215)); wy += 52
card_png = work/"card.png"; im.save(card_png)
card = work/"card.mp4"
run(["ffmpeg","-v","error","-y","-loop","1","-t","3","-i",str(card_png),"-f","lavfi","-t","3","-i","anullsrc=r=48000:cl=stereo",
     "-vf",f"fps={FPS},format=yuv420p","-c:v","libx264","-preset","medium","-crf","18","-c:a","aac","-b:a","192k","-shortest",str(card)])

# ---- 3) captions file across the whole timeline
ass = work/"captions.ass"; total_chunks = total_events = 0
ass_txt = None
# build per-shot then merge events (same header)
merged_events = []
header = None
for i in range(1, len(shots)+1):
    words = load_words(i)   # whisper timings + SCRIPT spelling (homophone-proof captions)
    tmp = work/f"cap{i}.ass"; c, e = build_ass(words, offsets[i-1], tmp); total_chunks += c; total_events += e
    txt = tmp.read_text(encoding="utf-8")
    head, _, events = txt.partition("[Events]\n")
    header = head; fmt_line, _, body = events.partition("\n")
    merged_events.append(body.strip("\n"))
ass.write_text(header + "[Events]\n" + "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(merged_events) + "\n", encoding="utf-8")
print(f"captions: {total_chunks} chunks / {total_events} karaoke events")

# ---- 4) concat the shots (hard cuts) + burn captions, then DISSOLVE into the card (no hard break)
lst = work/"concat.txt"; lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in norm) + "\n")
body = work/"body.mp4"
ass_path = ass.as_posix().replace(":", "\\:")
run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",str(lst),
     "-vf",f"subtitles='{ass_path}':fontsdir='C\\:/Windows/Fonts'",
     "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",str(body)])
body_dur = probe_dur(body)
draft = work/"draft.mp4"
run(["ffmpeg","-v","error","-y","-i",str(body),"-i",str(card),
     "-filter_complex",f"[0:v][1:v]xfade=transition=fade:duration={XF}:offset={body_dur-XF:.3f}[v];[0:a][1:a]acrossfade=d={XF}[a]",
     "-map","[v]","-map","[a]","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",str(draft)])
print("draft:", draft, f"{probe_dur(draft):.2f}s (body {body_dur:.2f}s + card, {XF}s dissolve)")

# ---- 5) audio post-pass: Neuron bed (ducked) + -16 LUFS, via the flywheel's audio_mix.py
version = next((a.split("=")[1] for a in sys.argv if a.startswith("--version=")), "1")
final = d/f"{ad}_neuron_ad_v{version}.mp4"
if audio_pass:
    r = subprocess.run([sys.executable, str(ENGINE/"audio_mix.py"), "--in", str(draft), "--lane", BR["lane"], "--shorts", "--out", str(final), "--force"],
                       capture_output=True, text=True)
    print("audio_mix:", r.stdout.strip()[-600:], r.stderr.strip()[-400:] if r.returncode else "")
    if r.returncode != 0 or not final.exists(): shutil.copy(draft, final); print("audio_mix failed; using draft audio")
else:
    shutil.copy(draft, final)
print("FINAL:", final, f"{probe_dur(final):.2f}s", final.stat().st_size//1024, "KB")
