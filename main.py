import argparse

from clipsys.discovery import discover
from clipsys.clipper import process_sources
from clipsys.scheduler import run_forever, post_next
from clipsys.db import conn


def status():
    with conn() as c:
        for t, col in (("campaigns", "status"), ("sources", "status"), ("clips", "status")):
            rows = c.execute(f"SELECT {col} s, COUNT(*) n FROM {t} GROUP BY {col}").fetchall()
            print(t, {r["s"]: r["n"] for r in rows})


def main():
    p = argparse.ArgumentParser(description="Clip -> YouTube/TikTok/Instagram pipeline")
    p.add_argument("command", choices=["discover", "clip", "post-now", "run", "status"])
    a = p.parse_args()
    if a.command == "discover":
        print(f"{discover()} usable campaigns")
    elif a.command == "clip":
        print(f"{process_sources()} clips rendered")
    elif a.command == "post-now":
        post_next()
    elif a.command == "run":
        run_forever()
    else:
        status()


if __name__ == "__main__":
    main()
