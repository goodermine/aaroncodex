"""Shared plumbing for the vocal-knowledge-base tools.

One place that knows how to find documents and read their front matter, so the
manifest generator, the validator and the public build can never disagree about
what counts as a document — which is exactly how a hand-maintained manifest
drifts from the library it describes.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(ROOT, "vocal-knowledge-base")

# Meta files describe the library; they are not documents in it.
META_FILES = {"README.md", "MANIFEST.md", "TOPICS.md", "LICENSE"}

# Folders that hold real documents, in reading order. A folder not listed here
# is deliberately not part of the library's content:
#   sources/   works-cited blocks — an audit trail to search, not to read
#   archive/   superseded documents, retained rather than deleted
#   private/   one singer's measured body (see private/README.md)
# NOTE the two axes are different. sources/ and archive/ are excluded because
# they are not documents; private/ is excluded because it is private. Only the
# second is a privacy boundary, and only that one is also guarded per-file by
# `visibility:` — belt and braces where a mistake would actually matter.
CONTENT_DIRS = [
    "01-vocal-science-technique",
    "02-course-book",
    "03-technique-deep-dives",
    "04-artist-analyses",
    "05-song-guides",
    "06-voxai-system",
    "07-reference",
    "08-external-reference",
]

NON_CONTENT_DIRS = ["sources", "archive", "private"]

SECTION_TITLES = {
    "01-vocal-science-technique": "Core technique and vocal science",
    "02-course-book": "Long-form works — one course, two complete books",
    "03-technique-deep-dives": "Single-topic technique studies",
    "04-artist-analyses": "Technique breakdowns of specific vocalists",
    "05-song-guides": "Song-by-song sing-through guides",
    "06-voxai-system": "VOXAI coaching system",
    "07-reference": "Glossary, ear training, tone reference",
    "08-external-reference": "Material by other creators — attributed, not published",
}

REQUIRED_KEYS = ("title", "category", "topics", "author", "status", "visibility")
VALID_VISIBILITY = {"public", "private"}
VALID_STATUS = {"active", "superseded"}


def parse_front_matter(text: str) -> tuple[dict, str]:
    """(front matter dict, body). Values keep their raw string form; `topics`
    is additionally exposed as a list under the key `topics_list`."""
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip().strip('"')
    fm["topics_list"] = [t.strip() for t in fm.get("topics", "").strip("[]").split(",")
                         if t.strip()]
    return fm, text[m.end():]


def read_doc(path: str) -> tuple[dict, str, int]:
    """(front matter, body, word count). Word count is of the WHOLE file, which
    is what MANIFEST has always reported — keep it that way so regenerating the
    manifest is not silently a different measurement."""
    text = open(path, encoding="utf-8").read()
    fm, body = parse_front_matter(text)
    return fm, body, len(text.split())


def iter_docs(dirs=None):
    """Yield (relative path, absolute path) for every markdown document, in
    folder then filename order. Meta files are skipped."""
    for d in (dirs if dirs is not None else CONTENT_DIRS + NON_CONTENT_DIRS):
        base = os.path.join(KB, d)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirnames, filenames in sorted(os.walk(base)):
            for name in sorted(filenames):
                if not name.endswith(".md") or name in META_FILES:
                    continue
                full = os.path.join(dirpath, name)
                yield os.path.relpath(full, KB), full


def controlled_topics() -> set:
    """The topic vocabulary, read from TOPICS.md — the file is the authority."""
    text = open(os.path.join(KB, "TOPICS.md"), encoding="utf-8").read()
    body = text.split("## Vocabulary", 1)[-1]
    return set(re.findall(r"`([a-z0-9-]+)`", body))


def controlled_categories() -> set:
    """Categories actually in use, plus the ones the library reserves. Unlike
    topics this had no controlled list at all until 3 Aug 2026, which is how
    `voxai-system` got invented for a single document."""
    return {
        "vocal-science", "technique", "long-form", "artist-analysis", "song-guide",
        "reference", "coaching-system", "singer-profile", "training-programme",
        "sources", "superseded",
    }
