"""Singnexa beta — the public, login-gated face of the analysis engine.

A small, separate web app (not the private VOX Suite deck) for invited test
users: sign in, upload a recording (lossless WAV/FLAC/AIFF welcome), and get the
full canonical analysis back on a results page that is kept. Uploaded audio and
stems are deleted as soon as the report is built; only the measured results are
kept. See docs/handoffs/SINGNEXA_BETA_DEPLOY.md.
"""
