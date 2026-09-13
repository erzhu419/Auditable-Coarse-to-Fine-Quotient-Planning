from __future__ import annotations

from collections import Counter, defaultdict

from acfqp.domains.standard_2048 import (
    Swipe2048Status,
    legal_actions_v1,
    state_from_board_v1,
)
from acfqp.science.controlled_predictive_2048_challenges_v2 import (
    FAMILIES,
    characterize_exact_case,
    generate_challenge_cases,
    generate_discovery_cases,
    generate_round2_discovery_cases,
)
from acfqp.science.controlled_predictive_2048_v1 import PUBLIC_DEVELOPMENT_BOARDS


def test_roster_retains_deterministic_sources_and_keeps_pairs_in_one_split() -> None:
    """Changing roster size or splitting spatial pairs would invalidate its unit."""
    cases = generate_challenge_cases()
    assert cases == generate_challenge_cases()
    assert len(cases) == len({case.name for case in cases}) == len({case.board for case in cases}) == 24
    assert Counter(case.split for case in cases) == {
        "TRAIN_DEVELOPMENT": 12, "CALIBRATION": 6, "EVALUATION": 6,
    }
    grouped = defaultdict(list)
    for case in cases:
        grouped[case.group].append(case)
    assert len(grouped) == 12
    for pair in grouped.values():
        assert len(pair) == 2
        assert len({(case.split, case.family, case.seed) for case in pair}) == 1
        assert {case.variant for case in pair} == {"identity", "rotate90"}
    assert {case.family for case in cases} == set(FAMILIES)
    discovery = generate_discovery_cases() + generate_round2_discovery_cases()
    assert len(discovery) == len({case.name for case in discovery}) == 36
    assert {case.split for case in discovery} == {"EXPOSED_GENERATOR_DISCOVERY"}
    assert {case.seed for case in cases}.isdisjoint(case.seed for case in discovery)
    assert {case.board for case in cases}.isdisjoint(case.board for case in discovery)
    assert {case.board for case in cases}.isdisjoint(PUBLIC_DEVELOPMENT_BOARDS.values())


def test_dense_source_boards_have_supported_actions_and_rotated_masks() -> None:
    """Invalid ranks, terminal roots, or the wrong spatial pairing break planning."""
    cases = generate_challenge_cases()
    pairs = defaultdict(dict)
    rotated_action = {"UP": "RIGHT", "RIGHT": "DOWN", "DOWN": "LEFT", "LEFT": "UP"}
    for case in cases:
        assert len(case.board) == 16 and all(1 <= rank <= 10 for rank in case.board)
        assert state_from_board_v1(case.board).status is Swipe2048Status.ACTIVE
        assert len(legal_actions_v1(case.board)) >= 2
        pairs[case.group][case.variant] = case
    for pair in pairs.values():
        source = pair["identity"].board
        assert pair["rotate90"].board == tuple(
            source[(3 - col) * 4 + row] for row in range(4) for col in range(4)
        )
        assert {action.value for action in legal_actions_v1(pair["rotate90"].board)} == {
            rotated_action[action.value] for action in legal_actions_v1(source)
        }


def test_exact_discovery_detects_delayed_switch_without_claiming_query_switch() -> None:
    """The characterized discovery fixture needs H3 while risk weights do not switch it."""
    case = next(case for case in generate_discovery_cases() if case.name == "discovery_cross_axis_pairs_830031")
    report = characterize_exact_case(case)
    assert report["split"] == "EXPOSED_GENERATOR_DISCOVERY"
    assert report["strict_horizon_switch_penalties"] == ["0.0", "0.05", "0.2", "1.0", "5.0"]
    assert report["horizons"]["3"]["strict_query_switch_pairs"] == []
    for penalty in report["strict_horizon_switch_penalties"]:
        assert set(report["horizons"]["1"]["queries"][penalty]["optimal_actions"]).isdisjoint(
            report["horizons"]["3"]["queries"][penalty]["optimal_actions"]
        )


def test_characterization_preserves_identity_on_complete_closure_budget_failure() -> None:
    """A reachable closure over budget must remain a reported candidate, not vanish."""
    case = generate_discovery_cases()[0]
    report = characterize_exact_case(case, max_nodes=1)
    assert report["name"] == case.name and report["board"] == list(case.board)
    assert {row["status"] for row in report["horizons"].values()} == {"BUDGET_EXCEEDED"}
    assert report["strict_horizon_switch_penalties"] == []
