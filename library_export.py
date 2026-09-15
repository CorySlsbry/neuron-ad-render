#!/usr/bin/env python3
"""library_export.py - name every reusable asset from the persona-ad renders and register it in the
GEO flywheel asset library (~/.geo-flywheel/asset-library, catalog.jsonl) so it can be FOUND and REUSED.

What gets exported (staging copy in Downloads\\neuron-ad-library\\, archive copy owned by the library):
  broll_clip   every cinematic shot (Seedance native voice) + every lip-synced shot (ElevenLabs VO)
  short_video  the finished ads
  image        persona stills (chosen + unchosen) and the end card
  audio        VO takes + voice-casting samples
  thumbnail    one frame per clip (source_id -> the clip) for visual browsing
  other        neuron-ad-library__manifest.json (HeyGen look/video ids, voice ids, prompts, dialogue, costs)

Naming convention (double underscore separates fields, hyphens inside a field):
  neuron-ad__{vertical}__{persona}__S{n}-{scene-slug}__{camera}__{voice}__{dur}s.mp4
  neuron-ad__{vertical}__{persona}__FINAL-v{n}__{voice}__{dur}s.mp4
  neuron-persona__{persona}__{hero|variant-x}.png
  neuron-vo__{vertical}__S{n}__{voice}__{dur}s.mp3
  neuron-voice-sample__{slug}__{line}.mp3
The DESCRIPTION carries the scene + the spoken line, so `find_clip.py "price shopping"` or
`find_clip.py "van phone"` both land on the right file. Idempotent: re-running never duplicates
(the library dedupes by sha256), it only refreshes titles/descriptions.
"""
import sys, json, pathlib, shutil, subprocess, datetime
ENGINE = pathlib.Path(r"C:\Users\Cory\.claude\skills\geo-flywheel\references\engine")
sys.path.insert(0, str(ENGINE))
import asset_library as AL  # the one registrar (P-1: never re-declare a catalog shape)

HERE = pathlib.Path(__file__).resolve().parent
PERS = pathlib.Path(__file__).resolve().parent / "personas"
STAGE = pathlib.Path(r"C:\Users\Cory\Downloads\neuron-ad-library")
BRAND = "neuron-hq"; CLUSTER = "persona-ads"; TODAY = datetime.date.today().isoformat()
shots = json.loads((HERE/"shots.json").read_text(encoding="utf-8"))

def dur(p):
    try: return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)],capture_output=True,text=True).stdout.strip())
    except Exception: return 0.0
def fmt(s): return f"{s:.1f}".rstrip("0").rstrip(".")
def stage(src, name):
    STAGE.mkdir(parents=True, exist_ok=True); dst = STAGE/name
    if not dst.exists() or dst.stat().st_size != pathlib.Path(src).stat().st_size: shutil.copy2(src, dst)
    return dst
def reg(path, type_, title, description, tags, meta, source_id=None, brand=None):
    r = AL.register(brand or BRAND, type_, path, title=title, description=description, cluster=CLUSTER,
                    source_id=source_id, tags=sorted(set(tags + ["persona-ad", "neuron-seo", TODAY[:7]])), meta=meta)
    if r and (r.get("title") != title or r.get("description") != description):
        AL.describe(r["id"], title=title, description=description)   # refresh names on re-runs
    return r
def thumb(clip, name, t=1.0):
    out = STAGE/"thumbs"/name; out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(t),"-i",str(clip),"-frames:v","1","-vf","scale=360:-1",str(out)], check=True)
    return out

