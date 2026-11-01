"""The check-claims verdict: 7 constraints, in order, judged against the labels re-derived from the pinned
box score and the claims' pinned meanings (never a stored answer alone)."""

from . import rules
from .checks import fail, hold, listed, plain, shown, skip, verdict
from .game import read_receipt
from .pin import key_problem

TEXT = {
    "answer-key": "The answer key is pinned for this task",
    "answer-key-data": "The pinned box score and claims are the bundled game and the pinned labels follow the rules on them",
    "task-echo": "The submission names the task's game",
    "agent-read": "read_game was called in this run for this game, on the pinned box score and claims",
    "claims-complete": "Every claim has exactly one verdict, in id order, and no other claim is judged",
    "labels-exact": "Each claim's label is what the box score gives",
    "observed-exact": "Each verdict's observed number is the box score's, and null exactly when the claim is not_found",
}
INTEGRITY = ("answer-key", "answer-key-data", "task-echo", "agent-read")  # a failure here scores 0


def why(claim):
    """Why the rules label ``claim`` (keyed) as they do, in a sentence."""
    subject = claim["subject"] if claim["subject_kind"] == "player" else f"the {claim['subject']}"
    if claim["label"] == "not_found":
        if claim["subject_kind"] == "team" and claim["stat"] != "points":
            return f"the box score gives a team's points only, not its {claim['stat']}"
        if claim["subject_kind"] == "team":
            return f"{claim['subject']} did not play this game"
        return f"{claim['subject']} did not appear in this game"
    comparison = "is" if claim["label"] == "supported" else "is not"
    return f"{subject} {rules.VERB[claim['stat']]} {claim['observed']} {claim['stat']}, which {comparison} {rules.PHRASE[claim['comparator']]} {claim['value']}"


