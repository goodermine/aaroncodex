# All takes — re-scored with the current engine (rubric v5, 2026-09-15)

Every eligible archived take re-scored with **deterministic_rubric_v5** (calibration active, 50 pro references). Scores from superseded rubrics have been retired from the archive (retire_legacy_scores.py), so every numeric score here is a current recompute. Retired or source-blocked records remain visible as **withheld** rows and are not recomputed from contaminated stored measurements. `cf` = capture-fair (voice_quality **and** dynamics excluded — the capture-robust components; **breath** is deliberately kept in, because air running out is the singer, not the room).

`breath` is new in v5. A blank means the analysis predates `analyse_breath()` and has no phrase-sag data, so it scored on 6 of 7 components (`coverage: partial`; weights renormalised). Re-analyse those takes with the current engine to close the gap — the difference is at most ~0.25 points, which is why they are still shown rather than withheld.

## Singer takes

Overall: min 5.4 · max 9.4 · mean 7.34. Dynamics component spreads 5.8–10.0 (was a flat 10.0 for every take in v3).

Full coverage: 234/248 takes.

| singer | song | notes | **v5** | cf | conf | inton | pitch | voice | vib | dyn | phrase | breath |
|---|---|--:|--:|--:|:--|--:|--:|--:|--:|--:|--:|--:|
| aaron | 2025-05-aaron-creep-learning | 156 | **7.4** | 6.8 | high | 10.0 | 0.0 | 10.0 | 7.9 | 7.12 | 8.82 | 5.59 |
| aaron | 3am | 153 | **8.5** | 8.0 | high | 10.0 | 0.0 | 9.96 | 9.88 | 9.48 | 10.0 | 10.0 |
| aaron | lose-control | 188 | **8.5** | 8.3 | high | 10.0 | 2.58 | 9.82 | 8.88 | 7.9 | 10.0 | 10.0 |
| aaron | hang-on-sloopy | 203 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | twist-and-shout | 119 | **8.3** | 8.5 | high | 10.0 | 10.0 | 7.34 | 9.31 | 8.55 | 1.85 | 7.94 |
| aaron | kryptonite | 130 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | lean-on-me | 282 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | bust-a-move | 162 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | bad-things | 88 | **7.2** | 6.3 | high | 10.0 | 0.0 | 10.0 | 8.3 | 8.08 | 10.0 | 0.0 |
| aaron | i-m-a-believer | 141 | **7.5** | 6.4 | high | 10.0 | 0.0 | 10.0 | 7.9 | 9.58 | 5.64 | 5.47 |
| aaron | mustang-sally | 199 | **7.1** | 5.9 | high | 6.0 | 0.0 | 10.0 | 7.9 | 9.4 | 10.0 | 7.05 |
| aaron | stand-by-me | 148 | **7.7** | 7.1 | high | 6.0 | 2.35 | 10.0 | 9.74 | 7.64 | 10.0 | 10.0 |
| aaron | the-letter | 171 | **7.5** | 6.5 | high | 6.0 | 0.0 | 10.0 | 9.25 | 9.34 | 9.85 | 10.0 |
| aaron | you-spin-me-round | 114 | **7.1** | 6.4 | high | 10.0 | 0.0 | 10.0 | 8.43 | 7.26 | 10.0 | -0.0 |
| aaron | play-that-funky-music | 206 | **7.4** | 8.1 | high | 10.0 | 6.99 | 3.23 | 8.43 | 9.61 | 5.12 | 7.41 |
| aaron | beggin | 225 | **6.9** | 7.3 | high | 10.0 | 0.0 | 4.65 | 8.68 | 8.22 | 10.0 | 6.38 |
| aaron | lonely-boy | 141 | **7.5** | 6.7 | high | 8.0 | 0.0 | 10.0 | 9.41 | 8.48 | 10.0 | 6.17 |
| aaron | beggin | 212 | **7.3** | 7.9 | high | 10.0 | 1.6 | 4.92 | 9.7 | 6.97 | 9.97 | 7.6 |
| aaron | ellis-play-that-funky-music | 201 | **7.4** | 8.1 | high | 10.0 | 8.42 | 3.23 | 7.79 | 9.57 | 4.91 | 6.72 |
| aaron | sunshine-smile | 157 | **9.1** | 9.4 | high | 10.0 | 9.11 | 7.4 | 9.85 | 9.82 | 9.88 | 7.05 |
| aaron | don-t-be-cruel | 223 | **8.0** | 7.7 | high | 6.0 | 6.82 | 7.41 | 10.0 | 9.74 | 9.03 | 8.82 |
| aaron | rebel-yell | 251 | **6.6** | 6.5 | high | 6.0 | 7.22 | 4.51 | 8.89 | 9.54 | 2.58 | 7.35 |
| aaron | you-sexy-thing | 188 | **6.6** | 5.1 | high | 8.0 | 0.0 | 10.0 | 8.64 | 9.64 | 5.45 | 0.0 |
| aaron | you-sexy-thing | 181 | **6.2** | 4.5 | high | 6.0 | 0.0 | 10.0 | 8.2 | 9.38 | 5.45 | 1.13 |
| aaron | you-sexy-thing | 184 | **7.0** | 5.9 | high | 10.0 | 0.0 | 10.0 | 7.78 | 8.35 | 5.76 | 1.5 |
| aaron | sex-bomb | 223 | **5.4** | 5.8 | high | 8.0 | 0.0 | 2.53 | 9.01 | 7.16 | 3.7 | 6.07 |
| aaron | you-sexy-thing | 206 | **5.9** | 5.2 | high | 6.0 | 0.0 | 6.25 | 8.92 | 9.0 | 5.27 | 5.68 |
| aaron | come-out-and-play | 175 | **7.4** | 7.5 | high | 8.0 | 9.11 | 6.73 | 9.85 | 7.68 | 1.55 | 6.17 |
| aaron | come-out-and-play | 193 | **7.0** | 7.5 | high | 6.0 | 10.0 | 3.82 | 9.68 | 8.51 | 2.91 | 8.82 |
| aaron | you-sexy-thing | 194 | **6.3** | 4.8 | high | 8.0 | 0.0 | 10.0 | 6.43 | 9.15 | 5.12 | 1.22 |
| aaron | you-sexy-thing | 212 | **5.9** | 5.7 | high | 8.0 | 0.0 | 3.4 | 8.65 | 9.78 | 4.12 | 6.0 |
| aaron | you-sexy-thing | 196 | **6.4** | 5.0 | high | 8.0 | 0.0 | 10.0 | 7.43 | 8.48 | 5.45 | 1.13 |
| aaron | you-sexy-thing | 205 | **7.3** | 7.0 | high | 10.0 | 0.0 | 7.01 | 9.81 | 9.23 | 5.64 | 7.41 |
| aaron | you-sexy-thing | 229 | **6.5** | 5.9 | high | 8.0 | 0.0 | 6.92 | 9.09 | 8.77 | 4.45 | 6.33 |
| aaron | funky-cold-medina | 236 | **6.0** | 5.9 | high | 8.0 | 0.0 | 4.96 | 8.62 | 7.79 | 2.55 | 8.55 |
| aaron | let-s-stay-together | 248 | **7.3** | 7.5 | high | 10.0 | 0.0 | 5.87 | 10.0 | 8.57 | 8.7 | 7.28 |
| aaron | let-s-stay-together | 196 | **8.8** | 9.1 | high | 10.0 | 10.0 | 6.89 | 10.0 | 9.95 | 5.45 | 7.81 |
| aaron | sex-bomb | 254 | **5.6** | 5.1 | high | 6.0 | 0.0 | 5.43 | 8.89 | 8.84 | 4.88 | 4.78 |
| aaron | she-s-not-there | 140 | **6.4** | 6.7 | high | 10.0 | 0.0 | 2.94 | 9.2 | 9.16 | 5.52 | 6.21 |
| aaron | the-letter | 176 | **6.4** | 6.6 | high | 10.0 | 0.29 | 3.43 | 9.14 | 9.59 | 3.21 | 7.05 |
| aaron | the-letter | 199 | **5.7** | 5.7 | high | 8.0 | 0.92 | 3.27 | 8.99 | 8.77 | 2.33 | 5.91 |
| aaron | living-on-a-prayer | 211 | **6.8** | 5.6 | high | 6.0 | 0.0 | 9.62 | 8.63 | 8.9 | 5.94 | 7.81 |
| aaron | you-sexy-thing | 223 | **6.5** | 5.6 | high | 8.0 | 0.0 | 7.71 | 7.96 | 9.56 | 6.36 | 3.53 |
| aaron | you-sexy-thing | 222 | **6.5** | 5.6 | high | 8.0 | 0.0 | 7.56 | 7.79 | 9.77 | 7.58 | 2.84 |
| aaron | do-wah-diddy-diddy | 201 | **9.2** | 9.7 | high | 10.0 | 10.0 | 7.95 | 8.83 | 8.56 | 10.0 | 9.58 |
| aaron | do-wah-diddy-diddy | 201 | **9.1** | 9.5 | high | 10.0 | 10.0 | 7.95 | 8.87 | 8.33 | 8.7 | 9.26 |
| aaron | funky-cold-medina | 119 | **6.4** | 5.0 | high | 6.0 | 0.0 | 9.2 | 8.92 | 9.86 | 3.45 | 5.84 |
| aaron | let-s-stay-together | 186 | **7.9** | 7.0 | high | 10.0 | 0.0 | 9.98 | 9.39 | 9.64 | 8.24 | 4.97 |
| aaron | living-on-a-prayer | 209 | **6.9** | 5.6 | high | 6.0 | 0.0 | 10.0 | 9.52 | 9.32 | 7.82 | 5.2 |
| aaron | oh-what-a-night | 186 | **7.9** | 7.3 | high | 8.0 | 0.86 | 10.0 | 9.59 | 8.55 | 10.0 | 8.94 |
| aaron | you-sexy-thing | 209 | **6.8** | 5.4 | high | 8.04 | 0.0 | 10.0 | 8.37 | 9.69 | 5.0 | 2.73 |
| aaron | get-up-i-feel-like-being-a-sex-machine | 285 | **6.5** | 6.7 | high | 8.0 | 5.16 | 4.15 | 8.65 | 8.12 | 2.36 | 7.53 |
| aaron | the-letter | 173 | **7.3** | 6.1 | high | 8.0 | 0.0 | 10.0 | 9.55 | 9.47 | 5.76 | 5.63 |
| aaron | the-letter | 191 | **5.9** | 5.4 | high | 6.0 | 0.0 | 5.97 | 9.92 | 8.17 | 2.94 | 7.44 |
| aaron | danger-zone | 166 | **7.2** | 6.5 | high | 8.0 | 0.0 | 8.09 | 8.98 | 9.45 | 9.58 | 5.71 |
| aaron | kryptonite | 154 | **8.8** | 8.2 | high | 6.0 | 10.0 | 10.0 | 9.85 | 9.67 | 10.0 | 7.05 |
| aaron | kryptonite | 172 | **7.2** | 7.8 | high | 8.0 | 10.0 | 3.01 | 9.86 | 9.65 | 1.52 | 7.51 |
| aaron | the-heat-is-on | 194 | **6.8** | 5.6 | high | 8.0 | 0.0 | 10.0 | 8.42 | 8.41 | 3.67 | 5.36 |
| aaron | the-letter | 173 | **5.9** | 5.8 | high | 8.0 | 0.0 | 3.4 | 9.13 | 9.81 | 2.06 | 7.88 |
| aaron | danger-zone | 177 | **7.5** | 6.9 | high | 10.0 | 0.0 | 9.11 | 9.3 | 8.76 | 10.0 | 2.47 |
| aaron | danger-zone | 174 | **7.6** | 6.6 | high | 10.0 | 0.0 | 10.0 | 9.03 | 9.05 | 7.52 | 3.63 |
| aaron | kryptonite | 186 | **7.5** | 7.8 | high | 9.0 | 6.82 | 4.84 | 9.11 | 9.7 | 2.97 | 8.89 |
| aaron | let-s-stay-together | 185 | **7.2** | 6.0 | high | 6.0 | 0.0 | 10.0 | 8.94 | 9.71 | 9.85 | 6.51 |
| aaron | the-heat-is-on | 239 | **6.5** | 6.9 | high | 10.0 | 2.64 | 2.71 | 8.44 | 9.6 | 2.85 | 7.41 |
| aaron | the-heat-is-on | 199 | **6.9** | 5.7 | high | 10.0 | 0.0 | 10.0 | 8.54 | 8.82 | 3.91 | 1.32 |
| aaron | the-heat-is-on | 208 | **6.5** | 5.1 | high | 8.0 | 0.0 | 10.0 | 8.3 | 8.84 | 3.85 | 2.06 |
| aaron | the-letter-joe-cocker | 172 | **7.3** | 6.2 | high | 8.0 | 0.0 | 10.0 | 9.48 | 8.83 | 6.36 | 6.03 |
| aaron | wild-thing | 155 | **6.8** | 5.8 | high | 8.08 | 0.0 | 9.13 | 8.17 | 9.0 | 3.18 | 7.51 |
| aaron | you-can-leave-your-hat-on | 154 | **6.6** | 6.0 | high | 10.0 | 0.0 | 8.57 | 7.44 | 7.01 | 1.58 | 7.55 |
| aaron | danger-zone | 166 | **7.2** | 6.5 | high | 8.0 | 0.0 | 8.09 | 8.98 | 9.45 | 9.58 | 5.71 |
| aaron | bye-bye-love | 138 | **6.6** | 5.1 | high | 7.0 | 0.0 | 10.0 | 7.81 | 9.08 | 6.18 | 3.05 |
| aaron | come-out-and-play | 187 | **6.7** | 6.7 | high | 8.0 | 3.55 | 4.7 | 8.82 | 9.48 | 4.55 | 7.27 |
| aaron | goodbye-s-been-good-to-you | 190 | **7.5** | 6.5 | high | 8.0 | 0.0 | 10.0 | 9.76 | 9.23 | 10.0 | 4.41 |
| aaron | bye-bye-love | 123 | **7.3** | 6.1 | high | 10.0 | 0.0 | 10.0 | 8.17 | 9.66 | 6.7 | 2.15 |
| aaron | bye-bye-love | 120 | **7.6** | 6.5 | high | 10.0 | 0.0 | 10.0 | 9.47 | 9.49 | 6.52 | 3.1 |
| aaron | the-heat-is-on | 202 | **6.3** | 5.7 | high | 8.0 | 0.0 | 7.12 | 8.25 | 8.28 | 3.82 | 6.31 |
| aaron | carved-from-stone | 182 | **6.2** | 5.8 | high | 9.0 | 0.0 | 4.96 | 8.36 | 9.98 | 1.76 | 6.51 |
| aaron | my-babe | 135 | **8.0** | 7.2 | high | 10.0 | 0.0 | 10.0 | 9.81 | 9.3 | 10.0 | 4.11 |
| aaron | my-babe | 146 | **7.1** | 5.9 | high | 8.0 | 0.0 | 10.0 | 8.38 | 9.78 | 7.85 | 3.46 |
| aaron | my-babe | 131 | **7.5** | 6.4 | high | 8.0 | 0.0 | 10.0 | 9.04 | 9.18 | 10.0 | 4.66 |
| aaron | my-babe | 134 | **7.0** | 5.6 | high | 6.0 | 0.0 | 10.0 | 7.94 | 9.94 | 10.0 | 5.03 |
| aaron | my-babe | 123 | **7.2** | 5.9 | high | 6.0 | 0.0 | 10.0 | 8.34 | 9.99 | 10.0 | 6.63 |
| aaron | my-babe | 166 | **7.4** | 7.3 | high | 10.0 | 4.3 | 6.32 | 9.06 | 9.49 | 2.79 | 6.86 |
| aaron | open-road | 154 | **8.4** | 9.1 | high | 10.0 | 10.0 | 4.8 | 8.32 | 9.97 | 8.15 | 7.34 |
| aaron | that-s-my-flavor | 161 | **6.9** | 6.8 | high | 10.0 | 0.0 | 5.1 | 9.51 | 9.76 | 3.91 | 7.51 |
| aaron | the-heat-is-on | 200 | **7.1** | 5.7 | high | 9.0 | 0.0 | 10.0 | 7.49 | 9.78 | 4.52 | 4.73 |
| aaron | the-heat-is-on | 248 | **5.9** | 5.5 | high | 8.0 | 0.0 | 6.33 | 7.88 | 7.25 | 2.39 | 7.05 |
| aaron | you-sexy-thing | 198 | **7.0** | 5.9 | high | 10.0 | 0.0 | 10.0 | 7.92 | 8.84 | 6.3 | 1.11 |
| aaron | the-heat-is-on | 217 | **5.9** | 5.8 | high | 8.0 | 0.0 | 4.79 | 9.18 | 8.19 | 2.48 | 7.2 |
| aaron | living-on-a-prayer | 208 | **7.0** | 7.1 | high | 10.0 | 3.09 | 4.48 | 8.05 | 9.96 | 4.06 | 7.39 |
| aaron | one | 155 | **8.4** | 7.9 | high | 6.0 | 9.28 | 10.0 | 10.0 | 8.35 | 10.0 | 5.45 |
| aaron | working-class-man | 161 | **7.0** | 7.4 | high | 8.0 | 6.99 | 4.1 | 10.0 | 8.68 | 2.94 | 7.39 |
| aaron | my-babe | 132 | **7.7** | 6.8 | high | 10.0 | 0.0 | 10.0 | 8.29 | 9.37 | 10.0 | 3.39 |
| aaron | wild-thing | 144 | **6.7** | 5.9 | high | 9.0 | 0.0 | 9.36 | 8.35 | 7.25 | 2.27 | 7.05 |
| aaron | my-babe | 178 | **8.2** | 8.7 | high | 10.0 | 10.0 | 6.53 | 8.39 | 7.93 | 3.67 | 8.82 |
| aaron | one | 178 | **8.9** | 9.0 | high | 9.0 | 10.0 | 8.33 | 9.85 | 9.21 | 8.09 | 6.79 |
| aaron | rockin-robin | 175 | **7.9** | 8.0 | high | 10.0 | 7.79 | 6.74 | 9.72 | 8.79 | 3.09 | 5.41 |
| aaron | one | 177 | **8.1** | 7.5 | high | 10.0 | 0.0 | 9.26 | 9.49 | 9.76 | 7.18 | 10.0 |
| aaron | pressure-down | 197 | **7.9** | 7.0 | high | 10.0 | 0.0 | 10.0 | 10.0 | 9.61 | 7.21 | 5.63 |
| aaron | pressure-down | 197 | **7.8** | 7.3 | high | 10.0 | 0.0 | 10.0 | 9.25 | 7.72 | 7.79 | 7.9 |
| aaron | pressure-down | 201 | **8.8** | 8.6 | high | 10.0 | 5.9 | 10.0 | 9.9 | 8.47 | 6.94 | 8.82 |
| aaron | pressure-down | 196 | **8.4** | 7.9 | high | 8.0 | 7.74 | 10.0 | 9.18 | 8.46 | 7.03 | 6.88 |
| aaron | pressure-down | 176 | **8.1** | 7.4 | high | 10.0 | 0.23 | 10.0 | 9.95 | 9.07 | 7.39 | 8.08 |
| aaron | pressure-down | 187 | **7.2** | 7.6 | high | 8.0 | 7.28 | 4.91 | 9.08 | 8.05 | 4.45 | 8.15 |
| aaron | my-babe | 181 | **8.1** | 8.5 | high | 10.0 | 10.0 | 6.43 | 8.38 | 8.03 | 3.24 | 8.22 |
| aaron | my-babe | 121 | **8.1** | 7.3 | high | 10.0 | 0.0 | 10.0 | 7.87 | 9.73 | 10.0 | 8.11 |
| aaron | my-babe | 160 | **6.7** | 6.4 | high | 8.0 | 4.81 | 5.35 | 7.74 | 9.95 | 1.79 | 7.71 |
| aaron | play-that-funky-music | 192 | **7.3** | 6.2 | high | 6.0 | 0.0 | 9.93 | 8.95 | 9.44 | 8.15 | 9.65 |
| aaron | play-that-funky-music | 221 | **7.8** | 8.3 | high | 10.0 | 8.77 | 4.67 | 8.66 | 9.77 | 4.09 | 7.05 |
| aaron | play-that-funky-music | 221 | **7.8** | 8.3 | high | 10.0 | 8.77 | 4.67 | 8.66 | 9.77 | 4.09 | 7.05 |
| aaron | pressure-down | 226 | **7.8** | 8.4 | high | 10.0 | 9.28 | 4.64 | 8.43 | 9.42 | 5.12 | 6.05 |
| aaron | pressure-down | 207 | **7.3** | 7.6 | high | 10.0 | 5.85 | 4.92 | 8.64 | 9.42 | 3.45 | 6.54 |
| aaron | pressure-down | 226 | **7.8** | 8.4 | high | 10.0 | 9.28 | 4.64 | 8.43 | 9.42 | 5.12 | 6.05 |
| aaron | tutti-frutti | 167 | **6.9** | 6.0 | high | 6.0 | 1.55 | 10.0 | 9.22 | 7.19 | 10.0 | 3.67 |
| aaron | tutti-frutti | 168 | **7.2** | 7.4 | high | 10.0 | 3.9 | 4.88 | 8.93 | 9.66 | 3.36 | 7.85 |
| aaron | danger-zone | 140 | **6.8** | 5.5 | high | 6.0 | 0.0 | 10.0 | 8.37 | 9.13 | 10.0 | 3.67 |
| aaron | kryptonite | 154 | **9.0** | 8.6 | high | 10.0 | 8.31 | 10.0 | 9.96 | 9.77 | 10.0 | 1.9 |
| aaron | the-heat-is-on | 198 | **6.2** | 4.8 | high | 6.0 | 0.0 | 10.0 | 9.06 | 8.39 | 4.21 | 3.28 |
| aaron | you-sexy-thing | 224 | **6.0** | 4.7 | high | 6.0 | 0.0 | 10.0 | 8.91 | 7.46 | 6.15 | 0.53 |
| aaron | hammer-to-the-heart | 229 | **7.6** | 6.9 | high | 10.0 | 0.0 | 10.0 | 9.22 | 8.14 | 10.0 | 3.05 |
| aaron | reasons | 182 | **7.4** | 6.6 | high | 10.0 | 0.17 | 10.0 | 9.56 | 8.11 | 6.3 | 3.6 |
| aaron | two-strong-hearts | 227 | **7.7** | 7.0 | high | 6.0 | 5.04 | 8.9 | 8.52 | 9.61 | 10.0 | 7.35 |
| aaron | kung-fu-fighting | 207 | **7.8** | 7.6 | high | 10.0 | 0.0 | 8.05 | 10.0 | 8.78 | 9.67 | 7.28 |
| aaron | my-babe | 246 | **8.6** | 9.5 | high | 10.0 | 10.0 | 4.25 | 7.8 | 9.47 | 10.0 | 9.65 |
| aaron | pressure-down | 160 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | reasons | 196 | **7.0** | 6.0 | high | 6.0 | 0.0 | 9.84 | 9.95 | 7.87 | 7.64 | 7.55 |
| aaron | you-sexy-thing | 186 | **7.2** | 6.3 | high | 7.0 | 0.0 | 9.4 | 9.1 | 9.01 | 7.39 | 8.45 |
| aaron | believe-it-or-not | 5 | **6.3** | 7.5 | medium | 10.0 | – | 3.7 | – | 7.02 | 1.24 | – |
| aaron | kung-fu-fighting | 192 | **7.7** | 7.6 | high | 10.0 | 0.0 | 6.69 | 9.11 | 9.37 | 10.0 | 8.2 |
| aaron | reasons | 200 | **7.1** | 6.2 | high | 7.0 | 0.0 | 8.72 | 9.98 | 9.75 | 7.3 | 6.6 |
| aaron | you-sexy-thing | 199 | **6.4** | 5.9 | high | 8.0 | 0.0 | 6.4 | 8.26 | 8.81 | 6.09 | 5.86 |
| aaron | kung-fu-fighting | 188 | **7.9** | 7.0 | high | 10.0 | 0.92 | 10.0 | 9.14 | 9.48 | 9.0 | 3.4 |
| aaron | kung-fu-fighting | 187 | **8.8** | 9.4 | high | 10.0 | 10.0 | 6.11 | 9.19 | 8.91 | 9.97 | 7.05 |
| aaron | kung-fu-fighting | 197 | **8.5** | 9.0 | high | 10.0 | 6.19 | 6.21 | 9.77 | 9.6 | 8.7 | 9.54 |
| aaron | pressure-down | 188 | **7.8** | 7.0 | high | 6.96 | 3.21 | 10.0 | 9.86 | 8.76 | 6.85 | 8.31 |
| aaron | pressure-down | 164 | **7.3** | 7.5 | high | 9.0 | 5.27 | 4.59 | 8.41 | 9.39 | 5.7 | 7.88 |
| aaron | reasons | 190 | **7.1** | 8.2 | high | 10.0 | 6.59 | 3.5 | 7.95 | 6.4 | 10.0 | 4.92 |
| aaron | cold-start-warm-up-4-8 | 321 | **6.9** | 6.2 | high | 8.04 | 0.0 | 9.77 | 7.19 | 6.63 | 10.0 | 5.4 |
| aaron | danger-zone | 131 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | do-wah-diddy | 159 | **9.1** | 9.6 | high | 10.0 | 10.0 | 8.61 | 7.85 | 7.38 | 10.0 | 10.0 |
| aaron | do-wah-diddy | 168 | **8.6** | 9.4 | high | 10.0 | 10.0 | 7.82 | 7.43 | 6.32 | 10.0 | – |
| aaron | do-wah-diddy | 172 | **9.4** | 9.2 | high | 10.0 | 10.0 | 10.0 | 8.89 | 9.26 | 10.0 | 5.8 |
| aaron | kung-fu-fighting | 171 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | let-s-stay-together | 174 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | my-babe | 120 | **7.0** | 5.9 | high | 7.0 | 0.0 | 10.0 | 8.25 | 8.74 | 9.3 | 4.85 |
| aaron | my-babe | 103 | **7.4** | 6.3 | high | 6.0 | 0.0 | 9.41 | 8.27 | 10.0 | 10.0 | 10.0 |
| aaron | oh-what-a-night | 178 | **8.5** | 8.3 | high | 10.0 | 4.18 | 10.0 | 9.1 | 7.53 | 8.36 | 8.61 |
| aaron | oh-what-a-night | 165 | **8.0** | 7.4 | high | 6.0 | 7.91 | 10.0 | 7.86 | 8.81 | 7.03 | 9.58 |
| aaron | pressure-down | 178 | **7.6** | 6.7 | high | 6.0 | 4.64 | 10.0 | 9.54 | 9.3 | 8.03 | 5.8 |
| aaron | reasons | 177 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | you-sexy-thing | 194 | **withheld** | – | – | – | – | – | – | – | – | – |
| aaron | kung-fu-fighting | 173 | **8.1** | 8.1 | high | 10.0 | 3.32 | 6.83 | 9.02 | 9.9 | 9.27 | 7.6 |
| aaron | pretty-woman | 132 | **7.6** | 6.8 | high | 9.0 | 0.0 | 10.0 | 8.56 | 8.54 | 8.79 | 6.72 |
| aaron | holy-grail | 163 | **6.4** | 6.1 | high | 6.0 | 0.0 | 5.26 | 9.0 | 9.21 | 10.0 | 7.32 |
| aaron | kung-fu-fighting | 185 | **7.8** | 8.0 | high | 6.0 | 10.0 | 6.14 | 10.0 | 8.78 | 10.0 | 5.29 |
| aaron | kung-fu-fighting | 201 | **7.8** | 9.1 | high | 10.0 | 10.0 | 3.61 | 7.52 | 6.81 | 8.06 | 9.14 |
| aaron | bust-a-move | 197 | **5.9** | 6.4 | high | 10.0 | 0.0 | 2.15 | 8.03 | 8.08 | 3.15 | 7.85 |
| aaron | come-and-play | 195 | **7.5** | 7.7 | high | 6.0 | 10.0 | 5.62 | 8.7 | 9.24 | 10.0 | 4.41 |
| aaron | kung-fu-fighting | 193 | **8.6** | 8.9 | high | 8.0 | 10.0 | 6.44 | 9.48 | 10.0 | 10.0 | 7.72 |
| aaron | never-gonna-give-you-up | 231 | **7.8** | 7.0 | high | 6.0 | 3.04 | 9.7 | 9.36 | 9.23 | 10.0 | 8.82 |
| aaron | to-be-with-you | 187 | **7.6** | 6.7 | high | 10.0 | 0.0 | 9.71 | 9.13 | 9.3 | 4.39 | 6.84 |
| aaron | baby-got-back | 172 | **5.5** | 6.1 | high | 8.0 | 2.12 | 2.14 | 9.23 | 6.72 | 2.3 | 6.68 |
| aaron | pretty-woman | 141 | **7.6** | 6.7 | high | 10.0 | 0.0 | 10.0 | 8.48 | 8.86 | 8.3 | 3.9 |
| aaron | reasons | 194 | **7.2** | 7.2 | high | 10.0 | 0.63 | 5.6 | 9.2 | 9.04 | 6.58 | 7.9 |
| aaron | reasons | 192 | **7.2** | 7.1 | high | 10.0 | 0.0 | 6.43 | 9.32 | 8.82 | 9.06 | 5.06 |
| aaron | cry-in-shame | 264 | **7.7** | 7.7 | high | 10.0 | 0.0 | 5.83 | 9.05 | 9.72 | 10.0 | 9.45 |
| aaron | kung-fu-fighting | 193 | **8.1** | 9.1 | high | 8.0 | 10.0 | 4.92 | 9.07 | 7.45 | 10.0 | 9.54 |
| aaron | lose-control | 207 | **7.2** | 7.3 | high | 8.0 | 4.87 | 5.83 | 9.46 | 8.86 | 10.0 | 3.05 |
| aaron | to-be-with-you | 159 | **6.2** | 5.4 | high | 6.0 | 0.0 | 7.46 | 9.2 | 8.58 | 6.3 | 5.4 |
| aaron | cry-in-shame | 291 | **7.8** | 8.5 | high | 10.0 | 7.51 | 4.43 | 8.29 | 9.23 | 7.18 | 7.57 |
| aaron | let-s-go | 129 | **7.4** | 6.9 | high | 10.0 | 0.0 | 10.0 | 8.54 | 6.66 | 5.24 | 8.75 |
| aaron | fireball | 230 | **6.9** | 6.8 | high | 10.0 | 0.0 | 5.58 | 9.41 | 9.06 | 2.7 | 9.44 |
| aaron | you-give-love-a-bad-name | 234 | **8.8** | 9.4 | high | 10.0 | 10.0 | 5.78 | 8.9 | 9.98 | 10.0 | 7.05 |
| aaron | get-back | 185 | **6.1** | 5.9 | high | 8.0 | 0.0 | 3.97 | 8.79 | 9.92 | 2.85 | 8.24 |
| aaron | goodbyes-been-good-to-you | 242 | **7.6** | 7.1 | high | 10.0 | 4.01 | 8.58 | 9.99 | 8.57 | 2.64 | 4.8 |
| aaron | let-s-go | 148 | **7.2** | 7.8 | high | 10.0 | 8.94 | 3.72 | 7.77 | 8.88 | 2.39 | 6.23 |
| aaron | this-is-how-we-do-it | 388 | **7.9** | 7.2 | high | 8.0 | 3.27 | 9.68 | 10.0 | 8.8 | 5.27 | 8.82 |
| aaron | all-that-she-wants | 218 | **6.7** | 5.6 | high | 6.0 | 0.4 | 9.92 | 9.68 | 8.12 | 4.39 | 7.28 |
| aaron | fireball | 257 | **7.7** | 7.3 | high | 10.0 | 0.0 | 8.02 | 9.47 | 9.58 | 8.76 | 6.84 |
| aaron | i-feel-good | 182 | **7.2** | 6.3 | high | 9.0 | 0.0 | 9.8 | 9.36 | 8.43 | 5.7 | 4.71 |
| aaron | reasons | 321 | **6.8** | 5.6 | high | 8.68 | 0.0 | 9.6 | 9.1 | 8.86 | 2.06 | 4.89 |
| aaron | things-that-make-you-go-hmm | 332 | **6.7** | 6.3 | high | 6.96 | 0.0 | 7.2 | 9.52 | 8.3 | 10.0 | 5.29 |
| aaron | this-is-how-we-do-it | 348 | **7.3** | 6.4 | high | 9.0 | 0.11 | 9.14 | 9.74 | 9.27 | 4.12 | 6.81 |
| aaron | this-is-how-we-do-it | 300 | **6.5** | 5.7 | high | 9.0 | 0.0 | 7.25 | 8.82 | 9.93 | 2.21 | 4.53 |
| aaron | fireball | 253 | **6.4** | 5.8 | high | 8.08 | 0.0 | 6.52 | 9.19 | 9.78 | 2.73 | 6.49 |
| aaron | fireball | 453 | **7.9** | 7.1 | high | 10.0 | 1.66 | 9.82 | 10.0 | 9.19 | 1.18 | 9.42 |
| aaron | groove-is-in-the-heart | 178 | **7.1** | 6.7 | high | 10.0 | 0.0 | 7.68 | 8.6 | 7.93 | 3.09 | 9.59 |
| aaron | kung-fu-fighting | 227 | **9.3** | 9.1 | high | 10.0 | 10.0 | 9.88 | 8.95 | 9.33 | 8.58 | 6.4 |
| aaron | playing-to-win | 138 | **7.3** | 6.2 | high | 8.0 | 0.0 | 10.0 | 9.72 | 8.65 | 10.0 | 2.24 |
| aaron | playing-to-win | 324 | **6.7** | 5.7 | high | 7.0 | 0.0 | 9.6 | 10.0 | 7.83 | 5.24 | 5.19 |
| aaron | to-be-with-you | 192 | **8.1** | 7.3 | high | 10.0 | 0.0 | 9.7 | 9.12 | 9.85 | 10.0 | 5.91 |
| aaron | a-bar-song-tipsy | 199 | **6.3** | 5.5 | high | 6.0 | 2.06 | 7.56 | 9.19 | 9.01 | 5.24 | 3.88 |
| aaron | fireball | 213 | **7.4** | 6.7 | high | 10.0 | 0.0 | 9.58 | 9.86 | 7.74 | 2.55 | 7.95 |
| aaron | goodbyes-been-good-to-you | 237 | **7.6** | 6.7 | high | 10.0 | 0.0 | 9.91 | 8.66 | 8.52 | 5.94 | 6.54 |
| aaron | kung-fu-fighting | 238 | **9.0** | 8.8 | high | 9.0 | 10.0 | 9.48 | 9.42 | 9.6 | 7.67 | 6.54 |
| aaron | you-give-love-a-bad-name | 221 | **6.7** | 5.9 | high | 8.0 | 0.0 | 9.73 | 9.24 | 6.31 | 2.91 | 7.64 |
| aaron-and-rilda | burning-down-the-house | 198 | **7.2** | 7.1 | high | 9.0 | 0.0 | 6.05 | 9.96 | 9.26 | 8.55 | 7.05 |
| aaron-g | 1973 | 156 | **8.9** | 8.7 | high | 8.0 | 10.0 | 10.0 | 9.75 | 7.97 | 5.82 | 10.0 |
| aaron-g | if-you-could-read-my-mind | 201 | **8.8** | 8.3 | high | 6.0 | 10.0 | 10.0 | 10.0 | 9.75 | 7.67 | 9.84 |
| aaron-g | vienna | 165 | **7.3** | 6.1 | high | 6.0 | 0.0 | 10.0 | 10.0 | 9.81 | 8.97 | 7.05 |
| chris | feeling-good | 204 | **5.8** | 5.3 | high | 6.0 | 0.0 | 4.67 | 10.0 | 9.98 | 4.55 | 5.29 |
| leo | chasin-that-neon-rainbow | 204 | **6.9** | 6.6 | high | 8.0 | 2.58 | 6.03 | 8.59 | 9.33 | 7.7 | 5.4 |
| leo | livin-on-a-prayer | 191 | **7.9** | 7.8 | high | 10.0 | 2.23 | 6.72 | 9.41 | 9.86 | 7.18 | 9.08 |
| leo | sunshine-smile | 176 | **8.2** | 7.6 | high | 10.0 | 1.03 | 10.0 | 10.0 | 8.9 | 9.88 | 5.8 |
| leo | sunshine-smile | 183 | **8.2** | 7.4 | high | 10.0 | 2.58 | 10.0 | 10.0 | 9.65 | 8.52 | 3.42 |
| leo | good-riddance-time-of-your-life | 117 | **8.3** | 9.2 | high | 10.0 | 10.0 | 5.87 | 9.79 | 7.2 | 3.94 | 10.0 |
| rilda | blue-bayou | 225 | **6.8** | 6.7 | high | 10.0 | 0.0 | 6.06 | 10.0 | 8.47 | 4.45 | 5.8 |
| rilda | on-the-radio | 226 | **7.9** | 7.9 | high | 10.0 | 0.0 | 7.1 | 10.0 | 8.66 | 10.0 | 9.54 |
| rilda | flowers | 182 | **withheld** | – | – | – | – | – | – | – | – | – |
| rilda | moonlight-serenade | 181 | **8.4** | 7.9 | high | 10.0 | 0.0 | 10.0 | 9.84 | 8.81 | 10.0 | 9.51 |
| rilda | moonlight-serenade | 183 | **7.4** | 7.3 | high | 10.0 | 0.0 | 6.89 | 10.0 | 8.76 | 5.85 | 8.99 |
| rilda | sexy-eyes | 161 | **6.2** | 6.0 | high | 8.0 | 0.0 | 4.55 | 9.88 | 9.46 | 2.33 | 7.8 |
| rilda | sway-with-my-heart | 182 | **7.2** | 6.2 | high | 7.0 | 0.0 | 10.0 | 9.9 | 8.46 | 7.73 | 6.75 |
| rilda | moondance | 314 | **6.8** | 6.4 | high | 8.0 | 0.0 | 6.33 | 9.43 | 9.88 | 6.33 | 7.39 |
| rilda | moonlight-serenade | 196 | **7.5** | 7.3 | high | 10.0 | 0.0 | 7.14 | 10.0 | 8.55 | 5.12 | 10.0 |
| rilda | sexy-eyes | 161 | **withheld** | – | – | – | – | – | – | – | – | – |
| rilda | let-s-stay-together | 199 | **7.5** | 6.4 | high | 8.0 | 0.0 | 10.0 | 9.82 | 9.87 | 8.85 | 4.3 |
| rilda | this-masquerade | 181 | **8.0** | 7.3 | high | 8.0 | 0.0 | 10.0 | 10.0 | 8.79 | 10.0 | 9.81 |
| rilda | she-s-not-there | 143 | **7.3** | 7.3 | high | 8.0 | 0.0 | 5.9 | 10.0 | 9.23 | 10.0 | 10.0 |
| rilda | make-it-with-you | 132 | **7.7** | 7.1 | high | 9.0 | 0.0 | 9.01 | 10.0 | 8.35 | 6.58 | 9.54 |
| rilda | make-it-with-you | 132 | **7.7** | 7.1 | high | 9.0 | 0.0 | 9.01 | 10.0 | 8.35 | 6.58 | 9.54 |
| rilda | hot-stuff | 235 | **6.3** | 5.9 | high | 8.0 | 0.0 | 5.63 | 8.93 | 9.0 | 4.21 | 6.91 |
| rilda | at-last | 186 | **7.1** | 7.5 | high | 6.0 | 6.3 | 4.73 | 10.0 | 8.47 | 8.03 | 8.92 |
| rilda | black-velvet | 264 | **6.9** | 6.7 | high | 8.6 | 0.0 | 5.62 | 10.0 | 9.63 | 6.33 | 7.72 |
| rilda | dreams | 260 | **7.6** | 7.6 | high | 10.0 | 2.98 | 6.94 | 10.0 | 8.13 | 4.39 | 8.48 |
| rilda | you-sexy-thing | 204 | **7.1** | 6.7 | high | 8.0 | 0.0 | 7.48 | 9.69 | 9.07 | 10.0 | 5.54 |
| rilda | bow-river | 205 | **7.6** | 6.9 | high | 10.0 | 0.0 | 10.0 | 9.8 | 7.86 | 5.79 | 6.23 |
| rilda | bow-river | 206 | **7.1** | 6.2 | high | 8.0 | -0.0 | 10.0 | 9.74 | 7.95 | 5.85 | 5.93 |
| rilda | bring-me-some-water | 192 | **7.9** | 6.9 | high | 10.0 | 0.0 | 10.0 | 9.71 | 9.74 | 7.15 | 5.04 |
| rilda | ex-s-oh-s | 204 | **7.9** | 7.3 | high | 10.0 | 0.0 | 10.0 | 9.98 | 8.07 | 10.0 | 4.41 |
| rilda | who-s-that-girl | 215 | **8.3** | 7.8 | high | 10.0 | 0.0 | 10.0 | 10.0 | 8.65 | 10.0 | 8.82 |
| rilda | crazy | 125 | **7.8** | 7.0 | high | 8.0 | 0.0 | 10.0 | 9.94 | 9.09 | 10.0 | 7.51 |
| rilda | love-will-keep-us-together | 216 | **7.5** | 7.3 | high | 10.0 | 0.0 | 7.29 | 10.0 | 8.77 | 6.85 | 8.1 |
| rilda | at-last | 114 | **8.3** | 7.8 | high | 10.0 | 0.0 | 10.0 | 9.84 | 8.42 | 10.0 | 8.66 |
| rilda | mustang-sally | 185 | **7.0** | 5.6 | high | 6.0 | 0.0 | 10.0 | 9.88 | 9.59 | 10.0 | 2.5 |
| rilda | back-to-black | 229 | **6.8** | 7.3 | high | 10.0 | 0.0 | 4.8 | 10.0 | 7.29 | 9.79 | 4.9 |
| rilda | bow-river | 236 | **6.7** | 6.9 | high | 10.0 | 0.06 | 4.18 | 9.94 | 9.05 | 4.7 | 6.74 |
| rilda | flowers | 159 | **6.0** | 7.0 | high | 10.0 | 0.92 | 2.72 | 10.0 | 5.75 | 4.48 | 6.46 |
| rilda | smile | 104 | **8.5** | 7.9 | high | 10.0 | 0.0 | 10.0 | 9.88 | 9.24 | 9.73 | 10.0 |
| rilda | sexy-eyes | 152 | **7.0** | 6.8 | high | 9.0 | 4.36 | 5.92 | 9.77 | 9.38 | 0.52 | 6.81 |
| rilda | i-love-to-love | 147 | **8.0** | 7.9 | high | 10.0 | 0.0 | 7.71 | 9.98 | 8.86 | 8.91 | 10.0 |
| rilda | sexy-eyes | 206 | **6.0** | 6.0 | high | 8.0 | 0.0 | 4.46 | 9.88 | 7.66 | 1.73 | 8.82 |
| rilda | bow-river | 247 | **6.2** | 6.0 | high | 6.0 | 1.83 | 4.6 | 10.0 | 9.6 | 7.42 | 4.48 |
| rilda | to-sir-with-love | 165 | **7.3** | 7.5 | high | 10.0 | 0.17 | 4.63 | 10.0 | 9.75 | 10.0 | 6.26 |
| rilda | tainted-love | 227 | **6.4** | 6.2 | high | 8.0 | 0.0 | 4.53 | 9.85 | 9.58 | 8.48 | 3.53 |
| rilda | ex-s-oh-s | 266 | **8.7** | 8.6 | high | 8.0 | 10.0 | 8.18 | 10.0 | 9.91 | 4.64 | 10.0 |
| rilda | give-me-one-reason | 226 | **7.3** | 6.5 | high | 9.0 | 0.0 | 9.64 | 9.68 | 7.8 | 3.0 | 8.82 |
| rilda | who-s-that-girl | 268 | **8.3** | 7.8 | high | 10.0 | 0.0 | 8.86 | 9.72 | 9.65 | 10.0 | 9.26 |