# ---------- scene metadata (what each shot IS - the part a filename cannot carry) ----------
SCENES = {
 "auto": {"persona": "P1-operator", "vertical_label": "auto repair shops",
   1: ("open-bay-car-on-lift", "pushin",  "Open auto bay, a car up on the two-post lift behind her, a mechanic under it, doors open to daylight; slow push-in, direct to camera"),
   2: ("front-counter-shop-phone", "pushin", "Behind the shop's front counter, a desk phone beside her, the bay out of focus through the doorway; slow push-in"),
   3: ("back-office-desk", "pushin", "Seated at the back-office desk, window light, laptop on the desk (Apple logo visible); slow push-in")},
 "contractors": {"persona": "P1-operator", "vertical_label": "contractors / home services",
   1: ("jobsite-walk-and-talk", "tracking", "Walking toward camera past a house addition under framing, white work trucks and crew in hi-vis behind; camera tracks back"),
   2: ("work-van-phone", "pushin", "At the open rear of a white work van, levels and tools inside, phone in hand, suburban street; slow push-in"),
   3: ("home-office-desk", "pushin", "Seated at a plain home-office desk, window light, animated gestures; slow push-in")},
}
SCENES["dental"] = {"persona": "P2-advisor", "vertical_label": "dental practices",
   1: ("practice-reception", "pushin", "Bright modern dental practice reception: pale wood front desk, plants, tall windows, a hygienist passing out of focus; slow push-in, direct to camera"),
   2: ("front-desk-phone", "pushin", "Leaning on the practice front desk, a desk phone beside him, calm waiting area behind; slow push-in"),
   3: ("consult-room-desk", "pushin", "Seated in a small consult room at a clean desk, side window light, closed laptop; slow push-in")}
SCENES["general"] = {"persona": "P1-operator", "vertical_label": "general local business",
   1: ("shop-counter", "pushin", "Behind the warm wood counter of a bright small local shop, plain goods and plants out of focus, morning window light; slow push-in, direct to camera"),
   2: ("shop-front-door-phone", "pushin", "Just inside the glass front door of the shop, tree-lined main street out of focus behind, phone in hand; slow push-in"),
   3: ("back-office-table", "pushin", "Seated at a small wooden table in the shop's back office, closed laptop and a mug, side window light; slow push-in")}
SCENES["general-pro"] = dict(SCENES["general"], persona="P1-operator-pro-blouse",
   vertical_label="general local business (professional look: hair down, ivory blouse)")
SCENES["medspa"] = {"persona": "P1-operator-medspa", "vertical_label": "med spa / aesthetics (look: low bun, white tunic)",
   1: ("treatment-room-doorway", "pushin", "Doorway of a bright, calm med-spa treatment room: white walls, treatment bed out of focus, warm daylight, one plant; slow push-in, direct to camera"),
   2: ("reception-desk-phone", "pushin", "Leaning on the pale med-spa reception desk, white desk phone beside her, eucalyptus, pendant light; slow push-in"),
   3: ("consult-nook", "pushin", "Seated in a small consult nook on a pale chair, low table with a closed tablet, side window light; slow push-in")}
VOICE = {"auto": {"native": "seedance-voice"}, "contractors": {"native": "seedance-voice", "vo": "hope"}, "dental": {"native": "seedance-voice", "sts": "eric"},
         "general": {"native": "seedance-voice", "sts": "hope"}, "general-pro": {"native": "seedance-voice", "sts": "hope"}, "medspa": {"native": "seedance-voice", "sts": "hope"},
         "law": {"native": "seedance-voice", "sts": "eric"},
         "autoadvisor": {"native": "seedance-voice", "sts": "jon"}, "tbos": {"native": "seedance-voice", "sts": "mark"}}
# Brand ads live under their OWN brand in the asset library (the lanes already exist there).
BRAND_OF = {"autoadvisor": "auto-advisor", "tbos": "top-builder-ai"}
SCENES["autoadvisor"] = {"persona": "AA1-dale", "vertical_label": "Auto Advisor brand ad (repair shops + dealer service drives)",
   1: ("service-drive-morning", "pushin", "Clean bright service drive of an independent repair shop, early morning: polished concrete, two lifts with plain cars out of focus, open bay doors; slow push-in"),
   2: ("bay-doorway-lift", "pushin", "Bay doorway, a car on the lift out of focus behind, plain grey parts shelf with unlabeled boxes; slow push-in"),
   3: ("shop-office-desk", "pushin", "Tidy shop-office desk in morning light, coffee mug and a closed laptop, plain walls; slow push-in")}
