#!/usr/bin/env python3
"""
lab_notebook_app.py -- tiny local web app to append timestamped entries to
docs/lab_notebook.md. Python stdlib only, no dependencies.

Run:    python3 tools/lab_notebook_app.py
Open:   http://127.0.0.1:8787   (type an entry, click Add)

Each entry is APPENDED (never overwrites) as one line:
    - **YYYY-MM-DD HH:MM:SS** <your text>
The file is the source of truth; this app just appends to it and shows the entries
as a Date / Time / Entry table. Ctrl-C to stop.
"""
import http.server, socketserver, urllib.parse, html, os, re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.normpath(os.path.join(HERE, "..", "docs", "lab_notebook.md"))
PORT = 8787

# entry line format written by this app / the seed:  - **<stamp>** <text>
ENTRY_RE = re.compile(r"^- \*\*(.+?)\*\*\s*(.*)$")

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Lab notebook</title>
<style>
 body{{font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem}}
 textarea{{width:100%;height:5rem;font:inherit;padding:.5rem;box-sizing:border-box}}
 button{{font:inherit;padding:.5rem 1rem;margin-top:.5rem;cursor:pointer}}
 h1{{font-size:1.2rem;margin-bottom:.3rem}} h2{{font-size:1rem;color:#444}}
 .hint{{color:#666;font-size:.85rem;margin-left:.5rem}}
 #v{{max-height:60vh;overflow:auto;border:1px solid #ddd;border-radius:6px}}
 table{{border-collapse:collapse;width:100%}}
 th,td{{border-bottom:1px solid #eee;padding:.4rem .6rem;text-align:left;vertical-align:top;font-size:.92rem}}
 th{{background:#eee;position:sticky;top:0}}
 td:nth-child(1){{white-space:nowrap;color:#333}}
 td:nth-child(2){{white-space:nowrap;color:#666}}
</style></head><body>
<h1>Lab notebook</h1>
<form method="POST" action="/add">
 <textarea name="note" autofocus placeholder="e.g. FC dial 1 -> 3   /   cold-packs removed   /   heavy door day"></textarea>
 <div><button type="submit">Add entry (timestamped now)</button>
 <span class="hint">appends to {path}</span></div>
</form>
<h2>Entries</h2>
<div id="v"><table><thead><tr><th>Date</th><th>Time</th><th>Entry</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<script>var v=document.getElementById('v');v.scrollTop=v.scrollHeight;</script>
</body></html>"""

def parse_entries():
    """Pull '- **stamp** text' lines out of the notebook into (date, time, text)."""
    try:
        with open(NOTEBOOK, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []
    out = []
    for ln in lines:
        m = ENTRY_RE.match(ln.rstrip("\n"))
        if not m:
            continue
        stamp, text = m.group(1).strip(), m.group(2).strip()
        parts = stamp.split(None, 1)           # date = first token, time = the rest
        date = parts[0] if parts else stamp
        tm = parts[1] if len(parts) > 1 else ""
        out.append((date, tm, text))
    return out

def rows_html():
    rows = parse_entries()
    if not rows:
        return '<tr><td colspan="3" style="color:#888">no entries yet</td></tr>'
    return "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(d), html.escape(t), html.escape(e))
        for d, t, e in rows)

class Handler(http.server.BaseHTTPRequestHandler):
    def _html(self, code, body):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.split("?")[0] != "/":
            self.send_response(404); self.end_headers(); return
        self._html(200, PAGE.format(rows=rows_html(), path=html.escape(NOTEBOOK)))

    def do_POST(self):
        if self.path != "/add":
            self.send_response(404); self.end_headers(); return
        n = int(self.headers.get("Content-Length", 0) or 0)
        fields = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8"))
        note = " ".join(fields.get("note", [""])[0].split())   # collapse to one line
        if note:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(NOTEBOOK, "a", encoding="utf-8") as f:    # append, never overwrite
                f.write(f"- **{stamp}** {note}\n")
        self.send_response(303); self.send_header("Location", "/"); self.end_headers()

    def log_message(self, *a):
        pass   # quiet

class Server(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with Server(("127.0.0.1", PORT), Handler) as srv:
        print(f"# lab notebook file: {NOTEBOOK}")
        print(f"# open http://127.0.0.1:{PORT}   (Ctrl-C to stop)")
        srv.serve_forever()
