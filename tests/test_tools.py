"""The tools: the game and its receipt, and the answer key, built into their contract classes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

from contract import FactCheckInput, Game, GameOutput, Label, PinClaimsOutput
from plugin import rules
from plugin.factcheck import expected_output, pin_claims, read_game, receipt_path


def test_read_game_shows_the_box_score_and_the_claims_texts_and_writes_its_receipt(tmp_path: Path) -> None:
    shown = read_game(build_output({"game": "lynx-herons"}, FactCheckInput), tmp_path)
    build_output(plain_output(shown), GameOutput)
    assert shown.game is Game.LYNX_HERONS and shown.box_score.home_score == 104 and len(shown.box_score.players) == 10
    assert [claim.id for claim in shown.claims] == [f"c{index:02d}" for index in range(1, 11)]
    assert shown.claims[0].text == "Mara Okafor scored at least 31 points."
    receipt = json.loads(receipt_path(tmp_path, "lynx-herons").read_text())
    assert receipt["game"] == "lynx-herons" and receipt["data_sha256"] == shown.data_sha256 == rules.DATA_SHA256["lynx-herons"]
    assert receipt["box_score"] == plain_output(shown)["box_score"] and receipt["claims"] == plain_output(shown)["claims"]
    assert "subject" not in json.dumps(receipt), "the agent never sees a claim's meaning, only its text"


def test_pin_claims_gives_the_rules_labels(tmp_path: Path) -> None:
    pinned = pin_claims(build_output({"game": "foxes-bison"}, FactCheckInput), tmp_path)
    build_output(plain_output(pinned), PinClaimsOutput)
    assert pinned.data_sha256 == rules.DATA_SHA256["foxes-bison"]
    assert [(claim.id, claim.label, claim.observed) for claim in pinned.claims][3:6] == [
        ("c04", Label.SUPPORTED, 80),
        ("c05", Label.CONTRADICTED, 80),
        ("c06", Label.CONTRADICTED, 30),
    ]
    assert pinned.claims[9].label is Label.NOT_FOUND and pinned.claims[9].observed is None
    assert not list(tmp_path.iterdir()), "the answer key writes nothing"
    expected = expected_output(build_output({"game": "foxes-bison"}, FactCheckInput))
    assert [(verdict.claim, verdict.label, verdict.observed) for verdict in expected.verdicts] == [(c.id, c.label, c.observed) for c in pinned.claims]


def test_an_unknown_game_is_refused_by_the_contract() -> None:
    with pytest.raises(ValueError, match="not a valid Game"):
        build_output({"game": "hawks-cranes"}, FactCheckInput)
