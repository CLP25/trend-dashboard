import os, time, hashlib, feedparser, psycopg2
from datetime import datetime, timezone

# Edit this list to add/remove sources
FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://www.theverge.com/rss/index.xml",
    "https://www.reddit.com/r/technology/.rss",
]
POLL_SECONDS = 300  # fetch every 5 minutes

def item_id(url, source):
    return hashlib.sha256(f"{source}|{url}".encode()).hexdigest()

def to_dt(entry):
    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)

def main():
    url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(url, sslmode="require")
    cur = conn.cursor()

    # Make sure the table/indexes exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
      item_id TEXT PRIMARY KEY,
      source TEXT,
      title TEXT,
      url TEXT,
      published_at TIMESTAMPTZ,
      summary_raw TEXT,
      fetched_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at DESC);
    CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
    """)
    conn.commit()

    while True:
        new_count = 0
        for src in FEEDS:
            feed = feedparser.parse(src)
            for e in feed.entries:
                iid = item_id(e.link, src)
                cur.execute("""
                  INSERT INTO items (item_id, source, title, url, published_at, summary_raw)
                  VALUES (%s,%s,%s,%s,%s,%s)
                  ON CONFLICT (item_id) DO NOTHING
                """, (
                    iid, src, e.title[:512], e.link,
                    to_dt(e), getattr(e, "summary", "")[:4000]
                ))
                if cur.rowcount > 0:
                    new_count += 1
        conn.commit()
        print(f"[fetcher] added {new_count} items; sleeping {POLL_SECONDS}s")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
