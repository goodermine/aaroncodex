# VOX Suite — one image, both destinations (Candi's machine + a cloud host).
#
# Packages the unified server (Analyze + Polish + Fused + /monitor + /timbertones
# + /hub) and the full analysis/scoring engine into one container, per
# docs/plans/PACKAGING_AND_DEPLOYMENT_PLAN.md (Option C, step 1).
#
# Build (default = full heavy image, incl. RoFormer separation + auto-tune):
#   docker build -t voxsuite .
# Lean image (light apps + scoring, DSP-fallback separation — smaller/faster):
#   docker build -t voxsuite:lite --build-arg WITH_SEPARATION=0 --build-arg WITH_PITCH=0 .
# Run:
#   docker run -p 8080:8080 -v vox-data:/data voxsuite
#
# GPU note: RoFormer separation is CPU-capable but slow; for a GPU host swap the
# base for an nvidia/cuda + cuDNN image and install onnxruntime-gpu. See
# docs/DEPLOYMENT.md.

FROM python:3.11-slim-bookworm

# --- what goes in the image (toggle the heavy pieces) -----------------------
ARG WITH_SEPARATION=1   # audio-separator + onnxruntime (RoFormer stems) — needed for canonical scores + Fused end-to-end
ARG WITH_PITCH=1        # pyworld WORLD vocoder for Polish auto-tune
ARG PREFETCH_MODEL=1    # bake the pinned separation model into the image (best-effort; needs network at build)
ARG VOX_BUILD_COMMIT=   # pass $(git rev-parse --short=12 HEAD) so /api/build shows the commit (no .git in the image)
ARG VOX_BUILD_BRANCH=

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    MPLBACKEND=Agg \
    HOME=/home/vox \
    # Writable caches for numba (librosa) and matplotlib — the defaults sit in
    # read-only site-packages and break for the non-root runtime user.
    NUMBA_CACHE_DIR=/tmp/numba \
    MPLCONFIGDIR=/tmp/mpl \
    XDG_CACHE_HOME=/home/vox/.cache \
    # The engine + static apps are loaded by absolute path, so pin the roots
    # explicitly rather than relying on the package's on-disk location.
    VOX_ANALYSIS_ROOT=/app/voxanalysis/vox-analysis \
    VOX_PITCHMONITOR_ROOT=/app/pitchmonitor \
    VOX_TIMBERTONES_ROOT=/app/timbertones \
    VOX_BASE=/data \
    VOX_BUILD_COMMIT=$VOX_BUILD_COMMIT \
    VOX_BUILD_BRANCH=$VOX_BUILD_BRANCH

# --- system deps ------------------------------------------------------------
# ffmpeg: audio I/O for librosa / soundfile / audio-separator / yt-dlp.
# libsndfile1: soundfile. build-essential + python3-dev + cython: build pyworld
# (auto-tune) and any sdist-only wheels. tini: correct signal handling / reaping.
# curl: container HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libsndfile1 tini curl \
        build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- python deps (cached layer: only the requirement lists change it) -------
# Copy just the requirement files first so the big install layer is reused when
# only source changes. viewer/requirements.txt pulls engine/requirements.txt via
# a relative -r, so both must be in place at their real paths.
COPY voxanalysis/vox-analysis/engine/requirements.txt  voxanalysis/vox-analysis/engine/requirements.txt
COPY voxanalysis/vox-analysis/viewer/requirements.txt  voxanalysis/vox-analysis/viewer/requirements.txt

# setuptools is pinned <70 on purpose: pyworld (the WORLD vocoder for Auto Tune)
# does `import pkg_resources` on load, and newer setuptools has REMOVED
# pkg_resources — so an unpinned `--upgrade setuptools` makes Auto Tune fail with
# "No module named 'pkg_resources'". 69.x still ships it and satisfies every
# build backend here (builds are PEP517-isolated, so this only sets the runtime).
RUN python -m pip install --upgrade pip wheel "setuptools>=68,<70" \
    && pip install -r voxanalysis/vox-analysis/viewer/requirements.txt \
    # voxpolish base dep + PDF rendering (reportlab is imported; pdfplumber per plan D7)
    && pip install pyloudnorm reportlab pdfplumber \
    # RoFormer stem separation (in-process voxpolish path). onnxruntime is the runtime backend.
    && if [ "$WITH_SEPARATION" = "1" ]; then pip install "audio-separator>=0.18" onnxruntime; fi \
    # WORLD vocoder for Polish auto-tune. Re-pin setuptools in case a dep bumped it,
    # then assert pkg_resources imports so a regression fails the build, not runtime.
    && if [ "$WITH_PITCH" = "1" ]; then pip install "pyworld>=0.3" "setuptools>=68,<70" cython \
         && python -c "import pkg_resources; print('pkg_resources OK — WORLD vocoder can load')"; fi

# --- app code + local packages ---------------------------------------------
COPY . /app

# Install our two packages EDITABLE (deps already present above). Editable is
# required, not cosmetic: neither package declares its static/ dir as package
# data, so a regular install copies only the .py files and DROPS the deck.html /
# CSS / JS assets — which 500s `/` and `/polish`. Editable points the import at
# /app/*/src (already in the image), where every asset lives. Also puts the
# `vox` console script on PATH.
RUN pip install --no-deps -e ./voxpolish -e ./voxsuite

# Guard: fail the build here (cheaply) if the deck assets don't resolve from the
# installed packages, instead of discovering it as a 500 after a 12 GB build.
RUN python -c "import voxsuite.server.app as s, voxpolish.server.app as p; \
assert (s.STATIC/'deck.html').is_file(), 'voxsuite deck.html not resolvable'; \
assert (p.STATIC/'deck.html').is_file(), 'voxpolish deck.html not resolvable'; \
print('deck assets OK:', s.STATIC/'deck.html', p.STATIC/'deck.html')"

# batch_stems.sh (engine-side separation helper) expects an audio-separator in a
# dedicated venv at $HOME/.venvs/vox-sep-uvr. Create it sharing the system
# packages (no torch duplication) so the entry point exists without a runtime
# `pip install`. Skipped when separation is off.
RUN if [ "$WITH_SEPARATION" = "1" ]; then \
        python -m venv --system-site-packages "$HOME/.venvs/vox-sep-uvr" \
        && "$HOME/.venvs/vox-sep-uvr/bin/pip" install --no-deps "audio-separator>=0.18"; \
    fi

# Best-effort: cache the pinned separation model into the image so first analysis
# doesn't wait on a download and the build is reproducible. Never fails the build
# (offline builds just download it on first run instead).
RUN if [ "$WITH_SEPARATION" = "1" ] && [ "$PREFETCH_MODEL" = "1" ]; then \
        python -c "from audio_separator.separator import Separator; s=Separator(); s.load_model(model_filename='vocals_mel_band_roformer.ckpt')" \
        || echo 'NOTE: separation model not prefetched (no network at build) — it will download on first analysis.'; \
    fi

# --- runtime ----------------------------------------------------------------
# Job state / uploads / new analyses land here — mount a volume so they persist.
RUN useradd --create-home --home-dir /home/vox --uid 10001 vox \
    && mkdir -p /data \
    && chown -R vox:vox /data /home/vox /app
VOLUME ["/data"]
USER vox

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8080/api/systems >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["vox", "--host", "0.0.0.0", "--port", "8080", "--base", "/data"]
