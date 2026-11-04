#!/usr/bin/env python3
"""Re-sync ONE cinematic shot to our ElevenLabs VO with HeyGen Lipsync.
Usage: python lipsync_shot.py <ad_key> <shot_idx> [speed|precision] [--trim]
  speed     $0.0333/s  (~$0.35 for a 10s shot)
  precision $0.0667/s  (~$0.70)  - avatar-inference lip-sync, default here
  --trim    HeyGen preflight rejects audio/video durations that differ by >15%. With --trim the
            cinematic clip is cut to min(clip, 1.10 x VO) and uploaded as an asset first.
Flow: upload shotN_vo.mp3 as an asset (POST /v3/assets, multipart) -> POST /v3/lipsyncs
{video: url|asset_id, audio: asset_id, mode} (answers 202) -> poll -> download shotN_synced_<mode>.mp4.
Idempotency-Key derived from (ad, shot, mode, trim, audio sha1, video sha1) so a re-run never double-bills."""
import sys, json, time, hashlib, pathlib, urllib.request, uuid, subprocess
sys.path.insert(0, r"C:\Users\you\.neuron-vault")
from secrets_vault import get
HERE = pathlib.Path(__file__).resolve().parent
KEY = get("HEYGEN_API_KEY")
ad, idx = sys.argv[1], int(sys.argv[2])
mode = next((a for a in sys.argv[3:] if a in ("speed", "precision")), "precision")
TRIM = "--trim" in sys.argv
d = HERE/ad
vo = d/f"shot{idx}_vo.mp3"
res = json.loads((d/f"shot{idx}_result.json").read_text())
video_url = res["data"]["video_url"]

def dur(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)],
                                capture_output=True, text=True).stdout.strip())

def call(method, url, data=None, headers=None, raw=None):
    h = {"x-api-key": KEY, "Accept": "application/json"}
    if data is not None: h["Content-Type"] = "application/json"
    if headers: h.update(headers)
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r: return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:600]

def upload_asset(path, mime):
    boundary = "----neuron" + uuid.uuid4().hex
    head = ("--" + boundary + "\r\n"
            "Content-Disposition: form-data; name=\"file\"; filename=\"" + path.name + "\"\r\n"
            "Content-Type: " + mime + "\r\n\r\n").encode()
    tail = ("\r\n--" + boundary + "--\r\n").encode()
    s, a = call("POST", "https://api.heygen.com/v3/assets",
                headers={"Content-Type": "multipart/form-data; boundary=" + boundary}, raw=head + path.read_bytes() + tail)
    print("ASSET", path.name, s, json.dumps(a)[:200] if isinstance(a, dict) else a)
    if s != 200: sys.exit(1)
    return (a.get("data") or {}).get("asset_id") or (a.get("data") or {}).get("id")

# 1) optional trim of the cinematic clip to within the 15% window, uploaded as the video asset
video_ref = {"type": "url", "url": video_url}
if TRIM:
    src = d/f"shot{idx}_cinematic.mp4"; a_len = dur(vo); v_len = dur(src); target = min(v_len, round(a_len*1.10, 2))
    tp = d/f"shot{idx}_cinematic_trim.mp4"
    if v_len < a_len + 0.3:
        # VO runs to (or past) the clip end: freeze-extend the last frame to 1.05x VO so the
        # sync never truncates the closing words (2026-08-27, sre-intro shot 1: 15.98s VO vs 15.1s clip).
        target = a_len * 1.05
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(src),
                        "-vf",f"tpad=stop_mode=clone:stop_duration={max(0.0, target - v_len) + 0.2:.3f}",
                        "-t",f"{target:.3f}","-c:v","libx264","-preset","fast","-crf","17",
                        "-c:a","aac","-b:a","160k",str(tp)], check=True)
        print(f"padded {v_len:.2f}s -> {dur(tp):.2f}s for a {a_len:.2f}s VO")
    else:
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(src),"-t",f"{target:.3f}","-c:v","libx264","-preset","fast","-crf","17",
                        "-c:a","aac","-b:a","160k",str(tp)], check=True)
        print(f"trimmed {v_len:.2f}s -> {dur(tp):.2f}s for a {a_len:.2f}s VO")
    video_ref = {"type": "asset_id", "asset_id": upload_asset(tp, "video/mp4")}

# 2) VO asset
audio_id = upload_asset(vo, "audio/mpeg")

# 3) lipsync
# key covers BOTH inputs (2026-08-24): audio-only hashing meant a re-rendered clip + unchanged VO
# collided with the previous job and HeyGen silently returned the OLD synced video ($0, 0s "completed").
clip_sha = hashlib.sha1((d/f"shot{idx}_cinematic.mp4").read_bytes()).hexdigest()[:12]
ikey = (f"neuron-{ad}-s{idx}-ls-{mode}-" + hashlib.sha1(vo.read_bytes()).hexdigest()[:12]
        + "-v" + clip_sha + ("-trim" if TRIM else ""))
s, l = call("POST", "https://api.heygen.com/v3/lipsyncs",
            data={"video": video_ref, "audio": {"type": "asset_id", "asset_id": audio_id},
                  "mode": mode, "title": f"neuron-{ad}-shot{idx}-lipsync", "keep_the_same_format": True},
            headers={"Idempotency-Key": ikey})
print("LIPSYNC", s, json.dumps(l)[:400] if isinstance(l, dict) else l)
if s not in (200, 202): sys.exit(1)   # HeyGen answers 202 Accepted for lipsync jobs
lid = (l.get("data") or {}).get("lipsync_id") or (l.get("data") or {}).get("id")
t0 = time.time()
while True:
    s, g = call("GET", f"https://api.heygen.com/v3/lipsyncs/{lid}")
    st = (g.get("data") or {}).get("status") if isinstance(g, dict) else "?"
    print(f"  {int(time.time()-t0):4d}s {st}", flush=True)
    if st == "completed":
        url = g["data"]["video_url"]; dest = d/f"shot{idx}_synced_{mode}.mp4"
        urllib.request.urlretrieve(url, dest); (d/f"shot{idx}_lipsync.json").write_text(json.dumps(g, indent=1))
        print("DOWNLOADED", dest, dest.stat().st_size//1024, "KB"); break
    if st in ("failed", "error"):
        print("FAILED", json.dumps(g)[:600]); sys.exit(2)
    if time.time()-t0 > 1500: print("TIMEOUT", lid); sys.exit(3)
    time.sleep(12)
s, me = call("GET", "https://api.heygen.com/v3/users/me")
print("WALLET after:", me["data"]["wallet"]["remaining_balance"] if isinstance(me, dict) else me)
