#!/usr/bin/env python3
"""make_avatar.py - turn an approved persona still into a HeyGen photo avatar LOOK ($1) and print the look id.
Usage: python make_avatar.py <still.png> "<name>"
Flow: POST /v3/avatars type=photo (base64, the REAL mime - our Gemini .png files are JPEG bytes) -> poll
GET /v3/avatars/looks?ownership=private until the new look appears -> print id. Record the id in
render_shot.py LOOKS so every shot of that persona+look reuses it. Idempotent by still sha1."""
import sys, json, time, base64, hashlib, pathlib, urllib.request
sys.path.insert(0, r"C:\Users\you\.neuron-vault")
from secrets_vault import get
H = {"x-api-key": get("HEYGEN_API_KEY"), "Accept": "application/json", "Content-Type": "application/json"}
still, name = pathlib.Path(sys.argv[1]), sys.argv[2]
raw = still.read_bytes()
mime = "image/jpeg" if raw[:3] == b"\xff\xd8\xff" else ("image/png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg")
def call(method, url, data=None, headers=None):
    h = dict(H); h.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r: return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:400]
s0, before = call("GET", "https://api.heygen.com/v3/avatars/looks?ownership=private&limit=100")
seen = {l["id"] for l in (before.get("data") or [])} if isinstance(before, dict) and isinstance(before.get("data"), list) else set()
s, d = call("POST", "https://api.heygen.com/v3/avatars", {"type": "photo", "name": name, "file": {"type": "base64", "data": base64.b64encode(raw).decode(), "media_type": mime}},
            {"Idempotency-Key": "neuron-look-" + hashlib.sha1(raw).hexdigest()[:16]})
print("CREATE", s, json.dumps(d)[:400] if isinstance(d, dict) else d)
if s != 200: sys.exit(1)
item = (d.get("data") or {}).get("avatar_item") or {}
look_id = item.get("id")
t0 = time.time()
while not look_id and time.time() - t0 < 300:
    time.sleep(10)
    s2, now = call("GET", "https://api.heygen.com/v3/avatars/looks?ownership=private&limit=100")
    looks = now.get("data") if isinstance(now, dict) else []
    new = [l for l in (looks or []) if l.get("id") not in seen]
    if new: look_id = new[0]["id"]; print("new look:", json.dumps(new[0])[:300])
print("LOOK_ID", look_id)
s3, me = call("GET", "https://api.heygen.com/v3/users/me"); print("WALLET", me["data"]["wallet"]["remaining_balance"] if isinstance(me, dict) else me)
