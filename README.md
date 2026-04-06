# YT Downloader API — Vercel Backend

A FastAPI + yt-dlp backend deployable to Vercel in one command.

## Deploy

```bash
npm i -g vercel
vercel deploy
```

That's it. Vercel auto-detects Python and installs `requirements.txt`.

> **Note:** Vercel Serverless Functions have a **10 second** response timeout on the Hobby plan and **60 seconds** on Pro. Long videos may time out. For large downloads, upgrade to Pro or use a VPS.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check + endpoint map |
| `GET` | `/video/<VIDEO_ID>` | Download video (MP4) |
| `GET` | `/audio/<VIDEO_ID>` | Download audio (MP3 etc.) |
| `GET` | `/metadata/<VIDEO_ID>` | Get video metadata (JSON) |
| `GET` | `/playlist/<PLAYLIST_ID>` | Download full playlist as ZIP |

### Query Parameters

**`/video/<id>`**
- `quality` — `best` (default), `1080p`, `720p`, `480p`, `360p`

**`/audio/<id>`**
- `fmt` — `mp3` (default), `m4a`, `opus`, `wav`

**`/playlist/<id>`**
- `audio_only` — `false` (default), `true` → downloads as MP3s

### Examples

```
GET /video/dQw4w9WgXcQ
GET /video/dQw4w9WgXcQ?quality=720p
GET /audio/dQw4w9WgXcQ?fmt=m4a
GET /metadata/dQw4w9WgXcQ
GET /playlist/PLbpi6ZahtOH6Ar_3GPy3workqsOtu2e3H
GET /playlist/PLbpi6ZahtOH6Ar_3GPy3workqsOtu2e3H?audio_only=true
```

---

## Local Development

```bash
pip install -r requirements.txt
uvicorn api.index:app --reload
```

You'll also need `ffmpeg` installed locally for audio extraction:
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`
- **Windows:** Download from https://ffmpeg.org/download.html

> Vercel's runtime includes ffmpeg automatically.

---

## ⚠️ Legal Notice

This tool is for personal use only. Downloading copyrighted YouTube content may violate YouTube's Terms of Service. Only download content you have rights to.
