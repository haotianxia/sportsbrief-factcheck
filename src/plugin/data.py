"""The bundled games of the Gulf Coast Basketball League, an invented league: every team, player and
number is made up. Each game has a box score whose team scores are its players' points added up, and
ten claims about it. A claim's text is rendered from its meaning by the rules' one template, so the
answer key's meaning is exactly what the agent reads. The claims hit the boundaries on purpose: a
number equal to the stat under at_least, more_than, at_most, fewer_than and exactly; a player from
another game; a team stat the box score does not give."""


def line(player, team, minutes, points, rebounds, assists):
    return {"player": player, "team": team, "minutes": minutes, "points": points, "rebounds": rebounds, "assists": assists}


def claim(number, kind, subject, stat, comparator, value):
    return {"id": f"c{number:02d}", "subject_kind": kind, "subject": subject, "stat": stat, "comparator": comparator, "value": value}


LYNX, HER, FOX, BIS, OTT, WOLF = "Harbor Lynx", "Bayou Herons", "Summit Foxes", "Prairie Bison", "Delta Otters", "Ridge Wolves"

GAMES = {
    "lynx-herons": {
        "box_score": {
            "home_team": LYNX,
            "away_team": HER,
            "home_score": 104,
            "away_score": 97,
            "players": [
                line("Mara Okafor", LYNX, 36, 31, 9, 4),
                line("Elias Tanaka", LYNX, 34, 22, 5, 7),
                line("Sam Oduya", LYNX, 30, 18, 11, 2),
                line("Jonah Reyes", LYNX, 28, 14, 3, 6),
                line("Kira Holmgren", LYNX, 25, 19, 7, 1),
                line("Theo Abara", HER, 35, 27, 6, 3),
                line("Nikolai Oyelaran", HER, 33, 20, 12, 2),
                line("Celeste Varga", HER, 31, 16, 4, 8),
                line("Imani Laurent", HER, 27, 18, 5, 1),
                line("Ruben Castillo", HER, 22, 16, 8, 2),
            ],
        },
        "claims": [
            claim(1, "player", "Mara Okafor", "points", "at_least", 31),
            claim(2, "player", "Mara Okafor", "points", "more_than", 31),
            claim(3, "player", "Elias Tanaka", "assists", "exactly", 7),
            claim(4, "player", "Sam Oduya", "rebounds", "at_most", 10),
            claim(5, "team", HER, "points", "fewer_than", 100),
            claim(6, "player", "Theo Abara", "minutes", "more_than", 30),
            claim(7, "player", "Rosa Quintero", "points", "at_least", 10),
            claim(8, "player", "Nikolai Oyelaran", "rebounds", "exactly", 11),
            claim(9, "team", LYNX, "points", "exactly", 104),
            claim(10, "player", "Kira Holmgren", "assists", "fewer_than", 2),
        ],
    },
    "foxes-bison": {
        "box_score": {
            "home_team": FOX,
            "away_team": BIS,
            "home_score": 88,
            "away_score": 80,
            "players": [
                line("Teo Lindqvist", FOX, 37, 24, 5, 6),
                line("Ada Mensah", FOX, 32, 17, 9, 3),
                line("Felix Oyinlola", FOX, 29, 15, 7, 2),
                line("Hana Sato", FOX, 30, 20, 4, 5),
                line("Marcus Delgado", FOX, 24, 12, 10, 1),
                line("Jalen Petrov", BIS, 36, 19, 6, 4),
                line("Luca Marsh", BIS, 30, 14, 3, 7),
                line("Owen Takahashi", BIS, 28, 16, 9, 2),
                line("Zara Hollis", BIS, 26, 13, 8, 3),
                line("Nico Fontaine", BIS, 22, 18, 5, 1),
            ],
        },
        "claims": [
            claim(1, "player", "Teo Lindqvist", "points", "more_than", 20),
            claim(2, "player", "Teo Lindqvist", "assists", "at_least", 7),
            claim(3, "player", "Marcus Delgado", "rebounds", "exactly", 10),
            claim(4, "team", BIS, "points", "at_least", 80),
            claim(5, "team", BIS, "points", "more_than", 80),
            claim(6, "player", "Luca Marsh", "minutes", "fewer_than", 30),
            claim(7, "player", "Mara Okafor", "points", "at_least", 20),
            claim(8, "player", "Nico Fontaine", "points", "at_most", 18),
            claim(9, "player", "Hana Sato", "minutes", "exactly", 30),
            claim(10, "team", FOX, "rebounds", "at_least", 30),
        ],
    },
    "otters-wolves": {
        "box_score": {
            "home_team": OTT,
            "away_team": WOLF,
            "home_score": 101,
            "away_score": 95,
            "players": [
                line("Rosa Quintero", OTT, 34, 22, 4, 7),
                line("Priya Castellanos", OTT, 31, 18, 6, 3),
                line("Dario Lenz", OTT, 29, 21, 8, 2),
                line("Amara Ekwueme", OTT, 27, 16, 12, 1),
                line("Hugo Bastien", OTT, 30, 24, 5, 4),
                line("Dmitri Achebe", WOLF, 33, 20, 13, 1),
                line("Tomas Ilunga", WOLF, 35, 23, 4, 6),
                line("Beatriz Faria", WOLF, 28, 17, 6, 5),
                line("Kwame Asante", WOLF, 26, 19, 7, 2),
                line("Lior Haddad", WOLF, 24, 16, 9, 3),
            ],
        },
        "claims": [
            claim(1, "player", "Hugo Bastien", "points", "at_least", 24),
            claim(2, "player", "Dmitri Achebe", "rebounds", "more_than", 12),
            claim(3, "player", "Rosa Quintero", "assists", "at_most", 6),
            claim(4, "player", "Amara Ekwueme", "rebounds", "exactly", 12),
            claim(5, "team", WOLF, "points", "fewer_than", 95),
            claim(6, "player", "Tomas Ilunga", "minutes", "more_than", 34),
            claim(7, "player", "Teo Lindqvist", "points", "more_than", 20),
            claim(8, "player", "Priya Castellanos", "points", "exactly", 18),
            claim(9, "team", OTT, "points", "at_most", 100),
            claim(10, "player", "Lior Haddad", "assists", "at_least", 4),
        ],
    },
}
