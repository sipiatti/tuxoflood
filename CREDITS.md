# Credits / Forrásmegjelölés

Author / Szerző: **Siposs Attila** <sipiatti@gmail.com>. The game, its artwork and audio were created using vibe coding, with the help of Grok Bot. / A játék (a grafikával és hangokkal együtt) vibe coding technikával, a Grok Bot segítségével készült.

| Asset | Files | Source | License |
|---|---|---|---|
| Penguin sprites (sailor-cap penguin: normal / happy / sad / in a swim ring) | `tuxoflood/assets/penguins/*.png`, `tuxoflood/assets/svg/*.svg` | Original artwork drawn as SVG code in `tools/make_assets.py` (Tux-*inspired*, not derived from Larry Ewing's Tux files) | **CC0 1.0** |
| UI icons (steps, drop, eye, restart, pause, lock, stars, trophy, palette, home, globe, arrows, gear, music, speaker, …) and the app icon | `tuxoflood/assets/icons/*.png`, `data/icons/*` | Original artwork, `tools/make_assets.py` | **CC0 1.0** |
| 16-colour palette and colour-blind symbols | `tuxoflood/theme.py`, `tuxoflood/ui.py` | Original, drawn in code | MIT (with the code) |
| Sound effects: click, hover, flood, splash, combo, warning, denied, start, unlock, victory, defeat | `tuxoflood/assets/sounds/*.wav` | Original, synthesized from code (numpy) in `tools/make_sounds.py` | **CC0 1.0** |
| Music: "Színes áradat" (menu loop, 33 s, 116 BPM, F major) and "Hullámzó jégtáblák" (gameplay loop, 87 s, 88 BPM, E minor / G major) | `tuxoflood/assets/music/menu.ogg`, `game.ogg` | Original compositions, synthesized by `tools/make_sounds.py` (ffmpeg/libvorbis used only as the encoder) | **CC0 1.0** |
| Font **Baloo 2** (500, 700, 800) | `tuxoflood/assets/fonts/Baloo2-*.ttf` | Copyright 2019 The Baloo 2 Project Authors, https://github.com/EkType/Baloo2 | **SIL Open Font License 1.1**, `tuxoflood/assets/fonts/OFL.txt` |
| Game engine | not bundled | pygame, https://www.pygame.org | LGPL 2.1 |

**Inspiration:** the classic colour-flood puzzle (known as *Flood-It* and many clones). TuxoFlood is an independent implementation and contains no third-party artwork, sounds or music.

"Tux" the Linux penguin was originally drawn by Larry Ewing using The GIMP. TuxoFlood's penguins are independent drawings in a similar spirit.
