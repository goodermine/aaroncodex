# Topic vocabulary

Every document carries a `topics:` list in its YAML front matter, drawn only from the
controlled vocabulary below. Tags are assigned by distinctiveness — a document is tagged
with a topic when it discusses it substantially more than the corpus average, not merely
when the word appears. Most documents mention breath and resonance; only the ones actually
about them are tagged that way.

Maximum six tags per document.

## Vocabulary

**Mechanism and anatomy**
`anatomy` · `breath-support` · `posture` · `registration` · `mixed-voice` · `passaggio` · `tension`

**Acoustics and resonance**
`resonance` · `formant-tuning` · `twang` · `vowels` · `tone`

**Skills**
`belting` · `vibrato` · `agility` · `range-extension` · `pitch-accuracy` · `ear-training` · `diction` · `dynamics` · `expression`

**Health and maintenance**
`vocal-health` · `warm-up` · `cool-down` · `fatigue` · `sovt`

**Style and repertoire**
`bel-canto` · `classical` · `contemporary` · `grit` · `song-breakdown`

**Learning and delivery**
`practice-design` · `motor-learning` · `performance` · `pedagogy` · `microphone` · `recording` · `career` · `terminology`

## Front matter schema

Core keys on every document:

```yaml
title:    quoted string
category: vocal-science | long-form | technique | artist-analysis | song-guide |
          coaching-system | singer-profile | training-programme | reference |
          sources | superseded
topics:   [list, from, vocabulary, above]
words:    integer
author:   "Aaron Ellis"
status:   active | superseded | sources
```

Documents in `sources/` and `archive/` additionally carry:

```yaml
exclude_from_training: true
```

Some documents carry extra bespoke keys (`subtitle`, `structure`, `companion`,
`supersedes`, `audience`, `source_format`). These are additive — the core keys above are
present on all 96 documents, and all 96 parse as valid YAML.
