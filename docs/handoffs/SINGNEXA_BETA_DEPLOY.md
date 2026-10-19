# Singnexa beta — run it for invited test users

**For:** Howard (the Tailscale box) · **Owner:** Aaron · **Written:** 19 Oct 2026

Singnexa is the public name of the analysis system (memory 042). This is the
**beta web app**. It is separate from the private VOX Suite deck and does this:

- **Invite-only sign-in.** Aaron or an admin creates each account. The user gets
  a one-time password and must choose their own at first sign-in.
- **Upload a recording.** WAV, FLAC, AIFF, MP3, M4A, AAC, OGG and Opus are
  accepted. Lossless 24-bit and 32-bit float WAV are fine, up to **300 MB** and
  **15 min**.
- **The canonical engine only:** RoFormer separation, then
  `analyse_song.py`/`compute_technical_score`. There is no YouTube lookup and
  no Polish/Fused.
  - **If separation fails, no score is made.** The user is told why (CLAUDE.md
    rule 4).
  - **If `tools/score_preflight.py` fails on the server,** the headline score
    is withheld and everything else is still shown (rule 2/4). The check runs
    at start-up, and admins can re-run it from `/admin`.
- **Results are kept.** Each user has a "My results" page and a permanent
  results page per take, using the same renderer as the deck. It leads with the
  higher of overall and capture-fair (rule 5) and offers a full-results `.txt`
  download from `report_builder` (rule 6).
- **Audio is deleted** as soon as the report is built: the upload, the stems
  and the playback MP3s. Only the measured analysis JSON, the job result and
  the engine's technical report are kept. Users can delete a result themselves.
- **Privacy:** users see only their own results. Admins see everyone's.
- **Talking is cut out before scoring** (`engine/talk_cut.py`, on by default):
  - What it removes: the MC, chat before and after the song, thank-yous, and
    stage talk over an instrumental break.
  - How it decides: it transcribes the vocal stem with Whisper and checks
    which phrases hold notes (singing) and which glide (speech). Lyrics stay
    in, shouted outros included.
  - It crops rather than silences. Silencing moved a hand-trimmed archive
    score from 8.8 to 9.3; cropping at the same window reproduced it exactly.
  - Results list what was cut, with the words heard, and say where the
    singing starts in the singer's recording.
  - A singer can tick "Keep everything" to skip the cut.
  - Checked against six hand-trimmed live and home takes: its start and end
    times land within about 4 s of the hand trims. The two bigger differences
    are both talk the hand trim had kept: a "thank you", and MC chatter after a
    song.
- **Coaching notes** (`singnexa/writeup.py`): a plain-English write-up above
  the full results, written by Claude from the results text. No audio is sent.
  - It can't invent a score: any /10 or listen-back time that isn't in the
    results gets one retry, then the write-up is dropped and the page shows
    the full results alone.
  - The notes appear about a minute after the results.
  - With no `ANTHROPIC_API_KEY` the feature is simply off.

Code: `voxsuite/src/voxsuite/singnexa/`. Tests: `voxsuite/tests/test_singnexa.py`,
`voxsuite/tests/test_singnexa_writeup.py`, `engine/tests/test_talk_cut.py`.

---

## Step 1 — sync and build (same procedure as `HOWARD_REBUILD.md`)

Sync the live checkout to the explicit `main` SHA first. HOWARD_REBUILD.md
explains why: the stale-mirror trap. Then:

```bash
cd ~/.openclaw/workspace/vox-suite-deploy && \
VOX_BUILD_COMMIT=$(git rev-parse --short=12 HEAD) docker compose build singnexa && \
docker compose up -d singnexa && \
sleep 20 && curl -fsS http://127.0.0.1:8090/healthz
```

You should see `{"ok":true,"scores_published":true}`.

`scores_published: false` means the engine check failed. **Don't invite anyone
yet.** Run the check by hand and fix what it says:

