#!/usr/bin/env python3
"""recover_from_transcript.py - rebuild the rail's source files from the session transcript.

The rail (neuron-ad-render) vanished from disk on ~2026-09-05. Every file in it was created and
patched through Claude Code tool calls that the session transcript (JSONL) records verbatim:
  * Write   -> full file body
  * Bash heredoc `cat > <file> <<'MARK' ... MARK` -> full file body
  * Edit    -> old_string -> new_string (replace_all honored)
  * Bash python blocks that read/patch/write a target (`p.write_text(s.replace(old, new))`,
    json.load/modify/json.dump ...) -> re-executed IN ORDER against the recovery tree, inside a
    sandbox: cwd = the rail dir, every write outside the rail/personas trees is refused, and every
    network/subprocess/whisper/lineage import is stubbed to raise (so a block that also launched a
    render just stops after its file write - or before it, in which case it is reported as FAILED
    for manual review).
Disk is the state: events are applied to the files in place, in transcript order, so later python
blocks see exactly what they saw originally. Ends with py_compile + marker gates and a RECOVERY.md.
Read-only against the transcript; writes only under the rail tree.
"""
import io, json, os, re, sys, types, pathlib, py_compile, traceback, builtins, importlib

JSONL = pathlib.Path(r"C:\Users\Cory\.claude\projects\C--Users-Cory-Downloads\d2b24766-2a78-4174-8123-67fab27201f8.jsonl")
RAIL = pathlib.Path(r"C:\Users\Cory\Downloads\neuron-ad-render")
PERSONAS_LEGACY = pathlib.Path(r"C:\Users\Cory\Downloads\neuron-ad-personas")   # old absolute path used by blocks
ALLOWED_WRITE_ROOTS = (RAIL, PERSONAS_LEGACY, pathlib.Path(r"C:\Users\Cory\Downloads\neuron-ad-library"))
TARGETS = {"render_shot.py", "lipsync_shot.py", "intro_run.py", "reroll_a.py", "make_vo.py", "assemble.py",
           "make_look.py", "make_avatar.py", "sync_drift.py", "render_with_wallet.py", "shots.json", "looks.json",
           "make_thumbs.py", "post_plan.py", "yt_post.py", "voicecheck.py", "sts_shot.py", "word_audit.py",
           "library_export.py", "find_clip.py", "intro_partial.py"}
MARKERS = {  # gates: the hard-won fixes that MUST be present in the recovered final
    "lipsync_shot.py": ["clip_sha", "tpad=stop_mode=clone"],
    "intro_run.py": ["fresh cinematic on disk"],
    "assemble.py": ["script_align"],
    "make_look.py": ["--scene="],
    "make_vo.py": ["TTS_MODELS"],
}
HEREDOC = re.compile(r"cat\s*>\s*([^\s<]+)\s*<<\s*'?(\w+)'?[^\n]*\n(.*?)\n\2[ \t]*(?:\n|$)", re.S)
PYBLOCK = re.compile(r"python3?(?:\s+-u)?\s+-\s*<<\s*'(\w+)'[^\n]*\n(.*?)\n\1[ \t]*(?:\n|$)", re.S)
PYC = re.compile(r"""python3?(?:\s+-u)?\s+-c\s+(['"])(.*?)\1""", re.S)
SIDE_STUBS = ["urllib.request", "subprocess", "faster_whisper", "lineage", "asset_library", "librosa", "numpy",
              "shorts_queue", "audio_mix"]
log = []

def note(s):
    log.append(s); print(s, flush=True)

def under_allowed(p):
    try:
        rp = pathlib.Path(p).resolve()
    except Exception:
        return False
    return any(str(rp).lower().startswith(str(r).lower()) for r in ALLOWED_WRITE_ROOTS)

def base_of(fp):
    return pathlib.PurePath(str(fp).strip('"\' ')).name

def apply_write(fp, content, tag):
    b = base_of(fp)
    dest = RAIL / b if b != "looks.json" else PERSONAS_LEGACY / b
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    note(f"  {tag:8} {b:22} {len(content):6}B")

def apply_edit(fp, old, new, all_, tag="Edit"):
    b = base_of(fp)
    dest = RAIL / b if b != "looks.json" else PERSONAS_LEGACY / b
    if not dest.is_file():
        note(f"  MISS     {b:22} edit before any body (skipped)"); return
    s = dest.read_text(encoding="utf-8")
    n = s.count(old)
    if n == 0:
        note(f"  MISS     {b:22} old_string not found ({len(old)}B) -> flagged"); flagged.append((b, tag, old[:80])); return
    s = s.replace(old, new) if all_ else s.replace(old, new, 1)
    dest.write_text(s, encoding="utf-8")
    note(f"  {tag:8} {b:22} {'x'+str(n) if all_ else 'x1'} ({len(old)}B->{len(new)}B)")

flagged = []

class _Refuse(types.ModuleType):
    def __getattr__(self, k):
        raise RuntimeError(f"sandbox: {self.__name__}.{k} is not available during recovery")

def sandbox_exec(src, lineno):
    """Run a past python patch block with cwd=RAIL, writes confined, side-effect modules stubbed."""
    saved_modules = {}
    for m in SIDE_STUBS:
        saved_modules[m] = sys.modules.get(m)
        sys.modules[m] = _Refuse(m)
    # secrets_vault.get -> a harmless placeholder so import-time key loads don't crash before the write
    sv = types.ModuleType("secrets_vault"); sv.get = lambda *a, **k: "RECOVERY-STUB"; sv.has = lambda *a, **k: False
    saved_modules["secrets_vault"] = sys.modules.get("secrets_vault"); sys.modules["secrets_vault"] = sv
    real_open = builtins.open
    real_wt, real_wb = pathlib.Path.write_text, pathlib.Path.write_bytes
    def guarded_open(f, mode="r", *a, **k):
        if any(ch in str(mode) for ch in "wax+") and not under_allowed(f):
            raise PermissionError(f"sandbox: refused write outside rail: {f}")
        return real_open(f, mode, *a, **k)
    def guarded_wt(self, *a, **k):
        if not under_allowed(self): raise PermissionError(f"sandbox: refused write outside rail: {self}")
        return real_wt(self, *a, **k)
    def guarded_wb(self, *a, **k):
        if not under_allowed(self): raise PermissionError(f"sandbox: refused write outside rail: {self}")
        return real_wb(self, *a, **k)
    builtins.open = guarded_open; pathlib.Path.write_text = guarded_wt; pathlib.Path.write_bytes = guarded_wb
    cwd = os.getcwd(); os.chdir(RAIL)
    out = io.StringIO(); old_stdout = sys.stdout; sys.stdout = out
    ok, err = True, ""
    try:
        exec(compile(src, f"<transcript:{lineno}>", "exec"), {"__name__": "__recovery__"})
    except SystemExit:
        pass
    except BaseException as e:
        ok, err = False, f"{type(e).__name__}: {str(e)[:160]}"
    finally:
        sys.stdout = old_stdout; os.chdir(cwd)
        builtins.open = real_open; pathlib.Path.write_text = real_wt; pathlib.Path.write_bytes = real_wb
        for m, v in saved_modules.items():
            if v is None: sys.modules.pop(m, None)
            else: sys.modules[m] = v
    return ok, err, out.getvalue()

def snapshot():
    return {t: ((RAIL / t) if t != "looks.json" else (PERSONAS_LEGACY / t)) for t in TARGETS}

def mtimes():
    return {t: (p.stat().st_mtime_ns if p.is_file() else None) for t, p in snapshot().items()}

def collect():
    """All tool_use events in the transcript, deduplicated (the file holds a re-logged copy of the
    08-23..08-25 stretch after a resume) and sorted by timestamp so replay order = real order."""
    seen = set(); out = []; n = 0
    with JSONL.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            n += 1
            try: ev = json.loads(line)
            except Exception: continue
            msg = ev.get("message") or {}
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list): continue
            ts = ev.get("timestamp", "")[:23]
            for blk in content:
                if not isinstance(blk, dict) or blk.get("type") != "tool_use": continue
                name = blk.get("name"); inp = blk.get("input") or {}
                if name not in ("Write", "Edit", "Bash"): continue
                key = (ts, name, hash(json.dumps(inp, sort_keys=True, default=str)))
                if key in seen: continue
                seen.add(key); out.append((ts, n, name, inp))
    out.sort(key=lambda e: (e[0], e[1]))
    return out

