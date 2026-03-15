from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Req(BaseModel):
    url: str

# ======================== YouTube ========================

def get_youtube(url):
    try:
        import yt_dlp
        info = {}
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True,
                                'format': 'best[ext=mp4]/best'}) as ydl:
            info = ydl.extract_info(url, download=False)
        return {
            'ok': True,
            'type': 'video',
            'title': info.get('title', ''),
            'thumb': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'url': info.get('url', ''),
            'source': 'youtube'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

# ======================== Instagram ========================

def get_instagram(url):
    # هەوڵی ١: instaloader
    try:
        import instaloader
        L = instaloader.Instaloader(quiet=True, download_videos=True,
            download_video_thumbnails=False, download_geotags=False,
            download_comments=False, save_metadata=False)
        match = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
        if match:
            post = instaloader.Post.from_shortcode(L.context, match.group(1))
            if post.is_video:
                return {
                    'ok': True, 'type': 'video',
                    'title': post.title or '',
                    'thumb': post.url,
                    'url': post.video_url,
                    'source': 'instaloader'
                }
            elif post.typename == 'GraphSidecar':
                urls = [n.video_url if n.is_video else n.display_url
                        for n in post.get_sidecar_nodes()]
                return {'ok': True, 'type': 'photos', 'urls': urls, 'source': 'instaloader'}
            else:
                return {'ok': True, 'type': 'photos', 'urls': [post.display_url], 'source': 'instaloader'}
    except Exception:
        pass

    # هەوڵی ٢: snapinsta
    try:
        session = requests.Session()
        r0 = session.get('https://snapinsta.app/', timeout=10,
                         headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 12)'})
        token_match = re.search(r'name="_token"\s+value="([^"]+)"', r0.text)
        if token_match:
            r = session.post('https://snapinsta.app/download',
                data={'url': url, '_token': token_match.group(1)},
                headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 12)',
                         'Referer': 'https://snapinsta.app/'},
                timeout=20)
            videos = re.findall(r'"(https://[^"]+\.mp4[^"]*)"', r.text)
            if videos:
                return {'ok': True, 'type': 'video', 'url': videos[0].replace('\\/', '/'),
                        'title': '', 'thumb': '', 'source': 'snapinsta'}
            imgs = re.findall(r'"(https://[^"]+\.jpg[^"]*)"', r.text)
            if imgs:
                return {'ok': True, 'type': 'photos',
                        'urls': [u.replace('\\/', '/') for u in imgs[:10]],
                        'source': 'snapinsta'}
    except Exception:
        pass

    raise HTTPException(status_code=500, detail="Instagram دانلۆد نەبوو — تەنها پۆستی گشتی")

# ======================== Endpoints ========================

@app.get("/")
def root():
    return {"status": "ok", "service": "Jack DL API", "by": "@j4ck_721s",
            "endpoints": ["/api/youtube", "/api/instagram"]}

@app.post("/api/youtube")
def youtube(req: Req):
    if 'youtu' not in req.url:
        raise HTTPException(status_code=400, detail="لینکی YouTube نییە")
    return get_youtube(req.url.strip())

@app.get("/api/youtube")
def youtube_get(url: str):
    return youtube(Req(url=url))

@app.post("/api/instagram")
def instagram(req: Req):
    if 'instagram.com' not in req.url:
        raise HTTPException(status_code=400, detail="لینکی Instagram نییە")
    return get_instagram(req.url.strip())

@app.get("/api/instagram")
def instagram_get(url: str):
    return instagram(Req(url=url))