## Professional references (calibration sanity check)

Overall: min 7.1 · max 9.8 · mean 8.45 — pros should sit near the top.

| reference | v5 | cf | inton | pitch | voice | vib | dyn | phrase | breath |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| andy-gibb-i-just-want-to-be-your-everything | **withheld** | – | – | – | – | – | – | – | – |
| john-farnham-pressure-down | **7.9** | 8.9 | 10.0 | 10.0 | 4.17 | 9.99 | 7.84 | 1.76 | 10.0 |
| frankie-valli-oh-what-a-night | **withheld** | – | – | – | – | – | – | – | – |
| carl-douglas-kung-fu-fighting-isolated-vocal | **8.7** | 9.5 | 10.0 | 10.0 | 6.12 | 8.7 | 8.11 | 9.21 | 9.14 |
| hot-chocolate-you-sexy-thing | **withheld** | – | – | – | – | – | – | – | – |
| little-walter-my-babe | **9.2** | 9.0 | 10.0 | 6.13 | 9.97 | 9.84 | 8.8 | 10.0 | 8.57 |
| manfred-mann-do-wah-diddy-diddy | **9.5** | 10.0 | 10.0 | 10.0 | 9.14 | 10.0 | 7.42 | 10.0 | 10.0 |
| suno-ai-sunshine-smile | **withheld** | – | – | – | – | – | – | – | – |
| alex-live-it-up | **7.1** | 7.4 | 8.0 | 1.95 | 3.7 | 9.79 | 9.89 | 8.24 | 10.0 |
| athea-fireflies | **7.8** | 9.6 | 10.0 | 10.0 | 2.67 | 9.08 | 5.38 | 8.48 | 10.0 |
| carpenters-this-masquerade | **9.8** | 9.9 | 10.0 | 9.63 | 10.0 | 10.0 | 8.81 | 10.0 | 10.0 |
| glenn-frey-the-heat-is-on | **7.7** | 7.7 | 10.0 | 2.12 | 6.28 | 9.9 | 9.57 | 5.09 | 10.0 |
| james-blunt-1973 | **8.7** | 9.6 | 10.0 | 10.0 | 6.0 | 10.0 | 8.02 | 7.15 | 10.0 |
| joe-cocker-the-letter | **8.4** | 9.1 | 10.0 | 10.0 | 6.14 | 9.85 | 7.97 | 3.48 | 9.79 |
| joe-cocker-you-can-leave-your-hat-on | **7.5** | 7.1 | 10.0 | 0.0 | 7.59 | 10.0 | 9.76 | 3.06 | 10.0 |
| kenny-loggins-danger-zone-official-audio-top-gun | **8.5** | 9.2 | 10.0 | 10.0 | 5.27 | 9.46 | 9.23 | 5.33 | 9.68 |
| kryptonite-3-doors-down | **9.0** | 9.2 | 10.0 | 6.59 | 9.8 | 9.41 | 7.01 | 10.0 | 10.0 |
| michael-buble-feeling-good | **8.3** | 8.0 | 10.0 | 0.0 | 10.0 | 9.94 | 7.54 | 10.0 | 10.0 |
| tina-turner-lets-stay-together | **8.6** | 8.9 | 8.0 | 10.0 | 7.19 | 10.0 | 8.88 | 7.09 | 10.0 |
