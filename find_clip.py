#!/usr/bin/env python3
"""find_clip.py - pull the right persona-ad asset out of the GEO asset library by words.
Usage:
  python find_clip.py "van phone"                  # any words from the scene OR the spoken line
  python find_clip.py "price shopping" --type broll_clip
  python find_clip.py P1 --type image              # the persona stills
  python find_clip.py --all                        # everything in the persona-ads cluster
Matches title, description, cluster and tags (asset_library.search); prints path + what she says."""
import sys, json, pathlib
sys.path.insert(0, r"C:\Users\Cory\.claude\skills\geo-flywheel\references\engine")
import asset_library as AL

typ = next((sys.argv[i+1] for i, a in enumerate(sys.argv) if a == "--type" and i+1 < len(sys.argv)), None)
args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i-1] != "--type"]
if "--all" in sys.argv:
    hits = AL.find(brand="neuron-hq", type=typ, cluster="persona-ads")
else:
    q = " ".join(args).strip()
    if not q: print(__doc__); sys.exit(0)
    hits = [r for r in AL.search(q, brand="neuron-hq", type=typ) if r.get("cluster") == "persona-ads"]
    if not hits:  # fall back to any-word match so "van phone" finds "work van ... phone in hand"
        words = [w.lower() for w in q.split()]
        hits = [r for r in AL.find(brand="neuron-hq", type=typ, cluster="persona-ads")
                if all(w in (" ".join(str(r.get(k) or "") for k in ("title", "description")) + " " + " ".join(r.get("tags") or [])).lower() for w in words)]
hits = [r for r in hits if r.get("type") != "thumbnail"]
if not hits: print("no match"); sys.exit(1)
for r in sorted(hits, key=lambda r: (r.get("type"), r.get("title") or "")):
    m = r.get("meta") or {}
    print(f"[{r['type']}] {r.get('title')}")
    print(f"   path: {r.get('path')}")
    if m.get("dialogue"): print(f"   says: \"{m['dialogue']}\"")
    if m.get("resync_window_s"): print(f"   resync to a VO of {m['resync_window_s'][0]}-{m['resync_window_s'][1]}s  |  id {r['id']}")
    else: print(f"   id {r['id']}")
print(f"\n{len(hits)} match(es)")