```bash
docker compose exec singnexa python3 tools/score_preflight.py
```

- The `singnexa` service builds from the same Dockerfile as the suite, but
  under its own image tag, `singnexa:beta`, with its own volume,
  `singnexa-data`. Building it never retags `voxsuite:latest`, so `vox` is not
  swapped onto the new build behind your back.
- Always name the service: `docker compose build singnexa` and
  `docker compose up -d singnexa`. A bare `docker compose up -d` starts or
  recreates every service in the file.
- It listens on **127.0.0.1:8090 only**, so nothing outside the box can reach
  it until you put an HTTPS tunnel in front (Step 3).
- The existing `vox` service on 18080 is untouched.

## Step 2 — create the accounts

```bash
docker compose exec singnexa singnexa-admin create-user aaron --name "Aaron" --admin
docker compose exec singnexa singnexa-admin create-user rilda --name "Rilda"
docker compose exec singnexa singnexa-admin list-users
```

- Each `create-user` prints a **one-time password**. Send it to that person
  privately, not in a group chat.
- After that, Aaron can add test users, reset passwords and disable accounts
  from **`/admin`** in the browser.
- `singnexa-admin reset-password <name>` and `disable` / `enable` work from
  the shell too.

## Step 3 — put HTTPS in front

**Hosting is still Aaron's decision.** Do only 3a until he chooses.

### 3a. Tailnet-only trial (do this now)

Only devices on the tailnet can reach this, which is enough for Aaron to test
it himself:

```bash
tailscale serve --bg --https=8443 http://127.0.0.1:8090
tailscale serve status
```

Open `https://<machine>.<tailnet>.ts.net:8443/`. The suite stays on `:443`.

### 3b. Public for outside test users (only when Aaron says go)

**Option A — Tailscale Funnel** (free, no domain needed; URL is `https://<machine>.<tailnet>.ts.net`):

```bash
tailscale funnel --bg --https=8443 http://127.0.0.1:8090
```

Funnel only allows ports 443, 8443 and 10000. Check that your tailnet policy
allows Funnel for this node.

**Option B — Cloudflare Tunnel** (needs a domain on Cloudflare):

```bash
cloudflared tunnel --url http://127.0.0.1:8090
```

For a fixed hostname, set up a named tunnel. Raise the upload limit if the plan
caps request bodies: Cloudflare Free caps them at 100 MB, which is **too small
for big WAVs**. In that case use Funnel, or a plan or proxy that allows 300 MB.

Whichever you choose:
- Keep `SINGNEXA_COOKIE_SECURE=1`. The site must be reached over HTTPS, or
  sign-in won't stick.
- **Don't** publish port 8090 directly.

## Step 4 — smoke test (before telling anyone)

1. Open the URL. Sign in as `aaron` with the one-time password, choose a new
   password, and you land on **Analyse a recording**.
2. Upload a real song as a WAV and choose where it was recorded. The results
   page shows the current stage.
   - Separation is the slow part.
   - **Write down how long the whole job took.** Aaron needs that number to
     decide on hosting and a GPU (see Timing).
3. When it's done, check four things:
   - the headline leads with the higher number, with "10 = a typical pro";
   - the full report renders;
   - **Download full results (.txt)** works;
   - the song is listed under **My results**.
4. Check the audio is gone:
   ```bash
   docker compose exec singnexa ls /data/singnexa/work
   ```
   This should list nothing for finished jobs.
5. Sign in as a second (non-admin) test user. Their **My results** must be
   empty, and opening Aaron's result URL must say it can't be found.

## Timing (what to expect on CPU)

The dev container used for testing had 4 CPUs and no GPU:
- A **full 3 min 05 s song** (32-bit float, 48 kHz stereo WAV, 71 MB) took
  **≈ 12 min** end to end.
- A 60 s clip (24-bit) took ≈ 9 min. That run also exported spectrograms and
  shared the CPU with another job, so it was slower than usual.
