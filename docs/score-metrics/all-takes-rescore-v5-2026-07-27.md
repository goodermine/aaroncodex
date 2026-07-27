# All takes — re-scored with the current engine (rubric v5, 2026-07-27)

Every archived take re-scored with **deterministic_rubric_v5** (calibration active, 50 pro references). Scores from superseded rubrics have been retired from the archive (retire_legacy_scores.py), so every number here is a current recompute — there are no stale scores left to quote. `cf` = capture-fair (voice_quality **and** dynamics excluded — the capture-robust components; **breath** is deliberately kept in, because air running out is the singer, not the room).

`breath` is new in v5. A blank means the analysis predates `analyse_breath()` and has no phrase-sag data, so it scored on 6 of 7 components (`coverage: partial`; weights renormalised). Re-analyse those takes with the current engine to close the gap — the difference is at most ~0.25 points, which is why they are still shown rather than withheld.

## Singer takes

Overall: min 6.1 · max 9.7 · mean 7.96. Dynamics component spreads 4.9–10.0 (was a flat 10.0 for every take in v3).

Full coverage: 91/113 takes.

| singer | song | notes | **v5** | cf | conf | inton | pitch | voice | vib | dyn | phrase | breath |
|---|---|--:|--:|--:|:--|--:|--:|--:|--:|--:|--:|--:|
| aaron | play-that-funky-music-take-001 | 206 | **7.7** | 8.5 | high | 7.62 | 10.0 | 3.05 | 9.66 | 9.86 | 6.05 | 8.94 |
| aaron | beggin-take-002 | 145 | **7.8** | 8.7 | high | 10.0 | 10.0 | 3.44 | 10.0 | 8.95 | 0.34 | 10.0 |
| aaron | lonely-boy-take-001 | 102 | **6.8** | 8.7 | medium | 10.0 | 10.0 | 1.07 | 10.0 | 5.28 | 0.0 | 10.0 |
| aaron | beggin-take-001 | 137 | **7.5** | 8.8 | high | 10.0 | 10.0 | 1.99 | 10.0 | 8.66 | 0.68 | 10.0 |
| aaron | ellis-play-that-funky-music-take-001 | 77 | **7.5** | 8.7 | medium | 10.0 | 10.0 | 2.37 | 10.0 | 8.54 | 0.0 | 10.0 |
| aaron | sunshine-smile-take-001 | 134 | **7.6** | 8.9 | high | 10.0 | 10.0 | 3.29 | 10.0 | 6.86 | 2.04 | 10.0 |
| aaron | don-t-be-cruel-take-001 | 162 | **7.7** | 8.8 | high | 10.0 | 10.0 | 1.83 | 10.0 | 9.64 | 1.32 | 10.0 |
| aaron | rebel-yell-take-001 | 163 | **7.3** | 8.7 | high | 10.0 | 10.0 | 1.47 | 10.0 | 7.8 | 0.53 | 10.0 |
| aaron | you-sexy-thing-take-001 | 193 | **7.4** | 6.4 | high | 7.62 | 4.8 | 9.92 | 9.09 | 9.17 | 6.77 | 1.36 |
| aaron | you-sexy-thing-take-002 | 177 | **6.1** | 4.4 | high | 5.71 | 0.04 | 9.57 | 7.86 | 9.89 | 6.28 | 0.49 |
| aaron | you-sexy-thing-take-003 | 183 | **6.2** | 5.0 | high | 7.62 | 0.0 | 9.56 | 7.46 | 7.89 | 6.58 | 0.42 |
| aaron | sex-bomb-take-001 | 190 | **7.3** | 9.1 | high | 10.0 | 10.0 | 1.44 | 10.0 | 5.82 | 3.52 | 9.94 |
| aaron | you-sexy-thing-take-004 | 208 | **7.1** | 6.9 | high | 7.62 | 6.39 | 5.95 | 8.99 | 9.55 | 4.61 | 4.81 |
| aaron | come-out-and-play-take-001 | 71 | **7.0** | 8.7 | medium | 10.0 | 10.0 | 1.39 | 10.0 | 6.24 | 0.0 | 10.0 |
| aaron | come-out-and-play-take-002 | 179 | **7.6** | 8.2 | high | 9.52 | 7.76 | 3.96 | 10.0 | 9.25 | 1.44 | 9.72 |
| aaron | you-sexy-thing-take-001 | None | **6.8** | 6.8 | low | – | – | – | – | 6.83 | – | – |
| aaron | you-sexy-thing-take-001 | 209 | **7.2** | 8.2 | high | 9.52 | 10.0 | 2.47 | 9.94 | 8.65 | 4.01 | 3.92 |
| aaron | you-sexy-thing-take-001 | 187 | **6.8** | 5.7 | high | 9.41 | 0.0 | 10.0 | 7.96 | 8.04 | 6.84 | 0.31 |
| aaron | you-sexy-thing-take-001 | 208 | **8.1** | 8.5 | high | 9.52 | 10.0 | 6.15 | 9.15 | 9.03 | 4.76 | 6.46 |
| aaron | you-sexy-thing-take-001 | 221 | **7.9** | 8.2 | high | 9.52 | 10.0 | 5.79 | 9.06 | 9.31 | 3.78 | 5.66 |
| aaron | funky-cold-medina-take-001 | 230 | **8.3** | 8.9 | high | 9.52 | 10.0 | 5.15 | 10.0 | 9.84 | 2.99 | 9.76 |
| aaron | let-s-stay-together-take-001 | 240 | **8.1** | 8.2 | high | 7.62 | 7.46 | 6.39 | 9.89 | 9.95 | 10.0 | 6.2 |
| aaron | let-s-stay-together-take-001 | 190 | **8.7** | 9.2 | high | 9.52 | 9.83 | 6.62 | 9.62 | 9.2 | 8.24 | 7.69 |
| aaron | sex-bomb-take-001 | 167 | **7.5** | 9.0 | high | 10.0 | 10.0 | 1.58 | 10.0 | 7.74 | 2.68 | 10.0 |
| aaron | she-s-not-there-take-001 | 180 | **7.9** | 9.1 | high | 10.0 | 10.0 | 2.62 | 10.0 | 9.27 | 3.25 | 9.72 |
| aaron | the-letter-take-001 | 170 | **7.3** | 8.0 | high | 9.52 | 8.05 | 3.79 | 9.0 | 8.62 | 3.93 | 6.44 |
| aaron | the-letter-take-002 | 203 | **6.9** | 7.3 | high | 7.62 | 9.32 | 3.36 | 9.03 | 9.52 | 3.67 | 4.46 |
| aaron | living-on-a-prayer-take-001 | 218 | **6.9** | 6.2 | high | 5.71 | 2.95 | 8.58 | 8.02 | 7.69 | 10.0 | 6.02 |
| aaron | you-sexy-thing-take-002 | 104 | **7.4** | 8.7 | medium | 10.0 | 10.0 | 4.45 | 10.0 | 4.89 | 0.0 | 10.0 |
| aaron | you-sexy-thing-take-003 | 236 | **7.9** | 7.8 | high | 7.62 | 6.57 | 7.05 | 8.03 | 9.95 | 10.0 | 7.47 |
| aaron | do-wah-diddy-diddy-take-002 | 149 | **7.8** | 8.9 | high | 10.0 | 10.0 | 2.63 | 10.0 | 9.2 | 2.91 | 8.59 |
| aaron | do-wah-diddy-diddy-take-003 | 191 | **8.3** | 8.7 | high | 9.52 | 7.51 | 7.75 | 8.87 | 6.81 | 9.3 | 7.94 |
| aaron | funky-cold-medina-take-001 | 120 | **8.0** | 7.7 | high | 7.62 | 10.0 | 8.7 | 10.0 | 8.48 | 4.46 | 4.53 |
| aaron | let-s-stay-together-take-003 | 182 | **8.0** | 7.1 | high | 6.67 | 3.66 | 10.0 | 9.14 | 9.82 | 10.0 | 7.51 |
| aaron | living-on-a-prayer-take-001 | 220 | **7.0** | 5.6 | high | 5.71 | 0.94 | 10.0 | 8.77 | 9.97 | 10.0 | 2.85 |
| aaron | oh-what-a-night-take-001 | 178 | **9.2** | 9.3 | high | 9.52 | 7.51 | 10.0 | 9.82 | 7.85 | 10.0 | 10.0 |
| aaron | you-sexy-thing-take-001 | 198 | **7.3** | 6.2 | high | 6.67 | 5.56 | 10.0 | 8.02 | 9.19 | 6.92 | 2.18 |
| aaron | get-up-i-feel-like-being-a-sex-machine-take-001 | 274 | **8.0** | 8.6 | high | 9.52 | 9.97 | 4.78 | 8.84 | 9.63 | 4.84 | 7.67 |
| aaron | the-letter-take-001 | 192 | **9.0** | 8.6 | high | 9.52 | 8.56 | 9.87 | 8.84 | 9.8 | 8.09 | 6.62 |
| aaron | the-letter-take-002 | 183 | **7.3** | 7.2 | high | 9.52 | 2.62 | 7.15 | 10.0 | 8.39 | 3.93 | 7.25 |
| aaron | danger-zone-take-001 | 172 | **7.8** | 7.2 | high | 5.71 | 8.09 | 8.66 | 8.73 | 9.54 | 10.0 | 4.84 |
| aaron | i-just-want-to-be-your-everything-take-001 | 192 | **9.4** | 9.7 | high | 9.52 | 10.0 | 9.84 | 9.84 | 7.79 | 10.0 | 8.96 |
| aaron | kryptonite-take-001 | 171 | **8.9** | 8.5 | high | 9.52 | 6.32 | 10.0 | 9.92 | 9.38 | 10.0 | 5.44 |
| aaron | kryptonite-take-002 | 176 | **8.1** | 8.6 | high | 9.52 | 6.75 | 5.25 | 9.25 | 9.73 | 8.66 | 7.67 |
| aaron | the-heat-is-on-take-001 | 238 | **9.3** | 9.0 | high | 9.52 | 8.2 | 9.94 | 8.89 | 9.77 | 10.0 | 8.32 |
| aaron | the-letter-take-001 | 182 | **7.0** | 6.9 | high | 6.67 | 5.23 | 5.46 | 9.2 | 9.62 | 3.63 | 9.92 |
| aaron | danger-zone-new-studio-take-002 | 178 | **9.5** | 9.5 | high | 9.52 | 10.0 | 10.0 | 8.6 | 9.14 | 10.0 | – |
| aaron | danger-zone-take-003 | 177 | **8.7** | 8.5 | high | 7.62 | 8.11 | 10.0 | 9.19 | 7.73 | 10.0 | – |
| aaron | kryptonite-mango-hill-tavern-take-001 | 176 | **8.0** | 8.7 | high | 9.52 | 6.75 | 4.3 | 9.25 | 9.73 | 8.66 | – |
| aaron | lets-stay-together-new-studio-take-001 | 194 | **7.7** | 6.5 | high | 5.71 | 2.75 | 10.0 | 9.09 | 9.88 | 10.0 | – |
| aaron | the-heat-is-on-captain-cook-tavern-take-001 | 278 | **7.6** | 8.8 | high | 9.52 | 10.0 | 2.41 | 8.53 | 9.44 | 5.75 | – |
| aaron | the-heat-is-on-new-studio-take-001 | 230 | **8.6** | 7.9 | high | 9.52 | 6.44 | 10.0 | 8.27 | 9.65 | 5.71 | – |
| aaron | the-heat-is-on-take-002 | 232 | **8.8** | 8.4 | high | 9.52 | 7.96 | 10.0 | 8.89 | 9.4 | 5.22 | – |
| aaron | the-letter-joe-cocker-take-001 | 192 | **9.3** | 8.9 | high | 9.52 | 8.56 | 10.0 | 8.84 | 9.8 | 8.09 | – |
| aaron | wild-thing-take-001 | 162 | **9.0** | 8.8 | high | 9.52 | 10.0 | 9.23 | 10.0 | 9.49 | 4.27 | 8.29 |
| aaron | you-can-leave-your-hat-on-bramble-bay-take-001 | 163 | **6.7** | 5.9 | high | 5.71 | 4.98 | 7.69 | 7.1 | 9.14 | 5.71 | – |
| aaron | danger-zone-home | 175 | **8.2** | 7.6 | high | 5.71 | 8.18 | 8.98 | 8.62 | 9.75 | 10.0 | – |
| aaron | bye-bye-love-take-002 | 133 | **7.2** | 6.2 | high | 9.52 | 0.0 | 10.0 | 7.49 | 8.94 | 7.6 | 3.52 |
| aaron | come-out-and-play-captain-cook-tavern-take-001 | 177 | **6.6** | 7.1 | high | 7.62 | 6.32 | 2.56 | 8.9 | 9.54 | 4.35 | – |
| aaron | goodbye-s-been-good-to-you-take-001 | 197 | **8.6** | 8.0 | high | 7.62 | 7.08 | 10.0 | 9.58 | 9.47 | 10.0 | 6.24 |
| aaron | bye-bye-love-take-001 | 125 | **7.3** | 6.2 | high | 9.52 | 0.25 | 10.0 | 8.02 | 9.0 | 8.24 | 2.07 |
| aaron | bye-bye-love-take-002 | 126 | **7.5** | 6.5 | high | 10.0 | 0.0 | 10.0 | 9.11 | 9.29 | 7.9 | 2.28 |
| aaron | the-heat-is-on-take-001 | 226 | **7.1** | 6.1 | high | 5.71 | 6.57 | 8.94 | 8.69 | 9.14 | 5.03 | 3.88 |
| aaron | carved-from-stone-take-001 | 217 | **7.6** | 7.2 | high | 5.71 | 6.37 | 7.02 | 9.21 | 9.88 | 9.87 | 6.78 |
| aaron | my-babe-take-001 | 145 | **9.0** | 8.6 | high | 9.52 | 5.74 | 10.0 | 9.73 | 9.47 | 10.0 | 7.62 |
| aaron | my-babe-take-002 | 152 | **8.6** | 8.0 | high | 7.62 | 6.57 | 10.0 | 9.46 | 9.79 | 10.0 | 6.85 |
| aaron | my-babe-take-003 | 142 | **8.7** | 8.4 | high | 9.52 | 5.7 | 10.0 | 9.11 | 8.32 | 8.58 | 8.34 |
| aaron | my-babe-take-004 | 147 | **8.1** | 7.3 | high | 5.71 | 8.29 | 10.0 | 8.85 | 9.74 | 10.0 | 4.5 |
| aaron | my-babe-take-005 | 133 | **8.1** | 7.3 | high | 5.71 | 5.97 | 10.0 | 7.86 | 9.58 | 10.0 | 10.0 |
| aaron | my-babe-take-006 | 161 | **8.7** | 8.8 | high | 9.52 | 8.96 | 7.36 | 8.24 | 9.79 | 8.28 | 8.32 |
| aaron | the-heat-is-on-take-001 | 231 | **8.3** | 7.6 | high | 9.52 | 3.66 | 10.0 | 7.66 | 9.81 | 8.36 | 7.54 |
| aaron | the-heat-is-on-take-002 | 251 | **7.3** | 7.2 | high | 7.62 | 5.88 | 6.3 | 8.36 | 8.87 | 6.16 | 7.65 |
| aaron | you-sexy-thing-take-001 | 206 | **7.2** | 6.1 | high | 7.62 | 1.97 | 10.0 | 8.13 | 8.67 | 8.39 | 3.06 |
| aaron | the-heat-is-on-take-001 | 228 | **7.2** | 7.1 | high | 5.71 | 7.22 | 5.39 | 9.36 | 9.89 | 6.01 | 8.34 |
| aaron | living-on-a-prayer-take-002 | 204 | **7.9** | 8.1 | high | 9.52 | 6.9 | 5.77 | 8.59 | 9.89 | 5.71 | 7.91 |
| aaron | one-take-001 | 155 | **8.4** | 7.7 | high | 7.62 | 4.07 | 10.0 | 9.96 | 9.65 | 10.0 | 7.65 |
| aaron | working-class-man-take-001 | 176 | **7.9** | 8.4 | high | 9.52 | 7.02 | 5.15 | 8.83 | 8.93 | 8.54 | 6.8 |
| aaron | my-babe-take-001 | 138 | **8.5** | 7.9 | high | 9.52 | 4.31 | 10.0 | 8.58 | 9.97 | 10.0 | 5.86 |
| aaron | wild-thing-take-001 | 148 | **8.1** | 8.0 | high | 9.52 | 7.96 | 9.16 | 8.8 | 7.32 | 3.86 | 6.85 |
| aaron | my-babe-take-001 | 159 | **8.4** | 8.7 | high | 9.52 | 8.24 | 6.87 | 9.2 | 9.43 | 7.3 | 7.69 |
| aaron | one-take-001 | 177 | **8.9** | 8.6 | high | 9.52 | 6.61 | 9.67 | 9.29 | 9.06 | 10.0 | 7.0 |
| aaron | rockin-robin-take-001 | 168 | **8.4** | 8.6 | high | 9.52 | 8.65 | 7.15 | 9.19 | 9.51 | 3.74 | 10.0 |
| aaron | one-take-001 | 184 | **9.0** | 8.6 | high | 9.52 | 4.85 | 10.0 | 9.72 | 9.96 | 8.58 | 10.0 |
| aaron | pressure-down-take-001 | 194 | **8.7** | 8.2 | high | 8.57 | 7.11 | 10.0 | 9.99 | 9.38 | 10.0 | 4.55 |
| aaron | pressure-down-take-002 | 183 | **8.0** | 7.3 | high | 5.71 | 5.99 | 10.0 | 9.24 | 8.91 | 10.0 | 7.51 |
| aaron | pressure-down-take-003 | 181 | **8.7** | 8.4 | high | 9.52 | 6.32 | 10.0 | 9.99 | 8.7 | 10.0 | 4.91 |
| aaron | pressure-down-take-004 | 188 | **9.0** | 8.8 | high | 9.52 | 7.95 | 10.0 | 9.2 | 8.73 | 10.0 | 6.56 |
| aaron | pressure-down-take-005 | 178 | **8.4** | 7.8 | high | 7.62 | 5.68 | 10.0 | 9.91 | 9.05 | 8.88 | 7.25 |
| aaron | pressure-down-take-006 | 205 | **7.9** | 8.0 | high | 5.71 | 7.95 | 6.33 | 9.28 | 9.3 | 10.0 | 10.0 |
| aaron | my-babe-take-001 | 159 | **8.4** | 8.7 | high | 9.52 | 8.24 | 6.87 | 9.2 | 9.43 | 7.3 | 7.69 |
| aaron | my-babe-take-002 | 137 | **8.2** | 8.0 | high | 7.62 | 7.58 | 9.86 | 8.01 | 7.54 | 10.0 | 7.25 |
| aaron | my-babe-take-003 | 183 | **8.1** | 8.1 | high | 9.52 | 8.27 | 6.77 | 8.41 | 9.64 | 3.74 | 8.43 |
| aaron | play-that-funky-music-take-001 | 195 | **8.6** | 8.1 | high | 5.71 | 10.0 | 10.0 | 9.1 | 9.53 | 10.0 | 7.72 |
| aaron | play-that-funky-music-take-002 | 219 | **8.7** | 9.3 | high | 9.52 | 9.9 | 5.71 | 8.67 | 9.84 | 9.45 | 8.43 |
| aaron | play-that-funky-music-take-003 | 219 | **8.7** | 9.3 | high | 9.52 | 9.9 | 5.71 | 8.67 | 9.84 | 9.45 | 8.43 |
| aaron | pressure-down-captain-cook-tavern-take-001 | 227 | **8.2** | 9.2 | high | 9.52 | 10.0 | 4.64 | 8.72 | 7.92 | 9.94 | 7.43 |
| aaron | pressure-down-take-007 | 224 | **7.8** | 7.8 | high | 7.62 | 8.05 | 6.29 | 8.34 | 9.74 | 7.03 | 8.18 |
| aaron | pressure-down-take-008 | 215 | **8.4** | 8.8 | high | 9.52 | 7.57 | 5.9 | 8.41 | 9.94 | 10.0 | 7.94 |
| aaron | tutti-frutti-take-001 | 154 | **8.1** | 7.2 | high | 7.62 | 5.29 | 10.0 | 9.05 | 9.95 | 10.0 | 3.14 |
| aaron | tutti-frutti-take-002 | 177 | **7.3** | 7.1 | high | 7.62 | 4.49 | 6.17 | 8.54 | 9.89 | 8.36 | 6.24 |
| aaron | kryptonite-take-001 | 154 | **8.4** | 8.1 | high | 9.52 | 6.91 | 10.0 | 9.95 | 7.75 | 10.0 | 1.96 |
| aaron | the-heat-is-on-take-001 | 198 | **6.8** | 5.5 | high | 5.71 | 3.35 | 10.0 | 8.96 | 8.62 | 5.26 | 3.37 |
| aaron | you-sexy-thing-take-001 | 224 | **6.5** | 4.9 | high | 5.71 | 0.9 | 10.0 | 8.8 | 9.41 | 7.67 | 0.54 |
| aaron-g | 1973-take-001 | 168 | **8.3** | 7.6 | high | 5.71 | 10.0 | 10.0 | 10.0 | 9.27 | 5.29 | – |
| aaron-g | if-you-could-read-my-mind-take-001 | 208 | **9.3** | 9.2 | high | 9.52 | 7.55 | 10.0 | 10.0 | 8.48 | 10.0 | – |
| aaron-g | vienna-take-001 | 175 | **9.7** | 9.6 | high | 9.52 | 9.23 | 10.0 | 10.0 | 9.43 | 10.0 | – |
| chris | feeling-good-take-001 | 221 | **7.7** | 8.4 | high | 7.62 | 6.97 | 3.73 | 10.0 | 9.97 | 10.0 | – |
| leo | chasin-that-neon-rainbow | 202 | **8.3** | 9.7 | high | 9.52 | 10.0 | 4.53 | 9.4 | 7.45 | 10.0 | – |
| rilda | lets-stay-together-home-take-001 | 199 | **7.8** | 7.0 | high | 7.62 | 1.23 | 10.0 | 9.75 | 8.16 | 10.0 | – |
| rilda | this-masquerade-take-001 | 165 | **8.2** | 7.5 | high | 9.52 | 0.0 | 10.0 | 9.77 | 9.35 | 10.0 | – |
| rilda | she-s-not-there-take-001 | 138 | **7.1** | 7.2 | high | 5.71 | 5.05 | 4.84 | 9.89 | 9.6 | 10.0 | – |
| rilda | dreams-take-001 | 260 | **8.3** | 8.5 | high | 9.52 | 6.43 | 6.44 | 10.0 | 9.97 | 6.88 | – |
| rilda | you-sexy-thing-take-001 | 205 | **8.0** | 8.0 | high | 7.62 | 5.39 | 7.31 | 9.8 | 9.0 | 10.0 | – |

