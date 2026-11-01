"""The tools: the answer key (pin_claims) and the game the agent checks (read_game), each a function of the
bundled data and the rules."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from contract import (
    BoxScore,
    Claim,
    ClaimKey,
    ClaimVerdict,
    Comparator,
    FactCheckInput,
    FactCheckOutput,
    GameOutput,
    Label,
    PinClaimsOutput,
    PlayerLine,
    Stat,
    SubjectKind,
)
from plugin import rules
from plugin.data import GAMES


def game(name: str) -> tuple[dict, list[dict]]:
    """The bundled game ``name``: its box score and its claims with their texts, checked against the recorded hash."""
    box_score = {**GAMES[name]["box_score"], "players": [dict(line) for line in GAMES[name]["box_score"]["players"]]}
    claims = [{**claim, "text": rules.render(claim)} for claim in GAMES[name]["claims"]]
    problem = rules.data_problem(name, box_score, claims)
    if problem:
        raise ValueError(f"game {name}: {problem}")
    return box_score, claims


def receipt_path(workspace: Path, name: str) -> Path:
    return workspace / rules.RECEIPTS / f"{name}.json"


def now() -> str:
    """The clock, a UTC time YYYY-MM-DDTHH:MM:SSZ: the answer key records when it was pinned and a receipt when it was
    written, so the verifier can tell a receipt of this run from one an earlier run left in the workspace."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def as_box_score(box_score: dict) -> BoxScore:
    return BoxScore(**{**box_score, "players": [PlayerLine(**line) for line in box_score["players"]]})


def read_game(given: FactCheckInput, workspace: Path) -> GameOutput:
    """The box score and the claims' texts, with a receipt of what it read under the workspace."""
    box_score, claims = game(given.game.value)
    digest = rules.sha256({"box_score": box_score, "claims": claims})
    shown = [{"id": claim["id"], "text": claim["text"]} for claim in claims]
    receipt = {"game": given.game.value, "data_sha256": digest, "box_score": box_score, "claims": shown, "written_at": now()}
    path = receipt_path(workspace, given.game.value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rules.canonical(receipt) + "\n", encoding="utf-8")
    return GameOutput(game=given.game, data_sha256=digest, box_score=as_box_score(box_score), claims=[Claim(**claim) for claim in shown])


def pin_claims(given: FactCheckInput, workspace: Path) -> PinClaimsOutput:
    """The answer key: the box score and every claim's meaning with the label the rules give."""
    box_score, claims = game(given.game.value)
    return PinClaimsOutput(
        game=given.game,
        pinned_at=now(),
        data_sha256=rules.sha256({"box_score": box_score, "claims": claims}),
        box_score=as_box_score(box_score),
        claims=[
            ClaimKey(
                **{
                    **claim,
                    "subject_kind": SubjectKind(claim["subject_kind"]),
                    "stat": Stat(claim["stat"]),
                    "comparator": Comparator(claim["comparator"]),
                    "label": Label(claim["label"]),
                }
            )
            for claim in rules.keyed(box_score, claims)
        ],
    )


def expected_output(given: FactCheckInput) -> FactCheckOutput:
    """What a correct check-claims submission is: the rules applied to the game (used by tests)."""
    pinned = pin_claims(given, Path("."))
    return FactCheckOutput(game=pinned.game, verdicts=[ClaimVerdict(claim=claim.id, label=claim.label, observed=claim.observed) for claim in pinned.claims])
