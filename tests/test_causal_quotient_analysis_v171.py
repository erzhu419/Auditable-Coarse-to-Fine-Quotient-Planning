"""Independent empirical edges, vector Bellman tables and physical replay."""
from collections import Counter
from copy import deepcopy

import pytest

from scripts import analyze_controlled_predictive_causal_quotient_v171 as audit
from scripts import run_controlled_predictive_causal_quotient_v171 as runner
from scripts import causal_quotient_diagnostics_v171 as diagnostics
from acfqp.science import controlled_predictive_causal_quotient_v171 as core
from test_causal_quotient_core_v171 import edge,row,payload,trace,S0,S1
from test_causal_quotient_runner_v171 import roots,outcome

ROWS = []


def test_independent_ground_labels_fit_edges_tails_and_all_feature_counts():
    source,forced,hidden = trace(),trace(forced=True),dict(life=1,query='risk1')
    actual = core.fit_model([source,hidden],[forced,hidden],0)
    independent = audit.fit_model([source,hidden],[forced,hidden],0)
    assert audit._equal(actual,independent)
    assert independent['counts']['source_transitions'] == independent['counts']['train_transitions'] == 2
    assert independent['counts']['teacher_tail_labels'] == 3
    assert sum(item['count'] for item in independent['rows']) == 4
    assert sum(item['count'] for item in independent['tails']) == 3
    for board in ((11,)+(0,)*15,(2,0,2)+(0,)*13,(1,2,3,4)*4):
        a,b = Counter(),Counter()
        assert core.state_key(board,a) == audit.state_key(board,b) and a == b


def test_independent_bellman_preserves_chosen_vector_events_support_and_source_boundary():
    fixtures = [payload([row(S0,'DOWN',[edge('LOST',3.)]),row(S0,'LEFT',[edge(S1,0.)]),row(S1,'UP',[edge('WON',4.)])]),
        payload([row(S0,'UP',[edge(S1,0.)]),row(S1,'DOWN',[edge('LOST',10.)]),row(S1,'LEFT',[edge('WON',9.)])]),
        payload([row(S0,'LEFT',[edge(S1,2.)]),row(S1,'UP',[edge('WON',100.)])],{S0:[0.,0.,0.]}),
        payload([row(S0,'RIGHT',[edge('LOST',2.,2),edge('WON',6.,6)]),row(S0,'DOWN',[edge('WON',99.,7)])])]
    for data in fixtures:
        actual,independent = core.compile_model(data),audit.IndependentModel(data)
        assert audit.tables_valid(actual.tables,independent)
        assert actual.counts == audit.compilation_counts(independent)
    wrong = deepcopy(core.compile_model(fixtures[0]).tables)
    next(value for value in wrong['depths']['3']['values'] if value['state'] == S0)['components'] = [999.,0.,1.]
    assert not audit.tables_valid(wrong,audit.IndependentModel(fixtures[0]))


def test_heldout_diagnostics_rebuild_brier_immediate_and_genuine_H2_boundary_targets():
    source = trace(); sources = [deepcopy(source) for _ in range(8)]
    fitted = [core.fit_model(sources,[],0)]
    for life in range(1,4):
        data = deepcopy(fitted[0]); data['life'] = life; fitted.append(data)
    actual = [core.compile_model(data) for data in fitted]
    independent = {data['life']:audit.IndependentModel(data) for data in fitted}
    validation = []
    for life in range(4):
        data = trace(life,forced=True); data['branch_id'] = f'VALID:{life}:0'; validation.append(data)
    before = deepcopy(fitted)
    report = audit.prediction_report(independent,validation)
    assert audit._equal(diagnostics.prediction_report(actual,validation),report)
    assert report['pooled']['transition_brier'] == pytest.approx(0.)
    assert all(history['counts']['tail_supported'] == 1 for history in report['per_history'])
    assert report['logical_work']['diagnostic_tail_rows_read'] == 4
    assert fitted == before


def test_independent_whole_episode_ci_and_five_arm_policy_accounting():
    values = [outcome(plan,reward=plan['episode'] if plan['mode'] == 'SAME_D3' else 0.) for plan in runner.eval_roster()]
    independent = audit.eval_summary(values)
    assert audit._equal(runner.eval_summary(values),independent)
    stats = independent['comparisons'][0]['metrics']['utility']
    assert stats['mean'] == 15.5 and stats['mean_variance'] == pytest.approx(.6875)
    assert 'conditional_episode_ci95' in stats and 'conditional_suffix_ci95' not in stats
    values[0].update(status='CUTOFF',utility=None)
    assert audit._equal(runner.eval_summary(values),audit.eval_summary(values))
    assert all(item['metrics']['utility']['mean'] is None for item in audit.eval_summary(values)['comparisons'])