SCENES["tbos"] = {"persona": "TB1-mike", "vertical_label": "Top Builder OS brand ad (1-10 person trades shops)",
   1: ("jobsite-golden-hour-walk", "tracking", "Residential job site at golden hour, plain white work truck and stacked roofing material out of focus; walks toward camera, tracking back"),
   2: ("tailgate-dusk-phone", "pushin", "Leaning on the open tailgate of a plain white pickup in a driveway at dusk, phone in hand; slow push-in"),
   3: ("kitchen-table-laptop-closed", "pushin", "Kitchen table in warm evening light, a CLOSED laptop pushed aside, a mug; slow push-in")}
SCENES["law"] = {"persona": "P2-advisor-law-blazer", "vertical_label": "small law firms (look: navy blazer)",
   1: ("firm-library-lamp", "pushin", "Small firm library: warm wood shelving of plain cloth-bound books, brass desk lamp, tall window daylight; slow push-in, direct to camera"),
   2: ("corridor-window-phone", "pushin", "Quiet minimal corridor of the firm beside a tall window, empty painted walls, city out of focus, phone in hand (glances at it once); slow push-in"),
   3: ("armchair-by-window", "pushin", "Seated in a deep leather armchair beside a tall window, bare wall, side table with one coffee cup; slow push-in")}

ERIC_ID = "cjVigY5qzO86Huf0OWal"
HOPE_ID = "tnSpp4vdxKPjI9w0GnoV"; SARAH_ID = "EXAVITQu4vr4xnSDxMaL"
LOOKS = {"P1-operator": "38fe6195513c85f6e11f4a6355f8c2d3", "P2-advisor": "eceb44fbf76973b1881b526f6b1de3a0",
         "P1-operator-pro-blouse": "1b35dda98b0a36edcbd35f100d54990b", "P1-operator-medspa": "93e2c6af912f6d7a2b375ff4b74121bc",
         "P2-advisor-law-blazer": "cd829141581435bcc63f5d0a70ea2267",
         "AA1-dale": "4cf8e5cbadcb366ed1c3cecc900c85d9", "TB1-mike": "8c638151f0b008355b838784c597658a"}

manifest = {"generated": TODAY, "brand": BRAND, "cluster": CLUSTER, "naming": __doc__.split("Naming convention")[1].split("The DESCRIPTION")[0].strip(),
            "heygen_looks": LOOKS, "voices": {"hope": HOPE_ID, "sarah": SARAH_ID, "eric_premade": "cjVigY5qzO86Huf0OWal"}, "assets": []}
rows = []

def add_clip(ad, n, src, voice_slug, voice_desc, synced):
    sc = SCENES[ad]; slug, cam, scene_desc = sc[n]; d = dur(src)
    shot = shots[ad][n-1]; line = shot["dialogue"]
    name = f"neuron-ad__{ad}__{sc['persona']}__S{n}-{slug}__{cam}__{voice_slug}__{fmt(d)}s.mp4"
    dst = stage(src, name)
    lo, hi = round(d*0.87, 1), round(d*1.15, 1)
    title = f"{sc['persona']} | {sc['vertical_label']} | S{n} {slug.replace('-', ' ')} | {voice_desc}"
    desc = (f"{scene_desc}. She says: \"{line}\" Voice: {voice_desc}. 9:16 1080x1920, {fmt(d)}s. "
            f"Reusable scene: re-lip-sync to any new VO of {lo}-{hi}s (HeyGen lipsync, ~$0.72) via lipsync_shot.py; "
            f"captions are NOT burned in.")
    tags = ["clip", ad, sc["persona"], f"S{n}", f"scene:{slug}", f"camera:{cam}", f"voice:{voice_slug}",
            "synced-to-vo" if synced else "native-speech", "resyncable", "no-captions"]
    meta = {"ad": ad, "shot": n, "persona": sc["persona"], "look_id": LOOKS[sc["persona"]], "scene": slug, "camera": cam,
            "dialogue": line, "voice": voice_desc, "voice_id": {"hope": HOPE_ID, "eric": ERIC_ID}.get(voice_slug),
            "prompt": shot["prompt"], "seconds": round(d, 2), "resync_window_s": [lo, hi],
            "heygen_video_id": (json.loads((HERE/ad/f"shot{n}_result.json").read_text())["data"].get("video_id") if (HERE/ad/f"shot{n}_result.json").exists() else None),
            "heygen_lipsync_id": (json.loads((HERE/ad/f"shot{n}_lipsync.json").read_text())["data"].get("id") if synced and (HERE/ad/f"shot{n}_lipsync.json").exists() else None),
            "cost_usd": 7.0 + (0.72 if synced else 0.0), "used_in_final": f"{ad}_neuron_ad_v1.mp4" if (not synced and ad == "auto") or (synced and ad == "contractors") else None}
    br = BRAND_OF.get(ad, BRAND)
    r = reg(dst, "broll_clip", title, desc, tags, meta, brand=br)
    th = thumb(dst, name.replace(".mp4", ".jpg"))
    reg(th, "thumbnail", title + " (thumb)", f"Thumbnail of {name}", ["thumb", ad, sc["persona"], f"S{n}"], {"of": r["id"]}, source_id=r["id"], brand=br)
    rows.append(("broll_clip", name, fmt(d)+"s", r["id"])); manifest["assets"].append({"id": r["id"], "file": name, "type": "broll_clip", **{k: meta[k] for k in ("ad","shot","scene","camera","voice","dialogue","seconds")}})

