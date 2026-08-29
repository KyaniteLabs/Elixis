"""Machine-encoded naming discipline for the Glass Bead Game.

Ports the house rules that previously lived only in prompts and experiment
docs (halo-collab/experiments/ELIXIS-INWORLD-GLASS.md round 2, ELIXIS-TITLES.md
sections 3/7, elixis_run/brief.md) into deterministic validators the engine
applies at Phase 5:

  (a) KILL LISTS — house rules (em dashes, journey/unlock/unleash slop,
      AI-slop tokens, single-part abbreviation names) plus object-level
      banned-word and dangerous-only-if-earned profiles.
  (b) PROSODY RUBRIC — ST (trochaic front-stress), EC (syllable economy),
      SO (say-it-once spellability), SY (pair symmetry), each scored 1-5
      from computable features of the string.
  (c) DENIABILITY — the wink must be present but deniable: a smoke pun
      exposed as a bare word fails the straight-face test; a pun buried in
      a compound passes; no wink is a warning, not a kill.
  (d) PLATE — silk + name + subtitle validated and emitted as one unit.

All scoring is signal-grade: it reproduces the reference cadence's ordering,
not every human-judged cell of the experiment tables.
"""

import re
from typing import Dict, List, Optional

# ── (a) Kill lists ─────────────────────────────────────────────────────

EM_DASHES = ("—", "–")  # en dash renders nearly identically in print; both die

HOUSE_TOKENS = (
    "journey", "unlock", "unleash", "level-up", "levelup",
)

AI_SLOP_TOKENS = (
    "delve", "tapestry", "testament", "symphony", "elevate", "empower",
    "embark", "seamless", "game-changer", "gamechanger", "revolutionize",
    "revolutionary", "cutting-edge", "next-generation", "game changing",
    "dive deep", "in today's world",
)

# Words that are bare abbreviations / single-part fragments: QK, MTP, CTX.
_SINGLE_PART_RE = re.compile(r"^[A-Z]{2,6}$")

# Substring-match families: any name containing these dies (glass-family,
# trademarked plastics, glass-case vocabulary).
FAMILY_SUBSTRINGS = (
    "glass", "lucite", "perspex", "makrolon", "plex", "vitrine", "vitreous",
    "lume",
)

# Object profile: glass-titles brief (ELIXIS-TITLES.md sections 3 and 7).
# Exact whole-name or word-boundary matches.
GLASS_TITLES_KILLED = (
    "caseback", "exhibition", "caliber", "tourbillon", "movement",
    "escapement", "chronograph", "printer", "teletype", "ticker", "tape",
    "tty", "op-1", "pocket operator", "teenage", "ibook", "studio display",
    "console", "cockpit", "hud", "dashboard", "copilot", "chat", "lab",
    "studio", "os", "grape", "purple", "atomic", "encarta",
    "pagerpath", "clearpass", "aurelia", "peridot", "moonjelly", "jellybox",
    "scrollbrick", "amber", "resin", "palm", "pilot",
)

# Inworld glass pass round-1 kills (ELIXIS-INWORLD-GLASS.md).
INWORLD_GLASS_KILLED = (
    "kiln", "mica", "sinter", "tokamber",
)

# Dangerous only if earned (surfaced as warnings; a human cites the brief
# that earned them). Order preserved from the source docs.
DANGEROUS_WORDS = (
    "watch", "ice", "bondi", "pager", "residual", "patch", "thru", "path",
    "brick", "pad", "case",
)

# Marketing tokens forbidden in subtitles (one line, no marketing).
MARKETING_TOKENS = (
    "revolutionary", "game-changing", "game changing", "cutting-edge",
    "next-generation", "seamless", "powerful", "ultimate", "magic",
    "unlock", "unleash", "journey", "elevate",
)

OBJECT_PROFILES: Dict[str, Dict] = {
    "glass-titles": {
        "killed_words": GLASS_TITLES_KILLED,
        "family_substrings": FAMILY_SUBSTRINGS,
        "dangerous_words": DANGEROUS_WORDS,
    },
    "inworld-glass": {
        "killed_words": INWORLD_GLASS_KILLED,
        "family_substrings": FAMILY_SUBSTRINGS,
        "dangerous_words": DANGEROUS_WORDS,
    },
}


def _words(text: str) -> List[str]:
    """Lowercased word tokens (middots and separators stripped)."""
    return re.findall(r"[a-z0-9'+-]+", text.lower())


