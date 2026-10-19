"""Every POST_EVERY_HOURS: take the next approved clip and post it to all platforms at the same time."""
import time
from concurrent.futures import ThreadPoolExecutor

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import POST_EVERY_HOURS
from .db import conn
from .uploaders import youtube, tiktok, instagram

PLATFORMS = {"youtube": youtube.upload, "tiktok": tiktok.upload, "instagram": instagram.upload}


def _post_one(name, fn, clip):
    last = ""
    for attempt in range(3):
        try:
            ref = fn(clip["path"], clip["title"], clip["description"], clip["hashtags"])
            return name, "ok", str(ref)
        except Exception as e:
            last = str(e)[:500]
            time.sleep(30 * (attempt + 1))
    return name, "failed", last


def post_next() -> bool:
    with conn() as c:
        clip = c.execute("SELECT * FROM clips WHERE status='approved' ORDER BY id LIMIT 1").fetchone()
        if not clip:
            print("[post] queue empty")
            return False
        with ThreadPoolExecutor(max_workers=len(PLATFORMS)) as pool:
            futures = [pool.submit(_post_one, n, f, clip) for n, f in PLATFORMS.items()]
            results = [f.result() for f in futures]
        for name, status, detail in results:
            c.execute("INSERT INTO posts(clip_id,platform,status,detail) VALUES(?,?,?,?)",
                      (clip["id"], name, status, detail))
            print(f"[post] clip {clip['id']} -> {name}: {status} {detail}")
        # Mark posted as soon as one platform succeeded so we never double-post there;
        # failed platforms are visible in the posts table.
        if any(s == "ok" for _, s, _ in results):
            c.execute("UPDATE clips SET status='posted' WHERE id=?", (clip["id"],))
        return True


def run_forever():
    sched = BlockingScheduler()
    sched.add_job(post_next, "interval", hours=POST_EVERY_HOURS,
                  max_instances=1, coalesce=True)
    print(f"Scheduler started: one clip every {POST_EVERY_HOURS}h on every platform. Ctrl+C to stop.")
    post_next()  # post the first one right away
    sched.start()
