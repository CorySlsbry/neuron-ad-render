#!/usr/bin/env python3
"""gates.py - the rail's static gates, cited by exit code (0 = all pass, 1 = failures listed).
py_compile every script, validate every JSON, assert the hard-won markers are present, and assert the
brokerage law: no "KW Westfield" anywhere a customer could see it (shots.json dialogue/prompt, end cards)."""
import json, pathlib, py_compile, sys
HERE = pathlib.Path(__file__).resolve().parent.parent
MARKERS = {
    "lipsync_shot.py": ["clip_sha", "tpad=stop_mode=clone"],
    "intro_run.py": ["fresh cinematic on disk", "dur(vo) > dur(clip) - 0.4"],
    "assemble.py": ["script_align", "SIMPLE CHOICE REAL ESTATE", '"sre-intro"', '"sre-walk-ab"'],
    "make_look.py": ["--scene="],
    "make_vo.py": ["TTS_MODELS"],
    "render_shot.py": ["--look=", "--retry="],
}
BANNED_VISIBLE = ["KW Westfield", "KW WESTFIELD", "Keller Williams"]
bad = 0
for p in sorted(HERE.glob("*.py")):
    try: py_compile.compile(str(p), doraise=True); print(f"compile  {p.name:24} OK")
    except Exception as e: bad += 1; print(f"compile  {p.name:24} FAIL {str(e)[:100]}")
for p in [HERE / "shots.json", HERE / "personas" / "looks.json"]:
    try: json.loads(p.read_text(encoding="utf-8")); print(f"json     {p.name:24} OK")
    except Exception as e: bad += 1; print(f"json     {p.name:24} FAIL {e}")
for f, marks in MARKERS.items():
    t = (HERE / f).read_text(encoding="utf-8", errors="ignore") if (HERE / f).is_file() else ""
    for m in marks:
        ok = m in t; bad += (not ok); print(f"marker   {f:24} {'OK ' if ok else 'MISSING'} {m!r}")
shots = json.loads((HERE / "shots.json").read_text(encoding="utf-8"))
for ad, lst in shots.items():
    for i, sh in enumerate(lst, 1):
        for k in ("dialogue", "prompt"):
            for b in BANNED_VISIBLE:
                if b in sh.get(k, ""):
                    bad += 1; print(f"BROKERAGE shots.json {ad} s{i} {k}: contains {b!r}")
asm = (HERE / "assemble.py").read_text(encoding="utf-8")
for b in BANNED_VISIBLE:
    if b in asm.replace('"KW Westfield" is BANNED', ""):
        bad += 1; print(f"BROKERAGE assemble.py contains {b!r}")
print(f"\nGATES: {'PASS' if not bad else str(bad) + ' FAILURE(S)'}")
sys.exit(1 if bad else 0)
