"""Preflight independent arithmetic at the actual finite source budgets, no RNG."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import scoped_repair_v228 as core
from acfqp.science import scoped_route_task_v228 as task
from scripts import run_scoped_lifecycle_v229 as runner
from scripts import scoped_repair_v229_math as math
from scripts import analyze_scoped_lifecycle_v229 as audit


def test_independent_task_roster_and_hidden_constants_match_without_observations():
    for life in range(12):
        assert audit.world(life) == task.world(life)


def integer_counts(law, n):
    counts = core.empty()
    for op, probabilities in law.items():
        values = {cat: n*p for cat, p in probabilities.items()}
        counts[op] = {cat: int(value) for cat, value in values.items()}
        order = sorted(probabilities, key=lambda cat: (-(values[cat]-int(values[cat])),
                                                      core.ALPHABETS[op].index(cat)))
        for cat in order[:n-sum(counts[op].values())]:
            counts[op][cat] += 1
    return counts


@pytest.mark.parametrize('arm', core.ARMS)
def test_independent_plan_choice_update_and_return_at_paid_source_budgets(arm):
    cases, laws, _, _ = task.world(0)
    source_a = [integer_counts(laws[i], 384) for i in (0, 1, 2)]
    source_b = [integer_counts(laws[i], 128) for i in (27, 28, 29)]
    producer_work, audit_work = Counter(), Counter()
    state = core.prepare(source_a, arm, producer_work)
    independent = math.prepare(source_a, arm, audit_work)
    assert math.same(runner.exact_json(runner.compact_state(state)), runner.compact_state(independent))
    # One ended A member exercises the inherited pooled state at the switch.
    a_member = integer_counts(laws[3], 16)
    a_plan = core.make_plan(a_member, cases[3], state, producer_work)
    a_audit = math.make_plan(a_member, cases[3], independent, audit_work)
    assert math.same(runner.exact_json(runner.compact_plan(a_plan)), runner.compact_plan(a_audit))
    core.advance(state, a_member, cases[3], a_plan, producer_work)
    math.advance(independent, a_member, cases[3], a_audit, audit_work)
    core.begin_b(state, source_b, producer_work)
    math.begin_b(independent, source_b, audit_work)
    member = core.empty()
    plan = core.make_plan(member, cases[30], state, producer_work)
    audit_plan = math.make_plan(member, cases[30], independent, audit_work)
    assert math.same(runner.exact_json(runner.compact_plan(plan)), runner.compact_plan(audit_plan))
    before = deepcopy(state)
    choice = core.choose(member, cases[30], state, plan, 0, producer_work)
    audit_choice = math.choose(member, cases[30], independent, audit_plan, 0, audit_work)
    assert math.same(runner.exact_json(choice), audit_choice)
    assert state == before
    assert choice is not None
    op = choice['operator']
    member[op] = integer_counts(laws[30], 16)[op]
    plan = core.make_plan(member, cases[30], state, producer_work)
    audit_plan = math.make_plan(member, cases[30], independent, audit_work)
    assert math.same(runner.exact_json(runner.compact_plan(plan)), runner.compact_plan(audit_plan))
    assert math.same(runner.exact_json(core.advance(state, member, cases[30], plan, producer_work)),
                     math.advance(independent, member, cases[30], audit_plan, audit_work))
    assert math.same(runner.exact_json(runner.compact_state(state)), runner.compact_state(independent))
    returned = core.make_plan(core.empty(), cases[54], state, producer_work)
    returned_audit = math.make_plan(math.empty(), cases[54], independent, audit_work)
    assert math.same(runner.exact_json(runner.compact_plan(returned)), runner.compact_plan(returned_audit))
