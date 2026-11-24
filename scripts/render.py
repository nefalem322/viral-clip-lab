"""Render an HTML template frame by frame into an MP4, with a source clip inside it.

The template exposes two functions:
    window.setup(data)            -> called once with the JSON data
    window.render(t, frameUrl)    -> draws the frame at time t (seconds); frameUrl = the clip frame for t
render(t) must be a pure function of t, so the video is deterministic (no dropped frames, no drift).

usage:
  python render.py --template templates/terminal.html --data job.json --clip clip.mp4 --out out.mp4
  optional: --w 1080 --h 1920 --fps 30 --start 0 --end 12.5 --speed 1.0
needs: ffmpeg in PATH (or FFMPEG env var), pip install playwright && python -m playwright install chromium
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def ffmpeg_bin():
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def probe(path):
    r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", str(path)], capture_output=True, text=True, errors="ignore")
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    size = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", r.stderr)
    audio = "Audio:" in r.stderr
    if not dur:
        sys.exit(f"cannot read {path}: is it a video?")
    d = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3])
    return d, (int(size[1]), int(size[2])) if size else (0, 0), audio


def analyze(frames, samples=12):
    """Pick the terminal theme from the clip: mean brightness -> dark/light, dominant vivid hue -> accent colour."""
    import colorsys
    from PIL import Image
    step = max(1, len(frames) // samples)
    luma, hues = [], [0.0] * 36
    for f in frames[::step][:samples]:
        px = Image.open(f).convert("RGB").resize((64, 64)).tobytes()
        for i in range(0, len(px), 3):
            r, g, b = px[i], px[i + 1], px[i + 2]
            luma.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s > 0.35 and v > 0.3:
                hues[int(h * 36) % 36] += s * v
    mean = sum(luma) / len(luma) / 255
    mode = "light" if mean > 0.44 else "dark"   # 0.44: daylight / white scenes read as light, night scenes as dark
    # smooth the hue histogram a little and take the peak
    sm = [hues[i - 1] * .5 + hues[i] + hues[(i + 1) % 36] * .5 for i in range(36)]
    peak = max(range(36), key=lambda i: sm[i])
    hue = (peak + 0.5) * 10 if sm[peak] > 0 else 330
    return {"mode": mode, "brightness": round(mean, 3), "hue": round(hue)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--clip", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=0.0, help="cut the clip at this second (0 = full clip)")
    ap.add_argument("--speed", type=float, default=1.0, help="1.03 = 3%% faster (light uniqueization)")
    ap.add_argument("--quality", type=int, default=90, help="JPEG quality of captured frames")
    ap.add_argument("--dur", type=float, default=0.0, help="force the video length; the clip loops inside it")
    ap.add_argument("--mute", action="store_true", help="silent track instead of the clip audio (dashboards)")
    a = ap.parse_args()

    from playwright.sync_api import sync_playwright

    clip = pathlib.Path(a.clip).resolve()
    src_dur, (cw, ch), has_audio = probe(clip)
    end = a.end if a.end > 0 else src_dur
    dur = (end - a.start) / a.speed
    if a.dur > 0:
        dur = a.dur
    if a.mute:
        has_audio = False
    if dur < 10:
        print(f"WARNING: output is {dur:.1f} s. X counts a view after ~10 s of watch time, so clips under 10 s get less reach.",
              flush=True)
    n = int(dur * a.fps)
    data = json.load(open(a.data, encoding="utf-8"))
    data.setdefault("duration", dur)
    data.setdefault("clip", {"w": cw, "h": ch})

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="vcl_"))
    try:
        # 1. the clip as numbered frames at the output fps (speed change applied here)
        print(f"extracting {n} clip frames ...", flush=True)
        subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-ss", str(a.start), "-to", str(end), "-i", str(clip),
                        "-vf", f"setpts=PTS/{a.speed},fps={a.fps}", "-q:v", "3", str(tmp / "f%05d.jpg")], check=True)
        frames = sorted(tmp.glob("f*.jpg"))
        if not frames:
            sys.exit("no frames extracted")
        auto = analyze(frames)
        th = data.get("theme")
        if isinstance(th, str):          # "dark" / "light" forced by hand, accent still from the clip
            auto["mode"] = th
        elif isinstance(th, dict):
            auto.update(th)
        data["theme"] = auto
        print(f"theme: {auto['mode']} (brightness {auto['brightness']}), accent hue {auto['hue']}", flush=True)

        # 2. encoder: frames in on stdin, audio from the clip
        out = pathlib.Path(a.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [ffmpeg_bin(), "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(a.fps), "-c:v", "mjpeg", "-i", "-"]
        if has_audio:
            cmd += ["-ss", str(a.start), "-to", str(end), "-i", str(clip), "-map", "0:v", "-map", "1:a",
                    "-af", f"atempo={a.speed}", "-c:a", "aac", "-b:a", "160k"]
        else:  # X wants an audio track
            cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a",
                    "-c:a", "aac", "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
                "-movflags", "+faststart", "-t", f"{dur:.3f}", str(out)]
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        # 3. the page, one screenshot per frame
        tpl = pathlib.Path(a.template).resolve()
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--allow-file-access-from-files", "--disable-web-security"])
            page = browser.new_page(viewport={"width": a.w, "height": a.h}, device_scale_factor=1)
            page.goto(tpl.as_uri())
            page.evaluate("d => window.setup(d)", {**data, "root": ROOT.as_uri()})
            page.evaluate("() => document.fonts.ready")
            for i in range(n):
                f = frames[i % len(frames)] if a.dur > 0 else frames[min(i, len(frames) - 1)]
                page.evaluate("([t, u]) => window.render(t, u)", [i / a.fps, f.as_uri()])
                page.wait_for_function("() => window.__ready === true")
                enc.stdin.write(page.screenshot(type="jpeg", quality=a.quality))
                if i % (a.fps * 2) == 0:
                    print(f"  frame {i}/{n}", flush=True)
            browser.close()
        enc.stdin.close()
        if enc.wait() != 0:
            sys.exit("ffmpeg failed")
        print("done:", out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
