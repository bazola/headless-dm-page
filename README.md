# headless-dm-page

The project site for **Headless DM** — a private AzerothCore 3.3.5a realm where hundreds of playerbots are
voiced by language models as people who live in Azeroth, and the dashboard that reads it.

Live at **https://bazola.github.io/headless-dm-page/** once the repository is public.

## What is here

| Path | What |
|---|---|
| `index.html` | Overview: what the dashboard is, and how to open it |
| `dashboard.html` | The interface — five regions, statistics bar, map and legend, inspector, keyboard |
| `panels.html` | All ten panels and every control, grouped by the question each one answers |
| `views.html` | The five full-screen archives |
| `results.html` | Data — measured counts, and an example of each kind of record the realm writes |
| `css/site.css` | The whole stylesheet. Dark only, mirroring the dashboard's own design tokens |
| `img/` | Screenshots of the live dashboard |
| `tools/capture.py` | Re-takes every screenshot from a running dashboard |

Plain static HTML. No build step, no framework, no JavaScript of its own. `.nojekyll` is present so GitHub
Pages serves the files as they are.

## Re-taking the screenshots

With the realm running and the dashboard answering on `127.0.0.1:8787`:

```sh
python3 tools/capture.py            # every shot
python3 tools/capture.py panel map  # only shots whose name contains one of these words
```

It drives headless Firefox through the snap's geckodriver over the WebDriver protocol — no selenium or
playwright needed. Override the target with `DASH_URL`, and the bot used for the inspector shots with
`DASH_BOT` (it needs one with a backstory, plenty of ties and a good pile of memories).

## The one rule this repository keeps

**No Blizzard-derived data, ever.** The dashboard's painted world map is extracted from the operator's own game
client, so `capture.py` turns it off — it sets `dash.art` to `0` in the page's local storage before taking a
single frame, which leaves the map drawing zone outlines, zone names, company holdings and live character
markers on the dark ground instead.

If you re-take screenshots by hand, switch **Layers ▸ Map art** off first.

Nothing else from a client, an extracted archive or a world database dump belongs in this repository either.

## Licence

MIT — see `LICENSE`.

World of Warcraft and Warcraft are trademarks of Blizzard Entertainment. This project is not affiliated with or
endorsed by Blizzard, and distributes no Blizzard data.
