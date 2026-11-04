#!/usr/bin/env python3
"""Submit ONE HeyGen cinematic_avatar shot ($7 flat, 4-15s), poll, download, report wallet.
Usage: python render_shot.py <ad_key> <shot_idx 1..3> [--dry]
Prompts + dialogue come from shots.json next to this file; scripts.json holds the validated copy.
Idempotency-Key is derived from (ad_key, shot_idx, prompt hash) so a re-run of the SAME prompt
never double-bills; a changed prompt is a deliberate reroll and bills again."""
import sys, json, time, hashlib, pathlib, urllib.request
sys.path.insert(0, r"C:\Users\you\.neuron-vault")
from secrets_vault import get
HERE = pathlib.Path(__file__).resolve().parent
KEY = get("HEYGEN_API_KEY"); H = {"x-api-key": KEY, "Content-Type": "application/json", "Accept": "application/json"}
# Persona LOOKS (HeyGen photo-avatar look ids). One persona, several wardrobes/hair - pick the look that
# fits the vertical BEFORE rendering (Cory 2026-08-21: "she still looks like that auto mechanic").
LOOKS = {"P1": "38fe6195513c85f6e11f4a6355f8c2d3",             # P1 Operator - navy work shirt, messy bun (trades: auto, contractors)
         "P1-pro-blouse": "1b35dda98b0a36edcbd35f100d54990b",  # P1 - hair down in waves, ivory blouse (general local; professional-approachable)
         "P1-medspa": "93e2c6af912f6d7a2b375ff4b74121bc",      # P1 - sleek low bun, white collarless tunic (med spa / aesthetics)
         "P2": "eceb44fbf76973b1881b526f6b1de3a0",             # P2 Advisor - light-blue shirt (dental)
         "P2-law-blazer": "cd829141581435bcc63f5d0a70ea2267",  # P2 - navy blazer over white open-collar shirt (law / professional services)
         "AA1-sam": "4cf8e5cbadcb366ed1c3cecc900c85d9",       # Auto Advisor brand persona - Sam, owner (charcoal quarter-zip)
         "TB1-mike": "8c638151f0b008355b838784c597658a"}       # Top Builder OS brand persona - Mike, roofer owner-operator (tan work shirt)
PERSONA = {"auto": "P1", "contractors": "P1", "general": "P1", "general-pro": "P1-pro-blouse", "medspa": "P1-medspa", "dental": "P2", "law": "P2-law-blazer",
           "autoadvisor": "AA1-sam", "tbos": "TB1-mike"}

ad, idx = sys.argv[1], int(sys.argv[2]); dry = "--dry" in sys.argv
retry = next((a.split("=")[1] for a in sys.argv if a.startswith("--retry=")), "")
look_arg = next((a.split("=")[1] for a in sys.argv if a.startswith("--look=")), None)   # a LOOKS key or a raw look id
LOOK = LOOKS.get(look_arg, look_arg) if look_arg else LOOKS[PERSONA[ad]]
shots = json.loads((HERE/"shots.json").read_text(encoding="utf-8"))[ad]
sh = shots[idx-1]
out_dir = HERE/ad; out_dir.mkdir(exist_ok=True)
body = {"type":"cinematic_avatar","prompt":sh["prompt"],"avatar_id":[LOOK],"aspect_ratio":"9:16",
        "resolution":"1080p","duration":sh["duration"],"enhance_prompt":False,
        "title":f"neuron-{ad}-shot{idx}"}
ikey = f"neuron-{ad}-s{idx}-" + hashlib.sha1(sh["prompt"].encode()).hexdigest()[:16] + (f"-r{retry}" if retry else "")
print("prompt chars:", len(sh["prompt"]), "| duration:", sh["duration"], "| idempotency:", ikey)
if dry: print(json.dumps(body, indent=1)[:1500]); sys.exit(0)

def call(method, url, data=None, extra=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={**H, **(extra or {})}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:600]

s, d = call("POST", "https://api.heygen.com/v3/videos", body, {"Idempotency-Key": ikey})
print("SUBMIT", s, json.dumps(d)[:400] if isinstance(d, dict) else d)
if s != 200: sys.exit(1)
vid = d["data"]["video_id"]; (out_dir/f"shot{idx}_submit.json").write_text(json.dumps(d, indent=1))
t0 = time.time()
while True:
    s, d = call("GET", f"https://api.heygen.com/v3/videos/{vid}")
    st = d["data"].get("status") if isinstance(d, dict) else "?"
    print(f"  {int(time.time()-t0):4d}s  {st}")
    if st == "completed":
        url = d["data"]["video_url"]; dest = out_dir/f"shot{idx}_cinematic.mp4"
        urllib.request.urlretrieve(url, dest)
        (out_dir/f"shot{idx}_result.json").write_text(json.dumps(d, indent=1))
        print("DOWNLOADED", dest, dest.stat().st_size//1024, "KB"); break
    if st == "failed":
        print("FAILED:", json.dumps(d)[:800]); (out_dir/f"shot{idx}_result.json").write_text(json.dumps(d, indent=1)); sys.exit(2)
    if time.time()-t0 > 1500: print("TIMEOUT polling; video_id", vid); sys.exit(3)
    time.sleep(15)
s, me = call("GET", "https://api.heygen.com/v3/users/me")
print("WALLET after:", me["data"]["wallet"]["remaining_balance"] if isinstance(me, dict) else me)