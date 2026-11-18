# TuxoFlood 🐧🌊

*[English below](#english)*

Pingvines, vidám, színkitöltő fejtörő (*Flood-It* típusú játék) Python 3 + pygame alapon.
A Tuxo játékcsalád harmadik tagja a [Tuxdoku](https://github.com/sipiatti/tuxdoku) és a [TuxoMage](https://github.com/sipiatti/tuxomage) után.

> **Szerző:** Siposs Attila <sipiatti@gmail.com>  
> A játék *vibe coding* technikával, a **Grok Bot** segítségével készült.

## A játék

A pálya színes jégtáblákból áll. A pingvin a **bal felső sarokból** indul, és az ottani azonos színű mezők alkotják a te **területedet**.

* Egy **lépésben** választasz egy színt: a területed átszíneződik, és elnyeli az összes vele szomszédos (fent, lent, balra, jobbra) ugyanolyan színű mezőt.
* A cél, hogy az **egész pálya egyetlen színű** legyen.
* Minden pályán **korlátos a lépések száma**. Ha elfogynak, mielőtt kész lennél, **a szint elveszett**, és új pályán kezdheted újra ugyanazt a szintet.
* **Időkorlát nincs**, nyugodtan gondolkodj. Az eltelt időt a játék csak statisztikaként mutatja, a pontozásba nem számít bele.

**A lépéskorlát** úgy készül, hogy a játék minden új pályát megold a beépített megoldóval. A megoldó a mohó, a kétlépéses előretekintő és a nyalábkereső (beam search) változat közül a legrövidebb megoldást választja. Ennek hossza a **pingvinrekord** (par), és ehhez jön néhány tartaléklépés. A tartalék a szintekkel fogy, +40%-ról +8%-ra. Így minden pálya **garantáltan megoldható** a korláton belül: a megoldó megoldását a játék ellenőrzi is.

### Szintek

Szintenként nő a pálya mérete és a színek száma, egészen 16 színig.

| Szint | Pálya | Színek | Tartalék | Pingvinrekord (kb.) | Lépéskorlát (kb.) |
|---|---|---|---|---|---|
| 1 | 6×6 | 3 | +40% | 5 | 7 |
| 2 | 7×7 | 3 | +38% | 7 | 9 |
| 3 | 8×8 | 4 | +36% | 9 | 12 |
| 4 | 9×9 | 4 | +34% | 10 | 14 |
| 5 | 10×10 | 5 | +32% | 14 | 18 |
| 6 | 11×11 | 5 | +30% | 15 | 19 |
| 7 | 12×12 | 6 | +28% | 19 | 24 |
| 8 | 13×13 | 6 | +26% | 20 | 25 |
| 9 | 14×14 | 7 | +24% | 26 | 32 |
| 10 | 14×14 | 8 | +22% | 27 | 33 |
| 11 | 15×15 | 8 | +20% | 30 | 36 |
| 12 | 16×16 | 9 | +19% | 35 | 42 |
| 13 | 17×17 | 10 | +18% | 40 | 47 |
| 14 | 18×18 | 10 | +17% | 42 | 50 |
| 15 | 18×18 | 11 | +16% | 44 | 52 |
| 16 | 19×19 | 12 | +15% | 51 | 59 |
| 17 | 20×20 | 12 | +14% | 54 | 61 |
| 18 | 21×21 | 13 | +13% | 62 | 70 |
| 19 | 22×22 | 14 | +12% | 66 | 74 |
| 20 | 23×23 | 14 | +11% | 72 | 80 |
| 21 | 24×24 | 15 | +10% | 79 | 87 |
| 22 | 25×25 | 16 | +9% | 84 | 92 |
| 23+ | 26×26 | 16 | +8% | 89 | 96 |

A 23. szinttől a játék **végtelen**: minden további szint 26×26-os, 16 színnel, mindig új pályával.
A pontos pingvinrekord és lépéskorlát pályáról pályára kicsit változik. Egy szint teljesítése feloldja a következőt, a **Szintek** képernyőn bármelyik feloldott szint újrajátszható.

**Főmenü:** ha már van haladásod, a **Folytatás: N. szint** a következő szinttől visz tovább, az **Új játék (1. szinttől)** pedig előröl kezdi a szinteket.
Előtte megerősítést kér („Biztosan előröl kezded? A feloldott szintek és pontok törlődnek.” – Igen / Mégse, alapból a Mégse van kijelölve).
Újrakezdéskor a feloldott szintek, a szintenkénti legjobb pontok és csillagok törlődnek; a **statisztika, a dicsőségtábla és a beállítások megmaradnak**.
A régi haladás nem vész el nyomtalanul: a mentésben a `campaign_backups` alatt (az utolsó 5), és a teljes korábbi fájl `progress.json.bak-ÉÉÉÉHHNN-ÓÓPPMM` néven is megmarad.
Friss mentésnél csak egy **Új játék** gomb látszik.

### Pontozás

* **Pályapont:** 10 × méret × színek száma (pl. 10×10, 5 szín: 500).
* **Megmaradt lépések:** minden fel nem használt lépés (10 + 5 × színek) pontot ér.
* **Pingvinrekord-bónusz:** ha legfeljebb annyi lépésből végzel, mint a megoldó, 50 × színek pontot kapsz, és minden lépésért, amivel megverted, további 25 × színek pontot.
* **Csillagok:** 3 ★ a pingvinrekord vagy jobb, 2 ★ a tartalék első felén belül, egyébként 1 ★.
* **Könnyítéssel** megoldott pálya: nincs csillag és pingvinrekord-bónusz.

Az idő **nem számít bele** a pontokba. Szintenként a legjobb eredmény marad meg, az összpontszám ezek összege.

### Irányítás

| Egér / billentyű | Hatás |
|---|---|
| Bal klikk egy színgombon vagy a pálya bármelyik mezőjén | az adott szín választása |
| Rámutatás egy színgombra | a gomb kiemelése (a pályán nem jelöl semmit) |
| 1–9, 0, Q W E R T Y | 1–16. szín |
| N / „Új pálya” gomb | új pálya ugyanezen a szinten |
| C / szem gomb | színtévesztő mód: minden színnek saját szimbóluma van |
| P vagy Esc | szünet (folytatás, új pálya, beállítások, súgó, menü) |
| ↑ ↓ / Tab, Enter / Szóköz | menüpont kiválasztása és indítása (Enter magában: Folytatás); a párbeszédablakban Esc = Mégse |
| M / S | zene / hangeffektek be/ki |
| F11 | teljes képernyő |

Ha kevés lépés marad (a korlát 15%-a, de legalább 3), a lépésszámláló pirosra vált és lüktet, és figyelmeztető hang szól.
A beállításokban állítható a zene és az effektek hangereje, a nyelv (magyar / angol), a teljes képernyő, a színtévesztő mód, a könnyítés és az áradás-animáció.

**Könnyítés** (alapból KI): ha bekapcsolod, rámutatáskor villogó keret jelzi a pályán, mely mezőket nyelné el a szín, a gombon pedig a mezők száma („+N”) látszik.
Az a pálya, amelyen a könnyítés akár csak egy pillanatra is be volt kapcsolva, **nem ér csillagot és pingvinrekord-bónuszt** (a pályapont és a megmaradt lépések pontja jár).
Ezt a győzelmi képernyő és a beállítások is jelzik.
Ha nincs hangeszköz, a játék hang nélkül fut; a `--mute` kapcsolóval a hangeszközt meg sem nyitja.
A haladás, a statisztika, a dicsőségtábla és a beállítások helye: `~/.local/share/tuxoflood/progress.json`
(vagy `$XDG_DATA_HOME/tuxoflood`, illetve `$TUXOFLOOD_DATA_DIR`).

## Futtatás

```bash
sudo apt install python3-pygame      # vagy: pip install -r requirements.txt
python3 -m tuxoflood                 # a projekt mappájából
python3 -m tuxoflood --lang en --fullscreen --mute
# vagy telepítve:
pip install .  &&  tuxoflood
```

Tesztek: `python3 -m pytest` (vagy `pip install -r requirements-dev.txt` után).

### Debian/Ubuntu csomag (.deb)

```bash
packaging/build_deb.sh                           # -> dist/tuxoflood_0.1.0_all.deb
sudo apt install ./dist/tuxoflood_0.1.0_all.deb  # telepítés
tuxoflood                                        # vagy a menüből: Játékok → TuxoFlood
sudo apt remove tuxoflood                        # eltávolítás
```

---

## English

A cheerful penguin colour-flood puzzle (*Flood-It* style) written in Python 3 with pygame 2.
It is the third game of the Tuxo family, after [Tuxdoku](https://github.com/sipiatti/tuxdoku) and [TuxoMage](https://github.com/sipiatti/tuxomage).

> **Author:** Siposs Attila <sipiatti@gmail.com>  
> This game was created using *vibe coding*, with the help of **Grok Bot**.

**Rules.** The board is made of coloured ice tiles. The penguin starts in the **top-left corner**, and the same-coloured tiles connected to it form **your area**.
Each **move** you pick a colour. Your area takes that colour and swallows every orthogonally touching tile of the same colour.
Fill the **whole board with one colour**. Every board has a **move limit**. If you run out of moves first, **the level is lost** and you start that level again on a new board.
There is **no time limit**. Elapsed time is shown as a statistic only, and it never affects the score.

**Move limit.** Every new board is solved by the built-in solver. It runs a greedy, a two-move lookahead and a beam-search variant and keeps the shortest solution.
That length is the **penguin par**, and a few spare moves are added on top. The spare moves shrink from +40% to +8% as the levels go up.
The solver's solution is verified, so every board is **guaranteed to be solvable** within the limit.

**Levels.** The board grows from 6×6 with 3 colours to 26×26 with 16 colours over 23 levels (see the table above). From level 23 on the game is **endless**: every level is 26×26 with 16 colours and a fresh board.
Completing a level unlocks the next one, and every unlocked level can be replayed from the **Levels** screen.

**Main menu.** Once you have progress, **Continue: level N** carries on from your next level, and **New game (from level 1)** starts the levels over.
It asks first ("Start over from level 1? Unlocked levels and scores will be cleared." – Yes / Cancel, with Cancel selected by default).
Starting over clears unlocked levels and the per-level best scores and stars; **statistics, the high-score list and settings are kept**.
The old progress is kept too: inside the save under `campaign_backups` (the last 5), and as a copy of the whole previous file named `progress.json.bak-YYYYmmdd-HHMMSS`.
On a fresh save the menu shows a single **New game** button.

**Scoring.**
* Board points: 10 × size × colours.
* Every unused move is worth (10 + 5 × colours).
* The par bonus is 50 × colours if you used no more moves than the solver, plus 25 × colours for every move under par.
* Stars: 3 ★ at par or better, 2 ★ within the first half of the spare moves, 1 ★ otherwise.
* Boards solved with the assist on: no stars and no par bonus.

Time is never scored. The best result of every level is kept, and the total score is their sum.

**Controls:**
* Click a colour button or any tile on the board to play that colour.
* Hovering a colour button only highlights the button; nothing is marked on the board.
* Keys **1–9, 0, Q W E R T Y** pick colours 1–16.
* **N** starts a new board, **C** toggles colour-blind symbols, and **P** / **Esc** pauses.
* **M** / **S** toggle music / sound effects, and **F11** toggles fullscreen.
* In menus **↑ ↓ / Tab** move the selection and **Enter / Space** presses it (Enter alone: Continue); in the confirmation dialog **Esc** cancels.

When few moves are left (15% of the limit, at least 3), the move counter turns red and pulses, and a warning sound plays.
Settings include music/effects volume, language (Hungarian / English), fullscreen, colour-blind mode, the assist and the flood animation.

**Assist** (off by default): when on, hovering a colour outlines on the board the tiles it would swallow and shows their count ("+N") on the button.
A board on which the assist was on at any moment earns **no stars and no par bonus** (board points and unused-move points still count).
The win screen and the settings screen both say so.
If no audio device is available, the game runs silently; `--mute` skips opening the audio device entirely.
Progress, statistics, high scores and settings live in `~/.local/share/tuxoflood/progress.json`
(or `$XDG_DATA_HOME/tuxoflood`, or `$TUXOFLOOD_DATA_DIR`).

**Run:** `python3 -m tuxoflood [--lang hu|en] [--fullscreen] [--mute]`. It needs `python3-pygame` or `pip install -r requirements.txt`.
Alternatively, run `pip install .` and then `tuxoflood`. Tests: `python3 -m pytest`.

**Debian package:** `packaging/build_deb.sh` builds a reproducible `dist/tuxoflood_0.1.0_all.deb` with plain `dpkg-deb`.
Install it with `sudo apt install ./dist/tuxoflood_0.1.0_all.deb`.
It depends on `python3 (>= 3.10)` and `python3-pygame (>= 2.1)`.
The maintainer is set at the top of the script, or via `TUXOFLOOD_MAINTAINER`.

**Project layout**

```
tuxoflood/           game package (python3 -m tuxoflood)
  flood.py           rules, board generator, solvers, level table, scoring (pure Python)
  i18n.py            Hungarian / English strings
  storage.py         progress / statistics / high scores / settings JSON
  audio.py           sound effects + music (silent fallback)
  app.py, ui.py, theme.py, resources.py   pygame front-end
  assets/            fonts (OFL), penguins, icons, sounds, music (CC0)
tools/make_assets.py   regenerates all artwork from SVG code
tools/make_sounds.py   synthesizes all sound effects + music
tools/screenshots.py   headless screenshots
data/                  desktop entry + icons
packaging/             build_deb.sh, launcher, man page, debian/
tests/                 pytest suite (rules, generator, solver, levels, scoring, saves, UI)
```

License: MIT © 2026 Siposs Attila (code); assets see [CREDITS.md](CREDITS.md).
