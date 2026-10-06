from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path

import pytest
from acfqp.science import retained_model_v227 as core
from scripts.run_conditioned_mechanisms_v205 import exact_json

ROOT = Path(__file__).resolve().parents[1]


def restore(value):
    if isinstance(value, dict):
        return {key: restore(item) for key, item in value.items()}
    if isinstance(value, list):
        return [restore(item) for item in value]
    if isinstance(value, str):
        try:
            return F(value)
        except ValueError:
            return value
    return value


def saved(value):
    return json.loads(json.dumps(exact_json(value)))


@pytest.fixture(scope='module')
def retained():
    folder = ROOT/'reports/limited_source_v226'
    return (json.loads((folder/'source_evidence.json').read_text()),
            json.loads((folder/'records.json').read_text()))


def source_for(libraries, row):
    return libraries[row['life']]['full' if row['arm']=='FULL_FIXED' else 'low']


def last_plan(row):
    return row['batches'][-1]['plan'] if row['batches'] else row['initial_plan']


def check_old_execution(row, result):
    assert saved(result['execution_plan']) == row['terminal_plan']
    for name in ('fallback', 'certified', 'identified', 'transferred', 'stop'):
        assert result[name] == row[name]


def test_twenty_retained_bad_fallbacks_keep_queries_without_promoting_execution(retained):
    libraries, rows = retained
    selected = [r for r in rows if r['arm']=='LOW_UNION' and r['index']>=15 and r['fallback']]
    assert len(selected) == 20
    changed_queries, changed_targets = 0, 0
    for row in selected:
        state = restore(row['library_before']); before = deepcopy(state)
        plan = restore(last_plan(row)); original = deepcopy(plan)
        result = core.finish(row['member'], source_for(libraries, row), row['case'],
                             row['arm'], Counter(), state, plan)
        check_old_execution(row, result)
        assert saved(result['knowledge_plan']) == last_plan(row)
        assert result['knowledge_mode']=='library' and len(result['knowledge_candidates'])==2
        assert not result['certified'] and not result['knowledge_query_ready']
        assert state == before and plan == original
        before_queries = core.queries({'pure_vectors': restore(last_plan(row)['pure_vectors'])})
        assert result['queries'] == before_queries
        changed = sum(result['queries'][q]['policy'] != row['terminal_query'][q]['policy']
                      for q in result['queries'])
        changed_queries += changed; changed_targets += bool(changed)
    assert changed_queries == 38 and changed_targets == 20


def test_actual_unique_query_ready_and_uncertified_unique_terminals_keep_old_eligibility(retained):
    libraries, rows = retained
    selected = [next(r for r in rows if r['arm']=='LOW_UNION' and r['identified']),
                next(r for r in rows if r['arm']=='LOW_UNION' and r['stop']=='query_set'),
                next(r for r in rows if r['arm']=='LOW_UNION' and not r['certified']
                     and not r['fallback'] and len(r['terminal_plan']['candidates'])==1)]
    for row in selected:
        state = restore(row['library_before']); before = deepcopy(state)
        result = core.finish(row['member'], source_for(libraries, row), row['case'], row['arm'],
                             Counter(), state, restore(last_plan(row)))
        check_old_execution(row, result)
        assert saved(result['knowledge_plan']) == row['terminal_plan']
        assert saved(result['queries']) == row['terminal_query']
        assert state == before


def test_absent_library_uses_member_knowledge_without_reintroducing_source_hypotheses(retained):
    libraries, rows = retained
    row = next(r for r in rows if r['arm']=='LOW_UNION' and r['index']>=15 and r['fallback'])
    state = restore(row['library_before']); state['bounds']=[]; state['no_feasible']=True
    before = deepcopy(state)
    plan = core.make_plan(row['member'], source_for(libraries,row), row['case'], row['arm'],
                          Counter(), state)
    assert plan['mode']=='member' and plan['candidates']==[]
    result = core.finish(row['member'], source_for(libraries,row), row['case'], row['arm'],
                         Counter(), state, plan)
    assert result['knowledge_mode']=='member' and result['knowledge_candidates']==[]
    assert saved(result['execution_plan']) == row['terminal_plan']
    assert saved(result['queries']) == row['terminal_query']
    assert not result['knowledge_query_ready'] and not result['certified']
    assert state == before


def test_parameter_state_and_commit_interface_retain_actual_v226_behavior(retained):
    libraries, rows = retained
    row = next(r for r in rows if r['arm']=='LOW_PARAM' and r['fallback']
               and r['library_before']['counts'] != source_for(libraries,r)
               and last_plan(r)['mode']=='library')
    state = restore(row['library_before']); before = deepcopy(state)
    plan = restore(last_plan(row))
    result = core.finish(row['member'], source_for(libraries,row), row['case'], row['arm'],
                         Counter(), state, plan)
    check_old_execution(row, result)
    assert result['knowledge_plan']['pure_vectors'] == restore(last_plan(row)['pure_vectors'])
    assert state == before
    event = core.advance(state, row['member'], source_for(libraries,row), row['arm'],
                         Counter(), terminal_plan=result['execution_plan'])
    assert saved(event) == row['advance'] and saved(state) == row['library_after']
