"""Instagram Reels via the Graph API using resumable upload (no public URL needed)."""
import os
import time
import requests

from ..config import IG_USER_ID, IG_ACCESS_TOKEN

GRAPH = "https://graph.facebook.com/v21.0"


def upload(path: str, title: str, description: str, hashtags: str) -> str:
    if not (IG_USER_ID and IG_ACCESS_TOKEN):
        raise RuntimeError("IG_USER_ID / IG_ACCESS_TOKEN not set")
    caption = f"{title}\n\n{description}\n\n{hashtags}"[:2200]

    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media",
        data={"media_type": "REELS", "upload_type": "resumable", "caption": caption,
              "access_token": IG_ACCESS_TOKEN},
        timeout=60,
    )
    r.raise_for_status()
    container = r.json()
    cid, upload_uri = container["id"], container["uri"]

    size = os.path.getsize(path)
    with open(path, "rb") as f:
        up = requests.post(
            upload_uri,
            headers={"Authorization": f"OAuth {IG_ACCESS_TOKEN}", "offset": "0", "file_size": str(size)},
            data=f, timeout=600,
        )
    up.raise_for_status()

    for _ in range(60):  # wait until processing finishes
        st = requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code", "access_token": IG_ACCESS_TOKEN},
                          timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram processing failed: {st}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram processing timed out")

    pub = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media_publish",
        data={"creation_id": cid, "access_token": IG_ACCESS_TOKEN}, timeout=60,
    )
    pub.raise_for_status()
    return pub.json()["id"]
