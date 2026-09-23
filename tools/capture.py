#!/usr/bin/env python3
"""Screenshot the live Headless DM dashboard for the guide pages.

Drives the Firefox snap's geckodriver over the WebDriver HTTP protocol (no selenium on the box).
The dashboard is a single-page app, so every shot is: drive the UI through its own click handlers,
wait for the render, grab the viewport.

Map art is turned OFF via localStorage (`dash.art`), because the zone and continent images are
extracted from the game client and must never be published. With art off the map draws zone
outlines, zone names, company holdings and every live character marker on the dark ground.

Usage:
    python3 tools/capture.py                 # every shot
    python3 tools/capture.py overview map    # only shots whose name contains one of these
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

PORT = 4457
DASH = os.environ.get("DASH_URL", "http://127.0.0.1:8787/")
OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "img"))
WIDTH, HEIGHT = 1600, 1000

# A bot with a backstory, hundreds of ties and a hundred-odd memories, for the inspector shots.
BOT = os.environ.get("DASH_BOT", "Melicia")


def call(method, path, body=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}", method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


class Browser:
    def __init__(self):
        profiles = os.path.expanduser("~/snap/firefox/common/geckodriver-profiles")
        os.makedirs(profiles, exist_ok=True)
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

    def esc(self):
        call("POST", f"/session/{self.sid}/actions", {"actions": [{
            "type": "key", "id": "kb", "actions": [
                {"type": "keyDown", "value": ""}, {"type": "keyUp", "value": ""}]}]})

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


# ---- helpers that run inside the page ----

def rail(b, label):
    r = b.js("""
      const want = %s;
      const x = [...document.querySelectorAll('.rail-btn')]
        .find(e => (e.querySelector('.lbl')||{}).textContent.trim() === want);
      if (!x) return 'MISSING rail ' + want;
      x.click(); return 'ok';""" % json.dumps(label))
    if r != "ok":
        print(f"  ! {r}")


def click(b, text, sel="button, .chip, [role=tab], a"):
    """Click the first visible element whose text OR title contains `text`."""
    r = b.js("""
      const want = %s;
      const x = [...document.querySelectorAll(%s)].find(e =>
        e.offsetParent !== null &&
        (e.textContent.replace(/\\s+/g,' ').trim().includes(want) || (e.title||'').includes(want)));
      if (!x) return 'MISSING ' + want;
      x.click(); return 'ok';""" % (json.dumps(text), json.dumps(sel)))
    if r != "ok":
        print(f"  ! {r}")
    return r


def boot(b, theme="dark"):
    """Load once to own the origin, set preferences, reload into them."""
    b.go(DASH)
    b.js(f"""
      localStorage.setItem('dash.art','0');        // never publish extracted map art
      localStorage.setItem('dash.outlines','1');   // draw zone rectangles instead
      localStorage.setItem('dash.holdings','1');
      localStorage.setItem('dash.theme','{theme}');
      localStorage.setItem('dash.dock','1');
      localStorage.setItem('dash.continent','0');
      localStorage.setItem('dash.panel','roster');
      localStorage.setItem('dash.roster','notable');
      return 'ok';""")
    b.go(DASH)
    time.sleep(10)   # static world data, first poll of every data file, map fit


PANELS = [("Roster", "panel-roster"), ("Feelings", "panel-feelings"), ("Groups", "panel-groups"),
          ("Companies", "panel-companies"), ("Chronicle", "panel-chronicle"), ("Market", "panel-market"),
          ("Commands", "panel-commands"), ("Lore", "panel-lore"), ("Memories", "panel-memories"),
          ("Journey", "panel-journey")]

# rail label -> (button text or title to click, shot name)
OVERLAYS = [("Chronicle", "Open Chronicle", "full-chronicle"),
            ("Groups", "Open Groups", "full-groups"),
            ("Journey", "Open Journey", "full-journey"),
            ("Feelings", "Show every one", "full-feelings"),
            ("Memories", "Show every one", "full-memories")]


def main():
    only = sys.argv[1:]
    want = lambda n: not only or any(o in n for o in only)

    b = Browser()
    try:
        print("booting dashboard (map art off)…")
        boot(b)

        if want("overview"):
            print("overview")
            b.shot("overview")

        for label, name in PANELS:
            if not want(name):
                continue
            print(name)
            rail(b, label)
            time.sleep(2.5)
            b.shot(name)

        # ---- inspector: select a character, then walk its tabs ----
        if want("inspector"):
            print("inspector")
            rail(b, "Roster")
            time.sleep(1)
            click(b, "Everyone", ".panel[data-panel=roster]")
            time.sleep(2)
            b.js("""const r = document.querySelector('.panel[data-panel=roster] .row');
                    if (r) r.click(); return 'ok';""")
            time.sleep(3)
            tabs = b.js("""return [...document.querySelectorAll('.inspector .tabs button')]
                             .map(t => t.textContent.replace(/\\s+/g,' ').trim());""")
            print("  inspector tabs:", tabs)
            b.shot("inspector")
            for i, t in enumerate(tabs or []):
                b.js(f"""const ts=[...document.querySelectorAll('.inspector .tabs button')];
                         if (ts[{i}]) ts[{i}].click(); return 'ok';""")
                time.sleep(2.5)
                slug = "".join(c for c in t.split()[0].lower() if c.isalpha()) or str(i)
                b.shot(f"inspector-{slug}")

        # ---- inspector, on a bot with a real story ----
        # Real players carry no generated lore, so the Story and Memories tabs are empty on them.
        # Search a well-travelled bot by name instead and walk the four tabs on her.
        if want("bot"):
            print("bot inspector")
            rail(b, "Roster")
            time.sleep(1.5)
            b.js("""const i = document.querySelector('.panel[data-panel=roster] input');
                    if (!i) return 'no input';
                    i.value = %s;
                    i.dispatchEvent(new Event('input', { bubbles: true }));
                    return 'ok';""" % json.dumps(BOT))
            time.sleep(2.5)
            b.shot("roster-search")
            b.js("""const r = document.querySelector('.panel[data-panel=roster] .row');
                    if (r) r.click(); return 'ok';""")
            time.sleep(3.5)
            tabs = b.js("""return [...document.querySelectorAll('.inspector .tabs button')]
                             .map(t => t.textContent.replace(/\\s+/g,' ').trim());""")
            print("  tabs:", tabs)
            for i, t in enumerate(tabs or []):
                b.js(f"""const ts=[...document.querySelectorAll('.inspector .tabs button')];
                         if (ts[{i}]) ts[{i}].click(); return 'ok';""")
                time.sleep(3)
                slug = "".join(c for c in t.split()[0].lower() if c.isalpha()) or str(i)
                b.shot(f"inspector-{slug}")

        # ---- full-screen views ----
        for label, trigger, name in OVERLAYS:
            if not want(name):
                continue
            print(name)
            rail(b, label)
            time.sleep(2)
            if click(b, trigger) == "ok":
                time.sleep(4)
                b.shot(name)
                b.esc()
                time.sleep(1.5)

        # ---- map details ----
        if want("map-layers"):
            print("map-layers")
            b.js("const c=document.querySelector('.rail-btn.on'); if(c) c.click(); return 'ok';")  # collapse dock
            time.sleep(1)
            click(b, "Layers")
            time.sleep(1.5)
            b.shot("map-layers")
            click(b, "Layers")
            time.sleep(1)

        if want("map-zoom"):
            print("map-zoom")
            for _ in range(4):
                b.js("const z=document.querySelector('.leaflet-control-zoom-in'); if(z) z.click(); return 'ok';")
                time.sleep(1.2)
            time.sleep(3)
            b.shot("map-zoom")

        if want("map-kalimdor"):
            print("map-kalimdor")
            click(b, "Kalimdor")
            time.sleep(4)
            b.shot("map-kalimdor")

        # ---- light theme ----
        if want("light"):
            print("light")
            boot(b, theme="light")
            b.shot("light-overview")
    finally:
        b.close()


if __name__ == "__main__":
    main()
