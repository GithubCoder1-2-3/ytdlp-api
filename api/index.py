from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import io
import os
import zipfile
import tempfile
import json

app = FastAPI(title="YT Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

YDL_BASE_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "cachedir": False,
    "concurrent_fragment_downloads": 1,
    "nopart": True,
    "overwrites": True,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    },
    "extractor_args": {
        "youtube": {
            "player_client": ["android"]
        }
    },
    "nocheckcertificate": True,
    "retries": 3,
    "fragment_retries": 3,
}


def load_cookies_from_env():
    cookie_data = os.getenv("YOUTUBE_COOKIES")
    if not cookie_data:
        return None

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
        tmp.write(cookie_data)
        tmp.flush()
        tmp.close()
        return tmp.name
    except Exception:
        return None


def make_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


@app.get("/video/{video_id}")
async def download_video(video_id: str, quality: str = "best"):
    url = make_video_url(video_id)

    format_map = {
    "best": "best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
}

    fmt = format_map.get(quality) or "best/bestvideo+bestaudio/best"
    
    tmpdir = "/tmp"
    output_path = os.path.join(tmpdir, "%(title)s.%(ext)s")

    ydl_opts = {
        **YDL_BASE_OPTS,
        "format": fmt,
        "outtmpl": output_path,
        "merge_output_format": "mp4",
    }

    cookiefile = load_cookies_from_env()
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", video_id)

        files = os.listdir(tmpdir)
        if not files:
            raise HTTPException(status_code=500, detail="Download failed — no file produced")

        filepath = os.path.join(tmpdir, files[0])
        filename = f"{title}.mp4".replace("/", "-")

        file_like = open(filepath, "rb")

        return StreamingResponse(
            file_like,
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cookiefile and os.path.exists(cookiefile):
            os.remove(cookiefile)


@app.get("/audio/{video_id}")
async def download_audio(video_id: str, fmt: str = "mp3"):
    url = make_video_url(video_id)

    audio_format = fmt if fmt in ("mp3", "m4a", "opus", "wav") else "mp3"

    tmpdir = "/tmp"
    output_path = os.path.join(tmpdir, "%(title)s.%(ext)s")

    ydl_opts = {
        **YDL_BASE_OPTS,
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_format,
            "preferredquality": "192",
        }],
    }

    cookiefile = load_cookies_from_env()
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", video_id)

        files = os.listdir(tmpdir)
        if not files:
            raise HTTPException(status_code=500, detail="Audio extraction failed")

        filepath = os.path.join(tmpdir, files[0])
        filename = f"{title}.{audio_format}".replace("/", "-")

        file_like = open(filepath, "rb")

        return StreamingResponse(
            file_like,
            media_type={
                "mp3": "audio/mpeg",
                "m4a": "audio/mp4",
                "opus": "audio/ogg",
                "wav": "audio/wav",
            }.get(audio_format, "audio/mpeg"),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cookiefile and os.path.exists(cookiefile):
            os.remove(cookiefile)


@app.get("/metadata/{video_id}")
async def get_metadata(video_id: str):
    url = make_video_url(video_id)
    ydl_opts = {**YDL_BASE_OPTS, "skip_download": True}

    cookiefile = load_cookies_from_env()
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        if cookiefile and os.path.exists(cookiefile):
            os.remove(cookiefile)

    safe = {
        "id": info.get("id"),
        "title": info.get("title"),
        "description": info.get("description"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "channel": info.get("uploader"),
        "channel_url": info.get("uploader_url"),
        "upload_date": info.get("upload_date"),
        "thumbnail": info.get("thumbnail"),
        "tags": info.get("tags", []),
        "categories": info.get("categories", []),
        "formats": [
            {
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution"),
                "fps": f.get("fps"),
                "vcodec": f.get("vcodec"),
                "acodec": f.get("acodec"),
                "filesize": f.get("filesize"),
                "tbr": f.get("tbr"),
            }
            for f in info.get("formats", [])
        ],
    }

    return JSONResponse(content=safe)


@app.get("/playlist/{playlist_id}")
async def download_playlist(playlist_id: str, audio_only: bool = False):
    url = f"https://www.youtube.com/playlist?list={playlist_id}"

    tmpdir = "/tmp"

    if audio_only:
        ydl_opts = {
            **YDL_BASE_OPTS,
            "noplaylist": False,
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmpdir, "%(playlist_index)s - %(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
    else:
        ydl_opts = {
            **YDL_BASE_OPTS,
            "noplaylist": False,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": os.path.join(tmpdir, "%(playlist_index)s - %(title)s.%(ext)s"),
            "merge_output_format": "mp4",
        }

    cookiefile = load_cookies_from_env()
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            playlist_title = info.get("title", playlist_id)

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        if cookiefile and os.path.exists(cookiefile):
            os.remove(cookiefile)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(tmpdir)):
            zf.write(os.path.join(tmpdir, fname), fname)

    zip_buffer.seek(0)
    zip_data = zip_buffer.read()

    zip_filename = f"{playlist_title}.zip".replace("/", "-")

    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename=\"{zip_filename}\"'},
    )


@app.get("/")
async def root():
    return {
        "status": "ok",
        "endpoints": {
            "video": "/video/<VIDEO_ID>?quality=best|1080p|720p|480p|360p",
            "audio": "/audio/<VIDEO_ID>?fmt=mp3|m4a|opus|wav",
            "metadata": "/metadata/<VIDEO_ID>",
            "playlist": "/playlist/<PLAYLIST_ID>?audio_only=false",
        }
    }
