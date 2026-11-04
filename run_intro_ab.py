#!/usr/bin/env python3
"""run_intro_ab.py - the AI-Cory A/B: Kie.ai (Kling 3.0 pro, from our own identity still) vs the surviving HeyGen
cinematic walk in C:\\Users\\you\\Downloads\\salisburyre-avatar-test, same VO, same scene. INTERNAL ONLY: the
control VO names the retired brokerage, so nothing here may be posted (assemble refuses without --internal).
Stages, each idempotent with a cited exit:  control -> still (STOP exit 10 until --approve) -> render -> sync -> qa -> report
  python run_intro_ab.py [--approve] [--retry=N]
Cost: $0.04 still + ~$1.35 Kling + ~$1.00 HeyGen lipsync. Pattern = the recovered intro_run.py."""
import sys, json, time, shutil, subprocess, pathlib, hashlib, datetime
HERE = pathlib.Path(__file__).resolve().parent
AD = "sre-walk-ab"; D = HERE / AD; D.mkdir(exist_ok=True)
CTRL = pathlib.Path(r"C:\Users\you\Downloads\salisburyre-avatar-test")
CANON = pathlib.Path(r"C:\Users\you\Downloads\cory-canonical-2026-08.jpg")
STILL = HERE / "personas" / "kie-sre-walk-ab-s1.png"
ENGINE = pathlib.Path(r"C:\Users\you\.claude\skills\geo-flywheel\references\engine")
APPROVE = "--approve" in sys.argv
RETRY = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--retry=")), "")
COST = []

def run(args, tag):
    r = subprocess.run([sys.executable, "-u"] + args, capture_output=True, text=True, cwd=HERE)
    out = r.stdout + r.stderr
    (HERE / f"intro_ab_{tag}.log").write_text(out, encoding="utf-8")
    for l in out.splitlines():
        if l.startswith("COST "): COST.append(l)
    return r.returncode, out

def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)

def lineage(evt, **kw):
    try:
        sys.path.insert(0, str(ENGINE)); import lineage as L
        getattr(L, evt)(AD, **kw)
    except Exception:
        pass

# ---- 1) control: the surviving HeyGen walk + its blend VO ------------------------------------------
need = ["cory_site_walk_cinematic.mp4", "cory_site_walk_blend.mp4", "blend_vo.mp3", "blend_words.json"]
missing = [n for n in need if not (CTRL / n).is_file()]
if missing: sys.exit(f"control missing: {missing}")
if not (D / "shot1_vo.mp3").is_file():
    shutil.copy2(CTRL / "blend_vo.mp3", D / "shot1_vo.mp3")
    shutil.copy2(CTRL / "blend_words.json", D / "shot1_clipwords.json")
    lineage("run_start", target="Kie vs HeyGen A/B on the Aug walk shot (internal)")
print(f"== control: HeyGen walk {dur(CTRL/'cory_site_walk_cinematic.mp4'):.2f}s, VO {dur(D/'shot1_vo.mp3'):.2f}s", flush=True)

# ---- 2) still: identity + set as the first frame; eyes-on gate before any Kie spend --------------
if not STILL.is_file():
    rc, out = run(["make_look.py", str(CANON), STILL.stem,
                   "Change the pose and framing: he is walking toward the camera mid-stride, medium shot from the waist up, "
                   "shoulders square to the lens, black button-down shirt with the sleeves rolled, arms swinging naturally.",
                   "--scene=a residential construction site on an overcast morning: houses at framing stage with fresh lumber "
                   "behind him, a plain white pickup at the left edge, one crew member far in the background, gravel and dirt underfoot",
                   "--ar=9:16", "--mouth-rest"], "still")
    if rc != 0 or not STILL.is_file(): print(out[-400:]); sys.exit(6)
    COST.append("COST $0.04 (still, Gemini)")
    # 3-up sheet: our still | control frame at 6s | canonical photo
    frame = D / "control_6s.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "6", "-i", str(CTRL / "cory_site_walk_cinematic.mp4"), "-frames:v", "1", str(frame)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(STILL), "-i", str(frame), "-i", str(CANON),
                    "-filter_complex", "[0]scale=360:-1[a];[1]scale=360:-1[b];[2]scale=360:-1[c];[a][b][c]hstack=3",
                    "-frames:v", "1", str(D / "qa_still.jpg")], check=True)
    print(f"== still: {STILL} written; sheet {D/'qa_still.jpg'} (ours | control@6s | canonical)")
approvals = json.loads((HERE / "personas" / "looks.json").read_text(encoding="utf-8")).get("kie_stills", {})
if STILL.stem not in approvals:
    if not APPROVE:
        print(f"AWAITING_APPROVAL: look at {D/'qa_still.jpg'}; re-run with --approve to spend on the render (exit 10)"); sys.exit(10)
    lp = HERE / "personas" / "looks.json"; L = json.loads(lp.read_text(encoding="utf-8"))
    L.setdefault("kie_stills", {})[STILL.stem] = {"still": f"personas/{STILL.name}", "source": str(CANON),
        "approved_by": f"Cory {datetime.date.today().isoformat()}", "sha": hashlib.sha1(STILL.read_bytes()).hexdigest()[:12]}
    lp.write_text(json.dumps(L, indent=1), encoding="utf-8"); print("== still approved and registered in looks.json")

