import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SOURCES_DIR = DATA / "sources"
CLIPS_DIR = DATA / "clips"
DB_PATH = DATA / "pipeline.db"
for d in (DATA, SOURCES_DIR, CLIPS_DIR):
    d.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

CAMPAIGN_LIST_URLS = [u.strip() for u in os.getenv("CAMPAIGN_LIST_URLS", "").split(",") if u.strip()]
POST_EVERY_HOURS = float(os.getenv("POST_EVERY_HOURS", "5"))

YOUTUBE_CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secret.json")
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "public")

TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_PRIVACY = os.getenv("TIKTOK_PRIVACY", "SELF_ONLY")

IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")

CLIP_MIN_SEC = int(os.getenv("CLIP_MIN_SEC", "20"))
CLIP_MAX_SEC = int(os.getenv("CLIP_MAX_SEC", "55"))
CLIPS_PER_SOURCE = int(os.getenv("CLIPS_PER_SOURCE", "8"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
