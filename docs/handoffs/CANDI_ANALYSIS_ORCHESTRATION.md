# Candi: running an analysis, waiting for it, and handling a failure

From 16 Oct 2026. This replaces any agent-side rule about how long to wait for
an analysis, or when to ask for a shorter clip.

## Why

An Aaron G analysis failed for operational reasons, not because of the
recording:

- The agent killed some separator PIDs by hand, and a RoFormer child kept
  running.
- The agent then started a second separation on top of it, so the two competed
  for the CPU.
- It gave up after an arbitrary eight minutes.
- The wrapper reported only `RuntimeError: Backend analysis failed`.

The singer was then told to send a 60–90 s clip, although nothing had shown the
clip was the problem.

## What the repository now guarantees

Implemented in `voxanalysis/vox-analysis/engine/managed_process.py`. It is used
by `scripts/candi_phase1.py`, `analyse_song.py --separate-stems` and the web
path (`pitch_track.separate_stems`).

- **One separation per host.** A second job waits in the queue. Its heartbeat
  says `waiting for the separation slot (held by pid …)`. A separator orphaned
  by a hard kill keeps the slot until it really exits, so nothing competes with
  it.
- **Process groups.** Each stage runs in its own process group. SIGTERM to
  `candi_phase1.py`, `analyse_song.py` or `batch_stems.sh` stops the whole tree,
  the separator included.
- **Timeouts owned by the repository.** All three can be overridden by
  environment variable.

  | Stage | Variable | Default |
  |---|---|---|
  | Separation | `VOX_SEPARATION_TIMEOUT` | 30 min |
  | Wait for the separation slot | `VOX_SEPARATION_LOCK_WAIT` | 30 min |
  | Whole backend run | `VOX_BACKEND_TIMEOUT` | 80 min (lock wait + separation + 20 min) |

  The agent must not impose its own shorter wall clock.
- **Progress.** `temp/metric-json/<take>-backend-status.json` is rewritten
  every 15 s. It holds the state, elapsed time, the timeout and the separator's
  own progress, for example `[separation] running 3m10s of 30m timeout, 42%
  (8/19)`.
- **Structured failures.** `prepare` no longer raises
  `Backend analysis failed`. It prints a payload and exits 2:

  ```json
  {"status": "backend_failed", "failed_stage": "separation", "kind": "timeout",
   "summary": "...", "exit_code": 1, "elapsed_s": 1800.4,
   "suggest_shorter_clip": true, "reply_guidance": "...",
   "failure_path": ".../<take>-backend-failure.json", "stderr_tail": "..."}
  ```

  The full record at `failure_path` keeps the command, stage, exit code,
  elapsed time, stdout/stderr tails and full log paths.

  `kind` takes one of these values:

  | `kind` | Meaning |
  |---|---|
  | `timeout` | The stage ran past the repository's timeout. |
  | `resource_limit` | Out of memory or disk, confirmed by the output. |
  | `busy` | The separation slot stayed held past the lock wait. |
  | `cancelled` | The job was cancelled. |
  | `killed` | A bare signal, for example a hand `kill -9`. |
  | `dependency` | The Python running the engine lacks a required module. The engine checks before separating, so this fails in seconds. |
  | `error` | Any other failure. |

## Which Python runs the engine

`candi_phase1.py` picks, in order:

1. `VOXAI_BACKEND_PYTHON`, if set.
2. `vox-analysis/engine/voxai_env/bin/python`, created by `engine/install.sh`
   with everything in `engine/requirements.txt`.
3. `python3` on `PATH`.

On 16 Oct the Aaron G retry fell through to `/usr/bin/python3`, which has no
matplotlib. To fix that, either run `bash vox-analysis/engine/install.sh` once,
or point `VOXAI_BACKEND_PYTHON` at an interpreter that has the requirements.

## Rules for the agent

1. Run `prepare` once and wait for it to exit. Read the status file if you want
   to report progress. Do not start a second `prepare` for the same take while
   one is running. If you do, it queues behind the first one rather than
   failing.
2. Never kill PIDs by hand. To stop a run, use:

   ```bash
   python3 voxanalysis/vox-analysis/engine/managed_process.py status   # who holds the slot
   python3 voxanalysis/vox-analysis/engine/managed_process.py cancel   # stop that whole tree
   ```

3. Ask the singer for a shorter clip **only** when `suggest_shorter_clip` is
   `true`, which happens only for `timeout` and `resource_limit`. For anything
   else (`error`, `busy`, `killed`, `cancelled`), tell Aaron the failed stage
   and summary, and do not blame the recording.
