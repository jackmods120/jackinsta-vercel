from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
import json
import re


# ── هێنانی زانیاری Instagram بە requests ─────────────────────
def fetch_instagram(url):
    """
    بەکارهێنانی Instagram oEmbed + GraphQL
    بۆ وەرگرتنی لینکی ڤیدیۆ
    """
    try:
        # ١. پاک کردنی لینک
        url = url.split("?")[0].rstrip("/") + "/"

        # ٢. هێنانی shortcode
        match = re.search(r"/(p|reel|tv)/([A-Za-z0-9_-]+)", url)
        if not match:
            return None
        shortcode = match.group(2)

        # ٣. oEmbed API بۆ زانیاری سەرەکی
        oembed = requests.get(
            "https://www.instagram.com/api/v1/oembed/",
            params={"url": url, "hidecaption": 0},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        meta = oembed.json() if oembed.status_code == 200 else {}

        # ٤. GraphQL بۆ لینکی ڤیدیۆ
        gql_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
        gql = requests.get(
            gql_url,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
                "Accept": "application/json",
                "Referer": "https://www.instagram.com/",
            },
            timeout=15
        )

        video_url   = ""
        thumbnail   = meta.get("thumbnail_url", "")
        title       = meta.get("title", "")
        author      = meta.get("author_name", "")
        username    = meta.get("author_name", "")

        if gql.status_code == 200:
            try:
                gdata = gql.json()
                media = (
                    gdata.get("graphql", {}).get("shortcode_media") or
                    gdata.get("items", [{}])[0] if "items" in gdata else {}
                )
                if isinstance(media, dict):
                    video_url = media.get("video_url", "")
                    thumbnail = media.get("display_url", thumbnail)
                    if not title:
                        cap = media.get("edge_media_to_caption", {})
                        edges = cap.get("edges", [])
                        title = edges[0]["node"]["text"][:100] if edges else ""
            except Exception:
                pass

        return {
            "shortcode": shortcode,
            "title":     title or f"Instagram Post {shortcode}",
            "author":    author,
            "username":  username,
            "thumbnail": thumbnail,
            "video_url": video_url,
            "webpage":   url,
        }

    except Exception:
        return None


def fetch_profile(username):
    try:
        r = requests.get(
            f"https://www.instagram.com/{username}/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        full_name = ""
        match = re.search(r'"full_name":"([^"]+)"', r.text)
        if match:
            full_name = match.group(1)
        followers = ""
        fmatch = re.search(r'"edge_followed_by":\{"count":(\d+)\}', r.text)
        if fmatch:
            followers = fmatch.group(1)
        return {
            "username":  username,
            "full_name": full_name,
            "followers": int(followers) if followers else 0,
            "url":       f"https://www.instagram.com/{username}/",
        }
    except Exception:
        return None


# ── Handler ───────────────────────────────────────────────────
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
                "endpoints": {
                    "/api/info":    "زانیاری پۆست یان ڕیلس  ?url=",
                    "/api/video":   "لینکی ڤیدیۆ/ڕیلس       ?url=",
                    "/api/audio":   "لینکی ئۆدیۆ             ?url=",
                    "/api/profile": "زانیاری پرۆفایڵ         ?user=",
                }
            })
            return

        # ── پشکنینی url ────────────────────────────────────
        if path in ["/api/info", "/api/video", "/api/audio"]:
            if not url:
                self._send(400, {"error": "پێویستە ?url= زیاد بکەیت"})
                return
            if "instagram.com" not in url:
                self._send(400, {"error": "تەنها لینکی Instagram پشتگیری دەکرێت"})
                return

        # ── /api/info ──────────────────────────────────────
        if path == "/api/info":
            data = fetch_instagram(url)
            if not data:
                self._send(404, {"error": "پۆستەکە نەدۆزرایەوە"})
                return
            self._send(200, {"status": "success", **data})

        # ── /api/video ─────────────────────────────────────
        elif path == "/api/video":
            data = fetch_instagram(url)
            if not data or not data.get("video_url"):
                self._send(404, {"error": "لینکی ڤیدیۆ نەدۆزرایەوە"})
                return
            self._send(200, {
                "status":    "success",
                "url":       data["video_url"],
                "thumbnail": data["thumbnail"],
                "title":     data["title"],
                "type":      "video"
            })

        # ── /api/audio ─────────────────────────────────────
        elif path == "/api/audio":
            data = fetch_instagram(url)
            if not data or not data.get("video_url"):
                self._send(404, {"error": "لینکی ئۆدیۆ نەدۆزرایەوە"})
                return
            # ئۆدیۆ هەمان لینکی ڤیدیۆیە، بۆتەکە جیا دەکاتەوە
            self._send(200, {
                "status": "success",
                "url":    data["video_url"],
                "title":  data["title"],
                "type":   "audio"
            })

        # ── /api/profile ───────────────────────────────────
        elif path == "/api/profile":
            if not user:
                self._send(400, {"error": "پێویستە ?user= زیاد بکەیت"})
                return
            data = fetch_profile(user.lstrip("@"))
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
