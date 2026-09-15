#!/usr/bin/env python3
"""show_block.py <transcript line no> [...]: print the tool_use input(s) recorded on that JSONL line
(Bash command / Write content / Edit old+new), for manual replay of a patch the sandbox could not apply."""
import json, sys, pathlib
JSONL = pathlib.Path(r"C:\Users\Cory\.claude\projects\C--Users-Cory-Downloads\d2b24766-2a78-4174-8123-67fab27201f8.jsonl")
want = {int(a) for a in sys.argv[1:]}
with JSONL.open(encoding="utf-8", errors="ignore") as f:
    for n, line in enumerate(f, 1):
        if n not in want: continue
        ev = json.loads(line)
        for blk in (ev.get("message") or {}).get("content") or []:
            if isinstance(blk, dict) and blk.get("type") == "tool_use":
                inp = blk.get("input") or {}
                print(f"===== L{n} {ev.get('timestamp','')[:19]} {blk.get('name')} =====")
                if blk.get("name") == "Bash": print(inp.get("command", ""))
                elif blk.get("name") == "Write": print(f"--- {inp.get('file_path')}\n{inp.get('content','')}")
                elif blk.get("name") == "Edit":
                    print(f"--- {inp.get('file_path')} replace_all={inp.get('replace_all', False)}\n--- OLD:\n{inp.get('old_string','')}\n--- NEW:\n{inp.get('new_string','')}")
                else: print(json.dumps(inp, indent=1)[:3000])
