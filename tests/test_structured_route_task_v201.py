"""Four synthetic witnesses for delay, joint policies, hard risk, and reset."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from acfqp.science import structured_route_task_v201 as core


def graph():
    return core.rows(core.roster()[0])


def test_declared_roster_and_delayed_signal_require_future_steps():
    cases = core.roster()
    assert len(cases) == 12
    assert cases[0] == dict(id="v201_normal_low_r17_20", weather="normal", operating="low", retry_cost="17/20")
    assert cases[-1] == dict(id="v201_blocked_high_r19_20", weather="blocked", operating="high", retry_cost="19/20")
    task = graph()
    assert all(row == [(F(1), f"{action}_ENTRY", F(0))] for action, row in task["START"].items())
    one = core.plan(task, 1, "goal")
    assert one["action_vectors"]["START", 1] == {name: (F(0), F(0), F(0)) for name in ("DETOUR", "SHORT", "WAIT")}
    assert core.evaluate_plan(task, 1, "SHORT")["root"] == (F(0), F(0), F(0))
    assert core.evaluate_plan(task, 2, "SHORT")["root"] == (F(-1, 10), F(1, 10), F(0))
    assert core.evaluate_plan(task, 3, "SHORT")["root"] == (F(-1, 10), F(1, 10), F(9, 10))
    counts = Counter()
    table = core.plan(task, 4, "goal", counts)
    assert len(table["values"]) == 45 and counts["dp_value_keys"] == 45
    assert counts["dp_action_rows"] == 36 and counts["dp_outcome_evaluations"] == 52


def test_joint_own_policy_recovery_changes_and_h2_waits():
    task = graph()
    goal, risk = core.plan(task, 4, "goal"), core.plan(task, 4, "risk")
    assert goal["policy"]["RECOVERY", 2] == "RETRY"
    assert goal["values"]["RECOVERY", 2] == (F(-17, 20), F(3, 4), F(1, 4))
    assert risk["policy"]["RECOVERY", 2] == "RETURN"
    assert risk["values"]["RECOVERY", 2] == (F(0), F(0), F(0))
    assert goal["policy"]["START", 4] == "SHORT"
    assert risk["policy"]["START", 4] == "DETOUR"
    for query, table in (("goal", goal), ("risk", risk)):
        actual = core.evaluate_plan(task, 4, table["policy"])
        assert actual["root"] == table["values"]["START", 4]
        short = core.evaluate_controller(task, 4, query, lookahead=2)
        assert short["policy"]["START", 4] == "WAIT" and short["root"] == (F(0), F(0), F(0))
        assert core.utility(actual["root"], query)-core.utility(short["root"], query) > F(1, 10)
    assert risk["values"]["START", 4] == (F(-1, 20), F(1, 100), F(17, 20))
    assert sum(risk["values"]["START", 4][1:]) < 1  # Safe abort separates F from 1-S.


def test_hard_constraint_is_an_achievable_feasible_mixture():
    task = graph()
    pure = core.pure_values(task)
    counts = Counter()
    result = core.hard_constraint(pure, counts=counts)
    assert result["mix"] == [("DETOUR_RETURN", F(5, 9)), ("SHORT", F(4, 9))]
    assert result["vector"] == (F(-13, 180), F(1, 20), F(157, 180))
    assert result["utility"] == F(41, 12)
    assert sum(weight for _, weight in result["mix"]) == 1
    assert all(weight > 0 for _, weight in result["mix"])
    assert result["vector"][1] == result["delta"]
    assert result["utility"]-core.utility(pure["DETOUR_RETURN"], "goal") == F(1, 15)
    assert pure["SHORT"][1] > result["delta"]
    risk = core.plan(task, 4, "risk")["values"]["START", 4]
    assert risk != result["vector"]  # A penalty policy is not the constrained optimum.
    assert counts["hard_pure_feasibility_checks"] == 4 and counts["hard_pair_checks"] == 6
    assert counts["hard_edge_intersections"] == 4


def test_fresh_prefix_reset_counts_each_cost_and_terminal_event_once():
    task = graph()
    frozen = deepcopy(task)
    whole = core.evaluate_plan(task, 4, "DETOUR_RETRY")["root"]
    suffix = core.evaluate_plan(task, 3, "DETOUR_RETRY", start="DETOUR_ENTRY")["root"]
    assert whole == suffix == (F(-169, 1000), F(23, 200), F(177, 200))
    recovery = core.evaluate_plan(task, 2, "DETOUR_RETRY", start="RECOVERY")["root"]
    assert recovery == (F(-17, 20), F(3, 4), F(1, 4))
    truncated = core.evaluate_plan(task, 3, "DETOUR_RETRY")["root"]
    assert truncated == (F(-169, 1000), F(23, 200), F(17, 20))
    assert core.evaluate_plan(task, 0, "DETOUR_RETRY", start="DELIVERY")["root"] == (F(0), F(0), F(0))
    assert core.evaluate_plan(task, 0, "DETOUR_RETRY", start="WON")["root"] == (F(0), F(0), F(1))
    assert task == frozen
