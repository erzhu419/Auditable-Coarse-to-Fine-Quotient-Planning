"""Small saved-kernel fixtures test direct-router audit without ground execution."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_observation_audit_v70 import audit, recover_mapping

WORK = Counter()


@pytest.fixture(scope='session', autouse=True)
def ledger():
    yield
    path = Path(__file__).resolve().parents[1]/'reports/controlled_predictive_observation_v70.audit_checks.json'
    path.write_text(json.dumps(dict(counts=dict(WORK), main_cohort_roots=0,
        ground_calls=0, model_builds=0, fit_calls=0, planning_calls=0,
        scope='Three tiny saved-kernel fixtures check exact matching, malformed kernels, and wrong/extrapolated routing.'), indent=2)+'\n')


def fixture():
    boards = [(1, 2)*8, (2, 1)*8, (3, 4)*8]
    full = dict(cells=[[0,2,'ACTIVE'],[1,2,'ACTIVE'],[2,1,'ACTIVE'],[3,0,'LOST'],[4,0,'CUTOFF']],
        rows=[[0,'go',[[1,1,2,1,2048]]],[1,'go',[[1,1,2,1,2048]]],
              [2,'finish',[[1,10,3,0,1],[9,10,4,0,1]]]], roots=[0,1],
        literal_boards=[[2,list(boards[0]),0],[2,list(boards[1]),1],[1,list(boards[2]),2]])
    composed = dict(cells=[[10,2,'ACTIVE'],[20,1,'ACTIVE'],[30,0,'LOST'],[40,0,'CUTOFF']],
        rows=[[10,'go',[[1,1,20,1,2048]]],[20,'finish',[[1,10,30,0,1],[9,10,40,0,1]]]], roots=[10,10])
    full_lookup = {(h,tuple(b)):s for h,b,s in full['literal_boards']}
    composed_lookup = {(h,tuple(b)):10 if s in (0,1) else 20 for h,b,s in full['literal_boards']}
    routers = dict(FULL_MAP=lambda b,h:full_lookup.get((h,tuple(b))),
        COMPOSED_MAP=lambda b,h:composed_lookup.get((h,tuple(b))),
        COMPOSED_DAG=lambda b,h:composed_lookup.get((h,tuple(b))))
    observations = [dict(board=list(boards[0]),horizon=2,expected_full=0,expected=10),
                    dict(board=list(boards[2]),horizon=1,expected_full=2,expected=20)]
    return full, composed, routers, observations


def checked(full, composed, routers, observations):
    result = audit(full, composed, routers, observations)
    WORK.update(result['counts'])
    WORK['audit_calls'] += 1
    return result


def test_exact_joint_mapping_and_complete_finite_support_routes():
    full, composed, routers, observations = fixture()
    recovered = recover_mapping(full, composed)
    WORK.update(recovered['counts'])
    WORK['standalone_mapping_calls'] += 1
    assert recovered['valid']
    assert recovered['mapping'] == {0:10,1:10,2:20,3:30,4:40}
    assert recovered['counts']['joint_rows_verified'] == 3
    result = checked(full, composed, routers, observations)
    assert result['routing_correct'] and result['active_observations'] == 3
    assert result['portable_observations'] == 2
    assert all(r['covered_observations'] == 3 and r['unsupported_observations'] == 2
               for r in result['routers'].values())


def test_changed_joint_kernel_cannot_inherit_frozen_correspondence():
    full, composed, routers, observations = fixture()
    changed = deepcopy(composed)
    changed['rows'][1][2][1][0] = 8
    result = checked(full, changed, routers, observations)
    assert result['engineering_complete'] and not result['routing_correct']
    assert result['kernel_correspondence']['errors']['unmatched_full_contract'] == 3


def test_wrong_known_route_and_unsupported_extrapolation_are_visible():
    full, composed, routers, observations = fixture()
    routers['COMPOSED_DAG'] = lambda board,h:10
    result = checked(full, composed, routers, observations)
    assert result['kernel_correspondence']['valid'] and not result['routing_correct']
    failures = result['routers']['COMPOSED_DAG']['errors']
    assert failures['retained_active_observation'] == 1
    assert failures['unsupported_observation'] == 2
    assert result['routers']['FULL_MAP']['valid']
    assert result['routers']['COMPOSED_MAP']['valid']
