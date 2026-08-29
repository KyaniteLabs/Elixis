# The naming discipline (machine-encoded)

`elixis/discipline.py` ports the house rules that previously lived only in
prompts and experiment docs into deterministic validators the engine
applies at Phase 5 (naming).

## Kill lists

House rules (always on): em/en dashes, `journey`/`unlock`/`unleash`/
`level-up`, AI-slop tokens, single-part abbreviation names (`QK`, `CTX`).

Object profiles (opt-in via `engine.name(object_profile=...)`):

- `glass-titles` — the ELIXIS-TITLES brief vocabulary: glass-family
  substrings (`glass`, `lucite`, `perspex`, `plex`, `vitrine`, `lume`),
  banned words (`console`, `copilot`, `aurelia`, `peridot`, ...), and
  dangerous-only-if-earned warnings (`watch`, `pager`, `brick`, ...).
- `inworld-glass` — the ELIXIS-INWORLD-GLASS round-1 kills
  (`kiln`, `mica`, `sinter`, `tokamber`).

Longer killed words match any readable occurrence inside a compound
(`tokkiln`, `glassback`); short generic ones match on word boundaries
(`os`, `hud`, `tty`).

## Prosody rubric (ST / EC / SO / SY, each 1-5)

- **ST** — trochaic front-stress (the TOK- reference beat): heavy first
  syllable and <=2 syllables is a 5; extra syllables cost; weak Latin
  prefixes pull stress forward.
- **EC** — syllable economy: 1-2 syllables is a 5, each extra costs one,
  consonant-cluster pileups cost more.
- **SO** — say-it-once spellability: ambiguous digraphs (`io`, `eo`,
  `ough`, `ph`, `sch`), y-as-vowel traps, length, and final-syllable
  spelling traps (`-ur`/`-ar`/`-al`) cost points.
- **SY** — pair symmetry, judged on the spoken "___ and ___" line of two
  names: equal syllable counts with shared cadence is a 5; each step of
  difference costs one; unspellable members break the walk.

Signal-grade by design: calibrated against the ELIXIS-INWORLD-GLASS
round-2 reference tables (SY reproduces all five documented pair cells;
ST/EC/SO land within one point of every human-judged cell with the field
ordering intact), not against every individual judgment.

## Deniability gate

The wink must be present but deniable. A smoke word readable inside the
name (`tokpipe`, `tokbowl`, `tokgreen`) fails the straight-face test and
is rejected. A wink carried by mineral etymology (`tokcairngorm`,
`tokmeerschaum`, `tokamethyst`) or a homophone compound (`tokmullite`)
passes. No wink is a warning, not a kill.

## The plate unit

Silk + name + subtitle, emitted and validated as ONE unit:

- silk: 2-5 letterspaced words, kill-list clean
- name: 1-3 words, passing prosody, deniable wink
- subtitle: one line, no marketing tokens, terminal punctuation

Sources of truth: `halo-collab/experiments/ELIXIS-INWORLD-GLASS.md`
(round-2 rubric tables), `ELIXIS-TITLES.md` (object kill lists, plate
rows), `elixis_run/brief.md` (house rules).
