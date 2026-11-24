---
name: viral-clip-lab
description: Find the fastest-growing AI videos on YouTube Shorts, TikTok and Reels, check them, decode the hook, write prompts for your own version and render a finished 9:16 video with the prompt terminal. Use when the user wants a viral short-form AI video made, analysed or rebuilt.
---

# viral-clip-lab

Run the steps in order. Show the user the result of each step and wait for "go" before posting anything. Never publish.

## 1. Scout
Find 30 AI-generated videos posted in the last 48 hours on YouTube Shorts, TikTok and Instagram Reels about the user's niche. Use yt-dlp and web search. For each: link, author, platform, upload time, views, likes, length. Calculate views per hour since upload, rank by it, show the top 10 as a table and mark anything under 10 seconds.

## 2. Check
Download the top pick with yt-dlp. Make a contact sheet (8 frames across the video plus the last frame). Look at the frames and answer:
1. Is it AI-generated? Name the evidence (generator mark, impossible physics, hands, text).
2. Search the subject on YouTube, TikTok and Instagram: was the same video already big in the last 7 days?
3. Watermarks, handles, end cards, "comment for the prompt" outros: pixel boxes and timestamps.
Answer TAKE or SKIP with one line why.

## 3. Decode
Extract the first 3 seconds at 4 fps (`ffmpeg -t 3 -vf fps=4`) and transcribe the audio with faster-whisper. Read the frames in order. Say what happens in second 1, what the viewer expects, where the payoff lands, and which hook it is:
impossible physics in an ordinary place · bait and switch · tiny action, huge result · an animal makes a deal · famous characters, ordinary room.
Write 5 hook lines for the user's own version.

## 4. Rebuild
From the frames write three prompts, each under 200 characters, one action per shot:
- image: one still. who, where, light, camera, vertical 9:16
- video: one action, one camera move, the length, what must not change
- remix: how to film your own version on a phone and swap the character in with motion control

## 5. Ship
Crop black bars, remove the watermarks from step 2 (crop them off if blur leaves a smear), scale to 1080x1920, keep the video over 10 seconds. Render the terminal:
`python scripts/render.py --template templates/terminal.html --data job.json --clip clip.mp4 --out final.mp4`
with the three prompts as pages and `"variant": "editor"`. Then write the caption: what happens in one line, the hook in the first 5 words, a question at the end; one version for TikTok, one for Shorts. Remind the user to add the AI label where the platform asks.

## 6. Track
Keep tracker.csv: video, platform, date posted, views after 24 h and 7 days, hook type. Each morning update views, estimate the payout per platform from rates.json (ranges, mark them est.), say which hook type won the week, and add winning hook lines to hooks.txt.