for ad in ("auto", "contractors", "dental", "general", "general-pro", "medspa", "law", "autoadvisor", "tbos"):
    if ad not in shots: continue
    for n in (1, 2, 3):
        c = HERE/ad/f"shot{n}_cinematic.mp4"
        if c.exists(): add_clip(ad, n, c, VOICE[ad]["native"], "Seedance native voice (baked in, verbatim script)", synced=False)
        s = HERE/ad/f"shot{n}_synced_precision.mp4"
        if s.exists(): add_clip(ad, n, s, "hope", "ElevenLabs Hope (upbeat), HeyGen precision lip-sync", synced=True)
        t = HERE/ad/f"shot{n}_sts.mp4"
        if t.exists():
            sts_voice = VOICE[ad].get("sts", "hope")
            add_clip(ad, n, t, sts_voice, ("ElevenLabs " + sts_voice.capitalize()) + " via speech-to-speech over the native performance (timing preserved, lips in sync)", synced=True)

# ---------- finished ads ----------
for ad, fn, voice_slug, voice_desc, ver in [("auto", "auto_neuron_ad_v1.mp4", "seedance-voice", "Seedance native voice", "v1"),
                                            ("auto", "auto_neuron_ad_v2.mp4", "seedance-voice", "Seedance native voice (v2: 1s hold + dissolve into the card)", "v2"),
                                            ("contractors", "contractors_neuron_ad_v1.mp4", "hope", "ElevenLabs Hope (HeyGen lipsync - superseded, sync drift)", "v1"),
                                            ("contractors", "contractors_neuron_ad_v2.mp4", "hope", "ElevenLabs Hope via speech-to-speech over the native performance (in sync; v2: 1s hold + dissolve)", "v2"),
                                            ("auto", "auto_neuron_ad_v3.mp4", "hope", "ElevenLabs Hope via speech-to-speech (v3: one voice across shots, 1s hold + dissolve)", "v3"),
                                            ("dental", "dental_neuron_ad_v1.mp4", "eric", "ElevenLabs Eric via speech-to-speech", "v1"),
                                            ("general", "general_neuron_ad_v1.mp4", "hope", "ElevenLabs Hope via speech-to-speech", "v1"),
                                            ("general-pro", "general-pro_neuron_ad_v1.mp4", "hope", "ElevenLabs Hope via speech-to-speech (professional look: hair down, ivory blouse)", "v1"),
                                            ("medspa", "medspa_neuron_ad_v1.mp4", "hope", "ElevenLabs Hope via speech-to-speech (med-spa look: low bun, white tunic; excited pace)", "v1"),
                                            ("law", "law_neuron_ad_v1.mp4", "eric", "ElevenLabs Eric via speech-to-speech (law look: navy blazer)", "v1"),
                                            ("autoadvisor", "autoadvisor_neuron_ad_v1.mp4", "jon", "Auto Advisor brand ad - Dale, ElevenLabs Jon via speech-to-speech", "v1"),
                                            ("tbos", "tbos_neuron_ad_v1.mp4", "mark", "Top Builder OS brand ad - Mike, ElevenLabs Mark via speech-to-speech", "v1")]:
    src = HERE/ad/fn
    if not src.exists(): continue
    d = dur(src); sc = SCENES[ad]
    name = f"neuron-ad__{ad}__{sc['persona']}__FINAL-{ver}__{voice_slug}__{fmt(d)}s.mp4"
    dst = stage(src, name)
    script = " ".join(s["dialogue"] for s in shots[ad])
    adname = {"autoadvisor": "Auto Advisor ad", "tbos": "Top Builder OS ad"}.get(ad, "Neuron SEO ad")
    title = f"FINAL {ver} | {adname} | {sc['vertical_label']} | {sc['persona']} | {voice_desc} | {fmt(d)}s"
    desc = (f"Finished 9:16 ad, karaoke captions burned in, Neuron bed, end card -> neuron-hq.com/free-ai-check. "
            f"Script: \"{script}\" Three scenes: " + "; ".join(f"S{n} {sc[n][0].replace('-', ' ')}" for n in (1,2,3)) + ".")
    br = BRAND_OF.get(ad, BRAND)
    cta = {"autoadvisor": "autoadvisorpartners.com (free Service-Drive Audit)", "tbos": "topbuilderai.com (free job-profit report)"}.get(ad, "neuron-hq.com/free-ai-check")
    r = reg(dst, "short_video", title, desc, ["final", "ad", ad, sc["persona"], f"voice:{voice_slug}", "captions-burned"],
            {"ad": ad, "persona": sc["persona"], "voice": voice_desc, "seconds": round(d, 2), "script": script, "cta": cta}, brand=br)
    th = thumb(dst, name.replace(".mp4", ".jpg"), t=2.0)
    reg(th, "thumbnail", title + " (thumb)", f"Thumbnail of {name}", ["thumb", "final", ad], {"of": r["id"]}, source_id=r["id"], brand=br)
    rows.append(("short_video", name, fmt(d)+"s", r["id"])); manifest["assets"].append({"id": r["id"], "file": name, "type": "short_video", "ad": ad, "seconds": round(d,2)})