def verify_task(arguments, output, reference, workspace):
    checks = []
    task, given = plain(arguments), plain(output)
    pin = None if reference is None else plain(reference)

    # 1 answer-key
    if pin is None:
        fail(checks, "answer-key", TEXT["answer-key"], "No answer key: pin_claims was not run for this task.", expected=task["game"])
    elif pin["game"] != task["game"]:
        fail(checks, "answer-key", TEXT["answer-key"], f"The answer key is for {pin['game']!r}, not {task['game']!r}.", expected=task["game"], actual=pin["game"])
    else:
        hold(checks, "answer-key", TEXT["answer-key"], expected=task["game"], actual=pin["game"])
    if not checks[-1]["ok"]:
        for name in list(TEXT)[1:]:
            skip(checks, name, TEXT[name], "answer-key")
        return verdict(checks, 0.0, "", expected=None, right=0)

    # 2 answer-key-data
    problem = key_problem(pin)
    if problem:
        fail(checks, "answer-key-data", TEXT["answer-key-data"], f"{problem[0].upper()}{problem[1:]}.", expected=pin["data_sha256"])
        for name in list(TEXT)[2:]:
            skip(checks, name, TEXT[name], "answer-key-data")
        return verdict(checks, 0.0, "", expected=None, right=0)
    hold(checks, "answer-key-data", TEXT["answer-key-data"], expected=pin["data_sha256"], actual=pin["data_sha256"])

    expected = rules.keyed(pin["box_score"], [rules.unlabelled(claim) for claim in pin["claims"]])
    by_id = {claim["id"]: claim for claim in expected}
    ids = [claim["id"] for claim in expected]

    # 3 task-echo
    if given["game"] != task["game"]:
        fail(checks, "task-echo", TEXT["task-echo"], f"The submission is for {given['game']!r}, not the task's {task['game']!r}.", expected=task["game"], actual=given["game"])
    else:
        hold(checks, "task-echo", TEXT["task-echo"], expected=task["game"], actual=given["game"])

    # 4 agent-read
    receipt, problem = read_receipt(workspace, task["game"])
    shown_claims = [{"id": claim["id"], "text": claim["text"]} for claim in expected]
    if problem:
        fail(checks, "agent-read", TEXT["agent-read"], f"{problem[0].upper()}{problem[1:]}.", expected=pin["data_sha256"])
    elif receipt["data_sha256"] != pin["data_sha256"] or receipt["box_score"] != pin["box_score"] or receipt["claims"] != shown_claims:
        fail(checks, "agent-read", TEXT["agent-read"], "The game read_game read is not the pinned game.", expected=pin["data_sha256"], actual=receipt["data_sha256"])
    elif receipt["written_at"] < pin["pinned_at"]:
        fail(
            checks,
            "agent-read",
            TEXT["agent-read"],
            f"The receipt was written at {receipt['written_at']}, before the answer key was pinned at {pin['pinned_at']}: it is left over "
            "from an earlier run. Call read_game in this run.",
            expected=pin["pinned_at"],
            actual=receipt["written_at"],
        )
    else:
        hold(checks, "agent-read", TEXT["agent-read"], expected=pin["data_sha256"], actual=receipt["data_sha256"])

    # 5 claims-complete
    judged = [entry["claim"] for entry in given["verdicts"]]
    unknown = sorted({name for name in judged if name not in by_id})
    twice = sorted({name for name in judged if judged.count(name) > 1})
    missing = [name for name in ids if name not in judged]
    if unknown or twice or missing or judged != ids:
        problems = []
        if unknown:
            problems.append(f"{listed(unknown)} {'is' if len(unknown) == 1 else 'are'} not among the claims (ids are c01, c02, ...)")
        if twice:
            problems.append(f"{listed(twice)} {'is' if len(twice) == 1 else 'are'} judged more than once")
        if missing:
            problems.append(f"{listed(missing)} {'has' if len(missing) == 1 else 'have'} no verdict")
        if not problems:
            problems.append("the verdicts are not in claim id order")
        fail(checks, "claims-complete", TEXT["claims-complete"], "The verdicts are malformed: " + "; ".join(problems) + ".", expected=ids, actual=shown(judged))
        for name in list(TEXT)[5:]:
            skip(checks, name, TEXT[name], "claims-complete")
        return verdict(checks, 0.0, "", expected=[(claim["id"], claim["label"], claim["observed"]) for claim in expected], right=0)
    hold(checks, "claims-complete", TEXT["claims-complete"], expected=ids, actual=judged)

    # 6 labels-exact
    wrong = [entry for entry in given["verdicts"] if entry["label"] != by_id[entry["claim"]]["label"]]
    if wrong:
        first, right = wrong[0], by_id[wrong[0]["claim"]]
        fail(
            checks,
            "labels-exact",
            TEXT["labels-exact"],
            f"{first['claim']} ({right['text']}) is labelled {first['label']}, but it is {right['label']}: {why(right)}."
            + (f" Also wrong: {listed(entry['claim'] for entry in wrong[1:])}." if len(wrong) > 1 else ""),
            expected=[f"{claim['id']}={claim['label']}" for claim in expected],
            actual=[f"{entry['claim']}={entry['label']}" for entry in given["verdicts"]],
        )
    else:
        hold(checks, "labels-exact", TEXT["labels-exact"], expected=[f"{claim['id']}={claim['label']}" for claim in expected], actual=[f"{entry['claim']}={entry['label']}" for entry in given["verdicts"]])

    # 7 observed-exact
    wrong = [entry for entry in given["verdicts"] if entry["observed"] != by_id[entry["claim"]]["observed"]]
    if wrong:
        first, right = wrong[0], by_id[wrong[0]["claim"]]
        if right["observed"] is None:
            reason = "the claim is not_found, so observed must be null"
        else:
            reason = f"the box score gives {right['observed']} {right['stat']} for {right['subject']}"
        fail(
            checks,
            "observed-exact",
            TEXT["observed-exact"],
            f"{first['claim']}'s observed number is given as {first['observed']}, but {reason}." + (f" Also wrong: {listed(entry['claim'] for entry in wrong[1:])}." if len(wrong) > 1 else ""),
            expected=[f"{claim['id']}={claim['observed']}" for claim in expected],
            actual=[f"{entry['claim']}={entry['observed']}" for entry in given["verdicts"]],
        )
    else:
        hold(checks, "observed-exact", TEXT["observed-exact"], expected=[f"{claim['id']}={claim['observed']}" for claim in expected], actual=[f"{entry['claim']}={entry['observed']}" for entry in given["verdicts"]])

    # The score: 0 when the data or the submission's integrity fails; otherwise the share of claims judged exactly right.
    right_count = sum((entry["label"], entry["observed"]) == (by_id[entry["claim"]]["label"], by_id[entry["claim"]]["observed"]) for entry in given["verdicts"])
    score = 0.0 if any(check["ok"] is False for check in checks if check["id"] in INTEGRITY) else right_count / len(expected)
    counts = {label: sum(claim["label"] == label for claim in expected) for label in rules.LABELS}
    summary = f"of the {len(expected)} claims about {task['game']}, {counts['supported']} are supported, {counts['contradicted']} contradicted and {counts['not_found']} not found."
    return verdict(checks, score, summary, expected=[(claim["id"], claim["label"], claim["observed"]) for claim in expected], right=right_count)
