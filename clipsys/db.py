import json
import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    title TEXT,
    terms_text TEXT,
    rules_json TEXT,
    status TEXT DEFAULT 'new'      -- new | rules_ok | blocked | processed
);
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    url TEXT UNIQUE,
    path TEXT,
    status TEXT DEFAULT 'new'      -- new | downloaded | clipped | failed
);
CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    campaign_id INTEGER,
    path TEXT,
    title TEXT,
    description TEXT,
    hashtags TEXT,
    duration REAL,
    status TEXT DEFAULT 'approved' -- approved | rejected | posted
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id INTEGER,
    platform TEXT,
    status TEXT,                   -- ok | failed
    detail TEXT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
