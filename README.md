# headless-dm-page

The project site for **Headless DM** — a private AzerothCore 3.3.5a realm where hundreds of playerbots are
voiced by language models as people who live in Azeroth, and the dashboard that reads it.

Live at **https://bazola.github.io/headless-dm-page/** once the repository is public.

## What is here

Five sections, in the order the top navigation lists them.

| Path | Section | What |
|---|---|---|
| `index.html` | **Home** | The landing page: what the realm is, today's figures, and where to go next |
| `features.html` | **Features** | Everything built and running, in nine chapters — the page that sells the idea |
| `dashboard.html` | **Dashboard** | The interface — five regions, statistics bar, map and legend, inspector, keyboard |
| `panels.html` | ↳ Dashboard | All ten panels and every control, grouped by the question each one answers |
| `views.html` | ↳ Dashboard | The five full-screen archives |
| `results.html` | ↳ Dashboard | Data — measured counts, and an example of each kind of record the realm writes |
| `roadmap.html` | **Roadmap** | The three large things not built yet, plus the shorter list behind them |
| `evidence.html` | **Evidence** | Verbatim transcripts from the live realm, and the dashboard reading the same records |
| `css/site.css` | — | The whole stylesheet. Dark only, mirroring the dashboard's own design tokens |
| `img/` | — | Screenshots of the live dashboard |
| `tools/capture.py` | — | Re-takes the panel, inspector and map screenshots |
| `tools/capture-evidence.py` | — | Re-takes the full-screen archive screenshots used on the Evidence page |

The four Dashboard pages share a sub-navigation strip and all mark **Dashboard** as the active top-level
section. Adding a page to that section means adding one line to the `.subnav` block in each of the four.

Plain static HTML. No build step, no framework, no JavaScript of its own. `.nojekyll` is present so GitHub
Pages serves the files as they are.

## Re-taking the screenshots

With the realm running and the dashboard answering on `127.0.0.1:8787`:

```sh
python3 tools/capture.py                 # every panel, inspector and map shot
python3 tools/capture.py panel map       # only shots whose name contains one of these words
python3 tools/capture-evidence.py        # the full-screen archives, by their own web addresses
```

Both drive headless Firefox through the snap's geckodriver over the WebDriver protocol — no selenium or
playwright needed. Override the target with `DASH_URL`, and the bot used for the inspector shots with
`DASH_BOT` (it needs one with a backstory, plenty of ties and a good pile of memories).

`capture.py` reaches the full-screen views by clicking their buttons; `capture-evidence.py` navigates
straight to `#overheard`, `#warmest`, `#moments` and `#memories`, which is shorter and survives a button
moving.

## Checking the site locally

```sh
python3 -m http.server 8099 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8099/`. There is no build step, so what you see is what Pages serves.

## The one rule this repository keeps

**No Blizzard-derived data, ever.** The dashboard's painted world map is extracted from the operator's own game
client, so both capture scripts turn it off — they set `dash.art` to `0` in the page's local storage before
taking a single frame, which leaves the map drawing zone outlines, zone names, company holdings and live
character markers on the dark ground instead.

If you re-take screenshots by hand, switch **Layers ▸ Map art** off first.

Nothing else from a client, an extracted archive or a world database dump belongs in this repository either.

## Figures on the site

Counts quoted on Home, Features and Evidence were read from the live realm and are dated on the page. When
they are refreshed, the date must be refreshed with them — a stale figure presented as current is the one
mistake this site can make that a reader cannot catch.

## Licence

MIT — see `LICENSE`.

World of Warcraft and Warcraft are trademarks of Blizzard Entertainment. This project is not affiliated with or
endorsed by Blizzard, and distributes no Blizzard data.
