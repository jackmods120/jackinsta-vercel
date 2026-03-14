from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import subprocess
import json
import os


def run_ytdlp(args):
    """yt-dlp بەکاربهێنە و ئەنجامەکە وەربگرە"""
    try:
        result = subprocess.run(
            ["yt-dlp"] + args,
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), -1


def get_info(url):
    """زانیاری پۆست/ڕیلس وەربگرە"""
    out, code = run_ytdlp([
        "--dump-json",
        "--no-playlist",
        "--no-warnings",
        url
    ])
    if code != 0:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def get_profile(username):
    """زانیاری پرۆفایڵ وەربگرە"""
    url = f"https://www.instagram.com/{username}/"
    out, code = run_ytdlp([
        "--dump-json",
        "--playlist-items", "1",
        "--no-warnings",
        url
    ])
    if code != 0:
        return None
    try:
        lines = [l for l in out.splitlines() if l.startswith("{")]
        if lines:
            d = json.loads(lines[0])
            return {
                "username":  d.get("uploader_id", username),
                "full_name": d.get("uploader", ""),
                "url":       f"https://www.instagram.com/{username}/",
            }
    except Exception:
        pass
    return None


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)
        url    = params.get("url",  [None])[0]
        user   = params.get("user", [None])[0]

        # ── / ──────────────────────────────────────────────
        if path == "" or path == "/":
            self._send(200, {
                "name":    "JackInsta API",
                "version": "1.0",
                "author":  "JACK",
                "channel": "@jack_721_mod",
                "powered": "yt-dlp",
                "endpoints": {
                    "/api/info":    "زانیاری پۆست یان ڕیلس",
                    "/api/video":   "لینکی ڤیدیۆ/ڕیلس",
                    "/api/audio":   "لینکی ئۆدیۆ",
                    "/api/profile": "زانیاری پرۆفایڵ  (?user=ناو)",
                }
            })
            return

        # ── پشکنینی url ────────────────────────────────────
        if path in ["/api/info", "/api/video", "/api/audio"]:
            if not url:
                self._send(400, {"error": "پێویستە ?url=لینکەکە زیاد بکەیت"})
                return
            if "instagram.com" not in url:
                self._send(400, {"error": "تەنها لینکی Instagram پشتگیری دەکرێت"})
                return

        # ── /api/info ──────────────────────────────────────
        if path == "/api/info":
            data = get_info(url)
            if not data:
                self._send(404, {"error": "پۆستەکە نەدۆزرایەوە"})
                return
            self._send(200, {
                "status":      "success",
                "title":       data.get("title", ""),
                "description": data.get("description", ""),
                "author":      data.get("uploader", ""),
                "username":    data.get("uploader_id", ""),
                "duration":    data.get("duration", 0),
                "views":       data.get("view_count", 0),
                "likes":       data.get("like_count", 0),
                "thumbnail":   data.get("thumbnail", ""),
                "video_url":   data.get("url", ""),
                "webpage":     data.get("webpage_url", url),
            })

        # ── /api/video ─────────────────────────────────────
        elif path == "/api/video":
            data = get_info(url)
            if not data:
                self._send(404, {"error": "پۆستەکە نەدۆزرایەوە"})
                return

            # باشترین کوالیتی
            formats = data.get("formats", [])
            best = None
            for f in reversed(formats):
                if f.get("vcodec", "none") != "none":
                    best = f
                    break

            video_url = best.get("url") if best else data.get("url", "")
            self._send(200, {
                "status":    "success",
                "url":       video_url,
                "title":     data.get("title", ""),
                "thumbnail": data.get("thumbnail", ""),
                "type":      "video"
            })

        # ── /api/audio ─────────────────────────────────────
        elif path == "/api/audio":
            data = get_info(url)
            if not data:
                self._send(404, {"error": "پۆستەکە نەدۆزرایەوە"})
                return

            # باشترین ئۆدیۆ
            formats = data.get("formats", [])
            best_audio = None
            for f in formats:
                if f.get("acodec", "none") != "none" and f.get("vcodec", "none") == "none":
                    best_audio = f
                    break

            audio_url = best_audio.get("url") if best_audio else data.get("url", "")
            self._send(200, {
                "status": "success",
                "url":    audio_url,
                "title":  data.get("title", ""),
                "type":   "audio"
            })

        # ── /api/profile ───────────────────────────────────
        elif path == "/api/profile":
            if not user:
                self._send(400, {"error": "پێویستە ?user=ناوی-هەژمار زیاد بکەیت"})
                return
            data = get_profile(user.lstrip("@"))
            if not data:
                self._send(404, {"error": "پرۆفایڵەکە نەدۆزرایەوە"})
                return
            self._send(200, {"status": "success", **data})

        else:
            self._send(404, {"error": "Endpoint نەدۆزرایەوە"})

    def _send(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass
