"""The check-claims verdict: a gold run holds every constraint on every game, and each of the 7 constraints
fails on its own case with its own message; plus the per-call checks."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import FactCheckInput, FactCheckOutput, GameOutput, PinClaimsOutput
from plugin.factcheck import expected_output, pin_claims, read_game, receipt_path
from verifier.task import TEXT


class Run:
    """A check-claims run: the answer key pinned, read_game called in the workspace (its receipt written),
    and the correct submission ready to be judged or broken."""

    def __init__(self, workspace: Path, game: str = "lynx-herons", read: bool = True) -> None:
        self.workspace = workspace
        self.task = {"game": game}
        self.given = build_output(self.task, FactCheckInput)
        self.pin = plain_output(pin_claims(self.given, workspace / "scratch"))
        if read:
            self.shown = plain_output(read_game(self.given, workspace))
        self.gold = plain_output(expected_output(self.given))

    def verdict(self, submission: dict | None = None, pin: dict | None = None, reference: bool = True) -> dict:
        submission = self.gold if submission is None else submission
        pinned = None if not reference else build_output(self.pin if pin is None else pin, PinClaimsOutput)
        return verifier.verify_task("check-claims", self.given, build_output(submission, FactCheckOutput), pinned, str(self.workspace))

    def verdicts(self, **changes) -> list[dict]:
        entries = copy.deepcopy(self.gold["verdicts"])
        for claim, fields in changes.items():
            entry = next(entry for entry in entries if entry["claim"] == claim)
            entry.update(fields)
        return entries


def failed(found: dict) -> list[str]:
    return [check["id"] for check in found["details"]["constraints"] if check["ok"] is False]


def unchecked(found: dict) -> list[str]:
    return [check["id"] for check in found["details"]["constraints"] if check["ok"] is None]


@pytest.mark.parametrize("game", ["lynx-herons", "foxes-bison", "otters-wolves"])
def test_a_gold_run_holds_every_constraint(tmp_path: Path, game: str) -> None:
    run = Run(tmp_path, game)
    found = run.verdict()
    assert found["valid"], found["message"]
    assert found["score"] == 1.0 and found["message"].startswith("All 7 checks hold")
    assert [check["ok"] for check in found["details"]["constraints"]] == [True] * 7
    assert [check["id"] for check in found["details"]["constraints"]] == list(TEXT)
    assert found["details"]["right"] == 10
    assert len(json.dumps(found)) < 5000, "the verdict lands in the chat's context: keep it small"


def test_no_answer_key_fails_first_and_scores_zero(tmp_path: Path) -> None:
    run = Run(tmp_path)
    found = run.verdict(reference=False)
    assert not found["valid"] and found["score"] == 0.0
    assert failed(found) == ["answer-key"] and "pin_claims was not run" in found["message"]
    assert unchecked(found) == list(TEXT)[1:]


def test_an_answer_key_for_another_game_fails_answer_key(tmp_path: Path) -> None:
    run = Run(tmp_path)
    other = plain_output(pin_claims(build_output({"game": "foxes-bison"}, FactCheckInput), tmp_path / "other"))
    found = run.verdict(pin=other)
    assert failed(found) == ["answer-key"] and found["score"] == 0.0 and "'foxes-bison', not 'lynx-herons'" in found["message"]


def test_a_tampered_answer_key_fails_answer_key_data(tmp_path: Path) -> None:
    run = Run(tmp_path)
    pin = copy.deepcopy(run.pin)
    pin["box_score"]["players"][0]["points"] = 33
    found = run.verdict(pin=pin)
    assert failed(found) == ["answer-key-data"] and found["score"] == 0.0
    assert "answer-key-data: The pinned data is not the bundled lynx-herons: Harbor Lynx's score is not its players' points." == found["message"]
    assert unchecked(found) == list(TEXT)[2:]
    pin = copy.deepcopy(run.pin)
    pin["claims"][1]["label"] = "supported"
    assert "not what the rules give" in run.verdict(pin=pin)["message"]
    pin = copy.deepcopy(run.pin)
    pin["claims"][0]["text"] = "Mara Okafor scored at least 30 points."
    found = run.verdict(pin=pin)
    assert "c01's text does not say what its meaning says" in found["message"]


def test_a_submission_for_another_game_fails_task_echo(tmp_path: Path) -> None:
    run = Run(tmp_path)
    found = run.verdict({**run.gold, "game": "foxes-bison"})
    assert failed(found) == ["task-echo"] and found["score"] == 0.0
    assert "task-echo: The submission is for 'foxes-bison', not the task's 'lynx-herons'." == found["message"]


def test_submitting_without_calling_read_game_fails_agent_read(tmp_path: Path) -> None:
    run = Run(tmp_path, read=False)
    found = run.verdict()
    assert failed(found) == ["agent-read"] and found["score"] == 0.0
    assert "agent-read: No readable receipt at factcheck/lynx-herons.json: read_game was not called" in found["message"]
    assert [check["ok"] for check in found["details"]["constraints"]][4:] == [True] * 3, "the verdicts themselves are still judged"
    read_game(build_output({"game": "foxes-bison"}, FactCheckInput), tmp_path)
    assert failed(run.verdict()) == ["agent-read"], "a receipt for another game does not count"


def test_a_receipt_altered_after_read_game_fails_agent_read(tmp_path: Path) -> None:
    run = Run(tmp_path)
    path = receipt_path(tmp_path, "lynx-herons")
    receipt = json.loads(path.read_text())
    receipt["claims"][0]["text"] = "Mara Okafor scored at least 30 points."
    path.write_text(json.dumps(receipt))
    found = run.verdict()
    assert failed(found) == ["agent-read"] and "The game read_game read is not the pinned game." == found["message"].removeprefix("agent-read: ")
    receipt["box_score"]["home_score"] = 105
    path.write_text(json.dumps(receipt))
    assert "was altered after read_game" in run.verdict()["message"]
    path.write_text("[]")
    assert "was altered after read_game" in run.verdict()["message"]
    path.write_text("[" * 50000 + "]" * 50000)  # nested past the decoder's depth: not JSON the verifier can read
    assert "No readable receipt" in run.verdict()["message"]
    path.unlink()
    assert "No readable receipt" in run.verdict()["message"]


def test_a_receipt_left_by_an_earlier_run_fails_agent_read(tmp_path: Path) -> None:
    run = Run(tmp_path)
    path = receipt_path(tmp_path, "lynx-herons")
    receipt = json.loads(path.read_text())
    receipt["written_at"] = "2026-10-01T00:00:00Z"  # before this task's answer key was pinned
    path.write_text(json.dumps(receipt))
    found = run.verdict()
    assert failed(found) == ["agent-read"] and found["score"] == 0.0
    assert "was written at 2026-10-01T00:00:00Z, before the answer key was pinned at" in found["message"] and "Call read_game in this run." in found["message"]
    receipt["written_at"] = "2026-10-01T00:00:00"
    path.write_text(json.dumps(receipt))
    assert "the receipt's written_at is not a UTC time" in run.verdict()["message"]
    pin = copy.deepcopy(run.pin)
    pin["pinned_at"] = ""
    found = run.verdict(pin=pin)
    assert failed(found) == ["answer-key-data"] and "The pinned time is not a UTC time" in found["message"]


def test_malformed_verdicts_fail_claims_complete_and_stop_the_judgement(tmp_path: Path) -> None:
    run = Run(tmp_path)
    found = run.verdict({**run.gold, "verdicts": run.gold["verdicts"][:9]})
    assert failed(found) == ["claims-complete"] and found["score"] == 0.0
    assert "claims-complete: The verdicts are malformed: c10 has no verdict." == found["message"]
    assert unchecked(found) == list(TEXT)[5:]
    found = run.verdict({**run.gold, "verdicts": [*run.gold["verdicts"], {"claim": "c99", "label": "supported", "observed": 1}]})
    assert "c99 is not among the claims" in found["message"]
    found = run.verdict({**run.gold, "verdicts": [run.gold["verdicts"][0], *run.gold["verdicts"]]})
    assert "c01 is judged more than once" in found["message"]
    found = run.verdict({**run.gold, "verdicts": list(reversed(run.gold["verdicts"]))})
    assert "the verdicts are not in claim id order" in found["message"]


def test_a_wrong_label_fails_labels_exact_and_states_the_number(tmp_path: Path) -> None:
    run = Run(tmp_path)
    found = run.verdict({**run.gold, "verdicts": run.verdicts(c02={"label": "supported"})})
    assert failed(found) == ["labels-exact"] and found["score"] == 0.9
    assert found["message"] == (
        "labels-exact: c02 (Mara Okafor scored more than 31 points.) is labelled supported, but it is contradicted: "
        "Mara Okafor scored 31 points, which is not more than 31."
    )
    found = run.verdict({**run.gold, "verdicts": run.verdicts(c07={"label": "contradicted", "observed": 0})})
    assert failed(found) == ["labels-exact", "observed-exact"]
    assert "c07 (Rosa Quintero scored at least 10 points.) is labelled contradicted, but it is not_found: Rosa Quintero did not appear in this game." in found["message"]
    assert found["message"].endswith("(+1 more)") and found["score"] == 0.9
    other = Run(tmp_path / "foxes", "foxes-bison")
    found = other.verdict({**other.gold, "verdicts": other.verdicts(c10={"label": "supported", "observed": 35})})
    assert "the box score gives a team's points only, not its rebounds" in found["message"]


def test_a_wrong_number_fails_observed_exact(tmp_path: Path) -> None:
    run = Run(tmp_path)
    found = run.verdict({**run.gold, "verdicts": run.verdicts(c01={"observed": 30})})
    assert failed(found) == ["observed-exact"] and found["score"] == 0.9
    assert "observed-exact: c01's observed number is given as 30, but the box score gives 31 points for Mara Okafor." == found["message"]
    found = run.verdict({**run.gold, "verdicts": run.verdicts(c07={"observed": 0})})
    assert "c07's observed number is given as 0, but the claim is not_found, so observed must be null." in found["message"]


def test_every_label_wrong_scores_zero_but_the_data_checks_hold(tmp_path: Path) -> None:
    run = Run(tmp_path)
    flipped = {"supported": "contradicted", "contradicted": "supported", "not_found": "supported"}
    verdicts = [{**entry, "label": flipped[entry["label"]], "observed": entry["observed"] if entry["observed"] is not None else 0} for entry in run.gold["verdicts"]]
    found = run.verdict({**run.gold, "verdicts": verdicts})
    assert failed(found) == ["labels-exact", "observed-exact"] and found["score"] == 0.0
    assert [check["ok"] for check in found["details"]["constraints"]][:5] == [True] * 5


def test_every_constraint_entry_has_the_same_keys_and_is_json(tmp_path: Path) -> None:
    run = Run(tmp_path)
    found = run.verdict({**run.gold, "verdicts": run.verdicts(c03={"label": "not_found", "observed": None})})
    for check in found["details"]["constraints"]:
        assert list(check) == ["id", "constraint", "ok", "expected", "actual", "message"]
        assert check["ok"] in (True, False, None)
    json.dumps(found)


# Every tool call is checked too.
def test_verify_output_holds_each_tool_to_the_rules(tmp_path: Path) -> None:
    given = build_output({"game": "otters-wolves"}, FactCheckInput)
    assert verifier.verify_input("read_game", given)["valid"] and verifier.verify_input("pin_claims", given)["valid"]
    shown = build_output(plain_output(read_game(given, tmp_path)), GameOutput)
    assert verifier.verify_output("read_game", given, shown, str(tmp_path))["valid"] is True
    assert verifier.verify_task("read-game", given, shown, None, str(tmp_path))["valid"] is True
    bent = plain_output(shown)
    bent["claims"][0]["text"] = "Hugo Bastien scored at least 25 points."
    assert "not the receipt's" in verifier.verify_output("read_game", given, build_output(bent, GameOutput), str(tmp_path))["message"]
    assert "no readable receipt" in verifier.verify_output("read_game", given, shown, str(tmp_path / "elsewhere"))["message"]

    pinned = build_output(plain_output(pin_claims(given, tmp_path)), PinClaimsOutput)
    assert verifier.verify_output("pin_claims", given, pinned, str(tmp_path))["valid"] is True
    bent = plain_output(pinned)
    bent["claims"][0]["observed"] = 25
    assert verifier.verify_output("pin_claims", given, build_output(bent, PinClaimsOutput), str(tmp_path))["valid"] is False