@pytest.mark.parametrize('failure',['seed','duplicate','cutoff'])
def test_independent_forced_roster_and_completion_stop(failure):
    source_roots = roots(); expected = audit.forced_roster(source_roots,'TRAIN')
    assert expected == runner.branch_roster(source_roots,'TRAIN')
    plans = expected[:3]; values = [outcome(plan) for plan in plans]
    assert audit.complete_cohort(values,plans)
    if failure == 'seed': values[-1]['seed'] += 1
    elif failure == 'duplicate': values.append(deepcopy(values[-1]))
    else: values[-1].update(status='CUTOFF',utility=None)
    assert not audit.complete_cohort(values,plans)


class SmallTeacher:
    def __init__(self): self.counts = Counter()
    def choose(self,board,query):
        self.counts['fixture_calls'] += 1
        for action in audit.ACTIONS:
            after,score,legal = audit.prior.ground.swipe_board_v1(tuple(board),audit.prior.ground.Swipe2048Action(action))
            if legal: return dict(action=action,afterstate=list(after),score=score)
        raise AssertionError('terminal board cannot request fixture H2')


def fixture_bank(monkeypatch):
    # Existing H2 value validation is separately exercised on production traces.
    # These finite fixtures target the new replay's physical/model/control logic.
    monkeypatch.setattr(audit.prior.prior.planning,'planning_counts_valid',lambda *args:True)
    monkeypatch.setattr(audit.prior.prior.local,'compact_choice_valid',lambda *args:True)
    monkeypatch.setattr(audit.prior.prior.h1,'root_choice_checks',lambda *args:{})
    return {query:SmallTeacher() for query in ('risk1','risk8')}


def test_real_finite_forced_first_then_H2_trace_replay_has_no_initial_spawns(monkeypatch):
    actual = runner.run_forced_branch(fixture_bank(monkeypatch),[1,0,1]+[0]*13,'LEFT',0,31,max_steps=4)
    actual.update(life=0,query='risk1'); ROWS.append(actual)
    checks,_ = audit.replay_forced(actual,max_steps=4)
    assert all(checks.values()) and actual['initial_spawns'] == []
    assert actual['module']['forced_decisions'] == 1 and actual['module']['h2_calls'] == 3
    assert actual['result']['environment_counts']['environment_random_draws'] == 8
    wrong = deepcopy(actual); wrong['first_action'] = 'UP'
    assert not audit.replay_forced(wrong,max_steps=4)[0]['forced_choice']


@pytest.mark.parametrize('mode,supported',[('SAME_D3',True),('XFER_D3',True),('SAME_D1',False)])
def test_real_finite_ordinary_quotient_episode_replay_current_frame_and_source_vectors(monkeypatch,mode,supported):
    data = []
    for life in range(4):
        rows = [row(state,action,[edge('WON',1.+life)]) for state in core.ACTIVE_STATES for action in audit.ACTIONS] if supported else []
        data.append(payload(rows,life=life))
    compiled = [core.compile_model(item) for item in data]
    actual = core.run_episode(fixture_bank(monkeypatch),compiled,0,mode,31,max_steps=4)
    actual['life'] = 0; ROWS.append(actual)
    checks,_ = audit.replay_eval(actual,{item['life']:audit.IndependentModel(item) for item in data},max_steps=4)
    assert all(checks.values()) and len(actual['initial_spawns']) == 2
    assert actual['result']['environment_counts']['sampled_transitions'] == 4
    if supported:
        assert actual['module']['model_decisions'] == 4
        if mode.startswith('XFER'): assert actual['module']['source_counts'] == [0,0,0,4]
    else: assert actual['module']['unsupported_fallbacks'] == actual['module']['h2_calls'] == 4
    wrong = deepcopy(actual); wrong['choices'][2]['model_decision']['depth'] = 99
    assert not audit.replay_eval(wrong,{item['life']:audit.IndependentModel(item) for item in data},max_steps=4)[0]['model_decisions']
    wrong = deepcopy(actual); wrong['spawned_ranks'][0] = 3
    assert not audit.replay_eval(wrong,{item['life']:audit.IndependentModel(item) for item in data},max_steps=4)[0]['rng']
