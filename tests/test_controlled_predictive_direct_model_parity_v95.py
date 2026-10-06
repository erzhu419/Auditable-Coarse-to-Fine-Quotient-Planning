"""Bounded model/ground parity, including the spawn after a winning swipe."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science import controlled_predictive_decision_experience_v78 as experience
from acfqp.science.controlled_predictive_direct_value_v95 import DirectSelector
from acfqp.science.controlled_predictive_fragment_experience_v83 import _controller_record
from acfqp.science.controlled_predictive_fragments_v83 import FragmentController, OPTIONS
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics


ROOT = Path(__file__).resolve().parents[1]
STEP_FIELDS = ("board", "action", "afterstate", "next_board", "score", "status")


class FixedValue:
    checkpoint = 12

    def __init__(self):
        self.calls = 0

    def predict(self, board, query, work=None):
        self.calls += 1
        if work is not None:
            work["continuation_predictions"] = work.get("continuation_predictions", 0) + 1
        return [1.0, 0.75, 0.25]


@pytest.fixture(scope="module")
def parity_records(request):
    ledger = dict(test_module=__file__, tree_fits=0, main_campaign_calls=0,
        selector_forbidden_ground_calls=0, selector_work=Counter(),
        reference_ground_work=Counter(), reference_planning_work=Counter(),
        observed_reference_calls=Counter(), cases=[],
        scope="Two active boards, five options, one replica, at most four actions; fixed fake tail values.")
    initial_failures = request.session.testsfailed

    def retain():
        path = ROOT / "reports/controlled_predictive_direct_model_parity_v95.checks.json"
        payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
        ledger["test_failures"] = request.session.testsfailed - initial_failures
        payload["attempts"].append(ledger)
        path.write_text(json.dumps(payload, indent=2) + "\n")

    request.addfinalizer(retain)
    dynamics_path = ROOT / "reports/controlled_predictive_bellman_v94/supplied_dynamics.json"
    ledger["inherited_dynamics_path"] = str(dynamics_path)
    rule = LearnedDynamics.from_payload(json.loads(dynamics_path.read_text()))
    records = []
    cases = (
        ("nonterminal", "reward", [1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0]),
        ("winning_swipe", "risk_goal", [10, 10] + [0] * 14),
    )

    def forbidden(*args, **kwargs):
        ledger["selector_forbidden_ground_calls"] += 1
        raise AssertionError("DirectSelector used a ground environment function")

    ground_swipe, ground_status, real_spawn = (
        ground.swipe_board_v1, ground.state_from_board_v1, experience._spawn)

    def counted_swipe(*args, **kwargs):
        ledger["observed_reference_calls"]["ground_swipe_calls"] += 1
        return ground_swipe(*args, **kwargs)

    def counted_status(*args, **kwargs):
        ledger["observed_reference_calls"]["ground_state_status_calls"] += 1
        return ground_status(*args, **kwargs)

    def counted_spawn(*args, **kwargs):
        ledger["observed_reference_calls"]["sampled_transitions"] += 1
        return real_spawn(*args, **kwargs)

    for index, (name, query, board) in enumerate(cases):
        value, work = FixedValue(), Counter()
        selector = DirectSelector(value, rule, 95_990_000_000 + index * 100, replicas=1)
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(ground, "swipe_board_v1", forbidden)
            patch.setattr(ground, "state_from_board_v1", forbidden)
            selector.select(board, query, work=work)
        ledger["selector_work"].update(work)
        prefixes = deepcopy(selector.last_prefixes)
        ledger["cases"].append(dict(name=name, query=query, board=board,
            prefixes=len(prefixes), value_predictions=value.calls))
        for prefix in prefixes:
            controller = FragmentController(None, query, rule,
                random.Random(prefix["planning_seed"]), immediate=True, fixed_option=prefix["option"])
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(ground, "swipe_board_v1", counted_swipe)
                patch.setattr(ground, "state_from_board_v1", counted_status)
                patch.setattr(experience, "_spawn", counted_spawn)
                game = experience.rollout_from_board(tuple(board), prefix["spawn_seed"],
                    controller.choose, max_steps=4)
            ledger["reference_ground_work"].update(game["work"])
            ledger["reference_planning_work"].update(controller.work)
            records.append(dict(case=name, prefix=prefix, game=game,
                controller=_controller_record(controller), planning_counts=dict(controller.work)))
    return records, ledger


def test_model_prefix_matches_real_controller_and_spawn_stream(parity_records):
    records, ledger = parity_records
    for case in ledger["cases"]:
        selected = [row for row in records if row["case"] == case["name"]]
        assert [row["prefix"]["option"] for row in selected] == list(OPTIONS)
    for row in records:
        prefix, game = row["prefix"], row["game"]
        assert prefix["replica"] == 0
        assert prefix["planning_seed"] == prefix["spawn_seed"] + 1_000_000_000_000
        for field in ("initial_board", "final_board", "return_score", "steps_count"):
            assert prefix[field] == game[field], (row["case"], prefix["option"], field)
        assert prefix["status"] == ("ACTIVE" if game["status"] == "CUTOFF" else game["status"])
        assert prefix["steps"] == [{field: step[field] for field in STEP_FIELDS} for step in game["steps"]]
        assert prefix["controller"] == row["controller"]
        assert prefix["planning_counts"] == row["planning_counts"]
        assert row["planning_counts"]["model_uniform_draws"] == 4 * game["steps_count"]


def test_winning_swipe_spawns_then_absorbs_without_tail_double_count(parity_records):
    records, ledger = parity_records
    winning = [row["prefix"] for row in records if row["prefix"]["status"] == "WON"]
    active = [row["prefix"] for row in records if row["prefix"]["status"] == "ACTIVE"]
    assert winning and active
    for prefix in winning:
        last = prefix["steps"][-1]
        assert max(last["afterstate"]) == max(last["next_board"]) == 11
        assert last["next_board"].count(0) == last["afterstate"].count(0) - 1
        assert prefix["direct"] == [prefix["return_score"] / 2048, 0.0, 1.0]
        assert prefix["tail"] == [0.0, 0.0, 0.0]
        assert prefix["completed"] == prefix["direct"]
    for prefix in active:
        assert prefix["steps_count"] == 4
        assert prefix["direct"] == [prefix["return_score"] / 2048, 0.0, 0.0]
        assert prefix["tail"] == [1.0, 0.75, 0.25]
        assert prefix["completed"] == [prefix["direct"][0] + 1.0, 0.75, 0.25]
    assert sum(case["value_predictions"] for case in ledger["cases"]) == len(active)


def test_selector_uses_no_ground_calls_and_reference_costs_are_charged(parity_records):
    records, ledger = parity_records
    assert ledger["selector_forbidden_ground_calls"] == 0
    assert ledger["tree_fits"] == ledger["main_campaign_calls"] == 0
    for name, count in ledger["observed_reference_calls"].items():
        assert ledger["reference_ground_work"][name] == count
    transitions = sum(row["game"]["steps_count"] for row in records)
    assert 0 < transitions <= 40
    assert ledger["reference_ground_work"]["sampled_transitions"] == transitions
    assert ledger["reference_ground_work"]["environment_random_draws"] == 2 * transitions
    assert ledger["reference_planning_work"]["model_uniform_draws"] == 4 * transitions