def kill_list_violations(text: str, profile: Optional[str] = None) -> List[str]:
    """Return a list of kill-list violations found in text. Empty = clean.

    House rules always apply; the named object profile (if given) adds its
    own killed words and substring families.
    """
    if not text:
        return []
    violations: List[str] = []

    for dash in EM_DASHES:
        if dash in text:
            violations.append(f"em dash ({dash!r})")
            break

    lowered = text.lower()
    tokens = set(_words(text))
    for tok in HOUSE_TOKENS:
        if tok in tokens:
            violations.append(f"house token: {tok}")
    for tok in AI_SLOP_TOKENS:
        if re.search(r"(?<![\w])" + re.escape(tok) + r"(?![\w])", lowered):
            violations.append(f"AI-slop token: {tok}")

    if _SINGLE_PART_RE.match(text.strip()):
        violations.append(f"single-part abbreviation name: {text.strip()}")

    if profile:
        conf = OBJECT_PROFILES.get(profile)
        if conf:
            for fam in conf["family_substrings"]:
                if fam in lowered:
                    violations.append(f"family word: {fam}")
            for killed in conf["killed_words"]:
                # Short generic tokens (os, hud, tty) match on word boundaries;
                # longer ones kill any readable occurrence inside a compound
                # (tokkiln, glassback) per the experiment kill lists.
                if len(killed) >= 4:
                    if killed in lowered:
                        violations.append(f"kill-list word: {killed}")
                elif re.search(r"(?<![\w])" + re.escape(killed) + r"(?![\w])", lowered):
                    violations.append(f"kill-list word: {killed}")
    return violations


def dangerous_words_found(text: str, profile: Optional[str] = None) -> List[str]:
    """Dangerous words present in text (warnings, not kills, until earned)."""
    if not text:
        return []
    conf = OBJECT_PROFILES.get(profile) if profile else None
    lexicon = conf["dangerous_words"] if conf else DANGEROUS_WORDS
    tokens = set(_words(text))
    return [w for w in lexicon if w in tokens]


# ── (b) Prosody rubric ─────────────────────────────────────────────────

_VOWELS = "aeiouy"

# Vowel pairs that reliably read as two syllables in names when more letters
# follow (i-o in iolite, i-a in diagonal). Diphthong pairs (ai/au/oi/ea) are
# deliberately excluded: cairngorm and meerschaum are one syllable per pair.
_DISYLLABIC_PAIRS = ("io", "ia", "eo", "ua", "uo", "iu", "eu", "ya", "ye", "yo")


def count_syllables(word: str) -> int:
    """Heuristic English syllable count (vowel-group method).

    Counts contiguous vowel groups, drops silent final e, splits vowel pairs
    that read as two syllables mid-word, and floors at 1. Signal-grade,
    not dictionary-grade.
    """
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    groups = 0
    prev_vowel = False
    i = 0
    while i < len(word):
        ch = word[i]
        is_vowel = ch in _VOWELS
        if is_vowel and not prev_vowel:
            groups += 1
            # Check for a disyllabic pair starting here (not word-final).
            if i + 2 < len(word) and word[i : i + 2] in _DISYLLABIC_PAIRS:
                rest = word[i + 2 :]
                if rest[0] not in _VOWELS and len(rest) > 1:
                    groups += 1
                    i += 1  # consume the second vowel of the pair
        prev_vowel = is_vowel
        i += 1
    if word.endswith("e") and groups > 1 and not word.endswith(("le", "ee", "ye")):
        groups -= 1
    return max(1, groups)


def name_syllables(name: str) -> int:
    """Syllables across a multiword name."""
    parts = [p for p in re.split(r"[\s·-]+", name) if re.search(r"[a-z]", p.lower())]
    return sum(count_syllables(p) for p in parts)


# Ambiguous spelling units and their penalties for the SO axis.
_SO_PENALTIES = (
    ("ough", 2), ("augh", 2), ("eigh", 2), ("io", 2), ("ii", 2),
    ("eo", 1), ("ae", 1), ("oe", 1), ("ph", 1), ("gh", 1),
    ("sch", 1), ("kn", 1), ("wr", 1), ("psy", 1), ("hy", 1),
)

# Suffixes whose vowel is not spelled the way it sounds to strangers.
_SO_LENGTH_STEP_1 = 9   # -1 from this many characters
_SO_LENGTH_STEP_2 = 12  # -2 from this many characters


