"""Source identification and independent predictions on hand-board transfers."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.domains.standard_2048 import (
    Swipe2048Action, state_from_board_v1, step_v1, swipe_board_v1,
)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    ACTION_ORDER, LearnedDynamics, RuleIdentificationError, fit_rules,
)


LEDGER = dict(ground_afterstate_labels=0, ground_spawn_rows=0,
              ground_spawn_outcomes=0, fits=[], prediction_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = Path(__file__).resolve().parents[1] / "reports/controlled_predictive_relational_dynamics_v69.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="hand source and transfer boards only; no registered target roots", **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def observe(board, action):
    moved, score, changed = swipe_board_v1(board, Swipe2048Action(action))
    LEDGER["ground_afterstate_labels"] += 1
    outcomes = []
    if changed:
        ground = step_v1(state_from_board_v1(board), Swipe2048Action(action))
        LEDGER["ground_spawn_rows"] += 1
        LEDGER["ground_spawn_outcomes"] += len(ground)
        outcomes = [dict(board=list(o.next_state.board), score=o.merge_score,
                         probability=[o.probability.numerator, o.probability.denominator],
                         spawned_cell=o.spawned_cell, spawned_rank=o.spawned_rank)
                    for o in ground]
    return dict(board=list(board), action=action, afterstate=list(moved), score=score,
                changed=changed, outcomes=outcomes)


def fit(records):
    try:
        result = fit_rules(records)
    except RuleIdentificationError as error:
        LEDGER["fits"].append(dict(status="fit_failed", counts=error.counts))
        raise
    LEDGER["fits"].append(dict(status="identified", counts=result.fit_counts,
                             elapsed_seconds=result.fit_seconds))
    return result


@pytest.fixture(scope="module")
def learned():
    boards = [(3, 3, 4, 0) + (0,) * 12,
              (4, 0, 4, 0) + (0,) * 12,
              (5, 5, 5, 5) + (0,) * 12]
    records = [observe(board, action) for board in boards for action in ACTION_ORDER]
    return fit(records), records


def test_source_identification_transfers_rank_variables_and_all_action_directions(learned):
    rule, _ = learned
    assert rule.fit_counts["rewrite_candidates"] == 144
    assert rule.fit_counts["consistent_rewrite_candidates"] == 1
    assert rule.spawn_distribution == ((1, Fraction(9, 10)), (2, Fraction(1, 10)))
    assert rule.program.consumption == "once"
    boards = [(7, 7, 8, 0, 1, 0, 1, 2, 8, 8, 8, 8, 0, 2, 0, 2),
              (1, 2, 3, 4, 2, 3, 4, 5, 3, 4, 5, 6, 4, 5, 6, 6)]
    for board in boards:
        for action in ACTION_ORDER:
            observed = observe(board, action)
            assert rule.swipe(board, action, LEDGER["prediction_work"]) == (
                tuple(observed["afterstate"]), observed["score"], observed["changed"])
            if observed["changed"]:
                expected = {(tuple(o["board"]), Fraction(o["score"], 2048)):
                            Fraction(*o["probability"]) for o in observed["outcomes"]}
                predicted = {(board, reward): p for p, board, reward in
                             rule.successors_from_afterstate(observed["afterstate"],
                                                             observed["score"],
                                                             LEDGER["prediction_work"])}
                assert predicted == expected
    assert rule.classify((11,) + (0,) * 15)[0] == "WON"
    dead = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)
    assert rule.classify(dead)[0] == "LOST"


def test_spawn_probabilities_are_identified_from_observations_not_a_fixed_constant(learned):
    _, records = learned
    changed = deepcopy(records)
    for row in changed:
        cells = len({item["spawned_cell"] for item in row["outcomes"]})
        for item in row["outcomes"]:
            mass = Fraction(3, 4) if item["spawned_rank"] == 1 else Fraction(1, 4)
            p = mass / cells
            item["probability"] = [p.numerator, p.denominator]
    fitted = fit(changed)
    assert fitted.spawn_distribution == ((1, Fraction(3, 4)), (2, Fraction(1, 4)))
    recovered = LearnedDynamics.from_payload(json.loads(json.dumps(fitted.to_payload())))
    board = (8, 0, 8, 9) + (0,) * 12
    moved, score, _ = fitted.swipe(board, "LEFT")
    assert recovered.successors_from_afterstate(moved, score) == fitted.successors_from_afterstate(moved, score)
    assert "records" not in recovered.to_payload() and "board" not in recovered.to_payload()


def test_ambiguous_or_inconsistent_source_does_not_pick_a_program_by_order(learned):
    ambiguous = dict(board=[1] + [0] * 15, action="UP", afterstate=[1] + [0] * 15,
                     score=0, changed=False, outcomes=[])
    with pytest.raises(RuleIdentificationError, match="consistent programs") as error:
        fit([ambiguous])
    assert error.value.counts["consistent_rewrite_candidates"] > 1
    _, records = learned
    bad = deepcopy(records)
    bad[0]["score"] = 13
    with pytest.raises(RuleIdentificationError, match="0 consistent programs"):
        fit(bad)
