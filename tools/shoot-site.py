#!/usr/bin/env python3
"""Render the site's own pages headlessly, for a look before publishing.

Writes full-height PNGs to the directory given by OUT_DIR (default: a `site-check` folder beside the repo),
never into img/ — these are proofs, not site assets.

Usage:  python3 tools/shoot-site.py [index dashboard panels views results] [--width 1280]
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

# Chosen at startup. A fixed port looks harmless until a geckodriver from an earlier run is still
# listening on it: the readiness probe below then succeeds against *that* driver, and the session we
# ask it for fails with an opaque 500 that looks like a page problem and is not one.
PORT = 0
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.environ.get("OUT_DIR", os.path.join(ROOT, "..", "site-check"))
PAGES = ["index", "features", "dashboard", "panels", "views", "results", "roadmap", "evidence"]


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
        return json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        # geckodriver explains itself in the body; without this the traceback says only "500".
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode(errors='replace')[:400]}") from None


def main():
    # Take the flag and its value out together. Dropping only the "--width" and keeping the "1280"
    # left the width as a page name, and the run died trying to open 1280.html.
    argv = sys.argv[1:]
    width = 1280
    if "--width" in argv:
        i = argv.index("--width")
        width = int(argv[i + 1])
        del argv[i:i + 2]
    pages = argv or PAGES

    unknown = [p for p in pages if not os.path.isfile(os.path.join(ROOT, p + ".html"))]
    if unknown:
        sys.exit(f"no such page(s): {', '.join(unknown)}\nknown pages: {', '.join(PAGES)}")
    os.makedirs(OUT, exist_ok=True)

    global PORT
    PORT = free_port()

    # A profile directory of this run's own, so a Firefox left behind by an earlier run cannot
    # hold the one we are about to use.
    root = os.path.expanduser("~/snap/firefox/common/geckodriver-profiles")
    os.makedirs(root, exist_ok=True)
    profiles = tempfile.mkdtemp(prefix="shoot-site-", dir=root)
    drv = subprocess.Popen(["/snap/bin/geckodriver", "--port", str(PORT), "--profile-root", profiles],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/status", timeout=2)
                break
            except OSError:
                time.sleep(0.5)
        sid = call("POST", "/session", {"capabilities": {"alwaysMatch": {
            "moz:firefoxOptions": {"args": ["-headless", f"--width={width}", "--height=1200"]}}}})["value"]["sessionId"]

        for name in pages:
            src = os.path.join(ROOT, name + ".html")
            call("POST", f"/session/{sid}/url", {"url": "file://" + src})
            time.sleep(3)   # web fonts
            h = call("POST", f"/session/{sid}/execute/sync",
                     {"script": "return document.documentElement.scrollHeight", "args": []})["value"]
            broken = call("POST", f"/session/{sid}/execute/sync", {"script": """
                return [...document.images].filter(i => !i.complete || i.naturalWidth === 0)
                                           .map(i => i.getAttribute('src'));""", "args": []})["value"]
            # Firefox will screenshot the whole document in one frame. Growing the window to the page
            # instead is what the earlier version did, and geckodriver answers 500 to a window that
            # tall -- features and evidence both run well past 8,000px, so every long page failed.
            try:
                png = call("GET", f"/session/{sid}/moz/screenshot/full")["value"]
            except urllib.error.HTTPError:
                call("POST", f"/session/{sid}/window/rect", {"width": width, "height": min(int(h) + 120, 8000)})
                time.sleep(2)
                png = call("GET", f"/session/{sid}/screenshot")["value"]
            path = os.path.join(OUT, name + ".png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(png))
            flag = f"  BROKEN IMAGES: {broken}" if broken else ""
            print(f"{name}.html -> {os.path.basename(path)} ({os.path.getsize(path)//1024} KB, {h}px tall){flag}")
        call("DELETE", f"/session/{sid}")
    finally:
        drv.terminate()
        try:
            drv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            drv.kill()
        shutil.rmtree(profiles, ignore_errors=True)


if __name__ == "__main__":
    main()
