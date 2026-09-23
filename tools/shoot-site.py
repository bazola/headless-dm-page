#!/usr/bin/env python3
"""Render the site's own pages headlessly, for a look before publishing.

Writes full-height PNGs to the directory given by OUT_DIR (default: a `site-check` folder beside the repo),
never into img/ — these are proofs, not site assets.

Usage:  python3 tools/shoot-site.py [index dashboard panels views results] [--width 1280]
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

PORT = 4458
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.environ.get("OUT_DIR", os.path.join(ROOT, "..", "site-check"))
PAGES = ["index", "dashboard", "panels", "views", "results"]


def call(method, path, body=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=180))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    width = 1280
    if "--width" in sys.argv:
        width = int(sys.argv[sys.argv.index("--width") + 1])
    pages = args or PAGES
    os.makedirs(OUT, exist_ok=True)

    profiles = os.path.expanduser("~/snap/firefox/common/geckodriver-profiles")
    os.makedirs(profiles, exist_ok=True)
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
            # Grow the window to the document so the whole page lands in one frame.
            h = call("POST", f"/session/{sid}/execute/sync",
                     {"script": "return document.documentElement.scrollHeight", "args": []})["value"]
            call("POST", f"/session/{sid}/window/rect", {"width": width, "height": min(int(h) + 120, 16000)})
            time.sleep(2)
            broken = call("POST", f"/session/{sid}/execute/sync", {"script": """
                return [...document.images].filter(i => !i.complete || i.naturalWidth === 0)
                                           .map(i => i.getAttribute('src'));""", "args": []})["value"]
            png = call("GET", f"/session/{sid}/screenshot")["value"]
            path = os.path.join(OUT, name + ".png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(png))
            flag = f"  BROKEN IMAGES: {broken}" if broken else ""
            print(f"{name}.html -> {os.path.basename(path)} ({os.path.getsize(path)//1024} KB, {h}px tall){flag}")
        call("DELETE", f"/session/{sid}")
    finally:
        drv.terminate()


if __name__ == "__main__":
    main()