# ---------- persona stills ----------
PERSONAS = {"P1-the-operator.png": ("P1-operator", "hero", "CHOSEN. The Operator: 30s, hair in a bun, navy work shirt, trades/shop worlds (auto, contractors, general local). HeyGen look " + LOOKS["P1-operator"]),
            "P2-the-advisor.png":  ("P2-advisor", "hero", "CHOSEN. The Advisor: man, warm authority without a suit, practices (dental, med spa, law). HeyGen look " + LOOKS["P2-advisor"]),
            "P3-the-peer.png":     ("P3-peer", "hero", "Unchosen candidate from the 2026-08-21 casting board"),
            "P4-the-veteran.png":  ("P4-veteran", "hero", "Unchosen candidate from the 2026-08-21 casting board"),
            "P5-the-guide.png":    ("P5-guide", "hero", "Unchosen candidate from the 2026-08-21 casting board"),
            "O1-operator-coil.png": ("P1-operator", "variant-coil", "Operator look variant (hair: coil) - not the chosen look"),
            "O2-operator-pony.png": ("P1-operator", "variant-pony", "Operator look variant (hair: ponytail)"),
            "O3-operator-bob.png":  ("P1-operator", "variant-bob", "Operator look variant (hair: bob)"),
            "O4-operator-crop.png": ("P1-operator", "variant-crop", "Operator look variant (hair: crop)"),
            "O5-operator-wave.png": ("P1-operator", "variant-wave", "Operator look variant (hair: wave)"),
            "P1-look-pro-blouse.png": ("P1-operator", "look-pro-blouse", "CHOSEN for general local business: same P1 face, hair down in soft waves, ivory silk blouse, gold studs (professional-approachable). HeyGen look " + "1b35dda98b0a36edcbd35f100d54990b"),
            "P1-look-pro-blazer.png": ("P1-operator", "look-pro-blazer", "P1 look: neat low ponytail, navy blazer over white tee (reserved for law / professional services)"),
            "P1-look-pro-knit.png":   ("P1-operator", "look-pro-knit", "REJECTED by Cory 2026-08-21 (outfit + hair): half-up hair, charcoal crew-neck over a white collared shirt"),
            "P1-look-pro-sage.png":   ("P1-operator", "look-pro-sage", "P1 look candidate: sleek blunt shoulder-length cut, fitted sage-green button-up (smart-casual / wellness)"),
            "P1-look-pro-mockneck.png": ("P1-operator", "look-pro-mockneck", "P1 look candidate: polished low chignon, black mock-neck, thin gold chain (med spa / premium services)"),
            "P1-look-pro-camel.png":  ("P1-operator", "look-pro-camel", "P1 look candidate: high sleek ponytail, camel unstructured blazer over cream tee (real estate / professional-warm)"),
            "P1-look-medspa.png":     ("P1-operator", "look-medspa", "CHOSEN for MED SPA: sleek low bun, white collarless tunic, small studs (clinical-premium). HeyGen look 93e2c6af912f6d7a2b375ff4b74121bc"),
            "P2-look-law-blazer.png": ("P2-advisor", "look-law-blazer", "CHOSEN for LAW: same P2 face, navy blazer over white open-collar shirt, no tie. HeyGen look cd829141581435bcc63f5d0a70ea2267"),
            "AA1-owner-dale.png":    ("AA1-dale", "hero", "CHOSEN Auto Advisor brand persona: Dale, owner, late 40s, charcoal quarter-zip. HeyGen look 4cf8e5cbadcb366ed1c3cecc900c85d9. Voice: Jon (ElevenLabs)"),
            "AA2-advisor-renee.png": ("AA2-renee", "hero", "Auto Advisor persona candidate (not picked): Renee, service-drive manager / co-owner, navy polo"),
            "AA3-owner-marco.png":   ("AA3-marco", "hero", "Auto Advisor persona - APPROVED alternate: Marco, tech-turned-owner, grey henley"),
            "TB1-roofer-mike.png":   ("TB1-mike", "hero", "CHOSEN Top Builder OS brand persona: Mike, roofing owner-operator, tan work shirt. HeyGen look 8c638151f0b008355b838784c597658a. Voice: Mark (ElevenLabs)"),
            "TB2-coowner-lauren.png":("TB2-lauren", "hero", "Top Builder OS persona - APPROVED alternate: Lauren, co-owner who runs the office and the money, denim shirt"),
            "TB3-foreman-luis.png":  ("TB3-luis", "hero", "Top Builder OS persona - APPROVED alternate: Luis, foreman-turned-owner (HVAC/plumbing), charcoal tee")}
