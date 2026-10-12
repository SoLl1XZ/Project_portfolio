# Portfolio

Statisk portefølje-hjemmeside (på engelsk), der viser et kort for hvert projekt i `Projects/`.
Et Python-script scanner søskendemapperne og skriver `data/projects.js`, som siden læser.

## Kør

```bash
python3 build.py           # scanner ../ og skriver data/projects.js
open index.html            # åbner siden (virker via file://)
```

Kun Pythons standardbibliotek bruges; der skal ikke installeres pakker.

## Test

```bash
python3 -m unittest discover tests
```

Visuelle tests: browser-panelet i Claude kan ikke indlæse CSS/JS fra `file://`. Brug preview-serveren "portfolio" (port 8123, defineret i `~/Documents/Code/.claude/launch.json`).

## GitHub og online-side

- Repo: https://github.com/SoLl1XZ/Project_portfolio (offentligt). Siden: https://soll1xz.github.io/Project_portfolio/
- GitHub Pages publicerer `main` fra roden uden byggetrin. `.nojekyll` slår Jekyll fra, så fx `CLAUDE.md` ikke bliver til en side.
- Commits bruger noreply-adressen `222303744+SoLl1XZ@users.noreply.github.com` (sat i repoets lokale git-config), aldrig gmail.
- Kun Macro Dashboard og Backtester vises (Eriks valg 2026-10-12). De andre projekter har `"hidden": true` i deres `portfolio.json`.

## Automatisk opdatering

En launchd-agent kører `publish.py` hver mandag kl. 9 og logger til `logs/build.log`. Den kører `build.py`, og hvis
et projekt er ændret (ikke kun tidsstemplet), committer den `data/projects.js` og pusher til GitHub.
Kun tidsstempel ændret: filen sættes tilbage, så arbejdsmappen forbliver ren.
Den pusher også commits, som en tidligere kørsel uden internet efterlod, og alle andre lokale commits på `main`.
Sover Mac'en på det tidspunkt, kører den ved næste opvågning; er den slukket, springes ugen over.

```bash
./launchd/install.sh                                                   # installér / geninstallér
launchctl kickstart -k gui/$(id -u)/com.eriklokkegaard.portfolio-build # kør nu
launchctl print gui/$(id -u)/com.eriklokkegaard.portfolio-build        # status og sidste exit code
./launchd/uninstall.sh                                                 # fjern igen
```

Ændres plist-filen, skal `install.sh` køres igen (den kopierer filen til `~/Library/LaunchAgents/`).

## Struktur

| Fil | Ansvar |
|-----|--------|
| `scan.py` | Udtrækker titel, beskrivelse, teknologier og dato fra én projektmappe |
| `build.py` | Scanner alle projektmapper og skriver `data/projects.js` |
| `publish.py` | Kører `build.py`, committer og pusher data, hvis et projekt er ændret (bruges af launchd) |
| `index.html`, `style.css`, `app.js` | Selve siden |
| `data/projects.js` | Genereret data: `window.PORTFOLIO_DATA = {...}` |
| `images/` | Skærmbilleder, ét pr. projekt: `<mappenavn>.jpg` |
| `launchd/` | Ugentlig genbygning: plist samt install- og uninstall-script |
| `tests/` | Unit tests (unittest) |

## Hvor projektdata kommer fra

Første kilde, der findes, vinder (pr. felt):

1. `portfolio.json` i projektmappen: `title`, `description`, `tags`, `links`, `hidden`
2. `README.md`: første `#`-overskrift og første afsnit
3. `CLAUDE.md`: samme, men et "CLAUDE.md – "-præfiks fjernes fra titlen
4. Mappenavnet (`macro_dashboard` → "Macro Dashboard")

Eksempel på `portfolio.json`:

```json
{
  "title": "Macro Dashboard",
  "description": "Static dashboard with macroeconomic indicators.",
  "tags": ["Python", "Chart.js"],
  "links": {"GitHub": "https://github.com/..."},
  "hidden": false
}
```

## Skærmbilleder og layout

- Findes `images/<mappenavn>.jpg`, får projektet feltet `image` og vises som stort kort ("Featured") øverst.
  Projekter uden billede vises som kompakte kort i et grid nedenunder. Der er intet `featured`-flag.
- Billederne ligger her (ikke i projektmapperne), fordi GitHub Pages kun viser filer fra dette repo.
- Ugejobbet committer kun `data/projects.js`. Et nyt eller ændret billede skal committes i hånden.
- `macro_dashboard.jpg` er 800×500 fra browser-panelet (fanen Global, mørk tilstand). Et skarpere billede med samme
  navn og forhold 16:10 kan erstatte det.
- Det store kort står side om side fra 900 px. Under det ligger billedet øverst, ellers bliver det en smal stribe.
- Backtester har intet billede, før dens dashboard (dens M4) findes. Brug aldrig et opdigtet diagram.

## Vigtige beslutninger

- Data gemmes som `.js` (ikke `.json`), fordi en side åbnet via `file://` ikke må `fetch()` lokale filer.
- Browseren kan ikke selv liste mapper på disken, derfor scanner Python og skriver en datafil.
- Tekst fra projekter indsættes med `textContent`, aldrig `innerHTML`, så indhold fra en README ikke kan køre som kode.
- `data/projects.js` committes, så siden kan ligge på GitHub Pages uden byggetrin.
- Byggeriet sker lokalt (ikke i GitHub Actions), fordi det skal læse søskendemapperne på Mac'en.
- launchd kører Python direkte, ikke et shell-script, fordi Python allerede har macOS' tilladelse til `~/Documents`.
