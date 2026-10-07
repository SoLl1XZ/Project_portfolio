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

## Automatisk opdatering

En launchd-agent kører `build.py` hver mandag kl. 9 og logger til `logs/build.log`.
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
| `index.html`, `style.css`, `app.js` | Selve siden |
| `data/projects.js` | Genereret data: `window.PORTFOLIO_DATA = {...}` |
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

## Vigtige beslutninger

- Data gemmes som `.js` (ikke `.json`), fordi en side åbnet via `file://` ikke må `fetch()` lokale filer.
- Browseren kan ikke selv liste mapper på disken, derfor scanner Python og skriver en datafil.
- Tekst fra projekter indsættes med `textContent`, aldrig `innerHTML`, så indhold fra en README ikke kan køre som kode.
- `data/projects.js` committes, så siden senere kan lægges på GitHub Pages uden byggetrin.
