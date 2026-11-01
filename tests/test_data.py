"""The bundled games: well formed, hashed as the rules record, and holding the boundary claims the task is about."""

from __future__ import annotations

import pytest

from plugin import rules
from plugin.data import GAMES


def keyed(name: str) -> list[dict]:
    claims = [{**claim, "text": rules.render(claim)} for claim in GAMES[name]["claims"]]
    return rules.keyed(GAMES[name]["box_score"], claims)


@pytest.mark.parametrize("name", sorted(GAMES))
def test_each_game_is_well_formed_and_matches_its_recorded_hash(name: str) -> None:
    claims = [{**claim, "text": rules.render(claim)} for claim in GAMES[name]["claims"]]
    assert rules.data_problem(name, GAMES[name]["box_score"], claims) is None
    assert rules.sha256({"box_score": GAMES[name]["box_score"], "claims": claims}) == rules.DATA_SHA256[name]
    assert set(rules.DATA_SHA256) == set(GAMES) and len(claims) == 10


def test_lynx_herons_labels() -> None:
    assert [(c["id"], c["label"], c["observed"]) for c in keyed("lynx-herons")] == [
        ("c01", "supported", 31),  # at least 31, with 31
        ("c02", "contradicted", 31),  # more than 31, with 31
        ("c03", "supported", 7),
        ("c04", "contradicted", 11),
        ("c05", "supported", 97),
        ("c06", "supported", 35),
        ("c07", "not_found", None),  # Rosa Quintero plays for the Otters
        ("c08", "contradicted", 12),
        ("c09", "supported", 104),
        ("c10", "supported", 1),
    ]


def test_foxes_bison_labels() -> None:
    assert [(c["id"], c["label"], c["observed"]) for c in keyed("foxes-bison")] == [
        ("c01", "supported", 24),
        ("c02", "contradicted", 6),
        ("c03", "supported", 10),
        ("c04", "supported", 80),  # at least 80, with 80
        ("c05", "contradicted", 80),  # more than 80, with 80
        ("c06", "contradicted", 30),  # fewer than 30, with 30
        ("c07", "not_found", None),
        ("c08", "supported", 18),  # at most 18, with 18
        ("c09", "supported", 30),
        ("c10", "not_found", None),  # a team's rebounds: not a number the box score gives
    ]


def test_otters_wolves_labels() -> None:
    assert [(c["id"], c["label"], c["observed"]) for c in keyed("otters-wolves")] == [
        ("c01", "supported", 24),
        ("c02", "supported", 13),
        ("c03", "contradicted", 7),
        ("c04", "supported", 12),
        ("c05", "contradicted", 95),  # fewer than 95, with 95
        ("c06", "supported", 35),
        ("c07", "not_found", None),
        ("c08", "supported", 18),
        ("c09", "contradicted", 101),
        ("c10", "contradicted", 3),
    ]


def test_every_comparator_stat_and_label_appears_across_the_games() -> None:
    claims = [claim for name in GAMES for claim in keyed(name)]
    assert {claim["comparator"] for claim in claims} == set(rules.COMPARATORS)
    assert {claim["stat"] for claim in claims} == set(rules.STATS)
    assert {claim["label"] for claim in claims} == set(rules.LABELS)
    assert {claim["subject_kind"] for claim in claims} == set(rules.KINDS)
