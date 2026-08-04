#!/usr/bin/env python3
"""Validate the vocal knowledge base. Exit 1 means do not publish.

    python3 tools/kb_validate.py

Why this exists: the library was hand-maintained and stayed perfectly clean for
78 documents. Then it gained a collaborator, and within two days it had a
document with 8 topic tags against a limit of 6, five tags outside the
controlled vocabulary, a `category` no other document used, and a MANIFEST whose
word counts were wrong four separate times. Nothing failed. Nothing noticed.

Checks, in the order a reader would care about them:
  1. front matter present, with every required key
  2. topics inside TOPICS.md, at most six
  3. category inside the controlled list
  4. status and visibility are valid values
  5. every private document really is in a private location, and vice versa
  6. internal .md links resolve
  7. README and MANIFEST counts match reality
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kb_common import (  # noqa: E402
    CONTENT_DIRS, KB, NON_CONTENT_DIRS, REQUIRED_KEYS, VALID_STATUS,
    VALID_VISIBILITY, controlled_categories, controlled_topics, iter_docs,
    parse_front_matter, read_doc)

MAX_TOPICS = 6
PRIVATE_DIRS = ("private/", "08-external-reference/")


def main() -> int:
    problems: list[str] = []
    topics_vocab = controlled_topics()
    categories = controlled_categories()

    docs = list(iter_docs())
    if not docs:
        print("FAIL  no documents found — is this the right repo?")
        return 1

    for rel, full in docs:
        fm, body, _words = read_doc(full)
        where = rel
        folder = rel.split(os.sep)[0]

        # `sources/` and `archive/` are not documents in the reading sense — the
        # sources files are extracted works-cited blocks carrying `status:
        # sources` and no topics, by design. Holding them to the document
        # standard would produce 44 permanent failures that mean nothing, and a
        # validator people learn to ignore is worse than no validator. They are
        # still required to declare visibility, because that is the guard that
        # actually protects something.
        light = folder in ("sources", "archive")

        if not fm:
            problems.append(f"{where}: no front matter")
            continue
        for key in (("title", "visibility") if light else REQUIRED_KEYS):
            if not fm.get(key):
                problems.append(f"{where}: missing `{key}` in front matter")
        if light:
            vis = fm.get("visibility")
            if vis and vis not in VALID_VISIBILITY:
                problems.append(f"{where}: visibility `{vis}` is not public or private")
            continue

        tags = fm.get("topics_list", [])
        if len(tags) > MAX_TOPICS:
            problems.append(f"{where}: {len(tags)} topics, limit is {MAX_TOPICS}")
        for tag in tags:
            if tag not in topics_vocab:
                problems.append(f"{where}: topic `{tag}` is not in TOPICS.md")

        if fm.get("category") and fm["category"] not in categories:
            problems.append(f"{where}: category `{fm['category']}` is not a known category")
        if fm.get("status") and fm["status"] not in VALID_STATUS:
            problems.append(f"{where}: status `{fm['status']}` is not one of {sorted(VALID_STATUS)}")

        vis = fm.get("visibility")
        if vis and vis not in VALID_VISIBILITY:
            problems.append(f"{where}: visibility `{vis}` is not public or private")
        # The privacy boundary, checked from both directions. A private document
        # that drifts into a public folder is the failure that actually matters.
        in_private_dir = rel.startswith(PRIVATE_DIRS)
        if in_private_dir and vis != "private":
            problems.append(f"{where}: lives in a private folder but is marked `{vis}`")
        if vis == "private" and not in_private_dir:
            problems.append(f"{where}: marked private but sits in a published folder")

    # internal links
    for rel, full in docs:
        text = open(full, encoding="utf-8").read()
        for target in re.findall(r"\]\(([^)#\s]+\.md)[^)]*\)", text):
            if target.startswith(("http://", "https://")):
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(full), target))
            if not os.path.exists(resolved):
                problems.append(f"{rel}: broken link -> {target}")

    # counts claimed vs measured
    content = [(r, f) for r, f in docs
               if r.split(os.sep)[0] in CONTENT_DIRS and
               parse_front_matter(open(f, encoding="utf-8").read())[0].get("visibility") != "private"]
    n_docs = len(content)
    n_words = sum(read_doc(f)[2] for _r, f in content)

    for name in ("README.md", "MANIFEST.md"):
        path = os.path.join(KB, name)
        if not os.path.isfile(path):
            problems.append(f"{name}: missing")
            continue
        text = open(path, encoding="utf-8").read()
        for claimed_docs, claimed_words in re.findall(
                r"(\d+) documents? · ~?([\d,]+) words", text):
            if int(claimed_docs) != n_docs:
                problems.append(f"{name}: claims {claimed_docs} documents, actual {n_docs}")
            approx = "~" in text.split(claimed_words)[0][-3:]
            got = int(claimed_words.replace(",", ""))
            if not approx and got != n_words:
                problems.append(f"{name}: claims {claimed_words} words, actual {n_words:,}")
            elif approx and abs(got - n_words) > 2000:
                problems.append(f"{name}: claims ~{claimed_words} words, actual {n_words:,}")

    if problems:
        print(f"FAIL  {len(problems)} problem(s):")
        for p in problems:
            print(f"        - {p}")
        print("\n      Fix the front matter, or regenerate the counts:")
        print("        python3 tools/kb_manifest.py")
        return 1

    private = sum(1 for r, _f in docs if r.startswith(PRIVATE_DIRS))
    print(f"ok    {n_docs} public documents · {n_words:,} words")
    print(f"ok    {private} document(s) held private and excluded from any public build")
    print("ok    front matter complete, topics and categories controlled")
    print("ok    every internal link resolves")
    print("ok    README and MANIFEST counts match the library")
    print("\nKNOWLEDGE BASE VALID.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
