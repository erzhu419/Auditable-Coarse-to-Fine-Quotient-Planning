"""Small retained graphs verify H1/H2 routes and detect joint/model changes."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_grouped_audit_v73 import audit


LEDGER = dict(audit_calls=0)


@pytest.fixture(scope='module', autouse=True)
def retain_work(request):
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_grouped_v73.audit_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(session_failures=request.session.testsfailed,
        test_module=__file__, model_builds=0, fit_calls=0, ground_calls=0,
        planning_calls=0, main_cohort_cases=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + '\n')


def fixture():
    boards = [(1, 2) * 8, (2, 1) * 8, (3, 4) * 8, (4, 3) * 8]
    full = dict(cells=[[0, 0, 'CUTOFF'], [1, 0, 'LOST'], [2, 1, 'ACTIVE'],
                       [3, 1, 'ACTIVE'], [4, 2, 'ACTIVE'], [5, 3, 'ACTIVE']], roots=[5],
        rows=[[s, 'go', [[1, 2, 0, 0, 1], [1, 2, 1, 1, 2]]] for s in (2, 3)]
             + [[4, 'descend', [[1, 2, 2, 0, 1], [1, 2, 3, 0, 1]]],
                [5, 'start', [[1, 1, 4, 1, 4]]]],
        literal_boards=[[1, list(boards[0]), 2], [1, list(boards[1]), 3],
                        [2, list(boards[2]), 4], [3, list(boards[3]), 5]])
    composed = dict(cells=full['cells'][:3] + full['cells'][4:], roots=[5],
        rows=full['rows'][:1] + [[4, 'descend', [[1, 1, 2, 0, 1]]], full['rows'][-1]])
    labels = [[3, list(boards[3]), 5]]
    router = lambda board, h: 2 if h == 1 else 4
    observations = [dict(board=list(boards[0]), horizon=1, expected=2, expected_full=2),
                    dict(board=list(boards[2]), horizon=2, expected=4, expected_full=4),
                    dict(board=list(boards[3]), horizon=3, expected=5, expected_full=5)]
    return full, composed, labels, router, observations


def checked(*args):
    LEDGER['audit_calls'] += 1
    return audit(*args)


def test_low_layers_use_procedures_and_only_higher_members_are_retained():
    full, composed, labels, router, observations = fixture()
    result = checked(full, composed, deepcopy(composed), labels, router, observations)
    assert result['valid'] and result['frozen_core_exact']
    assert result['active_observations'] == result['active_routes_matched'] == 4
    assert result['h1_observations'] == 2 and result['h2_observations'] == 1
    assert result['candidate_h1_labels'] == result['candidate_h2_labels'] == 0
    assert result['high_observations'] == result['candidate_high_labels'] == 1
    assert result['counts']['retained_h1_procedural_calls'] == 2
    assert result['counts']['retained_h2_procedural_calls'] == 1
    assert result['counts']['retained_high_map_lookups'] == 1
    assert result['portable_routes_matched'] == 3


def test_changed_reward_successor_joint_blocks_frozen_evidence_inheritance():
    full, composed, labels, router, observations = fixture()
    changed = deepcopy(composed)
    changed['rows'][0][2][0][3:] = [1, 2]
    changed['rows'][0][2][1][3:] = [0, 1]
    result = checked(full, composed, changed, labels, router, observations)
    assert not result['valid'] and not result['frozen_core_exact']
    assert result['kernel_correspondence']['errors']['unmatched_full_contract'] == 4


def test_low_member_leak_wrong_h2_procedure_and_missing_high_label_fail():
    full, composed, labels, router, observations = fixture()
    bad_labels = [[1, observations[0]['board'], 2], [2, observations[1]['board'], 4]]
    result = checked(full, composed, deepcopy(composed), bad_labels,
                     lambda board, h: 2, observations)
    assert result['kernel_correspondence']['valid'] and not result['valid']
    assert result['candidate_h1_labels'] == result['candidate_h2_labels'] == 1
    assert result['missing_high_observations'] == 1 and result['extra_high_observations'] == 2
    assert result['errors']['non_high_observation_label'] == 2
    assert result['errors']['active_route_difference'] == 2
