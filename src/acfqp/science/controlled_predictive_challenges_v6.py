"""Fixed structural 2048 challenges declared before V6 characterization.

These recipes specify competing merge geometry rather than search over random
boards. Their mechanism descriptions are hypotheses: neither query switches nor
successful tradeoffs are guaranteed by a recipe. Every declared board remains
in the discovery denominator, including public controls and unsuccessful cases.
"""

from __future__ import annotations

from dataclasses import dataclass

from .controlled_predictive_2048_v1 import PUBLIC_DEVELOPMENT_BOARDS


FAMILIES_V6 = ("crossing_rescue_pair", "spawn_edge_rescue", "crossed_vacancy_goal_detour")


@dataclass(frozen=True)
class V6Case:
    name: str
    group: str
    family: str
    variant: str
    board: tuple[int, ...]
    horizon: int = 3
    role: str = "MECHANISM_CHALLENGE"
    mechanism: str = ""


def _crossing_rescue_cases() -> tuple[V6Case, ...]:
    """A central large pair competes with two small vertical edge pairs."""
    settings = (
        (1, 2, 6, (9, 7, 5, 3, 4, 9, 3, 7)),
        (2, 1, 7, (6, 9, 3, 5, 9, 5, 8, 4)),
        (1, 3, 8, (7, 5, 9, 4, 5, 8, 4, 6)),
        (2, 3, 9, (5, 8, 3, 7, 9, 6, 7, 4)),
    )
    return tuple(V6Case(
        name=f"v6_crossing_rescue_pair_{index}",
        group=f"v6_crossing_rescue_pair_{index}", family="crossing_rescue_pair",
        variant=f"large_rank_{large}_edge_ranks_{left}_{right}",
        board=(left, large, large, right, left, 4, 6 if large == 8 else 8, right, *background),
        mechanism=(
            "A horizontal swipe takes the central large pair but shifts one of "
            "the two edge tiles away from its vertical rescue partner. A vertical "
            "swipe takes both small edge pairs, creates two vacancies, and shifts "
            "those columns relative to the central large pair. The reward gained "
            "and the surviving escape geometry can favor different continuations."
        ),
    ) for index, (left, right, large, background) in enumerate(settings))


def _spawn_edge_cases() -> tuple[V6Case, ...]:
    """An isolated merge frees opposite boundaries beside rank 1 or rank 2."""
    settings = (
        (6, 2, 1, (3, 6, 8, 9, 4, 8, 9, 5)),
        (7, 1, 2, (5, 8, 3, 9, 8, 3, 9, 4)),
        (8, 2, 1, (6, 3, 9, 5, 3, 9, 5, 8)),
        (9, 1, 2, (8, 5, 9, 3, 5, 9, 3, 6)),
    )
    return tuple(V6Case(
        name=f"v6_spawn_edge_rescue_{index}", group=f"v6_spawn_edge_rescue_{index}",
        family="spawn_edge_rescue", variant=f"large_rank_{large}_edge_ranks_{left}_{right}",
        board=(large, large, 5, 7, left, 4, 6, right, *background),
        mechanism=(
            "The only initial merge is the large top-row pair. LEFT frees the "
            "top-right boundary and RIGHT frees the top-left boundary; their "
            "vertical neighbors have different spawn ranks (1 versus 2). A "
            "matching spawn supplies an escape merge with rank-dependent payoff. "
            "Background ranks vary the subsequent continuation. This mechanism "
            "tests whether unequal escape probabilities actually create a "
            "reward/risk conflict rather than assuming that they do."
        ),
    ) for index, (large, left, right, background) in enumerate(settings))


def _goal_detour_cases() -> tuple[V6Case, ...]:
    """Opposite-side vacancies separate a central goal pair under either detour."""
    settings = (
        (4, (9, 7, 8, 5, 9, 6, 7, 3, 8, 5)),
        (6, (8, 9, 7, 4, 8, 5, 6, 2, 9, 3)),
        (8, (7, 6, 9, 3, 5, 7, 9, 4, 6, 2)),
        (9, (6, 8, 7, 2, 8, 4, 5, 3, 7, 6)),
    )
    cases = []
    for index, (detour, b) in enumerate(settings):
        board = (b[0], 0, detour, b[1],
                 10, 10, detour, b[2],
                 0, b[3], b[4], b[5],
                 b[6], b[7], b[8], b[9])
        cases.append(V6Case(
            name=f"v6_crossed_vacancy_goal_detour_{index}",
            group=f"v6_crossed_vacancy_goal_detour_{index}",
            family="crossed_vacancy_goal_detour", variant=f"detour_pair_rank_{detour}",
            board=board,
            mechanism=(
                "The middle-row 1024 pair can win immediately by a horizontal "
                "swipe. A separate vertical pair offers extra merge score. One "
                "vacancy lies above the right 1024 and another below the left "
                "1024, so either vertical detour moves the goal tiles to different "
                "rows. Recovering the goal then depends on subsequent moves and "
                "spawns. The four fixed detour ranks change the extra reward "
                "without preserving a trivially aligned goal pair."
            ),
        ))
    return tuple(cases)


def declared_cases_v6() -> tuple[V6Case, ...]:
    """Return all 12 mechanism roots and three exposed ordinary controls."""
    controls = tuple(V6Case(
        name=f"v6_control_{name}", group=f"v6_control_{name}",
        family="public_development_control", variant=name, board=board,
        role="EXPOSED_PUBLIC_CONTROL",
        mechanism="The unchanged V1 public board provides an exposed ordinary development control.",
    ) for name, board in PUBLIC_DEVELOPMENT_BOARDS.items())
    return (*_crossing_rescue_cases(), *_spawn_edge_cases(), *_goal_detour_cases(), *controls)
