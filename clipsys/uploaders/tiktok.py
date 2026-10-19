"""TikTok Content Posting API (direct post, FILE_UPLOAD).

Unaudited apps can only post with privacy SELF_ONLY. Set TIKTOK_PRIVACY after TikTok approves your app.
"""
import os
import requests

from ..config import TIKTOK_ACCESS_TOKEN, TIKTOK_PRIVACY

BASE = "https://open.tiktokapis.com/v2/post/publish"


def upload(path: str, title: str, description: str, hashtags: str) -> str:
    if not TIKTOK_ACCESS_TOKEN:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN not set")
    size = os.path.getsize(path)
    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    init = requests.post(
        f"{BASE}/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title": f"{title} {hashtags}"[:2200],
                "privacy_level": TIKTOK_PRIVACY,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            },
        },
        timeout=60,
    )
    init.raise_for_status()
    data = init.json()["data"]
    with open(path, "rb") as f:
        put = requests.put(
            data["upload_url"],
            data=f,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(size),
                "Content-Range": f"bytes 0-{size - 1}/{size}",
            },
            timeout=600,
        )
    put.raise_for_status()
    return data["publish_id"]
