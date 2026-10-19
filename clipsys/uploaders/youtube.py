"""YouTube upload via the official Data API (resumable). First run opens a browser for OAuth consent."""
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..config import YOUTUBE_CLIENT_SECRETS, YOUTUBE_PRIVACY, DATA

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN = DATA / "youtube_token.pickle"


def _creds():
    creds = None
    if TOKEN.exists():
        creds = pickle.loads(TOKEN.read_bytes())
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.write_bytes(pickle.dumps(creds))
    return creds


def upload(path: str, title: str, description: str, hashtags: str) -> str:
    yt = build("youtube", "v3", credentials=_creds())
    body = {
        "snippet": {
            "title": (title[:90] + " #Shorts"),
            "description": f"{description}\n\n{hashtags}",
            "categoryId": "22",
        },
        "status": {"privacyStatus": YOUTUBE_PRIVACY, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(path, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]
