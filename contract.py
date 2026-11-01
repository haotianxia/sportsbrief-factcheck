"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    PIN_CLAIMS = "pin_claims"
    READ_GAME = "read_game"


class Task(Enum):
    CHECK_CLAIMS = "check-claims"
    READ_GAME = "read-game"


class Game(Enum):
    LYNX_HERONS = "lynx-herons"
    FOXES_BISON = "foxes-bison"
    OTTERS_WOLVES = "otters-wolves"


class Stat(Enum):
    POINTS = "points"
    REBOUNDS = "rebounds"
    ASSISTS = "assists"
    MINUTES = "minutes"


class Comparator(Enum):
    AT_LEAST = "at_least"
    MORE_THAN = "more_than"
    EXACTLY = "exactly"
    AT_MOST = "at_most"
    FEWER_THAN = "fewer_than"


class SubjectKind(Enum):
    PLAYER = "player"
    TEAM = "team"


class Label(Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NOT_FOUND = "not_found"


GAME = "One of the bundled games: lynx-herons, foxes-bison or otters-wolves"
CLAIM_ID = "A claim's id as the game lists it, e.g. c04"
OBSERVED = "The number the box score gives for the claim's subject and stat; null when the claim is not_found"


@dataclass
class FactCheckInput(Output):
    game: Annotated[Game, GAME]


@dataclass
class PlayerLine(Output):
    player: Annotated[str, "The player's name as the box score spells it"]
    team: Annotated[str, "The player's team"]
    minutes: Annotated[int, "Minutes played"]
    points: Annotated[int, "Points scored"]
    rebounds: Annotated[int, "Rebounds"]
    assists: Annotated[int, "Assists"]


@dataclass
class BoxScore(Output):
    home_team: Annotated[str, "The home team"]
    away_team: Annotated[str, "The away team"]
    home_score: Annotated[int, "The home team's points: its players' points added up"]
    away_score: Annotated[int, "The away team's points: its players' points added up"]
    players: Annotated[list[PlayerLine], "Every player who appeared, home team first"]


@dataclass
class Claim(Output):
    id: Annotated[str, CLAIM_ID]
    text: Annotated[str, "The claim, one sentence about a player's or a team's number in this game"]


@dataclass
class GameOutput(Output):
    game: Annotated[Game, GAME]
    data_sha256: Annotated[str, "sha256 of the game's bundled data, canonical JSON"]
    box_score: Annotated[BoxScore, "The game's box score"]
    claims: Annotated[list[Claim], "The claims to check, in id order"]


@dataclass
class ClaimKey(Output):
    id: Annotated[str, CLAIM_ID]
    text: Annotated[str, "The claim as the agent reads it"]
    subject_kind: Annotated[SubjectKind, "Whether the claim is about a player or a team"]
    subject: Annotated[str, "The player's or team's name"]
    stat: Annotated[Stat, "The stat the claim is about"]
    comparator: Annotated[Comparator, "How the claim compares the stat with its number"]
    value: Annotated[int, "The claim's number"]
    label: Annotated[Label, "The label the rules give"]
    observed: Annotated[int | None, OBSERVED]


@dataclass
class PinClaimsOutput(Output):
    game: Annotated[Game, GAME]
    pinned_at: Annotated[str, "When the answer key was pinned, a UTC time YYYY-MM-DDTHH:MM:SSZ: a receipt written earlier is another run's"]
    data_sha256: Annotated[str, "sha256 of the game's bundled data, canonical JSON"]
    box_score: Annotated[BoxScore, "The game's box score"]
    claims: Annotated[list[ClaimKey], "Every claim with its meaning and the label the rules give, in id order"]


@dataclass
class ClaimVerdict(Output):
    claim: Annotated[str, CLAIM_ID]
    label: Annotated[
        Label,
        "supported: the number the box score gives satisfies the claim's comparison; contradicted: the box score gives a number but it "
        "does not satisfy the comparison (a number equal to N fails 'more than N' and 'fewer than N'); not_found: the claim's player "
        "did not appear in this game, its team did not play it, or its stat is not one the box score gives for a team",
    ]
    observed: Annotated[int | None, OBSERVED]


@dataclass
class FactCheckOutput(Output):
    game: Annotated[Game, "The task's game, as given"]
    verdicts: Annotated[list[ClaimVerdict], "One verdict per claim, in id order"]


TOOLS = {
    Tool.PIN_CLAIMS: (FactCheckInput, PinClaimsOutput),
    Tool.READ_GAME: (FactCheckInput, GameOutput),
}
TASKS = {
    Task.CHECK_CLAIMS: (FactCheckInput, FactCheckOutput),
    Task.READ_GAME: (FactCheckInput, GameOutput),
}
