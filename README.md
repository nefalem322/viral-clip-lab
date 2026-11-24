# viral-clip-lab

A Claude Code skill that runs the whole short-form AI video workflow: find the video that's growing fastest, check it, decode the hook, write the prompts for your own version, and render a finished 9:16 video with the prompt typed under it.

Made for YouTube Shorts, TikTok and Reels. Claude does the work, you approve and post.

## Install

```
git clone https://github.com/nefalem322/viral-clip-lab ~/.claude/skills/viral-clip-lab
cd ~/.claude/skills/viral-clip-lab
pip install -r requirements.txt
python -m playwright install chromium
```

You also need ffmpeg (Claude Code installs it if you ask).

Open Claude Code in an empty folder and type `/viral-clip-lab`, or paste any prompt from `SKILL.md`.

## What's inside

- `SKILL.md` — the 6 steps and their prompts (scout, check, decode, rebuild, ship, track)
- `scripts/render.py` — renders an HTML template frame by frame into an MP4 with your clip inside
- `templates/terminal.html` — the clip + prompt terminal (light or dark, picked from the clip's tone)
- `templates/lab.html`, `templates/chapter.html` — the animated dashboards
- `assets/fonts` — JetBrains Mono, Oswald, Inter (SIL Open Font License)

## Render a terminal video

```
python scripts/render.py --template templates/terminal.html --data job.json --clip clip.mp4 --out out.mp4
```

`job.json`:

```json
{
  "name": "TIN MAN DINNER",
  "variant": "editor",
  "slug": "tin-man",
  "pages": [
    {"tag": "image:", "text": "one still: who, where, light, camera"},
    {"tag": "video:", "text": "one action, one camera move, the length"},
    {"tag": "remix:", "text": "film your own version and swap the character in"}
  ]
}
```

Add `"theme": "light"` or `"dark"` to override the automatic pick.

## Rules the skill follows

- every final video is over 10 seconds
- realistic AI video gets the platform's AI label
- you post everything yourself

MIT licence.
