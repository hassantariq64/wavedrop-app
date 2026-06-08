# ◉ WaveDrop — Universal Media Downloader

A free, open-source desktop app for macOS that downloads audio and video
from YouTube, SoundCloud, Instagram, TikTok, and 1000+ other sites.

---

## Quick Start

### Step 1 — One-time setup
Open Terminal, navigate to this folder, and run:

```bash
chmod +x setup.sh launch.sh
./setup.sh
```

This installs: Homebrew (if needed), ffmpeg, yt-dlp, and customtkinter.

### Step 2 — Run the app
```bash
python3 app.py
```
Or double-click `launch.sh` in Finder.

---

## Features

- Download **audio** (MP3, M4A, WAV, FLAC) or **video** (MP4, WebM, MKV)
- Quality selector: best / 320kbps / 192kbps / 128kbps (audio), 1080p / 720p / 480p (video)
- Supports **YouTube, SoundCloud, Instagram, TikTok, Twitter/X, Vimeo**, and 1000+ sites
- Real-time progress bar with download speed and ETA
- Download history (per session)
- Dark mode UI
- All downloads saved to `~/Downloads/WaveDrop/`

---

## Requirements

| Dependency    | Purpose                     | Cost |
|---------------|-----------------------------|------|
| Python 3.9+   | App runtime                 | Free |
| yt-dlp        | Download engine             | Free |
| ffmpeg        | Audio/video conversion      | Free |
| customtkinter | Modern macOS GUI framework  | Free |

Total cost: **$0**

---

## Updating yt-dlp

YouTube frequently changes its systems. If downloads stop working:

```bash
pip3 install -U yt-dlp
```

---

## Sites That Work

YouTube, SoundCloud, Instagram (public posts), TikTok, Twitter/X, Vimeo,
Dailymotion, Twitch clips, Reddit videos, Facebook videos, and 1000+ more.

> **Note:** Spotify is a streaming service and does NOT provide downloadable
> audio streams. For Spotify, use a different approach (e.g., recording).

---

## Troubleshooting

**"yt-dlp not found"** → Run `./setup.sh` again
**"ffmpeg not found"** → Run `brew install ffmpeg`
**Download fails** → Update yt-dlp: `pip3 install -U yt-dlp`
**Instagram/TikTok fails** → Some content is private or geo-restricted

---

## License

This project uses yt-dlp (Unlicense) and ffmpeg (LGPL).
WaveDrop itself is free and open-source.
