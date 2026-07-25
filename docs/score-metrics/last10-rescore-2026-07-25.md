# Last-10 re-score — score metrics snapshot (2026-07-25)

Re-scored with the **current engine** (`deterministic_rubric_v3`, calibration active, 50 pro references) over the 10 most recent singer takes in `voxanalysis/archive/scratch-analyses/`. `v2` is the score baked into the archived file at capture time; `v3` is the current engine's recompute; `cf` is capture-fair (voice_quality excluded).

## Overall

- **overall v3**: min 6.6 · max 9.3 · mean 7.97 · spread 2.7
- **capture-fair v3**: min 6.6 · max 9.7 · mean 8.17 · spread 3.1
- v2→v3 change per take never exceeds 0.1 (the rubric bump barely moved the numbers).

## Per take

| take | notes | v2 | v3 | cf | conf | inton | pitch | voice | vib | dyn | phrase |
|---|--:|--:|--:|--:|:--|--:|--:|--:|--:|--:|--:|
| she-s-not-there-take-001 (rilda) | 138 | 7.2 | **7.1** | 7.7 | high | 5.71 | 5.05 | 4.84 | 9.89 | 10.0 | 10.0 |
| goodbye-s-been-good-to-you-take-001 (aaron) | 197 | 9.0 | **8.9** | 8.6 | high | 7.62 | 7.08 | 10.0 | 9.58 | 10.0 | 10.0 |
| come-out-and-play-captain-cook-tavern-take-001 (aaron) | 177 | 6.7 | **6.6** | 7.7 | high | 7.62 | 6.32 | 2.56 | 8.9 | 10.0 | 4.35 |
| chasin-that-neon-rainbow (leo) | 202 | 8.8 | **8.7** | 9.7 | high | 9.52 | 10.0 | 4.53 | 9.4 | 10.0 | 10.0 |
| danger-zone-home (aaron) | 175 | 8.3 | **8.2** | 8.1 | high | 5.71 | 8.18 | 8.98 | 8.62 | 10.0 | 10.0 |
| this-masquerade-take-001 (rilda) | 165 | 8.4 | **8.3** | 7.9 | high | 9.52 | 0.0 | 10.0 | 9.77 | 10.0 | 10.0 |
| lets-stay-together-home-take-001 (rilda) | 199 | 8.1 | **8.1** | 7.6 | high | 7.62 | 1.23 | 10.0 | 9.75 | 10.0 | 10.0 |
| feeling-good-take-001 (chris) | 221 | 7.8 | **7.7** | 8.7 | high | 7.62 | 6.97 | 3.73 | 10.0 | 10.0 | 10.0 |
| you-can-leave-your-hat-on-bramble-bay-take-001 (aaron) | 163 | 6.7 | **6.8** | 6.6 | high | 5.71 | 4.98 | 7.69 | 7.1 | 10.0 | 5.71 |
| the-letter-joe-cocker-take-001 (aaron) | 192 | 9.2 | **9.3** | 9.1 | high | 9.52 | 8.56 | 10.0 | 8.84 | 10.0 | 8.09 |

## Raw metrics per take

| take | med dev (c) | drift (c) | within25c | jitter% | shimmer% | HNR dB | vib% | phrase s |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| she-s-not-there-take-001 (rilda) | 30.0 | 52.1 | 46.4 | 1.3249 | 15.3137 | 11.1 | 43.5 | 3.63 |
| goodbye-s-been-good-to-you-take-001 (aaron) | 25.0 | 40.9 | 51.3 | 0.3702 | 3.8645 | 19.95 | 43.1 | 6.63 |
| come-out-and-play-captain-cook-tavern-take-001 (aaron) | 25.0 | 45.1 | 49.2 | 2.1566 | 17.5688 | 9.65 | 34.6 | 1.65 |
| chasin-that-neon-rainbow (leo) | 20.0 | 19.1 | 52.0 | 1.3697 | 15.1166 | 10.54 | 32.8 | 4.7 |
| danger-zone-home (aaron) | 30.0 | 34.8 | 47.4 | 0.6255 | 10.4454 | 14.25 | 38.2 | 3.94 |
| this-masquerade-take-001 (rilda) | 20.0 | 118.6 | 51.5 | 0.615 | 3.7471 | 24.14 | 49.0 | 7.01 |
| lets-stay-together-home-take-001 (rilda) | 25.0 | 73.2 | 50.3 | 0.4558 | 4.7144 | 21.01 | 50.5 | 3.81 |
| feeling-good-take-001 (chris) | 25.0 | 41.5 | 50.7 | 1.745 | 15.7648 | 10.46 | 49.5 | 4.83 |
| you-can-leave-your-hat-on-bramble-bay-take-001 (aaron) | 30.0 | 52.5 | 47.2 | 0.9725 | 11.1715 | 14.87 | 17.6 | 2.01 |
| the-letter-joe-cocker-take-001 (aaron) | 20.0 | 32.7 | 54.7 | 0.6213 | 6.3934 | 18.63 | 34.6 | 2.64 |