for fn, (persona, kind, d) in PERSONAS.items():
    src = PERS/fn
    if not src.exists(): continue
    name = f"neuron-persona__{persona}__{kind}.png"; dst = stage(src, name)
    chosen = d.startswith("CHOSEN")
    sbrand = "auto-advisor" if persona.startswith("AA") else ("top-builder-ai" if persona.startswith("TB") else BRAND)
    r = reg(dst, "image", f"Persona still | {persona} | {kind}" + (" | CHOSEN" if chosen else ""), d + ". Nano Banana Pro (gemini-3-pro-image), 9:16, the source still for the HeyGen photo avatar.",
            ["persona-still", persona, kind] + (["chosen"] if chosen else ["unchosen"]), {"persona": persona, "kind": kind, "look_id": LOOKS.get(persona)}, brand=sbrand)
    rows.append(("image", name, "", r["id"])); manifest["assets"].append({"id": r["id"], "file": name, "type": "image", "persona": persona, "kind": kind})

# ---------- end card ----------
card = HERE/"contractors"/"build"/"card.png"
if card.exists():
    name = "neuron-ad__endcard__free-ai-check__v1.png"; dst = stage(card, name)
    r = reg(dst, "image", "End card v1 | SEE WHERE YOU SHOW UP | neuron-hq.com/free-ai-check", "3s end card used on the persona ads: last frame darkened, 'SEE WHERE YOU SHOW UP. It's free. neuron-hq.com/free-ai-check', NEURON HQ wordmark. Regenerated per ad by assemble.py from the last frame.", ["end-card", "cta"], {"cta": "neuron-hq.com/free-ai-check"})
    rows.append(("image", name, "", r["id"]))

