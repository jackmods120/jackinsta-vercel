from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
import requests
import json
import re


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.instagram.com/",
    "Origin": "https://www.instagram.com",
    "X-IG-App-ID": "936619743392459",
}


def get_shortcode(url):
    match = re.search(r"/(p|reel|tv|reels)/([A-Za-z0-9_-]+)", url)
    return match.group(2) if match else None


def fetch_via_embed(url):
    """Instagram embed endpoint — بەبێ لۆگین کاردەکات"""
    try:
        shortcode = get_shortcode(url)
        if not shortcode:
            return None

        # Embed JSON endpoint
        embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        r = requests.get(embed_url, headers=HEADERS, timeout=20)

        video_url   = ""
        thumbnail   = ""
        title       = ""
        author      = ""

        # ڕزگارکردنی video_url
        vm = re.search(r'"video_url":"([^"]+)"', r.text)
        if vm:
            video_url = vm.group(1).replace("\\u0026", "&")

        # thumbnail
        tm = re.search(r'"display_url":"([^"]+)"', r.text)
        if tm:
            thumbnail = tm.group(1).replace("\\u0026", "&")

        # author
        am = re.search(r'"username":"([^"]+)"', r.text)
        if am:
            author = am.group(1)

        # title/caption
        cm = re.search(r'"edge_media_to_caption":\{"edges":\[\{"node":\{"text":"([^"]{0,150})', r.text)
        if cm:
            title = cm.group(1)

        if not video_url:
            # یەکەم ڕێگا کار نەکرد، هەوڵی دووەم
            vm2 = re.search(r'video_url":"(https:[^"]+\.mp4[^"]*)"', r.text)
            if vm2:
                video_url = vm2.group(1).replace("\\u0026", "&").replace("\\/", "/")

        return {
            "shortcode": shortcode,
            "title":     title or f"Instagram Reel {shortcode}",
            "author":    author,
            "username":  author,
            "thumbnail": thumbnail,
            "video_url": video_url,
            "webpage":   f"https://www.instagram.com/p/{shortcode}/",
        }

    except Exception as e:
        return {"error": str(e)}


def fetch_profile(username):
    try:
        r = requests.get(
            f"https://www.instagram.com/{username}/",
            headers=HEADERS,
            timeout=20
        )
        full_name = ""
        followers = 0
        bio = ""

        fn = re.search(r'"full_name":"([^"]*)"', r.text)
        if fn:
            full_name = fn.group(1)

        fc = re.search(r'"edge_followed_by":\{"count":(\d+)\}', r.text)
        if fc:
            followers = int(fc.group(1))

        bc = re.search(r'"biography":"([^"]*)"', r.text)
        if bc:
            bio = bc.group(1)

        return {
            "username":  username,
            "full_name": full_name or username,
            "followers": followers,
            "bio":       bio,
            "url":       f"https://www.instagram.com/{username}/",
        }
    except Exception:
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
                "version": "2.0",
                "author":  "JACK",
                "channel": "@jack_721_mod",
                "endpoints": {
                    "/api/info":    "زانیاری پۆست/ڕیلس   ?url=",
                    "/api/video":   "لینکی ڤیدیۆ          ?url=",
                    "/api/audio":   "لینکی ئۆدیۆ          ?url=",
                    "/api/profile": "زانیاری پرۆفایڵ      ?user=",
                }
            })
            return

        if path in ["/api/info", "/api/video", "/api/audio"]:
            if not url:
                self._send(400, {"error": "پێویستە ?url= زیاد بکەیت"})
                return
            if "instagram.com" not in url:
                self._send(400, {"error": "تەنها لینکی Instagram"})
                return

        # ── /api/info ──────────────────────────────────────
        if path == "/api/info":
            data = fetch_via_embed(url)
            if not data or "error" in data:
                self._send(404, {"error": "پۆستەکە نەدۆزرایەوە"})
                return
            self._send(200, {"status": "success", **data})

        # ── /api/video ─────────────────────────────────────
        elif path == "/api/video":
            data = fetch_via_embed(url)
            if not data or not data.get("video_url"):
                self._send(404, {"error": "لینکی ڤیدیۆ نەدۆزرایەوە"})
                return
            self._send(200, {
                "status":    "success",
                "url":       data["video_url"],
                "thumbnail": data.get("thumbnail", ""),
                "title":     data.get("title", ""),
                "type":      "video"
            })

        # ── /api/audio ─────────────────────────────────────
        elif path == "/api/audio":
            data = fetch_via_embed(url)
            if not data or not data.get("video_url"):
                self._send(404, {"error": "لینکی ئۆدیۆ نەدۆزرایەوە"})
                return
            self._send(200, {
                "status": "success",
                "url":    data["video_url"],
                "title":  data.get("title", ""),
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
