# Clip Pipeline

Finds content-reward campaigns, reads their terms, generates clips, and posts one clip
every 5 hours to YouTube, TikTok and Instagram at the same time.

## Flow

1. `discover`: reads the campaign listing pages in `CAMPAIGN_LIST_URLS` (respecting robots.txt),
   sends each campaign's terms to Claude, and stores structured rules. Campaigns that do not
   clearly allow clipping are marked `blocked` and never used.
2. `clip`: downloads the allowed source videos, transcribes with Whisper, Claude picks the best
   highlights, FFmpeg renders 9:16 captioned clips. Every clip must pass the campaign rules
   (length, required hashtags, required credit) or it is saved as `rejected`.
3. `run`: posts the oldest approved clip to all three platforms in parallel every
   `POST_EVERY_HOURS` hours (first post immediately).

## Setup

```bash
pip install -r requirements.txt
# also install FFmpeg (https://ffmpeg.org) and make sure `ffmpeg` is on PATH
cp .env.example .env     # then fill it in
```

## Usage

```bash
python main.py discover   # find campaigns + extract rules
python main.py clip       # download, transcribe, cut clips
python main.py status     # see queue counts
python main.py post-now   # post one clip right now (test)
python main.py run        # keep running: one clip every 5 hours
```

The computer must stay on and connected while `run` is active.

## Platform setup

- **YouTube:** create an OAuth client (Desktop app) in Google Cloud Console, enable YouTube Data API v3,
  save the JSON as `client_secret.json`. A browser window opens on the first upload. New API projects
  may have uploads locked to private until the project passes Google's audit.
- **TikTok:** register an app at developers.tiktok.com with the Content Posting API, get an access token
  with `video.publish` scope. Until your app is audited, posts are private (`SELF_ONLY`).
- **Instagram:** Business or Creator account linked to a Facebook Page, a Meta app with
  `instagram_content_publish`, then set `IG_USER_ID` and a long-lived `IG_ACCESS_TOKEN`
  (tokens expire, so refresh them periodically).

## Important

- Only clip content that the campaign or creator explicitly allows. The rule check is a gate, but
  you are responsible for reading the final terms too.
- Only point `CAMPAIGN_LIST_URLS` at sites whose terms allow automated reading.
- Posting identical clips on several platforms is allowed, but spammy or repetitive content can
  reduce reach or get accounts limited.