def _has_y_as_vowel(word: str) -> bool:
    """Non-initial y followed by a vowel (the hyalite/typhoon trap)."""
    w = word.lower()
    return bool(re.search(r"(?<=.)y[aeiou]", w)) or bool(re.search(r"[aeiou]y(?![aeiou])", w))


# Unstressed final syllables whose vowel strangers spell three ways
# (sulfur/sulphur, spar/sphäre, opal/opel): each costs one SO point.
_SO_FINAL_TRAPS = ("ur", "ar", "or", "er", "al")


def score_so(name: str) -> int:
    """SO: say-it-once spellability, 1-5.

    A stranger hears the name once and can spell it. Penalizes ambiguous
    digraphs, y-as-vowel traps, sheer length, and final syllables whose
    vowel has multiple common spellings.
    """
    w = re.sub(r"[^a-z]", "", name.lower())
    if not w:
        return 1
    score = 5
    for unit, penalty in _SO_PENALTIES:
        occurrences = w.count(unit)
        if occurrences:
            score -= penalty * min(occurrences, 2)
    if _has_y_as_vowel(w):
        score -= 1
    if len(w) >= _SO_LENGTH_STEP_2:
        score -= 2
    elif len(w) >= _SO_LENGTH_STEP_1:
        score -= 1
    if w.endswith(_SO_FINAL_TRAPS):
        score -= 1
    return max(1, min(5, score))


def score_ec(name: str) -> int:
    """EC: syllable economy, 1-5.

    1-2 syllables is a 5; each extra syllable costs a point; consonant
    cluster pileups (4+ letters) cost one more.
    """
    s = name_syllables(name)
    if s == 0:
        return 1
    score = 5 - max(0, s - 2)
    lowered = re.sub(r"[^a-z]", "", name.lower())
    if re.search(r"[bcdfghjklmnpqrstvwxz]{4,}", lowered):
        score -= 1
    return max(1, min(5, score))


# Weak Latin prefixes pull stress off the first syllable.
_WEAK_PREFIX_RE = re.compile(
    r"^(a|e|i|o|u|be|de|re|dis|con|com|en|em|sub|super|over|under)[bcdfgklmnprstv]",
)

# Front-stress suffix families: the final syllable stays light.
_FRONT_STRESS_OK_SUFFIXES = ("ite", "al", "ol", "in", "an", "on", "ar", "is")


def score_st(name: str) -> int:
    """ST: trochaic front-stress, 1-5.

    Bisyllables with a heavy first syllable set the TOK- reference beat (5);
    a third syllable costs one, a fourth costs two, five-plus floors at 2;
    a weak prefix pulls stress forward and costs two more.
    """
    first = re.split(r"[\s·-]+", name.strip())[0] if name.strip() else ""
    first_alpha = re.sub(r"[^a-z]", "", first.lower())
    if not first_alpha:
        return 1
    s = name_syllables(first)
    if s <= 2:
        heavy_coda = bool(re.search(r"[aeiouy]{1,2}[bcdfghjklmnpqrstvwxz]{1,2}$", first_alpha))
        long_first = bool(re.search(r"[aeiouy]{2}", first_alpha[:4]))
        score = 5 if (heavy_coda or long_first) else 4
    elif s == 3:
        score = 4
    elif s == 4:
        score = 3
    else:
        score = 2
    if _WEAK_PREFIX_RE.match(first_alpha):
        score -= 2
    lowered = first_alpha
    if lowered.endswith(_FRONT_STRESS_OK_SUFFIXES) and s >= 3:
        score += 0  # already front-stressed by default in noun compounds
    return max(1, min(5, score))


def score_sy(name_a: str, name_b: str) -> int:
    """SY: pair symmetry spoken aloud, 1-5, judged on the PAIR.

    "___ and ___" must walk evenly. Equal syllable counts with a shared
    ending cadence (or both perfect trochees) is a 5; equal counts with
    different endings is a 4; each step of syllable difference costs one
    point; mismatched front-stress or a member that cannot be spelled
    (SO <= 2) breaks the spoken walk and costs one more.
    """
    sa, sb = name_syllables(name_a), name_syllables(name_b)
    diff = abs(sa - sb)
    if diff == 0:
        a_end = re.sub(r"[^a-z]", "", name_a.lower())[-3:]
        b_end = re.sub(r"[^a-z]", "", name_b.lower())[-3:]
        both_trochee = score_st(name_a) >= 5 and score_st(name_b) >= 5
        score = 5 if (a_end == b_end or both_trochee) else 4
    else:
        score = max(1, 4 - diff)  # diff 1 -> 3, diff 2 -> 2, diff 3+ -> 1
    if diff == 0 and score_st(name_a) != score_st(name_b):
        score -= 1  # uneven stress only adds damage when counts already match
    if min(score_so(name_a), score_so(name_b)) <= 2:
        score -= 1
    return max(1, min(5, score))