# ---- 3) render via Kie (Kling 3.0 pro, 15s) ----------------------------------------------------------
clip = D / "shot1_cinematic.mp4"
if not (clip.is_file() and (D / "shot1_result.json").is_file() and clip.stat().st_mtime > STILL.stat().st_mtime):
    rc, out = run(["kie_shot.py", AD, "1", f"--still={STILL}", "--model=kling3"] + ([f"--retry={RETRY}"] if RETRY else []), "render")
    print("\n".join(l for l in out.splitlines() if l.startswith(("ESTIMATE", "TASK", "RESUME", "DOWNLOADED", "KIE", "COST", "FAILED", "CAP", "NO_CREDITS", "STILL"))), flush=True)
    if rc != 0: sys.exit(rc)
else:
    print("== render: fresh Kie clip on disk, skipping")

# ---- 4) sync: precision lipsync to the blend VO, forced through the local-upload fit path ------------
blend = D / "shot1_blend.mp4"
if not (blend.is_file() and blend.stat().st_mtime > clip.stat().st_mtime):
    rc, out = run(["lipsync_shot.py", AD, "1", "precision", "--trim"], "sync")
    print("\n".join(l for l in out.splitlines() if l.startswith(("trimmed", "padded", "LIPSYNC", "DOWNLOADED", "WALLET"))), flush=True)
    if rc != 0 or not (D / "shot1_synced_precision.mp4").is_file(): print(out[-400:]); sys.exit(rc or 2)
    blend.write_bytes((D / "shot1_synced_precision.mp4").read_bytes())
    COST.append(f"COST ${0.0667 * dur(D/'shot1_synced_precision.mp4'):.2f} (lipsync, HeyGen)")
else:
    print("== sync: blend newer than clip, skipping")

# ---- 5) qa: drift + envelope on both, side-by-side sheets ------------------------------------------
rc_k, out_k = run(["sync_drift.py", AD, "1"], "qa_kie")
rc_c, out_c = run(["sync_drift.py", AD, "1", f"--clip={CTRL/'cory_site_walk_blend.mp4'}", f"--vo={D/'shot1_vo.mp3'}"], "qa_control")
kie_line = next((l for l in out_k.splitlines() if l.startswith("shot1")), out_k[-200:])
ctl_line = next((l for l in out_c.splitlines() if l.startswith("shot1")), out_c[-200:])
print("== qa kie    :", kie_line); print("== qa control:", ctl_line)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(CTRL / "cory_site_walk_blend.mp4"), "-i", str(blend),
                "-filter_complex", "[0]fps=1/2,scale=200:-1,tile=7x1[a];[1]fps=1/2,scale=200:-1,tile=7x1[b];[a][b]vstack=2",
                "-frames:v", "1", str(D / "ab_sheet.jpg")], check=False)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(CTRL / "cory_site_walk_blend.mp4"), "-i", str(blend),
                "-filter_complex", "[0]select='eq(n\\,48)+eq(n\\,168)+eq(n\\,288)',crop=540:540:270:120,scale=300:300,tile=3x1[a];"
                                   "[1]select='eq(n\\,60)+eq(n\\,210)+eq(n\\,360)',crop=540:540:270:120,scale=300:300,tile=3x1[b];[a][b]vstack=2",
                "-vsync", "vfr", "-frames:v", "1", str(D / "ab_face.jpg")], check=False)

# ---- 6) report ---------------------------------------------------------------------------------
res = json.loads((D / "shot1_result.json").read_text(encoding="utf-8")) if (D / "shot1_result.json").is_file() else {}
kie = res.get("kie", {})
rep = f"""# A/B report: Kie (Kling 3.0 pro) vs HeyGen cinematic - the Aug walk shot  ({datetime.date.today()})
INTERNAL ONLY - the shared VO names the retired brokerage; never post either clip.

| | control (HeyGen) | variant (Kie) |
|---|---|---|
| clip | {CTRL/'cory_site_walk_blend.mp4'} ({dur(CTRL/'cory_site_walk_blend.mp4'):.2f}s) | {blend} ({dur(blend):.2f}s) |
| render cost | $7.00 cinematic + $1 look (tape note) | ${kie.get('usd', 0):.2f} ({kie.get('credits_consumed')} cr, reconcile {kie.get('reconcile')}) |
| lipsync | ~$0.88 | {next((c for c in COST if 'lipsync' in c), '')} |
| drift/envelope | {ctl_line} | {kie_line} |

Sheets: `ab_sheet.jpg` (top control, bottom Kie, 7 frames each), `ab_face.jpg` (face crops @2/7/12s), `qa_still.jpg`.
Costs this run: {'; '.join(COST) or '(all stages replayed)'}
Eyes-on checklist (Cory): [ ] that's me  [ ] continuous natural walk, no morphing hands/teeth, no extra people  [ ] mouth reads natural while speaking  [ ] clean last second
Decision rule: pass -> new reels default to --renderer=kie (seedance15 <=12s lines, kling3 13-15s); fail -> one --retry=1 on seedance15 at 12s; fail twice -> HeyGen stays for AI-Cory, Kie stays for faceless.
"""
(D / "AB_REPORT.md").write_text(rep, encoding="utf-8")
lineage("asset", kind="video", ref=str(blend), note="Kie A/B variant synced; see AB_REPORT.md")
lineage("run_end", exit=0, outcome="A/B artifacts ready for Cory's eyes-on", produced=[str(blend), str(D / "AB_REPORT.md")])
print(f"== report: {D/'AB_REPORT.md'}"); print("\n".join(COST))
