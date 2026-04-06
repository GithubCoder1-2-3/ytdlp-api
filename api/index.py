import os
from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL

app = Flask(__name__)

# -----------------------------
# CORE CONFIG (SAFE DEFAULTS)
# -----------------------------
BASE_OPTS = {
    "quiet": True,
    "no_warnings": True,

    # IMPORTANT: allow playlists when needed
    "noplaylist": False,

    # 🔥 critical fix: NEVER over-specify formats
    "format": "best",

    # prevents ffmpeg merge crashes on serverless
    "merge_output_format": "mp4",

    # stability for Vercel
    "retries": 3,
    "fragment_retries": 3,
    "socket_timeout": 10,
}


# -----------------------------
# SAFE EXECUTION WRAPPER
# -----------------------------
def safe_extract(url, opts):
    try:
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        # fallback: force generic extractor if YouTube gets picky
        try:
            opts = dict(opts)
            opts["force_generic_extractor"] = True
            with YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception:
            return {"error": str(e)}


# -----------------------------
# HOME / HEALTH CHECK
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok"})


# -----------------------------
# VIDEO ENDPOINT
# -----------------------------
@app.route("/video", methods=["GET"])
def video():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "missing url"}), 400

    opts = BASE_OPTS.copy()
    opts["noplaylist"] = True
    opts["format"] = "best"

    info = safe_extract(url, opts)

    if "error" in info:
        return jsonify(info), 500

    return jsonify({
        "type": "video",
        "id": info.get("id"),
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "url": info.get("url") or info.get("original_url"),
    })


# -----------------------------
# PLAYLIST ENDPOINT
# -----------------------------
@app.route("/playlist", methods=["GET"])
def playlist():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "missing url"}), 400

    opts = BASE_OPTS.copy()
    opts["noplaylist"] = False
    opts["format"] = "best"

    info = safe_extract(url, opts)

    if "error" in info:
        return jsonify(info), 500

    entries = []

    for e in (info.get("entries") or []):
        if not e:
            continue

        entries.append({
            "id": e.get("id"),
            "title": e.get("title"),
            "url": e.get("url"),
            "thumbnail": e.get("thumbnail"),
            "duration": e.get("duration"),
        })

    return jsonify({
        "type": "playlist",
        "id": info.get("id"),
        "title": info.get("title"),
        "count": len(entries),
        "entries": entries,
    })


# -----------------------------
# SEARCH ENDPOINT
# -----------------------------
@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "missing query"}), 400

    opts = BASE_OPTS.copy()

    # IMPORTANT: prevents deep extraction crashes
    opts.update({
        "extract_flat": True,
        "skip_download": True,
        "noplaylist": True,
        "format": "best",
    })

    info = safe_extract(f"ytsearch10:{query}", opts)

    if "error" in info:
        return jsonify(info), 500

    results = []

    for e in (info.get("entries") or []):
        if not e:
            continue

        results.append({
            "id": e.get("id"),
            "title": e.get("title"),
            "url": e.get("url"),
            "duration": e.get("duration"),
        })

    return jsonify({
        "type": "search",
        "query": query,
        "results": results,
    })


# -----------------------------
# VERCEL ENTRY
# -----------------------------
if __name__ == "__main__":
    app.run()
