"""Small native-table parity for the independent DIRECT critic oracle."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from scripts import analyze_controlled_predictive_module_control_variate_v159 as audit

TEMP = Path(__file__).resolve().parents[1] / 'reports/v159_runtime_tmp'
MODELS, ORACLES = [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP / 'critic_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed - before, environment_samples=0, production_source_reads=0,
        native_model_counts=dict(sum((m.counts for m in MODELS), Counter())),
        setup_counts=dict(sum((m.setup_counts for m in MODELS), Counter())),
        oracle_counts=dict(sum((o.counts for o in ORACLES), Counter())),
        scope='Twelve fixed synthetic board predictions with small native tables; no environment sampling.'))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def test_direct_oracle_matches_native_target_conversion_terminals_and_work():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(5, 8)), (2, Fraction(3, 8))), 'uniform', 4)
    source = NtupleValue(rule, TEMP / 'critic_build')
    MODELS.append(source)
    source.weights[:] = (np.arange(source.weights.size).reshape(source.weights.shape) % 13) * .003
    source.weights.flags.writeable = False
    source.updates = 42
    source_query = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
    boards = ([1, 1] + [0] * 14,
        [1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 0],
        [1, 2, 1, 2] + [0] * 12,
        [3, 3] + [0] * 14,
        [4] + [0] * 15,
        [1, 2, 1, 2, 2, 1, 2, 1] * 2)
    for penalty in (1., 8.):
        target = dict(reward_weight=1., failure_penalty=penalty, goal_bonus=penalty)
        parent = QueryParent(source, source_query, target, .4)
        leaf = QueryTD(parent, 'PRIOR', TEMP / 'critic_build')
        leaf.freeze()
        MODELS.append(leaf)
        metadata = dict(kind=leaf.kind, target_query=target, source_query=source_query,
            failure_shift=leaf.failure_shift, success_shift=leaf.success_shift)
        assert leaf.failure_shift != 0 and leaf.success_shift != 0 and leaf.offset != 0
        oracle = audit.DirectOracle(rule, leaf.weights.reshape(-1), metadata)
        ORACLES.append(oracle)
        baseline, source_before = leaf.weights.copy(), source.counts.copy()
        for index, board in enumerate(boards):
            native_before, expected_before = leaf.counts.copy(), oracle.native_counts.copy()
            expected = oracle(board)
            actual = leaf.choose(board, target)
            assert expected == actual['value']
            assert leaf.counts - native_before == oracle.native_counts - expected_before
            if index == 4: assert actual['value'] == penalty and actual['status'] == 'WON'
            if index == 5: assert actual['value'] == -penalty and actual['status'] == 'LOST'
        assert leaf.updates == 0 and not leaf.weights.flags.writeable
        assert source.counts == source_before and source.updates == 42
        np.testing.assert_array_equal(leaf.weights, baseline)