def main():
    RAIL.mkdir(parents=True, exist_ok=True); PERSONAS_LEGACY.mkdir(parents=True, exist_ok=True)
    events = 0
    all_events = collect()
    note(f"tool events collected (deduped): {len(all_events)}")
    if True:
        for ts, n, name, inp in all_events:
            ts = ts[:19]
            if True:
                if name == "Write":
                    b = base_of(inp.get("file_path", ""))
                    if b in TARGETS:
                        events += 1; note(f"[{ts} L{n}]"); apply_write(inp["file_path"], inp.get("content", ""), "Write")
                elif name == "Edit":
                    b = base_of(inp.get("file_path", ""))
                    if b in TARGETS:
                        events += 1; note(f"[{ts} L{n}]")
                        apply_edit(inp["file_path"], inp.get("old_string", ""), inp.get("new_string", ""), bool(inp.get("replace_all")))
                elif name == "Bash":
                    cmd = inp.get("command", "")
                    touched = False
                    for m in HEREDOC.finditer(cmd):
                        b = base_of(m.group(1))
                        if b in TARGETS:
                            events += 1; touched = True; note(f"[{ts} L{n}]"); apply_write(m.group(1), m.group(3), "Heredoc")
                    hits = [t for t in TARGETS if re.search(r'["\'/\\]' + re.escape(t) + r'["\']', cmd)]
                    writes = (".write_text(" in cmd or "json.dump" in cmd or ".write_bytes(" in cmd)
                    if hits and writes:
                        blocks = [(mm.group(2)) for mm in PYBLOCK.finditer(cmd)] + [mm.group(2) for mm in PYC.finditer(cmd)]
                        for src in blocks:
                            if not any(t in src for t in hits): continue
                            events += 1; before = mtimes()
                            ok, err, out = sandbox_exec(src, n)
                            changed = [t for t, mt in mtimes().items() if mt != before.get(t)]
                            tag = "PyBlock " if ok else "PyFAIL  "
                            note(f"[{ts} L{n}]"); note(f"  {tag} {','.join(hits):22} changed={changed or '-'} {('ERR ' + err) if not ok else ''}")
                            if not ok and not changed:
                                flagged.append((",".join(hits), f"PyFAIL L{n}", err))
    # ---- gates ----
    note("\n== GATES ==")
    bad = 0
    for t, p in sorted(snapshot().items()):
        if not p.is_file():
            note(f"  ABSENT   {t}"); continue
        if t.endswith(".py"):
            try: py_compile.compile(str(p), doraise=True); note(f"  compile  {t:22} OK ({p.stat().st_size}B)")
            except Exception as e: bad += 1; note(f"  compile  {t:22} FAIL {str(e)[:120]}")
        else:
            try: json.loads(p.read_text(encoding="utf-8")); note(f"  json     {t:22} OK ({p.stat().st_size}B)")
            except Exception as e: bad += 1; note(f"  json     {t:22} FAIL {e}")
        for mk in MARKERS.get(t, []):
            if mk in p.read_text(encoding="utf-8", errors="ignore"): note(f"  marker   {t:22} '{mk}' present")
            else: bad += 1; note(f"  marker   {t:22} '{mk}' MISSING")
    note(f"\nevents applied: {events}; flagged for review: {len(flagged)}; gate failures: {bad}")
    for fl in flagged: note(f"  FLAG {fl}")
    (RAIL / "_recovery" / "RECOVERY.md").write_text(
        "# Recovery log\n\nSource: session transcript `" + JSONL.name + "`, replayed " + __import__("datetime").datetime.now().isoformat()[:19] +
        "\n\n```\n" + "\n".join(log) + "\n```\n", encoding="utf-8")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
