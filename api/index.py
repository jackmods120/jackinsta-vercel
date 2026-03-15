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

class DownloadRequest(BaseModel):
    url: str

def try_savefrom(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        r = requests.post('https://savefrom.net/api/convert', data={'url': url}, headers=headers, timeout=15)
        data = r.json()
        if data.get('url'):
            for item in data['url']:
                if item.get('ext') == 'mp4':
                    return {'type': 'video', 'url': item['url'], 'thumb': data.get('thumb', '')}
    except Exception:
        pass
    return None

def try_snapsave(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11)',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        r = requests.post('https://snapsave.app/action.php', data={'url': url}, headers=headers, timeout=15)
        
        # ڤیدیۆ
        videos = re.findall(r'href="(https://[^"]+\.mp4[^"]*)"', r.text)
        if videos:
            return {'type': 'video', 'url': videos[0], 'thumb': ''}
        
        # وێنەکان (carousel)
        imgs = re.findall(r'href="(https://[^"]+\.jpg[^"]*)"', r.text)
        if imgs:
            return {'type': 'photos', 'urls': imgs[:10]}
    except Exception:
        pass
    return None

def try_igdownloader(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11)',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        r = requests.post(
            'https://igdownloader.app/api/download',
            data={'url': url},
            headers=headers,
            timeout=15
        )
        data = r.json()
        if data.get('video'):
            return {'type': 'video', 'url': data['video'], 'thumb': data.get('thumbnail', '')}
        if data.get('images'):
            return {'type': 'photos', 'urls': data['images']}
    except Exception:
        pass
    return None

@app.get("/")
def root():
    return {"status": "ok", "service": "Instagram Downloader API", "by": "@j4ck_721s"}

@app.post("/api/download")
def download(req: DownloadRequest):
    url = req.url.strip()

    if 'instagram.com' not in url:
        raise HTTPException(status_code=400, detail="لینکی Instagram نییە")

    # هەوڵی ١
    result = try_savefrom(url)
    if result:
        return {"ok": True, "source": "savefrom", **result}

    # هەوڵی ٢
    result = try_snapsave(url)
    if result:
        return {"ok": True, "source": "snapsave", **result}

    # هەوڵی ٣
    result = try_igdownloader(url)
    if result:
        return {"ok": True, "source": "igdownloader", **result}

    raise HTTPException(status_code=500, detail="دانلۆد نەبوو، تەنها پۆستی گشتی کاردەکات")

@app.get("/api/download")
def download_get(url: str):
    return download(DownloadRequest(url=url))
