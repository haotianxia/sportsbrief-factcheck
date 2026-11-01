"""read_game, and the read-game task: the box score and claims are the bundled game's, with a receipt."""

from pathlib import Path

from . import rules
from .checks import plain, read_json, result

RECEIPT_KEYS = ("game", "data_sha256", "box_score", "claims", "written_at")
LINE_KEYS = ("assists", "minutes", "player", "points", "rebounds", "team")


def receipt_path(workspace, game):
    return Path(workspace) / rules.RECEIPTS / f"{game}.json"


def shaped(receipt):
    """Whether ``receipt`` has the shape read_game writes: a box score and claims of id and text."""
    if not isinstance(receipt, dict) or sorted(receipt) != sorted(RECEIPT_KEYS):
        return False
    box_score, claims = receipt["box_score"], receipt["claims"]
    if not isinstance(box_score, dict) or sorted(box_score) != ["away_score", "away_team", "home_score", "home_team", "players"]:
        return False
    if not all(isinstance(box_score[key], str) for key in ("home_team", "away_team")):
        return False
    if not all(isinstance(box_score[key], int) and not isinstance(box_score[key], bool) for key in ("home_score", "away_score")):
        return False
    if not isinstance(box_score["players"], list) or not all(
        isinstance(line, dict)
        and tuple(sorted(line)) == LINE_KEYS
        and isinstance(line["player"], str)
        and isinstance(line["team"], str)
        and all(isinstance(line[key], int) and not isinstance(line[key], bool) for key in ("minutes", "points", "rebounds", "assists"))
        for line in box_score["players"]
    ):
        return False
    return isinstance(claims, list) and all(
        isinstance(claim, dict) and sorted(claim) == ["id", "text"] and isinstance(claim["id"], str) and isinstance(claim["text"], str) for claim in claims
    )


def receipt_problem(receipt, game):
    """What is wrong with ``receipt`` as read_game's record of reading ``game``, or None. The receipt holds
    the claims' texts only, so it is held to the bundled hash through the answer key (verify_task) and to
    its own shape and box score here."""
    if not shaped(receipt):
        return "the receipt does not hold a game, its data_sha256, a box score, claims of id and text, and written_at"
    if receipt["game"] != game:
        return f"the receipt is for {receipt['game']!r}"
    problem = rules.stamp_problem(receipt["written_at"])
    if problem:
        return f"the receipt's written_at is not a UTC time: {problem}"
    problem = rules.box_problem(receipt["box_score"])
    if problem:
        return f"the receipt's box score is malformed: {problem}"
    if [claim["id"] for claim in receipt["claims"]] != [f"c{index:02d}" for index in range(1, len(receipt["claims"]) + 1)] or not receipt["claims"]:
        return "the receipt's claims are not numbered c01, c02, ... in order"
    return None


def read_receipt(workspace, game):
    """``(receipt, problem)``: the receipt read_game wrote for the game, or why there is none."""
    path = receipt_path(workspace, game)
    receipt = read_json(path)
    if receipt is None:
        return None, f"no readable receipt at {rules.RECEIPTS}/{path.name}: read_game was not called for this game"
    problem = receipt_problem(receipt, game)
    if problem:
        return None, f"the receipt {rules.RECEIPTS}/{path.name} was altered after read_game: {problem}"
    return receipt, None


def output_problem(given, made, workspace):
    if made["game"] != given["game"]:
        return f"the game read is {made['game']!r}, not the requested {given['game']!r}"
    receipt, problem = read_receipt(workspace, given["game"])
    if problem:
        return problem
    if made["data_sha256"] != receipt["data_sha256"] or made["box_score"] != receipt["box_score"] or made["claims"] != receipt["claims"]:
        return "the box score and claims given are not the receipt's"
    if made["data_sha256"] != rules.DATA_SHA256[made["game"]]:
        return "data_sha256 is not the bundled game's"
    return None


def verify_input(value):
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    problem = output_problem(plain(input_value), plain(output_value), workspace)
    if problem:
        return result(False, problem)
    return result(True, "the game is the bundled one", claims=len(output_value.claims))


def verify_task(arguments, output, reference, workspace):
    problem = output_problem(plain(arguments), plain(output), workspace)
    if problem:
        return result(False, problem)
    return result(True, f"the box score and {len(output.claims)} claims of {output.game.value} are listed, unchanged", claims=len(output.claims))
