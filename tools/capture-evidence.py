#!/usr/bin/env python3
"""Screenshot the dashboard's hash-addressed full-screen views, for the Evidence page.

capture.py drives the panels through their own buttons. The five full-screen views also set a web
address of their own (`#overheard`, `#warmest`, …), so this one navigates straight to them, which is
both shorter and less likely to break when a button moves.

Map art is turned OFF the same way capture.py does it — the zone and continent images come from the
operator's game client and must never be published.

Usage:
    python3 tools/capture-evidence.py              # every shot below
    python3 tools/capture-evidence.py overheard    # only shots whose name contains this
"""
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# Chosen at startup, not fixed: a geckodriver left listening from an interrupted run would other-
# wise answer the readiness probe below, and the session asked of it fails with an opaque 500.
PORT = 0
DASH = os.environ.get("DASH_URL", "http://127.0.0.1:8787/")
OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "img"))
WIDTH, HEIGHT = 1600, 1000

# shot name -> (the view's own address, how many rows to open first)
# The Overheard list opens collapsed, one row per conversation. Collapsed rows prove only that
# conversations happened; the evidence is the words inside them, so that shot opens its rows.
VIEWS = [
    ("evidence-overheard", "#overheard", 0),
    ("evidence-overheard-open", "#overheard", 5),
    ("evidence-warmest", "#warmest", 0),
    ("evidence-moments", "#moments", 0),
    ("evidence-memories", "#memories", 0),
]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def call(method, path, body=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        # geckodriver explains itself in the body; without this the traceback says only "500".
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode(errors='replace')[:400]}") from None


class Browser:
    def __init__(self):
        global PORT
        PORT = free_port()
        root = os.path.expanduser("~/snap/firefox/common/geckodriver-profiles")
        os.makedirs(root, exist_ok=True)
        # This run's own profile, so a Firefox left behind by an earlier run cannot hold it.
        self.profiles = profiles = tempfile.mkdtemp(prefix="capture-evidence-", dir=root)
        self.proc = subprocess.Popen(
            ["/snap/bin/geckodriver", "--port", str(PORT), "--profile-root", profiles],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/status", timeout=2)
                break
            except OSError:
                time.sleep(0.5)
        self.sid = call("POST", "/session", {"capabilities": {"alwaysMatch": {
            "moz:firefoxOptions": {"args": ["-headless", f"--width={WIDTH}", f"--height={HEIGHT}"]}}}})["value"]["sessionId"]

    def go(self, url):
        call("POST", f"/session/{self.sid}/url", {"url": url})

    def js(self, script):
        return call("POST", f"/session/{self.sid}/execute/sync", {"script": script, "args": []})["value"]

    def shot(self, name):
        png = call("GET", f"/session/{self.sid}/screenshot")["value"]
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, name + ".png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(png))
        print(f"  wrote {name}.png ({os.path.getsize(path) // 1024} KB)")

    def close(self):
        try:
            call("DELETE", f"/session/{self.sid}")
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            shutil.rmtree(self.profiles, ignore_errors=True)


def main():
    only = sys.argv[1:]
    want = lambda n: not only or any(o in n for o in only)

    b = Browser()
    try:
        print("booting dashboard (map art off)…")
        b.go(DASH)
        b.js("""
          localStorage.setItem('dash.art','0');        // never publish extracted map art
          localStorage.setItem('dash.outlines','1');
          localStorage.setItem('dash.holdings','1');
          localStorage.setItem('dash.theme','dark');
          localStorage.setItem('dash.dock','1');
          localStorage.setItem('dash.continent','0');
          return 'ok';""")
        b.go(DASH)
        time.sleep(10)

        for name, hashaddr, expand in VIEWS:
            if not want(name):
                continue
            print(name, hashaddr)
            b.go(DASH + hashaddr)
            time.sleep(7)
            if expand:
                # A conversation is a <details class="card"> with a <summary>; opening it reveals the
                # exchange as spoken and the feelings it caused. Set `open` rather than clicking the
                # summary, which the view's own handler would toggle straight back shut.
                opened = b.js("""
                  const rows = [...document.querySelectorAll('.fx-list details.card')].slice(0, %d);
                  rows.forEach(r => r.open = true);
                  return rows.length;""" % expand)
                print(f"    opened {opened} rows")
                if not opened:
                    print("    ! nothing matched .fx-list details.card — check the view's markup")
                time.sleep(3)
            b.shot(name)
    finally:
        b.close()


if __name__ == "__main__":
    main()