# ---------- VO takes ----------
for ad, vslug, vid in (("auto", "sarah", SARAH_ID), ("contractors", "hope", HOPE_ID)):
    for n in (1, 2, 3):
        src = HERE/ad/f"shot{n}_vo.mp3"
        if not src.exists(): continue
        d = dur(src); name = f"neuron-vo__{ad}__S{n}__{vslug}__{fmt(d)}s.mp3"; dst = stage(src, name)
        line = shots[ad][n-1]["dialogue"]
        used = "USED in the contractors v1 (lip-synced into the clips)" if ad == "contractors" else "unused in auto v1 (the clips kept their native Seedance voice)"
        r = reg(dst, "audio", f"VO | {ad} | S{n} | {vslug}", f"ElevenLabs {vslug} reading S{n} of the {ad} script: \"{line}\" {fmt(d)}s, mp3 44.1k. {used}.",
                ["vo", ad, f"S{n}", f"voice:{vslug}"], {"ad": ad, "shot": n, "voice_id": vid, "dialogue": line, "seconds": round(d, 2)})
        rows.append(("audio", name, fmt(d)+"s", r["id"]))

# ---------- voice-casting samples ----------
vm = HERE/"voices"/"manifest.json"
if vm.exists():
    for m in json.loads(vm.read_text()):
        src = HERE/"voices"/m["file"]
        if not src.exists(): continue
        line = "auto-hook" if m["gender"] == "female" else "dental-hook"
        name = f"neuron-voice-sample__{m['slug']}__{line}.mp3"; dst = stage(src, name)
        chosen = m["slug"] in ("F1-hope-upbeat", "N9-eric")
        r = reg(dst, "audio", f"Voice sample | {m['label']}" + (" | CHOSEN" if chosen else ""), f"Casting sample ({m['gender']}, {m.get('descriptive')}), ElevenLabs voice_id {m['voice_id']}, reads the {line.replace('-', ' ')}, {m['seconds']}s." + (" CHOSEN for " + ("P1" if m["gender"] == "female" else "P2") + "." if chosen else ""),
                ["voice-sample", m["gender"], f"voice:{m['slug']}"] + (["chosen"] if chosen else []), {"voice_id": m["voice_id"], "label": m["label"], "seconds": m["seconds"]})
        rows.append(("audio", name, f"{m['seconds']}s", r["id"]))

# ---------- manifest + human index ----------
mf = STAGE/"neuron-ad-library__manifest.json"; mf.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
reg(mf, "other", "Persona-ad library manifest", "Index of the persona-ad assets: HeyGen look ids, voice ids, per-clip prompt + dialogue + resync window, costs.", ["manifest"], {"count": len(rows)})
md = ["# Neuron persona-ad asset library", f"Exported {TODAY}. Canonical copies live in `~/.geo-flywheel/asset-library/neuron-hq/<type>/`; this folder is the browsable mirror.",
      "", "Find a clip: `python Downloads\\neuron-ad-render\\find_clip.py \"van phone\"` (or any words from the scene or the spoken line).", "",
      "| type | file | dur | catalog id |", "|---|---|---|---|"] + [f"| {t} | `{n}` | {d} | `{i}` |" for t, n, d, i in rows]
(STAGE/"LIBRARY.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"{len(rows)} assets staged in {STAGE} and registered (cluster={CLUSTER})")
for t, n, d, i in rows: print(f"  {t:<12} {d:>6}  {i}  {n}")