- Separation alone took ≈ 2 min 50 s per minute of audio.

**Measure Howard's box with a full song (Step 4.2).** Only one job runs at a
time, and the queue holds the rest. The compose file raises the time limits
(`VOX_PITCH_TIMEOUT=5400`, `VOX_STEM_TIMEOUT=4500`) so long songs aren't cut
off on CPU.

**A GPU is the real fix for speed.** That's the Step 3 decision in the plan.

## Settings (environment, in `docker-compose.yml`)

| Variable | Default | Meaning |
|---|---|---|
| `SINGNEXA_MAX_UPLOAD_MB` | 300 | upload size cap |
| `SINGNEXA_DAILY_LIMIT` | 10 | uploads per user per 24 h (admins exempt) |
| `SINGNEXA_USER_ACTIVE` | 2 | jobs a user can have waiting/running |
| `SINGNEXA_MAX_QUEUE` | 20 | jobs waiting/running server-wide |
| `SINGNEXA_WORKERS` | 1 | analyses run at once (separation is one-at-a-time per host anyway) |
| `SINGNEXA_COOKIE_SECURE` | 1 | `0` only for plain-http local testing |
| `VOX_PITCH_TIMEOUT` / `VOX_STEM_TIMEOUT` | 5400 / 4500 s | per-job and separation time limits |
| `SINGNEXA_CUT_TALK` | 1 | `0` turns talk cutting off for everyone |
| `VOX_TALK_MODEL` | small.en | the Whisper model talk cutting uses |
| `ANTHROPIC_API_KEY` | unset | turns the coaching notes on. Put it in an untracked `.env` beside `docker-compose.yml` (git ignores `.env`), never in the compose file |
| `SINGNEXA_WRITEUP_MODEL` | claude-opus-5-5 | which Claude model writes the notes. Each request is about 2,500 tokens in and 1,500–2,500 out, so roughly 9c a song on Opus 5.5, 4–5c on Sonnet 5.5 and under 1c on Haiku 5.5 (estimates at Oct 2026 prices) |
| `SINGNEXA_WRITEUP_EFFORT` | medium | how hard it thinks (low / medium / high) |
| `SINGNEXA_WRITEUP` | 1 | `0` turns the notes off even with a key |

The coaching notes use the refusal fallback (`fallbacks: "default"`) on Opus
and Sonnet, so a request the first model declines is re-run on its
recommended fallback inside the same call.

## Back-ups

Everything that matters is in the `singnexa-data` volume, under
`/data/singnexa/`:

- `singnexa.db`: accounts, sessions and the job list
- `results/`: the kept analyses

Copy both somewhere safe weekly:

```bash
docker compose exec singnexa sh -c 'cd /data && tar czf - singnexa/singnexa.db singnexa/results' > singnexa-backup-$(date +%F).tgz
```

## Security notes

- **Passwords:** scrypt-hashed. Session cookies are random, `HttpOnly`,
  `Secure` and `SameSite=Lax`, and only their hash is stored.
- **CSRF:** every state-changing call needs an `X-Singnexa: 1` header, which
  a cross-site page can't send.
- **Sign-in limits:** 8 wrong passwords per username per 15 min.
- **Isolation:** another user's result returns "not found", never "forbidden".
- **Headers:** strict CSP (no inline scripts), `X-Frame-Options: DENY` and
  HSTS.
- **Licensing:** parselmouth (GPL) stays server-side, which is fine for a
  hosted service. Don't hand the image to third parties
  (`docs/dependency-license-audit.md`).

## Not done yet (deliberately)

- Choosing public hosting, and a domain (Aaron's decision).
- A GPU image.
- Email: no password-reset emails or "your result is ready" notices. Reset is
  done by an admin.
- Self sign-up.
- A privacy page for outside testers. Write one before inviting people outside
  the circle.
