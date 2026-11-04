#!/usr/bin/env python3
"""_conform.py - make a generated clip a first-class citizen of a pipeline's bin.
  python _conform.py <in.mp4> --to <out.(mkv|mp4)> [--fps=30] [--size=1080x1920] [--strip-audio]
Footage-cut bins (video-production/playbooks/footage-cut.md) hold stabilized 1080x1920 30 fps intermediates with
PCM audio (`stab/*_stab.mkv`); the avatar rail assembles at 30 fps too. A Kie/HeyGen clip may come back at 24 fps or
with AAC 44.1 kHz, so conform it once here (scale-to-cover + centre crop, constant fps, yuv420p) and never guess.
Prints the probed result so the driver can cite it. Exit 1 if the output does not probe as requested."""
import sys, pathlib, subprocess
src = pathlib.Path(sys.argv[1])
to = pathlib.Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--to=")), "") or (sys.argv[sys.argv.index("--to") + 1] if "--to" in sys.argv else ""))
fps = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--fps=")), 30))
size = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--size=")), "1080x1920")
w, h = (int(x) for x in size.lower().split("x"))
strip_audio = "--strip-audio" in sys.argv
if not src.is_file() or not to: sys.exit("usage: _conform.py <in> --to <out> [--fps=30] [--size=1080x1920] [--strip-audio]")
to.parent.mkdir(parents=True, exist_ok=True)
vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},format=yuv420p"
audio = ["-an"] if strip_audio else (["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"] if to.suffix.lower() == ".mkv" else ["-c:a", "aac", "-b:a", "160k", "-ar", "48000"])
cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-vf", vf,
       "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-r", str(fps), *audio, str(to)]
subprocess.run(cmd, check=True)
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,pix_fmt",
                        "-show_entries", "format=duration", "-of", "default=nw=1", str(to)], capture_output=True, text=True).stdout
got = dict(l.split("=", 1) for l in probe.strip().splitlines() if "=" in l)
ok = got.get("width") == str(w) and got.get("height") == str(h) and got.get("r_frame_rate", "").startswith(f"{fps}/")
print(f"CONFORMED {to} {got.get('width')}x{got.get('height')} {got.get('r_frame_rate')} {got.get('pix_fmt')} {float(got.get('duration', 0)):.2f}s -> {'OK' if ok else 'MISMATCH'}")
sys.exit(0 if ok else 1)
