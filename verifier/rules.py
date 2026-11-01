"""The fact-check rules: pure functions of a game's box score and claims, shared by the tools and the verifier.

verifier/rules.py is a byte-for-byte copy of this file (tests/test_rules.py enforces it), so the
verifier re-derives every label with the very code the tools used, importing only pure
standard-library modules. Values are plain JSON values here. Every claim's text is rendered from
its meaning (subject, stat, comparator, value) by one template, so the meaning the answer key
holds is exactly what the sentence says.
"""

import hashlib
import json
import re

TEAMS = (
    "Bayou Herons",
    "Canyon Hawks",
    "Delta Otters",
    "Harbor Lynx",
    "Lakeside Cranes",
    "Prairie Bison",
    "Ridge Wolves",
    "Summit Foxes",
)
STATS = ("points", "rebounds", "assists", "minutes")
COMPARATORS = ("at_least", "more_than", "exactly", "at_most", "fewer_than")
KINDS = ("player", "team")
LABELS = ("supported", "contradicted", "not_found")
CLAIM_ID = re.compile(r"^c[0-9]{2}$")
PHRASE = {"at_least": "at least", "more_than": "more than", "exactly": "exactly", "at_most": "at most", "fewer_than": "fewer than"}
VERB = {"points": "scored", "rebounds": "grabbed", "assists": "handed out", "minutes": "played"}
MIN_PLAYERS = 5
RECEIPTS = "factcheck"  # read_game records what it read under <workspace>/factcheck/<game>.json
# sha256 of each bundled game's canonical JSON (src/plugin/data.py); tests/test_data.py keeps them current.
DATA_SHA256 = {
    "lynx-herons": "63d30c793682c2fc0dadcb185de35c02fa978b12fc6085a5304b573f04dec3fe",
    "foxes-bison": "d635b6700d396d17a8b4c3a5c911212bfb8cd1ec5a015c045b89c4912e65ee32",
    "otters-wolves": "9fa2a7e948e9210d4ad2759b25aae2ed96b786906edb78b2ca817a8a5c066a49",
}

STAMP = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z$")  # a UTC time, comparable as text


def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year, month):
    if month == 2:
        return 29 if is_leap(year) else 28
    return 30 if month in (4, 6, 9, 11) else 31


def stamp_problem(text):
    """Why ``text`` is not a UTC time YYYY-MM-DDTHH:MM:SSZ, or None. Such times compare as text."""
    found = STAMP.fullmatch(text) if isinstance(text, str) else None
    if not found:
        return f"{text!r} is not a UTC time YYYY-MM-DDTHH:MM:SSZ"
    year, month, day, hour, minute, second = (int(part) for part in found.groups())
    if not 1 <= month <= 12 or not 1 <= day <= days_in_month(year, month):
        return f"{text!r} is not a calendar day"
    if hour > 23 or minute > 59 or second > 59:
        return f"{text!r} is not a time of day"
    return None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def render(claim):
    """The sentence a claim (subject_kind, subject, stat, comparator, value) makes."""
    subject = claim["subject"] if claim["subject_kind"] == "player" else f"The {claim['subject']}"
    return f"{subject} {VERB[claim['stat']]} {PHRASE[claim['comparator']]} {claim['value']} {claim['stat']}."


def compare(observed, comparator, value):
    if comparator == "at_least":
        return observed >= value
    if comparator == "more_than":
        return observed > value
    if comparator == "exactly":
        return observed == value
    if comparator == "at_most":
        return observed <= value
    return observed < value


def lookup(box_score, claim):
    """The number the box score gives for the claim's subject and stat, or None when it gives none:
    a player who did not appear, a team that did not play, or a team stat other than points."""
    if claim["subject_kind"] == "team":
        if claim["stat"] != "points":
            return None
        if claim["subject"] == box_score["home_team"]:
            return box_score["home_score"]
        if claim["subject"] == box_score["away_team"]:
            return box_score["away_score"]
        return None
    for line in box_score["players"]:
        if line["player"] == claim["subject"]:
            return line[claim["stat"]]
    return None


def evaluate(box_score, claim):
    """``(label, observed)`` for the claim against the box score."""
    observed = lookup(box_score, claim)
    if observed is None:
        return "not_found", None
    return ("supported" if compare(observed, claim["comparator"], claim["value"]) else "contradicted"), observed


def keyed(box_score, claims):
    """The claims with their text, label and observed number filled in from the rules."""
    return [{**claim, "text": render(claim), **dict(zip(("label", "observed"), evaluate(box_score, claim)))} for claim in claims]


def box_problem(box_score):
    """What is wrong with the plain ``box_score``, or None."""
    home, away = box_score["home_team"], box_score["away_team"]
    if home not in TEAMS or away not in TEAMS or home == away:
        return "the box score is not between two different league teams"
    players = box_score["players"]
    names = [line["player"] for line in players]
    if len(set(names)) != len(names):
        return "a player appears twice"
    for line in players:
        if line["team"] not in (home, away):
            return f"{line['player']} plays for neither team"
        if not line["player"].strip():
            return "a player has no name"
        if min(line["minutes"], line["points"], line["rebounds"], line["assists"]) < 0:
            return f"{line['player']} has a negative number"
    for team, score in ((home, box_score["home_score"]), (away, box_score["away_score"])):
        lines = [line for line in players if line["team"] == team]
        if len(lines) < MIN_PLAYERS:
            return f"{team} has fewer than {MIN_PLAYERS} players"
        if sum(line["points"] for line in lines) != score:
            return f"{team}'s score is not its players' points"
    if [line["team"] for line in players] != [home] * len([line for line in players if line["team"] == home]) + [away] * len([line for line in players if line["team"] == away]):
        return "the players are not listed home team first"
    if box_score["home_score"] == box_score["away_score"]:
        return "the game has no winner"
    return None


def claims_problem(claims):
    """What is wrong with the plain structured ``claims`` (id, text, subject_kind, subject, stat, comparator, value), or None."""
    if not claims:
        return "the game holds no claim"
    if [claim["id"] for claim in claims] != [f"c{index:02d}" for index in range(1, len(claims) + 1)]:
        return "the claims are not numbered c01, c02, ... in order"
    for claim in claims:
        if claim["subject_kind"] not in KINDS or claim["stat"] not in STATS or claim["comparator"] not in COMPARATORS:
            return f"{claim['id']} has no valid meaning"
        if claim["subject_kind"] == "team" and claim["subject"] not in TEAMS:
            return f"{claim['id']} names no league team"
        if not claim["subject"].strip() or claim["value"] < 0:
            return f"{claim['id']} has no subject or a negative number"
        if claim["text"] != render(claim):
            return f"{claim['id']}'s text does not say what its meaning says: {claim['text']!r} is not {render(claim)!r}"
    return None


def data_problem(name, box_score, claims):
    """What is wrong with ``box_score`` and ``claims`` (structured, without labels) as the bundled game ``name``, or None."""
    if name not in DATA_SHA256:
        return f"{name!r} is not a bundled game"
    problem = box_problem(box_score) or claims_problem(claims)
    if problem:
        return problem
    digest = sha256({"box_score": box_score, "claims": claims})
    if digest != DATA_SHA256[name]:
        return f"the data is not the bundled game {name}: sha256 {digest} instead of {DATA_SHA256[name]}"
    return None


def unlabelled(claim):
    """A keyed claim without its label and observed number: what the data holds."""
    return {name: claim[name] for name in ("id", "text", "subject_kind", "subject", "stat", "comparator", "value")}