def prosody_scores(name: str, partner: Optional[str] = None) -> Dict[str, int]:
    """Full rubric for one name. SY uses the partner if given, else 0 (unset)."""
    return {
        "ST": score_st(name),
        "EC": score_ec(name),
        "SO": score_so(name),
        "SY": score_sy(name, partner) if partner else 0,
    }


def prosody_average(name: str, partner: Optional[str] = None) -> float:
    scores = prosody_scores(name, partner)
    if partner:
        return round(sum(scores.values()) / 4, 2)
    return round((scores["ST"] + scores["EC"] + scores["SO"]) / 3, 2)


PROSODY_PASS_THRESHOLD = 3.0  # average at or above this passes the rubric


# ── (c) Deniability gate ───────────────────────────────────────────────

# Smoke-bridge lexicon: words whose presence as a BARE word makes the wink
# the whole dish (tokpipe / tokbowl died on exactly this). Homophone bridges
# (tok-, minerals like meerschaum or amethyst) stay deniable.
WINK_LEXICON = (
    "toke", "tokay", "pipe", "bowl", "bong", "joint", "blunt", "weed",
    "grass", "herb", "smoke", "smoking", "stoned", "dope", "cannabis",
    "marijuana", "thc", "green",
)

# Etymological wink carriers: a name containing one of these carries a
# present-but-deniable wink (mineral etymology does the smoking).
WINK_CARRIERS = (
    "cairngorm", "meerschaum", "sepiolite", "amethyst", "sulfur", "sulphur",
    "brimstone", "morion", "fumarole", "pitchblende", "autunite",
)


def deniability_check(name: str) -> Dict:
    """The straight-face gate: the wink must be present but deniable.

    Returns {"verdict": "pass"|"fail"|"no-wink", "wink": str, "reason": str}.
    fail = a smoke word is readable inside the name (tokpipe died here:
    the wink is the whole dish and fails the straight-face test);
    no-wink = no wink detected (demoted, not killed);
    pass = wink present and buried in etymology or a homophone compound.
    """
    lowered = name.lower()
    for wink in WINK_LEXICON:
        if wink in lowered:
            return {
                "verdict": "fail",
                "wink": wink,
                "reason": f"the wink is the whole dish: {wink!r} is readable on first read",
            }
    for carrier in WINK_CARRIERS:
        if carrier in lowered:
            return {
                "verdict": "pass",
                "wink": carrier,
                "reason": f"wink carried by etymology ({carrier}); survives a straight face",
            }
    if lowered.startswith("tok") and len(lowered) > 3:
        return {
            "verdict": "pass",
            "wink": "tok~toke homophone",
            "reason": "homophone bridge buried inside the compound; deniable in an investor conversation",
        }
    return {
        "verdict": "no-wink",
        "wink": "",
        "reason": "no wink detected; prosody may still carry the name",
    }


# ── Variant adjudication ───────────────────────────────────────────────

def apply_discipline(variants: List[Dict], profile: Optional[str] = None) -> Dict:
    """Adjudicate LLM naming variants against the machine-encoded discipline.

    Returns {"kept": [...], "rejected": [...]} where every variant carries:
      prosody (ST/EC/SO/SY + average), kill_list_violations,
      dangerous_words, deniability, discipline_pass.
    Rejected variants keep their audit trail (the corpus prizes the rejects).
    """
    kept: List[Dict] = []
    rejected: List[Dict] = []
    for v in variants:
        name = (v.get("name") or "").strip()
        enriched = dict(v)
        enriched["name"] = name
        violations = kill_list_violations(name, profile)
        dangerous = dangerous_words_found(name, profile)
        deniability = deniability_check(name)
        partner = None  # SY filled pairwise for the plate below
        scores = prosody_scores(name, partner)
        enriched["prosody"] = dict(scores, average=prosody_average(name))
        enriched["kill_list_violations"] = violations
        enriched["dangerous_words"] = dangerous
        enriched["deniability"] = deniability
        hard_fail = bool(violations) or deniability["verdict"] == "fail"
        prosody_fail = enriched["prosody"]["average"] < PROSODY_PASS_THRESHOLD
        enriched["discipline_pass"] = not hard_fail and not prosody_fail
        (rejected if hard_fail else kept).append(enriched)
    return {"kept": kept, "rejected": rejected}


