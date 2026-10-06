"""Fixed-policy offset fitting and unchanged-candidate comparison checks."""
from collections import Counter
import json
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science.controlled_predictive_anchored_success_v127 import choose_gpi
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_policy_calibration_v129 import (
    PolicyOffsetCalibrator, calibrated_choice)
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/controlled_predictive_policy_calibration_v129_build'
BOARD = [1, 1] + [0] * 14
OTHER = [2, 0, 1, 0] + [0] * 12
GOAL = [4] + [0] * 15
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
CALIBRATORS, SOURCES = [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT / 'reports/controlled_predictive_policy_calibration_v129.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before,
        calibration_work=dict(sum((m.counts for m in CALIBRATORS), Counter())),
        source_reference_work=dict(sum((m.counts for m in SOURCES), Counter())),
        setup_counts=dict(sum((m.setup_counts for m in CALIBRATORS + SOURCES), Counter())),
        newly_sampled_environment_transitions=0, optimizer_steps=0,
        scope='Synthetic retained boards/scores and candidate fixtures; offsets only, source parameters unchanged.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def calibrator():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 13 * .001
    source.weights.flags.writeable = False
    SOURCES.append(source)
    result = PolicyOffsetCalibrator(source, QUERY, BUILD)
    CALIBRATORS.append(result)
    return result


def test_batch_original_values_match_v120_and_current_reward_occurs_once():
    result = calibrator()
    tails = np.array([result.source.value(BOARD), result.source.value(OTHER)])
    before = result.source.counts.copy(); weights = result.source.weights.copy()
    row = result.fit_episode([BOARD, OTHER], [4, 8], 'LOST')
    expected_targets = np.array([12/2048 - 4, 8/2048 - 4])
    expected_anchors = np.array([4/2048, 8/2048]) + tails
    assert row['n'] == 2
    assert row['target_sum'] == expected_targets.sum()
    assert row['anchor_sum'] == expected_anchors.sum()
    assert row['residual_sum'] == (expected_targets - expected_anchors).sum()
    assert row['offset_after'] == row['residual_sum'] / 2
    assert row['work']['source_tail_predictions'] == 2
    assert row['work']['source_table_lookups'] == 64
    assert result.source.counts == before
    np.testing.assert_array_equal(result.source.weights, weights)


def test_win_row_analytic_exclusion_retains_goal_score_in_earlier_targets():
    result = calibrator()
    row = result.fit_episode([BOARD, OTHER, GOAL], [4, 8, 16], 'WON')
    assert row['n'] == 2 and row['analytic_goals'] == 1
    assert row['target_sum'] == (28 + 24)/2048 + 8
    assert result.n == 2 and result.counts['source_tail_predictions'] == 2
    assert result.to_payload()['offset'] == row['residual_sum'] / 2


def test_cumulative_offset_weights_samples_and_censors_entire_cutoff_game():
    result = calibrator(); assert result.offset == 0.
    first = result.fit_episode([BOARD, OTHER], [4, 8], 'LOST')
    second = result.fit_episode([OTHER], [16], 'LOST')
    assert result.n == 3
    assert result.offset == (first['residual_sum'] + second['residual_sum']) / 3
    before = result.to_payload(); source_before = result.source.counts.copy()
    cutoff = result.fit_episode([BOARD, OTHER], [4, 8], 'CUTOFF')
    assert cutoff['n'] == 0 and cutoff['censored_afterstates'] == 2
    assert not cutoff['work'].get('source_tail_predictions', 0)
    assert result.offset == before['offset'] and result.n == 3
    assert result.source.counts == source_before


class CandidatePolicy:
    def __init__(self, actions):
        self.actions = actions
        self.rule = SimpleNamespace(goal_rank=4)
    def choose(self, board, query, mode='LEARNED'):
        values = {action: dict(afterstate=GOAL if goal else BOARD, score=16 if goal else 0,
            value=value, anchor_value=value - 1, success_probability=1. if goal else .25)
            for action, value, goal in self.actions}
        action = min(values, key=lambda a: (-values[a]['value'], a))
        return dict(action=action, **values[action], action_values=values, status='ACTIVE')


def test_zero_offsets_equal_original_all_action_gpi_including_ties():
    models = [CandidatePolicy([('LEFT', 2., False), ('DOWN', 1., False)]),
              CandidatePolicy([('UP', 2., False), ('DOWN', 2., False)])]
    original = choose_gpi(models, BOARD, QUERY)
    actual = calibrated_choice(models, [0., 0.], BOARD, QUERY)
    assert (actual['action'], actual['policy_index'], actual['value']) == (
        original['action'], original['policy_index'], original['value'])
    assert actual['comparison_value'] == original['value']
    assert actual['per_policy_candidates'][0]['action'] == 'LEFT'
    assert actual['per_policy_candidates'][1]['action'] == 'DOWN'


def test_offset_changes_cross_policy_selection_without_rewriting_candidates():
    models = [CandidatePolicy([('LEFT', 2., False), ('DOWN', 1., False)]),
              CandidatePolicy([('UP', 1.5, False), ('RIGHT', 1., False)])]
    actual = calibrated_choice(models, [0., 1.], BOARD, QUERY)
    assert actual['action'] == 'UP' and actual['policy_index'] == 1
    assert actual['value'] == 1.5 and actual['comparison_value'] == 2.5
    assert [row['value'] for row in actual['per_policy_candidates']] == [2., 1.5]
    assert [row['action'] for row in actual['per_policy_candidates']] == ['LEFT', 'UP']
    assert actual['per_policy_action_values'][1]['UP']['value'] == 1.5


def test_single_policy_action_unchanged_and_analytic_goals_never_shifted():
    nonwinning = CandidatePolicy([('LEFT', 9., False), ('UP', 8., True)])
    actual = calibrated_choice([nonwinning], [-100.], BOARD, QUERY)
    assert actual['action'] == 'LEFT' and actual['value'] == 9.
    assert actual['comparison_value'] == -91.
    winning = CandidatePolicy([('LEFT', 7., False), ('UP', 8., True)])
    actual = calibrated_choice([winning], [100.], BOARD, QUERY)
    assert actual['action'] == 'UP' and actual['value'] == 8.
    assert actual['comparison_value'] == 8. and actual['applied_offset'] == 0.
    other = CandidatePolicy([('DOWN', 7.5, False)])
    actual = calibrated_choice([winning, other], [100., 1.], BOARD, QUERY)
    assert actual['action'] == 'DOWN' and actual['comparison_value'] == 8.5
    assert actual['per_policy_candidates'][0]['comparison_value'] == 8.
