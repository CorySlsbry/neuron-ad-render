#!/usr/bin/env python3
"""make_thumbs.py - custom YouTube thumbnails for the persona ads (1280x720).

⛔ Brain-First hard rule (Cory 2026-08-03): EVERY YouTube video, long-form AND Short, gets a CUSTOM
thumbnail, generated AND uploaded with the video - never YouTube's auto-still. "Treat the thumbnail
AS A HOOK": big bold hook text (a few words of the video's hook), on-brand image, high contrast,
readable at a tiny size. An upload without one is INCOMPLETE. Each lane's config also carries
require_thumbnail: true.

Layout: the 9:16 frame is cropped to a left-hand portrait panel (the presenter stays a face, not a
letterboxed sliver), the hook sits on a brand-coloured right panel, wordmark bottom-right.
"""
import json, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = pathlib.Path(__file__).resolve().parent
W, H = 1280, 720
FONT_HOOK = r"C:\Windows\Fonts\seguibli.ttf"   # Segoe UI Black Italic
FONT_MARK = r"C:\Windows\Fonts\seguibl.ttf"

# ad -> (final mp4, grab time, hook lines, brand bg, accent, wordmark)
ADS = {
 "auto":        ("auto/shot1_sts.mp4",              6.0, ["THEY ALREADY", "PICKED", "YOUR SHOP."],      (12,10,20), (124,92,255), "NEURON HQ"),
 "contractors": ("contractors/shot1_sts.mp4",       7.0, ["SHE DECIDED", "IT'S YOU", "WEDNESDAY."],     (12,10,20), (124,92,255), "NEURON HQ"),
 "general-pro": ("general-pro/shot1_sts.mp4",       8.0, ["THE BEST", "KIND OF", "PHONE CALL."],        (12,10,20), (124,92,255), "NEURON HQ"),
 "dental":      ("dental/shot1_sts.mp4",            7.0, ["SHE CHOSE", "YOUR PRACTICE", "SUNDAY NIGHT."],(12,10,20), (124,92,255), "NEURON HQ"),
 "medspa":      ("medspa/shot1_sts.mp4",            7.0, ["SHE PICKED", "YOU", "LAST NIGHT."],          (12,10,20), (124,92,255), "NEURON HQ"),
 "law":         ("law/shot1_sts.mp4",               8.0, ["THE CASE", "ALREADY PICKED", "YOUR FIRM."],  (12,10,20), (124,92,255), "NEURON HQ"),
 "autoadvisor": ("autoadvisor/shot1_sts.mp4",       8.0, ["A GOOD", "TUESDAY.", "SHOP RUNS ITSELF."],   (10,12,18), (77,163,255), "AUTO ADVISOR"),
 "tbos":        ("tbos/shot1_sts.mp4",              9.0, ["KNOW WHAT", "EVERY JOB", "MADE."],           (8,8,10),   (99,102,241), "TOP BUILDER OS"),
}

def fit(draw, text, path, target_w, start=96, lo=44):
    for size in range(start, lo - 1, -2):
        f = ImageFont.truetype(path, size)
        if draw.textlength(text, font=f) <= target_w: return f
    return ImageFont.truetype(path, lo)

out_dir = HERE/"thumbs"; out_dir.mkdir(exist_ok=True)
only = sys.argv[1:] or list(ADS)
made = []
for key in only:
    src, t, lines, bg, accent, mark = ADS[key]
    mp4 = HERE/src
    if not mp4.exists(): print(f"SKIP {key}: {src} missing"); continue
    grab = out_dir/f"_{key}_frame.png"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(t),"-i",str(mp4),"-frames:v","1",str(grab)], check=True)
    src_im = Image.open(grab).convert("RGB")

    canvas = Image.new("RGB", (W, H), bg)
    # left portrait panel: crop the 9:16 frame to 4:5-ish and scale to full height
    panel_w = 470
    sw, sh = src_im.size
    want_ratio = panel_w / H
    crop_h = sh
    crop_w = int(sh * want_ratio)
    x0 = max(0, (sw - crop_w)//2)
    face = src_im.crop((x0, 0, x0 + crop_w, crop_h)).resize((panel_w, H), Image.LANCZOS)
    canvas.paste(face, (0, 0))
    # soft edge blend into the brand panel
    grad = Image.new("L", (140, H), 0)
    gd = ImageDraw.Draw(grad)
    for i in range(140): gd.line([(i,0),(i,H)], fill=int(255 * (i/140)))
    plate = Image.new("RGB", (140, H), bg)
    canvas.paste(plate, (panel_w-140, 0), grad)

    dr = ImageDraw.Draw(canvas)
    tx = panel_w + 46; avail = W - tx - 56
    y = 150
    for i, ln in enumerate(lines):
        f = fit(dr, ln, FONT_HOOK, avail, start=104, lo=48)
        col = accent if i == len(lines) - 1 else (255, 255, 255)
        for dx, dy in ((-4,0),(4,0),(0,-4),(0,4),(-4,-4),(4,4),(-4,4),(4,-4)):
            dr.text((tx+dx, y+dy), ln, font=f, fill=(0,0,0))
        dr.text((tx, y), ln, font=f, fill=col)
        y += f.size + 14
    fm = ImageFont.truetype(FONT_MARK, 34)
    wmw = dr.textlength(mark, font=fm)
    dr.rectangle([(W-56-wmw-26, H-92), (W-30, H-40)], fill=accent)
    dr.text((W-56-wmw-13, H-84), mark, font=fm, fill=(255,255,255) if key != "tbos" else (255,255,255))

    dest = out_dir/f"{key}_thumb.jpg"
    canvas.save(dest, quality=92)
    grab.unlink(missing_ok=True)
    kb = dest.stat().st_size//1024
    made.append((key, dest, kb))
    print(f"OK {key:12s} {dest.name} {kb} KB {'(over 2MB!)' if kb > 2048 else ''}")
print(f"\n{len(made)} thumbnails in {out_dir}")
