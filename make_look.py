"""make_look.py - an identity-locked still (same face) from a reference photo with Nano Banana Pro (gemini-3-pro-image).
Two jobs: a NEW LOOK for a persona (outfit/hair change) and, since 2026-09-15, the SCENE STILL that seeds a Kie.ai
image-to-video render of Cory (the still IS the identity for Kie, so it is composed as the clip's first frame).
$0.04 per still; eyes-on gate before any paid render.
Usage: python make_look.py <source_photo> <out_slug> "<change prompt>" [--scene=<set description>] [--ar=3:4|9:16|1:1|4:3|16:9]
                           [--mouth-rest] [--no-identity]
  writes personas/<out_slug>.png (default aspect 3:4; use --ar=9:16 for Kie stills - the output is then validated portrait).
  --mouth-rest   : force the closed, resting mouth (Cory 2026-08-24: the canonical photo smiles at rest).
  --no-identity  : faceless still (no reference photo edit - pure generation from the prompt), for B-roll first frames."""
import sys, json, base64, urllib.request, pathlib
sys.path.insert(0, r"C:\Users\you\.neuron-vault")
from secrets_vault import get
HERE = pathlib.Path(__file__).resolve().parent
KEY = get("GEMINI_API_KEY"); MODEL = "gemini-3-pro-image"
OUT = HERE / "personas"; OUT.mkdir(exist_ok=True)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
src, slug, change = pathlib.Path(args[0]), args[1], (args[2] if len(args) > 2 else "")
scene = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--scene=")), "")
ar = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--ar=")), "3:4")
if ar not in {"3:4", "9:16", "1:1", "4:3", "16:9"}:
    sys.exit(f"make_look: bad --ar {ar}")
mouth_rest = "--mouth-rest" in sys.argv
no_identity = "--no-identity" in sys.argv
NOTEXT = (" ABSOLUTELY NO TEXT ANYWHERE: no letters, words, numbers, logos, brand marks, name tags, embroidery, "
          "labels, signage, posters, book spines, papers, plates or screens.")
PLAIN_BG = " Plain, empty, softly out-of-focus neutral background - no shelves, no decor."
# --scene: keep the SAME face but place the person in a real environment. A photo avatar or an image-to-video
# model animates this still, so whatever is in the frame IS the set - shot-composed, not a cut-out on a backdrop.
BG = (f" Setting: {scene} The subject is genuinely in that place, lit by that place's own light, with the background "
      "softly out of focus at a shallow depth of field. Photoreal documentary photograph, not a composite and not a "
      "studio cut-out.") if scene else PLAIN_BG
MOUTH = (" The mouth is CLOSED and at rest: lips gently together, corners level, no smile, cheeks soft, jaw relaxed - "
         "the calm face of a person listening.") if mouth_rest else ""
if no_identity:
    instr = ("Photoreal vertical documentary photograph. " + change + BG + MOUTH + NOTEXT)
else:
    instr = ("Edit this photo. Keep the SAME person: identical face, facial structure, skin tone, eye colour, eyebrows, hair, "
             "beard, age and build - instantly recognisable as the same person. " + change + MOUTH +
             " Keep the soft natural real skin texture, no beauty retouching, photoreal documentary look, 50mm f2.8." + BG + NOTEXT)
parts = [{"text": instr}]
if not no_identity:
    raw = src.read_bytes()
    mime = "image/png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"     # sniff bytes; extensions lie
    parts = [{"inlineData": {"mimeType": mime, "data": base64.b64encode(raw).decode()}}, {"text": instr}]
payload = json.dumps({"contents": [{"parts": parts}],
                      "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": ar}}}).encode()
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                             data=payload, headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
with urllib.request.urlopen(req, timeout=240) as r:
    d = json.loads(r.read().decode())
for p in d["candidates"][0]["content"]["parts"]:
    if "inlineData" in p:
        dest = OUT / f"{slug}.png"; dest.write_bytes(base64.b64decode(p["inlineData"]["data"]))
        try:
            from PIL import Image
            w, h = Image.open(dest).size
        except Exception:
            w = h = 0
        if ar == "9:16" and w and h <= w:
            print(f"FAIL {dest} is not portrait ({w}x{h}) - regenerate"); sys.exit(6)
        print(f"OK {dest} {dest.stat().st_size//1024} KB {w}x{h}"); break
else:
    print("FAIL no image part:", json.dumps(d)[:400]); sys.exit(2)
