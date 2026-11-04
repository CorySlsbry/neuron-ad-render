"""kie_ref_video.py - one reference-to-video generation on Kie.ai (Seedance 2.5, Vidu Q4, ...): Cory's face from
reference photos and his voice from a reference clip, native sound on. Reuses kie_shot.py's spend guard (ledger
reservation, caps, balance check), create, poll and download; only the upload is wider (images AND audio).
Cory 2026-10-16: "yes run both 5 second tests" (Seedance 2.5 vs Vidu Q4 identity tests for the POV sketch).

  python kie_ref_video.py <spec.json> [--dry] [--retry=N]
spec.json: {"slug", "out", "model", "est_usd", "input": {...},
            "images": [paths] -> input[images_field], "audio": [paths] -> input[audio_field]}
Fields per model (docs.kie.ai, read 2026-10-16):
  bytedance/seedance-2-5      reference_image_urls (<=30), reference_audio_urls (<=10, 2-30 s), generate_audio,
                              resolution 480p|720p|1080p, aspect_ratio, duration 4-30
  vidu-q4/reference-to-video  reference_image_urls (1-15), reference_audio_urls (<=3, MP3, 3-12 s), audio,
                              resolution 540p..4k, aspect_ratio, duration 3-16
"""
import sys, os, json, time, base64, hashlib, pathlib, datetime

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kie_shot as K  # noqa: E402

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
        ".mp3": "audio/mpeg", ".wav": "audio/wav"}


def upload(path):
    """Kie's free 24 h host, any image or audio file (kie_shot.upload_still only knows png/jpeg)."""
    p = pathlib.Path(path)
    mime = MIME.get(p.suffix.lower())
    if not mime:
        print(f"BAD INPUT: no upload type for {p.name}"); sys.exit(6)
    body = {"base64Data": f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode(),
            "uploadPath": "audio" if mime.startswith("audio") else "images",
            "fileName": f"{p.stem}-{K.sha1_file(p)[:8]}{p.suffix.lower()}"}
    last = ""
    for host in K.UPLOAD_HOSTS:
        try:
            d = K._req("POST", f"{host}/api/file-base64-upload", body, timeout=180)
            data = d.get("data") or {}
            url = data.get("fileUrl") or data.get("downloadUrl")
            if url:
                return url
            last = json.dumps(d)[:200]
        except RuntimeError as e:
            last = str(e)
    print(f"UPLOAD FAILED {p.name}: {last}"); sys.exit(7)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry, retry = "--dry" in sys.argv, int(K.arg("retry", "0"))
    spec = json.loads(pathlib.Path(args[0]).read_text(encoding="utf-8"))
    model, est = spec["model"], float(spec["est_usd"])
    out = pathlib.Path(spec["out"]); tdir = out.parent; tdir.mkdir(parents=True, exist_ok=True)
    files = [*spec.get("images", []), *spec.get("audio", [])]
    for f in files:
        if not pathlib.Path(f).is_file():
            print(f"BAD INPUT: missing {f}"); sys.exit(6)
    key = hashlib.sha1(json.dumps([model, spec["input"], [K.sha1_file(f) for f in files]], sort_keys=True).encode()).hexdigest()[:16]
    key += f"-r{retry}" if retry else ""
    tasks = K.tasks_load(tdir); rec = tasks.get(key) or {}
    if rec.get("out_sha") and out.is_file() and K.sha1_file(out) == rec["out_sha"]:
        print(f"DOWNLOADED {out} (replayed, $0)"); return 0
    capline = K.guard_caps(est, dry)
    bal = K.credits()
    print(f"ESTIMATE {model} {spec['input'].get('duration')}s {spec['input'].get('resolution')} ~${est:.2f} | {capline} | "
          f"balance ${bal['usd']:.2f} ({bal['credits']:.0f} cr)")
    if dry:
        print(json.dumps({"model": model, "input": spec["input"], "images": spec.get("images"), "audio": spec.get("audio")}, indent=1))
        return 0
    if bal["usd"] < est:
        print(f"NO_CREDITS: balance ${bal['usd']:.2f} < estimate ${est:.2f}"); sys.exit(5)
    task_id = rec.get("taskId") if rec.get("state") not in (None, "fail") else None
    rid = hashlib.sha1(f"{os.getpid()}|{time.time()}|{key}".encode()).hexdigest()[:12]
    ts0 = datetime.datetime.now().isoformat(timespec="seconds")
    if not task_id:
        K.reserve(est, {"rid": rid, "ts": ts0, "slug": spec["slug"], "out": str(out), "model": model,
                        "duration": spec["input"].get("duration"), "task_id": None, "key": key, "usd": est,
                        "credits": round(est / K.CREDIT_USD), "state": "reserved", "balance_before": bal["credits"]})
        try:
            inp = dict(spec["input"])
            if spec.get("images"):   # nano-banana-edit names its field image_urls
                inp[spec.get("images_field", "reference_image_urls")] = [upload(p) for p in spec["images"]]
            if spec.get("audio"):
                inp[spec.get("audio_field", "reference_audio_urls")] = [upload(p) for p in spec["audio"]]
            task_id = K.create_task(model, inp)
        except BaseException as e:
            K.ledger_patch(rid, {"state": "fail", "fail": f"create: {str(e)[:160]}"}); raise
        K.ledger_patch(rid, {"task_id": task_id, "state": "submitted"})
        tasks[key] = {"taskId": task_id, "state": "submitted", "created": ts0, "model": model}
        K.tasks_save(tdir, tasks)
        print(f"TASK {task_id}", flush=True)
    else:
        print(f"RESUME {task_id}", flush=True)
    try:
        video_url, consumed, data = K.poll(task_id)
    except K.KieFailed as e:
        K.ledger_patch(rid, {"_task_id": task_id, "state": "fail", "fail": f"{e.args[0]}: {e.args[1] if len(e.args) > 1 else ''}"})
        tasks[key]["state"] = "fail"; K.tasks_save(tdir, tasks)
        print(f"FAILED {e.args[0]} {e.args[1] if len(e.args) > 1 else ''}"); sys.exit(2)
    except K.KieStillRunning:
        print(f"STILL RUNNING - task {task_id} kept; re-run to resume"); sys.exit(3)
    if spec.get("kind") == "image":     # K.download's ffprobe duration check would reject a still
        import urllib.request
        urllib.request.urlretrieve(video_url, out)
        if out.stat().st_size < 1000:
            print(f"FAILED BAD_DOWNLOAD {out} is {out.stat().st_size} bytes"); sys.exit(2)
        dur = 0.0
    else:
        dur = K.download(video_url, out)
    after = K.credits()
    usd = round((consumed or est / K.CREDIT_USD) * K.CREDIT_USD, 4)
    K.ledger_patch(rid, {"_task_id": task_id, "state": "success", "credits": round(consumed or est / K.CREDIT_USD), "usd": usd,
                         "balance_after": after["credits"], "settled": datetime.datetime.now().isoformat(timespec="seconds")})
    tasks[key].update({"state": "success", "resultUrl": video_url, "out": str(out), "out_sha": K.sha1_file(out)}); K.tasks_save(tdir, tasks)
    print(f"DOWNLOADED {out} {out.stat().st_size // 1024} KB {dur:.2f}s")
    print(f"COST ${usd:.2f} ({consumed:.0f} cr) | KIE credits after: {after['credits']:.0f} (${after['usd']:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
