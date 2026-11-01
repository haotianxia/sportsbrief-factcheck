"""The rules: the claim template, the comparisons, the lookup and the data checks; and the verifier's copy of
the rules is byte-for-byte the tools'."""

from __future__ import annotations

from pathlib import Path

import pytest

from plugin import rules
from plugin.data import claim, line

ROOT = Path(__file__).resolve().parents[1]
LYNX, HER = "Harbor Lynx", "Bayou Herons"
BOX = {
    "home_team": LYNX,
    "away_team": HER,
    "home_score": 50,
    "away_score": 45,
    "players": [
        line("Mara Okafor", LYNX, 30, 20, 9, 4),
        line("Elias Tanaka", LYNX, 25, 10, 5, 7),
        line("Sam Oduya", LYNX, 20, 10, 11, 2),
        line("Jonah Reyes", LYNX, 15, 5, 3, 6),
        line("Kira Holmgren", LYNX, 10, 5, 7, 1),
        line("Theo Abara", HER, 30, 15, 6, 3),
        line("Nikolai Oyelaran", HER, 25, 10, 12, 2),
        line("Celeste Varga", HER, 20, 10, 4, 8),
        line("Imani Laurent", HER, 15, 5, 5, 1),
        line("Ruben Castillo", HER, 10, 5, 8, 2),
    ],
}


def test_the_verifier_runs_the_very_rules_the_tools_use() -> None:
    assert (ROOT / "verifier" / "rules.py").read_bytes() == (ROOT / "src" / "plugin" / "rules.py").read_bytes()


def test_render_makes_one_sentence_per_meaning() -> None:
    assert rules.render(claim(1, "player", "Mara Okafor", "points", "at_least", 31)) == "Mara Okafor scored at least 31 points."
    assert rules.render(claim(1, "player", "Sam Oduya", "rebounds", "at_most", 10)) == "Sam Oduya grabbed at most 10 rebounds."
    assert rules.render(claim(1, "player", "Elias Tanaka", "assists", "exactly", 7)) == "Elias Tanaka handed out exactly 7 assists."
    assert rules.render(claim(1, "player", "Theo Abara", "minutes", "more_than", 30)) == "Theo Abara played more than 30 minutes."
    assert rules.render(claim(1, "team", HER, "points", "fewer_than", 100)) == "The Bayou Herons scored fewer than 100 points."


@pytest.mark.parametrize(
    ("comparator", "below", "equal", "above"),
    [("at_least", False, True, True), ("more_than", False, False, True), ("exactly", False, True, False), ("at_most", True, True, False), ("fewer_than", True, False, False)],
)
def test_the_five_comparisons_at_and_around_the_number(comparator: str, below: bool, equal: bool, above: bool) -> None:
    assert (rules.compare(9, comparator, 10), rules.compare(10, comparator, 10), rules.compare(11, comparator, 10)) == (below, equal, above)


def test_lookup_reads_a_players_line_or_a_teams_points_and_nothing_else() -> None:
    assert rules.lookup(BOX, claim(1, "player", "Mara Okafor", "rebounds", "exactly", 9)) == 9
    assert rules.lookup(BOX, claim(1, "player", "Ruben Castillo", "minutes", "exactly", 9)) == 10
    assert rules.lookup(BOX, claim(1, "team", LYNX, "points", "exactly", 50)) == 50
    assert rules.lookup(BOX, claim(1, "team", HER, "points", "exactly", 45)) == 45
    assert rules.lookup(BOX, claim(1, "team", HER, "rebounds", "exactly", 45)) is None
    assert rules.lookup(BOX, claim(1, "team", "Summit Foxes", "points", "exactly", 45)) is None
    assert rules.lookup(BOX, claim(1, "player", "Rosa Quintero", "points", "exactly", 9)) is None
    assert rules.lookup(BOX, claim(1, "player", "mara okafor", "points", "exactly", 9)) is None, "names match exactly as spelled"


def test_evaluate_labels_the_boundaries() -> None:
    assert rules.evaluate(BOX, claim(1, "player", "Mara Okafor", "points", "at_least", 20)) == ("supported", 20)
    assert rules.evaluate(BOX, claim(1, "player", "Mara Okafor", "points", "more_than", 20)) == ("contradicted", 20)
    assert rules.evaluate(BOX, claim(1, "player", "Mara Okafor", "points", "fewer_than", 20)) == ("contradicted", 20)
    assert rules.evaluate(BOX, claim(1, "player", "Mara Okafor", "points", "at_most", 20)) == ("supported", 20)
    assert rules.evaluate(BOX, claim(1, "team", HER, "points", "exactly", 45)) == ("supported", 45)
    assert rules.evaluate(BOX, claim(1, "player", "Nobody", "points", "at_least", 0)) == ("not_found", None)
    assert rules.evaluate(BOX, claim(1, "team", HER, "assists", "at_least", 0)) == ("not_found", None)


def test_box_problem_names_what_is_wrong() -> None:
    assert rules.box_problem(BOX) is None
    assert rules.box_problem({**BOX, "away_team": LYNX}) == "the box score is not between two different league teams"
    assert rules.box_problem({**BOX, "home_score": 51}) == "Harbor Lynx's score is not its players' points"
    assert rules.box_problem({**BOX, "players": [*BOX["players"], BOX["players"][0]]}) == "a player appears twice"
    assert rules.box_problem({**BOX, "players": [{**BOX["players"][0], "points": -1}, *BOX["players"][1:]]}) == "Mara Okafor has a negative number"
    assert rules.box_problem({**BOX, "players": BOX["players"][1:]}) == "Harbor Lynx has fewer than 5 players"
    assert rules.box_problem({**BOX, "players": [*BOX["players"][5:], *BOX["players"][:5]]}) == "the players are not listed home team first"
    tied = {**BOX, "away_score": 50, "players": [*BOX["players"][:5], {**BOX["players"][5], "points": 20}, *BOX["players"][6:]]}
    assert rules.box_problem(tied) == "the game has no winner"


def test_claims_problem_holds_every_text_to_its_meaning() -> None:
    claims = [{**claim(1, "player", "Mara Okafor", "points", "at_least", 20), "text": "Mara Okafor scored at least 20 points."}]
    assert rules.claims_problem(claims) is None
    assert rules.claims_problem([]) == "the game holds no claim"
    assert rules.claims_problem([{**claims[0], "id": "c02"}]) == "the claims are not numbered c01, c02, ... in order"
    assert rules.claims_problem([{**claims[0], "comparator": "roughly"}]) == "c01 has no valid meaning"
    assert rules.claims_problem([{**claims[0], "subject_kind": "team", "subject": "Houston Rockets"}]) == "c01 names no league team"
    assert rules.claims_problem([{**claims[0], "text": "Mara Okafor scored at least 21 points."}]).startswith("c01's text does not say what its meaning says")


def test_data_problem_checks_the_recorded_hash() -> None:
    claims = [{**claim(1, "player", "Mara Okafor", "points", "at_least", 20), "text": "Mara Okafor scored at least 20 points."}]
    assert rules.data_problem("no-such-game", BOX, claims) == "'no-such-game' is not a bundled game"
    assert rules.data_problem("lynx-herons", BOX, claims).startswith("the data is not the bundled game lynx-herons: sha256 ")
