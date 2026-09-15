#!/usr/bin/env python3
"""yt_post.py - upload the persona ads to each brand's OWN YouTube channel as Shorts.

YouTube is NOT on the shorts_queue path (that covers IG/TikTok/FB/LinkedIn); each lane has its own
channel-guarded uploader. Every upload carries the CUSTOM THUMBNAIL the hard rule requires and passes
--expect-channel-id so a token that drifts to the wrong channel aborts instead of posting.

⛔ The AI/altered-content disclosure is NOT settable through the Data API (yt_upload.py's own docs).
The description carries the disclosure text; the formal Studio toggle is a needs-Cory item.

Usage: python yt_post.py [key ...] [--dry-run]
"""
import json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
UPLOADER = pathlib.Path(r"C:\Users\Cory\.claude\skills\video-generation\references\yt_upload.py")
sys.path.insert(0, str(HERE))
import post_plan as P

LANE_YT = {
 "neuron-hq":      dict(channel="neuron",      chan_id="UCw9aqS5uTVzldhwJL0XLWiQ", category="28"),
 "auto-advisor":   dict(channel="autoadvisor", chan_id="UC5PSfwP-wBsxX46MgJfYVcg", category="2"),
 "top-builder-ai": dict(channel="topbuilderos",chan_id="UC3DHSlPj2uYkusfutAafyYA", category="28"),
}
# Was {"top-builder-ai": ...} while its token was dead. Cory re-authed 2026-08-23 and
# yt_channel_guard --assert now verifies topbuilderos -> UC3DHSlPj2uYkusfutAafyYA ("Top Builder").
# Keep this empty: a STATIC block list goes stale and lies. The live guard is --expect-channel-id
# on the uploader plus yt_channel_guard, both of which abort on a mismatch.
BLOCKED = {}

dry = "--dry-run" in sys.argv
only = [a for a in sys.argv[1:] if not a.startswith("--")]
ads = [a for a in P.ADS if not only or a["key"] in only]
results = []
for a in ads:
    lane = a["lane"]; cfg = LANE_YT[lane]
    mp4 = HERE/a["mp4"]; thumb = HERE/"thumbs"/f"{a['key']}_thumb.jpg"; desc = HERE/"yt_meta"/f"{a['key']}_desc.txt"
    if lane in BLOCKED:
        print(f"[{a['key']:12s}] BLOCKED - {BLOCKED[lane]}"); results.append((a["key"], "blocked", "")); continue
    for p in (mp4, thumb, desc):
        if not p.exists(): print(f"[{a['key']:12s}] MISSING {p.name}"); break
    else:
        cmd = [sys.executable, str(UPLOADER), "--channel", cfg["channel"], "--file", str(mp4),
               "--title", a["title"], "--desc-file", str(desc), "--tags", a["tags"],
               "--privacy", "public", "--category", cfg["category"],
               "--expect-channel-id", cfg["chan_id"], "--thumb", str(thumb), "--require-thumb", "--json"]
        if dry:
            print(f"[{a['key']:12s}] DRY {' '.join(cmd[-14:])[:150]}"); results.append((a["key"], "dry", "")); continue
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        out = (r.stdout or "").strip()
        vid = ""
        for ln in out.splitlines():
            if ln.startswith("{"):
                try:
                    d = json.loads(ln); vid = d.get("video_id") or d.get("id") or ""
                except Exception: pass
        ok = r.returncode == 0 and vid
        print(f"[{a['key']:12s}] rc={r.returncode} {'https://youtu.be/'+vid if vid else (out or r.stderr)[-220:]}")
        results.append((a["key"], "ok" if ok else "fail", vid))
print("\n" + json.dumps([{"key": k, "status": s, "video_id": v} for k, s, v in results], indent=1))
