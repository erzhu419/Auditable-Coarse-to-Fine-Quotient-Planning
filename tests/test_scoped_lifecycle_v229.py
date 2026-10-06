from collections import Counter
from copy import deepcopy
from fractions import Fraction as F

from scripts import scoped_lifecycle_v229_stats as stats


def row(life, index, arm, stage, spent=64):
    impossible = stage == 'B' and index < 38
    utility = F(3,2) if impossible else F(5,2)
    point = dict(actual=[0, F(1,100), utility/4], risk_upper=F(1,20),
        coverage=True, true_candidate=True, true_candidate_coverage=True,
        query_bounds_ok=True, goal_upper_ok=True)
    return dict(life=life, index=index, arm=arm, stage=stage, spent=spent,
        execution_certified=not impossible, goal_impossible=impossible,
        query_certified=True, oracle_goal=utility,
        terminal=dict(actual_utility=utility),
        query_post={name:dict(regret=F(0)) for name in ('reward', 'goal', 'risk')},
        history=[point], true_branch_retained=True, true_masks_retained=True,
        point_committed=False, point_commit_correct=True)


def cohort():
    rows = []
    for life in range(12):
        for arm in stats.ARMS:
            for stage, start in (('A', 3), ('B', 30), ('A_RETURN', 54)):
                for index in range(start, start+24):
                    extra = 0
                    if stage == 'B' and index == 30:
                        extra = 16*(life+1) if arm == 'REBUILD_CS' else 16*(12-life) if arm == 'PARAM' else 0
                    rows.append(row(life, index, arm, stage, 64+extra))
    return rows


def summary(rows, common_A_path=True):
    costs = {arm:[4608]*12 for arm in stats.ARMS}
    seconds = {arm:[1.1 if arm == 'REPAIR_CS' else 1.0]*12 for arm in stats.ARMS}
    return stats.summarize(rows, costs, seconds, Counter(), common_A_path)


def test_goal_impossibility_resolves_goal_without_claiming_execution_or_query_success():
    rows = [row(0, 3, 'REPAIR_CS', 'A'), row(0, 30, 'REPAIR_CS', 'B')]
    rows[1]['query_certified'] = False
    result = stats.metrics(rows)
    assert result['execution_certified'] == 1
    assert result['goal_impossible_certified'] == 1
    assert result['goal_resolved'] == 2
    assert result['query_certified'] == result['resolved_queries'] == 1
    assert result['oracle_unreachable'] == 1 and result['false_impossible_certificates'] == 0
    rows[1]['oracle_goal'] = F(2)
    assert stats.metrics(rows)['false_impossible_certificates'] == 1


def test_whole_lifecycle_paired_costs_charge_all_sources_and_keep_life_units():
    result = summary(cohort())
    assert result['complete'] and all(result['conditions'].values())
    assert result['decision'] == 'SCOPED_REPAIR_LIFECYCLE_SUPPORTED'
    assert result['contrasts']['rebuild_cs_minus_repair_samples'] == [16*(life+1) for life in range(12)]
    assert result['contrasts']['param_minus_repair_samples'] == [16*(12-life) for life in range(12)]
    for arm in stats.ARMS:
        assert result['arms'][arm]['source_samples'] == 55296
        assert result['arms'][arm]['total_samples'] == 55296+result['arms'][arm]['target_samples']
        assert result['arms'][arm]['stages']['B']['goal_impossible_certified'] == 96
        assert result['arms'][arm]['stages']['B']['execution_certified'] == 192
    assert result['bootstrap']['rebuild_cs_minus_repair_samples']['mean'] == 104
    assert result['bootstrap']['param_minus_repair_samples']['ci'][0] > 0


def test_lower_cost_cannot_hide_param_quality_loss_or_changed_old_paths():
    rows = cohort()
    for item in rows:
        if item['arm'] == 'PARAM' and stats.late_b(item):
            item['terminal']['actual_utility'] += F(1,10)
    result = summary(rows)
    assert result['conditions']['REBUILD_REFERENCE'] and result['conditions']['PARAMETER_REFERENCE']
    assert not result['conditions']['B_QUALITY']
    assert result['decision'] == 'SCOPED_REPAIR_LIFECYCLE_NOT_SUPPORTED'
    old_path = summary(cohort(), False)
    assert not old_path['conditions']['OLD_RETENTION']


def test_true_candidate_coverage_or_false_impossibility_failure_blocks_support():
    rows = cohort()
    rows[0]['history'][0]['true_candidate_coverage'] = False
    assert not summary(rows)['conditions']['RISK_SCOPE']
    rows = deepcopy(cohort())
    item = next(item for item in rows if item['goal_impossible'])
    item['oracle_goal'] = F(2)
    assert not summary(rows)['conditions']['RISK_SCOPE']