## Professional references (calibration sanity check)

Overall: min 8.4 · max 9.7 · mean 8.9 — pros should sit near the top.

| reference | v5 | cf | inton | pitch | voice | vib | dyn | phrase | breath |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| carpenters-this-masquerade | **9.2** | 9.0 | 10.0 | 5.83 | 10.0 | 10.0 | 9.26 | 10.0 | 8.94 |
| glenn-frey-the-heat-is-on | **8.4** | 8.8 | 9.52 | 8.02 | 5.74 | 9.74 | 9.82 | 5.86 | 10.0 |
| james-blunt-1973 | **8.8** | 9.6 | 10.0 | 10.0 | 6.1 | 10.0 | 8.3 | 7.37 | 10.0 |
| joe-cocker-the-letter | **8.6** | 9.2 | 9.52 | 10.0 | 5.48 | 10.0 | 9.5 | 5.33 | 10.0 |
| joe-cocker-you-can-leave-your-hat-on | **8.5** | 9.1 | 9.52 | 9.74 | 5.82 | 10.0 | 9.24 | 4.57 | 10.0 |
| kenny-loggins-danger-zone-official-audio-top-gun | **9.0** | 9.9 | 10.0 | 10.0 | 5.5 | 9.38 | 9.09 | 10.0 | 10.0 |
| kryptonite-3-doors-down | **9.7** | 9.7 | 9.52 | 10.0 | 9.68 | 9.44 | 9.39 | 10.0 | 10.0 |
| michael-buble-feeling-good | **9.4** | 9.2 | 10.0 | 6.68 | 10.0 | 9.96 | 9.39 | 10.0 | 9.16 |
| tina-turner-lets-stay-together | **8.5** | 8.4 | 6.67 | 9.34 | 7.84 | 10.0 | 10.0 | 9.38 | 7.67 |
