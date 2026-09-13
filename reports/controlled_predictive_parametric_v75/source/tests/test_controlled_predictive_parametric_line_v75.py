"""Small exact-rank binding checks against the frozen learned line program."""
from collections import Counter
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_parametric_line_v75 import ParametricLines


ROOT = Path(__file__).resolve().parents[1]
LEDGER = dict(inputs=[], reference_line_calls=0, parametric_work=Counter())


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_parametric_line_v75.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Fixed four-rank lines and two repeated-swipe chains; no target boards.",
        ground_calls=0, fit_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def rule():
    return LearnedDynamics.from_payload(json.loads((ROOT /
        "reports/controlled_predictive_composition_v69/learned_rule.json").read_text()))


def compare(compiler, rule, inputs):
    LEDGER["inputs"].append(list(inputs))
    LEDGER["reference_line_calls"] += 1
    expected = rule.program.line(inputs)
    actual = compiler.line(inputs)
    assert actual == expected
    return actual


def test_distinct_rank_bindings_share_one_zero_equality_template(rule):
    compiler = ParametricLines(rule)
    for inputs in ((1, 1, 2, 0), (3, 3, 7, 0), (8, 8, 9, 0), (10, 10, 9, 0)):
        compare(compiler, rule, inputs)
    assert compiler.work["template_compilations"] == 1
    assert compiler.work["template_cache_hits"] == 3
    template = next(iter(compiler.templates.values()))
    assert template.pattern == (0, 0, 1, -1)
    assert template.outputs == ((0, 1), (1, 0), None, None)
    assert template.reward_slots == (0,)
    LEDGER["parametric_work"].update(compiler.work)


def test_packing_once_consumption_goal_and_multiple_rewards_remain_exact(rule):
    compiler = ParametricLines(rule)
    cases = ((1, 1, 1, 1), (1, 1, 2, 2), (1, 2, 2, 0),
             (0, 4, 0, 4), (10, 10, 10, 10), (0, 0, 0, 0))
    results = {inputs: compare(compiler, rule, inputs) for inputs in cases}
    assert results[(1, 1, 1, 1)] == ((2, 2, 0, 0), 8)
    assert results[(10, 10, 10, 10)] == ((11, 11, 0, 0), 4096)
    LEDGER["parametric_work"].update(compiler.work)


def test_merge_offset_changes_future_equality_instead_of_becoming_an_opaque_variable(rule):
    compiler = ParametricLines(rule)
    first_equal, _ = compare(compiler, rule, (3, 3, 4, 0))
    first_unequal, _ = compare(compiler, rule, (3, 3, 5, 0))
    assert compiler.work["template_compilations"] == 1
    assert first_equal == (4, 4, 0, 0)
    assert first_unequal == (4, 5, 0, 0)
    assert compare(compiler, rule, first_equal) == ((5, 0, 0, 0), 32)
    assert compare(compiler, rule, first_unequal) == ((4, 5, 0, 0), 0)
    LEDGER["parametric_work"].update(compiler.work)
