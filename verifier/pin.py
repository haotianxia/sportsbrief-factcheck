"""pin_claims, the check-claims reference: its answer key is the bundled game with the labels the rules give."""

from . import rules
from .checks import plain, result


def key_problem(pin):
    """What is wrong with the plain answer key ``pin``, or None: its box score and claims are the bundled
    game's, every claim's text says what its meaning says, and its labels are what the rules give."""
    problem = rules.stamp_problem(pin["pinned_at"])
    if problem:
        return f"the pinned time is not a UTC time: {problem}"
    claims = [rules.unlabelled(claim) for claim in pin["claims"]]
    problem = rules.data_problem(pin["game"], pin["box_score"], claims)
    if problem:
        return f"the pinned data is not the bundled {pin['game']}: {problem}"
    if pin["data_sha256"] != rules.sha256({"box_score": pin["box_score"], "claims": claims}):
        return "the pinned data does not match its own sha256"
    if pin["claims"] != rules.keyed(pin["box_score"], claims):
        return "the pinned labels are not what the rules give on the pinned box score"
    return None


def verify_input(value):
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    given, pin = plain(input_value), plain(output_value)
    if pin["game"] != given["game"]:
        return result(False, f"the answer key is for {pin['game']!r}, not the task's {given['game']!r}")
    problem = key_problem(pin)
    if problem:
        return result(False, problem)
    return result(True, "the answer key follows the rules", claims=len(pin["claims"]))