# ── (d) The plate unit ─────────────────────────────────────────────────

SILK_MIN_WORDS = 2
SILK_MAX_WORDS = 5
NAME_MIN_WORDS = 1
NAME_MAX_WORDS = 3


def make_plate(silk: str, name: str, subtitle: str, partner: str = "") -> Dict:
    """Assemble the plate: silk + name + subtitle emitted as ONE unit."""
    return {
        "silk": silk,
        "name": name,
        "subtitle": subtitle,
        "partner": partner,
        "prosody": prosody_scores(name, partner or None),
        "deniability": deniability_check(name),
    }


def validate_plate(plate: Dict, profile: Optional[str] = None) -> Dict:
    """Validate a plate against the full discipline.

    A plate is valid when every row is kill-list clean, the silk is 2-5
    words, the name is 1-3 words with passing prosody and a deniable (or
    at least not-failed) wink, and the subtitle is one marketing-free line.
    """
    violations: List[str] = []
    warnings: List[str] = []

    silk = (plate.get("silk") or "").strip()
    name = (plate.get("name") or "").strip()
    subtitle = (plate.get("subtitle") or "").strip()
    partner = (plate.get("partner") or "").strip()

    for field, value in (("silk", silk), ("name", name), ("subtitle", subtitle)):
        hits = kill_list_violations(value, profile)
        for hit in hits:
            violations.append(f"{field}: {hit}")

    silk_words = [w for w in re.split(r"[\s·]+", silk) if re.search(r"[a-z0-9]", w.lower())]
    if not (SILK_MIN_WORDS <= len(silk_words) <= SILK_MAX_WORDS):
        violations.append(
            f"silk: {len(silk_words)} words (needs {SILK_MIN_WORDS}-{SILK_MAX_WORDS})"
        )

    name_words = [w for w in name.split() if re.search(r"[a-z0-9]", w.lower())]
    if not (NAME_MIN_WORDS <= len(name_words) <= NAME_MAX_WORDS):
        violations.append(
            f"name: {len(name_words)} words (needs {NAME_MIN_WORDS}-{NAME_MAX_WORDS})"
        )

    if name:
        scores = prosody_scores(name, partner or None)
        avg = round(
            (scores["ST"] + scores["EC"] + scores["SO"]) / 3 if not partner
            else sum(scores.values()) / 4, 2
        )
        if avg < PROSODY_PASS_THRESHOLD:
            violations.append(f"name: prosody average {avg} below {PROSODY_PASS_THRESHOLD}")
        deniability = deniability_check(name)
        if deniability["verdict"] == "fail":
            violations.append(f"name: not deniable ({deniability['reason']})")
        elif deniability["verdict"] == "no-wink":
            warnings.append(f"name: {deniability['reason']}")

    if subtitle:
        if "\n" in subtitle:
            violations.append("subtitle: must be one line")
        lowered = subtitle.lower()
        for tok in MARKETING_TOKENS:
            if re.search(r"(?<![\w])" + re.escape(tok) + r"(?![\w])", lowered):
                violations.append(f"subtitle: marketing token {tok!r}")
        if subtitle and not subtitle.rstrip().endswith((".", "!", "?")):
            warnings.append("subtitle: does not end with terminal punctuation")

    for field, value in (("silk", silk), ("name", name), ("subtitle", subtitle)):
        for w in dangerous_words_found(value, profile):
            warnings.append(f"{field}: dangerous word {w!r} present, must be earned")

    return {"valid": not violations, "violations": violations, "warnings": warnings}


def format_plate(plate: Dict) -> str:
    """Render the plate for print: silk letterspaced, name, subtitle."""
    silk = plate.get("silk", "").upper()
    return "\n".join([
        silk,
        plate.get("name", "").upper(),
        plate.get("subtitle", ""),
    ])
