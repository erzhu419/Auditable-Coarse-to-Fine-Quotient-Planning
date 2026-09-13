from __future__ import annotations

from collections import Counter

from acfqp.domains.standard_2048 import (
    Swipe2048Action as Action,
    Swipe2048Status,
    legal_actions_v1,
    state_from_board_v1,
    swipe_board_v1,
)
from acfqp.science.controlled_predictive_2048_v1 import PUBLIC_DEVELOPMENT_BOARDS
from acfqp.science.controlled_predictive_challenges_v6 import declared_cases_v6


def test_declared_roster_is_complete_and_supported() -> None:
    """A missing, duplicate, terminal, or malformed input would change the cohort."""
    cases = declared_cases_v6()
    assert cases == declared_cases_v6()
    assert len(cases) == len({case.name for case in cases}) == len({case.board for case in cases}) == 15
    assert Counter(case.family for case in cases) == {
        "crossing_rescue_pair": 4, "spawn_edge_rescue": 4,
        "crossed_vacancy_goal_detour": 4, "public_development_control": 3,
    }
    for case in cases:
        assert case.horizon == 3
        assert state_from_board_v1(case.board).status is Swipe2048Status.ACTIVE
        assert len(legal_actions_v1(case.board)) >= 2
    controls = [case for case in cases if case.role == "EXPOSED_PUBLIC_CONTROL"]
    assert {case.board for case in controls} == set(PUBLIC_DEVELOPMENT_BOARDS.values())


def test_crossing_recipe_really_displaces_a_rescue_partner() -> None:
    """A misplaced pair would remove the intended axis-dependent competition."""
    for case in declared_cases_v6():
        if case.family != "crossing_rescue_pair":
            continue
        board = case.board
        left, left_score, _ = swipe_board_v1(board, Action.LEFT)
        right, right_score, _ = swipe_board_v1(board, Action.RIGHT)
        vertical, vertical_score, _ = swipe_board_v1(board, Action.UP)
        assert left_score == right_score == 2 ** (board[1] + 1)
        assert vertical_score == 2 ** (board[0] + 1) + 2 ** (board[3] + 1)
        assert left[0] == left[4] and left[3] != left[7]
        assert right[0] != right[4] and right[3] == right[7]
        assert left.count(0) == right.count(0) == 1
        assert vertical.count(0) == 2


def test_spawn_recipe_frees_the_declared_opposite_boundaries() -> None:
    """Extra initial merges or a wrong boundary neighbor invalidate this recipe."""
    for case in declared_cases_v6():
        if case.family != "spawn_edge_rescue":
            continue
        board = case.board
        assert set(legal_actions_v1(board)) == {Action.LEFT, Action.RIGHT}
        left, left_score, _ = swipe_board_v1(board, Action.LEFT)
        right, right_score, _ = swipe_board_v1(board, Action.RIGHT)
        assert left.count(0) == right.count(0) == 1
        assert left[3] == right[0] == 0
        assert {left[7], right[4]} == {1, 2}
        assert left_score == right_score == 2 ** (board[0] + 1)


def test_vertical_goal_detours_separate_the_goal_tiles() -> None:
    """A detour preserving goal adjacency would be the previous trivial shortcut."""
    for case in declared_cases_v6():
        if case.family != "crossed_vacancy_goal_detour":
            continue
        for action in (Action.LEFT, Action.RIGHT):
            moved, score, _ = swipe_board_v1(case.board, action)
            assert 11 in moved and score >= 2048
        for action in (Action.UP, Action.DOWN):
            moved, score, _ = swipe_board_v1(case.board, action)
            # The rank-9 detour itself produces a third 1024 in column 2.
            # Track the two original goal tiles, which stay in columns 0 and 1.
            goal_rows = [index // 4 for index, rank in enumerate(moved)
                         if rank == 10 and index % 4 in (0, 1)]
            assert len(goal_rows) == len(set(goal_rows)) == 2
            assert score == 2 ** (case.board[2] + 1)
