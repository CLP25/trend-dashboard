import os, psycopg2
from flask import Flask, request, redirect, url_for, render_template_string

HTML = """<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trend Dashboard</title>
<style>
body{font-family:system-ui,Arial,sans-serif;margin:24px}
.wrap{max-width:900px;margin:auto}
.item{padding:12px 0;border-bottom:1px solid #eee}
.title{font-weight:600}
.meta{color:#666;font-size:14px;margin-bottom:16px}
.topbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.badge{background:#eee;padding:2px 8px;border-radius:999px;font-size:12px}
a{text-decoration:none}
</style></head><body><div class="wrap">
<h1>Trend Dashboard</h1>
<div class="meta">Live RSS feed. Use the filters. Click ↻ to fetch now.</div>

<form class="topbar" method="get">
  <label>Time window:
    <select name="hours" onchange="this.form.submit()">
      {% for h in [1,3,6,12,24,48,168] %}
        <option value="{{h}}" {% if h == hours %}selected{% endif %}>last {{h}}h</option>
      {% endfor %}
    </select>
  </label>
  <label>Source:
    <select name="source" onchange="this.form.submit()">
      <option value="">All</option>
      {% for s in sources %}
        <option value="{{s}}" {% if s == source %}selected{% endif %}>{{s}}</option>
      {% endfor %}
    </select>
  </label>
  <span class="badge">{{ count }} items</span>
  <a href="{{ url_for('force_refresh') }}">↻ fetch now</a>
</form>

{% for it in items %}
  <div class="item">
    <div class="title"><a href="{{ it['url'] }}" target="_blank" rel="noopener">{{ it['title'] }}</a></div>
    <div class="meta">{{ it['source'] }} — {{ it['published_at'] }} UTC</div>
    {% if it['summary_raw'] %}
      <div>{{ it['summary_raw'][:280] }}{% if it['summary_raw']|length > 280 %}…{% endif %}</div>
    {% endif %}
  </div>
{% endfor %}
</div></body></html>"""

def get_conn():
    # Render env var we set earlier
    url = os.environ["DATABASE_URL"]
    return psycopg2.connect(url, sslmode="require")

app = Flask(__name__)

@app.route("/")
def index():
    hours = int(request.args.get("hours", 12))
    source = request.args.get("source", "")
    with get_conn() as conn, conn.cursor() as cur:
        if source:
            cur.execute("""
              SELECT source, title, url, published_at, summary_raw
              FROM items
              WHERE source = %s
                AND published_at >= NOW() - INTERVAL '%s hours'
              ORDER BY published_at DESC
              LIMIT 500
            """, (source, hours))
        else:
            cur.execute("""
              SELECT source, title, url, published_at, summary_raw
              FROM items
              WHERE published_at >= NOW() - INTERVAL '%s hours'
              ORDER BY published_at DESC
              LIMIT 500
            """, (hours,))
        rows = cur.fetchall()

        cur.execute("SELECT DISTINCT source FROM items ORDER BY source")
        sources = [r[0] for r in cur.fetchall()]

    items = [{
        "source": r[0],
        "title": r[1],
        "url": r[2],
        "published_at": r[3].strftime("%Y-%m-%d %H:%M:%S"),
        "summary_raw": r[4]
    } for r in rows]

    return render_template_string(HTML,
        items=items, hours=hours, source=source, sources=sources, count=len(items))

@app.route("/refresh")
def force_refresh():
    # This will just bounce back to the homepage.
    # The background worker actually fetches new items.
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Local dev only; Render uses gunicorn
    app.run(host="0.0.0.0", port=5000)

