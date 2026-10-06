"""Selected observed banks supply both frozen heads and shared planning beliefs."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import numpy as np

from acfqp.science import bank_belief_run_v310 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1]/'reports/bank_belief_v310/runtime_tests/driver'


def add_facts(memory, n, k):
    for index in range(n):
        memory.observe(2 if index<k else 1)


def dataset(stage, fit_fours):
    memory = SpawnMemory('LIBRARY'); add_facts(memory, 256, fit_fours)
    scale = core.STAGES.index(stage)+1
    return dict(lifecycle=0, parent=0,
        afterstates=np.tile([1, 1, 0, 0]+[0]*12, (7, 1)).astype(np.int32),
        rewards=np.asarray([.1, .2, .3, .4, .5, .6, .7])*scale,
        ends=np.asarray([2, 4, 7], dtype=np.int64), terminal_codes=np.full(3, -1, dtype=np.int32),
        fit_game_count=2, fit_step_end=4, fit_end_raw=8, fit_memory=memory.to_payload(),
        costs=dict(excluded_tail_raw_tiles=3),
        games=[dict(episode=i, split='FIT' if i<2 else 'HELDOUT', status='LOST',
                    steps=2 if i<2 else 3) for i in range(3)])


class Evaluator:
    def __init__(self, template):
        self.template, self.calls, self.stage = template, [], None

    def state(self):
        return 0

    def evaluate_games(self, leaf, p, true, seeds, depth, max_steps):
        assert not leaf.weights.flags.writeable and depth==2 and max_steps==8192
        if isinstance(leaf, core.SplitLeaf):
            assert not leaf.risk_weights.flags.writeable
            arm = 'CONTEXT_LOCAL'
        else:
            arm = 'SOURCE' if leaf is self.template else 'CONTEXT_MC'
        task = 'B' if true==.5 else 'A'
        assert true==core.PROBABILITIES[task]
        assert seeds==[310900000000+(100000 if task=='B' else 0)+episode for episode in range(32)]
        self.calls.append(dict(stage=self.stage, arm=arm, task=task, p=p, leaf=leaf,
            weights=leaf.weights, risk=leaf.risk_weights if arm=='CONTEXT_LOCAL' else None))
        utility = float(leaf.weights.sum())-100.*p
        if arm=='CONTEXT_LOCAL':
            utility+=float(leaf.risk_weights.sum())
        return dict(game_summaries=[dict(seed=seed, status='LOST', utility=utility, steps=1)
                    for seed in seeds], counts=dict(environment={}, planning={}), seconds=0., cpu_seconds=0.)


def fixture(monkeypatch, plans=None, capped=(), fit_fours=None):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    template = QueryTD(QueryParent(source, core.QUERY, core.QUERY, .5), 'PRIOR', BUILD)
    template.freeze(); engine = Evaluator(template)
    plans = plans or dict(A1=[(256, 0)], B1=[(256, 128)], A2=[(256, 5)],
                          B2=[(256, 125)], A3=[(256, 3)])
    fit_fours = fit_fours or {stage:128 if core.TASKS[stage]=='B' else 0 for stage in core.STAGES}
    events, acquisitions, facts = [], [], {}
    def acquire(leaf, life, parent, stage, router, emit, runtime, **kw):
        assert leaf is template and leaf.updates==0 and not leaf.weights.flags.writeable
        assert (life, parent)==(0, 0) and kw['p_four']==core.PROBABILITIES[core.TASKS[stage]]
        index = core.STAGES.index(stage)
        assert kw['warmup_seed_base']==310100000000+index*100000
        assert kw['training_seed_base']==310200000000+index*100000 and kw['raw_budget']==131072
        memory = SpawnMemory('LIBRARY'); decision = None
        prototypes = deepcopy(router.banks)
        for look, (n, k) in enumerate(plans[stage]):
            add_facts(memory, n, k); payload = memory.to_payload()
            assert not set(payload).intersection(('task', 'stage', 'phase', 'true_p_four', 'context_id'))
            decision = router.probe(payload); assert prototypes==router.banks
            if look<len(plans[stage])-1:
                assert decision['decision']=='PENDING_CONFIRMATION'
        if stage in capped:
            assert memory.observations_seen>=4096 and decision['decision']=='PENDING_CONFIRMATION'
            decision = dict(decision, decision='CAP_REUSE_UNRESOLVED', created=False)
        route = router.commit(payload, decision)
        if stage in capped:
            assert router.banks==prototypes
        p = memory.predict(); engine.stage = stage
        events.append((stage, 'DETECTION', route['context_id']))
        data = dataset(stage, fit_fours[stage]) if route['created'] else None; facts[stage] = data
        training = (dict(raw_tiles=20, counts=dict(environment={'actual_spawns':20},
            planning={'planning_calls':2}, learning={})) if route['created'] else None)
        total = memory.observations_seen; initial = plans[stage][0][0]
        acquisition = dict(warmup=dict(raw_tiles=total, initial_raw_tiles=initial,
            confirmation_raw_tiles=total-initial, confirmation_games=len(plans[stage])-1,
            detector_looks=len(plans[stage]), environment_counts={'actual_spawns':total},
            direct_counts={}, memory_counts=dict(memory.counts)), training=training,
            native_setup_counts={}, cpu_seconds=.2,
            reconstruction=dict(counts={}, memory_counts={}, cpu_seconds=.1))
        acquisitions.append((stage, route, data))
        return dict(route=route, detector_belief=dict(memory=payload, estimated_p_four=p),
                    dataset=data, acquisition=acquisition)
    def split(leaf, p, true, seeds, runtime, max_steps):
        return dict(engine.evaluate_games(leaf, p, true, seeds, 2, max_steps),
                    representation_counts={}, setup_counts={})
    monkeypatch.setattr(core, 'acquire_stage', acquire)
    monkeypatch.setattr(core, 'evaluate_split', split)
    fits = {arm:[] for arm in core.LEARNERS}
    native_mc, native_local = core.fit_consolidated, core.fit_split
    def record(arm, leaf, data):
        stage = next(stage for stage, value in facts.items() if value is data)
        assert events[-1][0]==stage and events[-1][1] in ('DETECTION', 'FIT')
        assert leaf.updates==0
        np.testing.assert_array_equal(leaf.weights, template.parent.source.weights)
        if arm=='CONTEXT_LOCAL':
            assert not np.any(leaf.risk_weights)
        entry = dict(stage=stage, leaf=leaf, data=data, weights=leaf.weights,
            risk=leaf.risk_weights if arm=='CONTEXT_LOCAL' else None)
        fits[arm].append(entry); events.append((stage, 'FIT', arm))
        return entry
    def mc(leaf, data, method, runtime, alpha):
        entry = record('CONTEXT_MC', leaf, data)
        assert method=='EPISODE_MEAN_MC' and alpha==.0025
        result = native_mc(leaf, data, method, runtime, alpha=alpha)
        entry['fitted_weights'] = leaf.weights.copy()
        return result
    def local(leaf, data, runtime, alpha):
        entry = record('CONTEXT_LOCAL', leaf, data); assert alpha==.0025
        result = native_local(leaf, data, runtime, alpha=alpha)
        entry.update(fitted_weights=leaf.weights.copy(), fitted_risk=leaf.risk_weights.copy())
        return result
    monkeypatch.setattr(core, 'fit_consolidated', mc)
    monkeypatch.setattr(core, 'fit_split', local)
    return template, engine, acquisitions, fits, events


def run_fixture(values):
    template, engine, _, _, _ = values
    return core._run_lifecycle(template, 0, 0, BUILD, engine, lambda row:None)


def costs(row):
    return core.build_accounting(dict(source_training_raw_tiles=100, dynamics_raw_tiles=5),
        [row], [dict(trace_bytes=11, cpu_seconds=1., compiler_cpu_seconds=.2)], .1, 1.)


def test_reused_bank_keeps_first_fit_belief_and_parameters_despite_new_detector_facts(monkeypatch):
    values = fixture(monkeypatch); row = run_fixture(values)
    template, engine, acquisitions, fits, _ = values
    assert [route['context_id'] for _, route, _ in acquisitions]==[0, 1, 0, 1, 0]
    assert 'evaluation_beliefs' not in row
    assert set(row['bank_beliefs'])=={'0', '1'}
    assert row['bank_beliefs']['0']['estimated_p_four']==1/258
    assert row['bank_beliefs']['1']['estimated_p_four']==.5
    assert template.updates==0 and len(engine.calls)==27
    for bank in row['context_bank']['banks']:
        assert bank['planning_belief']==row['bank_beliefs'][str(bank['context_id'])]
    for stage in ('A2', 'B2', 'A3'):
        assert row['stages'][stage]['dataset'] is None
        assert row['stages'][stage]['detector_belief']['estimated_p_four']!=row['stages'][stage]['planning_beliefs'][core.TASKS[stage]]['estimated_p_four']
    for call in engine.calls:
        stage = row['stages'][call['stage']]
        context = stage['evaluation_routes'][call['task']]['context_id']
        belief = row['bank_beliefs'][str(context)]
        assert stage['planning_beliefs'][call['task']]==belief
        assert call['p']==belief['estimated_p_four']
        assert stage['arms'][call['arm']]['evaluations'][call['task']]['estimated_p_four']==call['p']
    for arm in core.LEARNERS:
        assert [entry['stage'] for entry in fits[arm]]==['A1', 'B1']
        for entry in fits[arm]:
            assert entry['leaf'].updates==4
            np.testing.assert_array_equal(entry['weights'], entry['fitted_weights'])
            if arm=='CONTEXT_LOCAL':
                np.testing.assert_array_equal(entry['risk'], entry['fitted_risk'])
        for stage in ('A2', 'B2', 'A3'):
            assert row['stages'][stage]['arms'][arm]['fit']['method']=='NONE'
    for arm in core.ARMS:
        first = {'A':row['stages']['A1']['arms'][arm]['evaluations']['A'],
                 'B':row['stages']['B1']['arms'][arm]['evaluations']['B']}
        for stage in core.STAGES:
            for task, result in row['stages'][stage]['arms'][arm]['evaluations'].items():
                assert result==first[task]


def test_false_new_a_return_switches_both_head_and_fit_belief_for_all_arms(monkeypatch):
    plans = {stage:[(256, 128 if core.TASKS[stage]=='B' else 0)] for stage in core.STAGES}
    plans['A2']=[(256, 256)]
    values = fixture(monkeypatch, plans, fit_fours=dict(A1=0, B1=128, A2=256, B2=128, A3=0))
    row = run_fixture(values); _, engine, acquisitions, fits, _ = values
    assert [route['context_id'] for _, route, _ in acquisitions]==[0, 1, 2, 1, 0]
    a2 = row['stages']['A2']
    assert a2['context_route']['decision']=='CONFIRMED_NEW'
    assert a2['evaluation_routes']['A']==dict(kind='ACTUAL_STAGE_ROUTE', context_id=2)
    assert row['bank_beliefs']['2']['estimated_p_four']==257/258
    assert row['bank_beliefs']['2']['memory']==fits['CONTEXT_LOCAL'][2]['data']['fit_memory']
    for arm in core.ARMS:
        returned = next(call for call in engine.calls if (call['stage'], call['task'], call['arm'])==('A2', 'A', arm))
        assert returned['p']==257/258
        if arm!='SOURCE':
            assert returned['weights'] is fits[arm][2]['weights']
        assert a2['planning_beliefs']['B']==row['bank_beliefs']['1']
        assert a2['arms'][arm]['evaluations']['B']==row['stages']['B1']['arms'][arm]['evaluations']['B']
    first = row['stages']['A1']['arms']['SOURCE']['evaluations']['A']
    returned = a2['arms']['SOURCE']['evaluations']['A']
    assert returned['game_summaries']!=first['game_summaries']
    assert returned['estimated_p_four']!=first['estimated_p_four']
    assert row['stages']['A3']['arms']['SOURCE']['evaluations']['A']==first
    b2 = row['stages']['B2']
    assert b2['evaluation_routes']['A']['kind']=='READ_ONLY_FIRST_DETECTOR'
    assert b2['evaluation_routes']['A']['context_id']==0
    assert b2['planning_beliefs']['A']==row['bank_beliefs']['0']
    assert costs(row)['processed_training_samples']==dict(SOURCE=0, CONTEXT_MC=12, CONTEXT_LOCAL=12)


def test_cap_fallback_uses_stored_fit_belief_without_committing_detector_or_refitting(monkeypatch):
    plans = dict(A1=[(300, 30)], B1=[(300, 150)], A2=[(300, 60), (3796, 590)],
                 B2=[(256, 128)], A3=[(256, 26)])
    values = fixture(monkeypatch, plans, capped=('A2',)); row = run_fixture(values)
    _, engine, _, fits, _ = values; stage = row['stages']['A2']; route = stage['context_route']
    assert route['decision']=='CAP_REUSE_UNRESOLVED' and not route['created']
    assert not route['prototype_committed'] and route['prototype_before']==route['prototype_after']
    assert stage['dataset'] is None and stage['acquisition']['training'] is None
    assert stage['planning_beliefs']['A']==row['bank_beliefs']['0']
    assert stage['planning_beliefs']['A']['estimated_p_four']!=stage['detector_belief']['estimated_p_four']
    for arm in core.ARMS:
        returned = next(call for call in engine.calls if (call['stage'], call['task'], call['arm'])==('A2', 'A', arm))
        assert returned['p']==1/258
        if arm!='SOURCE':
            assert returned['weights'] is fits[arm][0]['weights']
            assert stage['arms'][arm]['fit']['method']=='NONE'
    cost = costs(row)
    assert cost['context_prototype_commits']==4 and cost['total_contexts_created']==2
    assert cost['new_confirmation_raw_tiles']==3796 and cost['new_confirmation_games']==1
    assert cost['unresolved_cap_stages']==[dict(lifecycle=0, stage='A2')]
    assert cost['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS, 5353)


def test_false_b_merge_keeps_selected_a_bank_belief_instead_of_task_identity(monkeypatch):
    plans = dict(A1=[(256, 0)], B1=[(256, 5)], A2=[(256, 0)], B2=[(256, 5)], A3=[(256, 0)])
    values = fixture(monkeypatch, plans); row = run_fixture(values)
    _, engine, acquisitions, fits, _ = values
    assert [route['context_id'] for _, route, _ in acquisitions]==[0, 0, 0, 0, 0]
    assert set(row['bank_beliefs'])=={'0'} and len(row['context_bank']['banks'])==1
    assert row['stages']['B1']['fit_snapshot'] is None
    assert row['stages']['B1']['detector_belief']['estimated_p_four']!=1/258
    assert all(call['p']==1/258 for call in engine.calls)
    for arm in core.LEARNERS:
        assert [entry['stage'] for entry in fits[arm]]==['A1']
        assert all(call['weights'] is fits[arm][0]['weights'] for call in engine.calls if call['arm']==arm)
    assert costs(row)['physical_acquisitions']==1


def test_shared_paid_confirmation_facts_and_head_costs_remain_closed(monkeypatch):
    plans = {stage:[(256, 128 if core.TASKS[stage]=='B' else 0)] for stage in core.STAGES}
    plans['B1']=[(256, 8), (256, 248)]
    values = fixture(monkeypatch, plans); row = run_fixture(values)
    _, engine, acquisitions, fits, _ = values
    assert row['stages']['B1']['context_route']['decision']=='CONFIRMED_NEW'
    for index in range(2):
        assert fits['CONTEXT_MC'][index]['data'] is fits['CONTEXT_LOCAL'][index]['data']
        assert fits['CONTEXT_MC'][index]['data'] is acquisitions[index][2]
    for stage in core.STAGES:
        for task in row['stages'][stage]['planning_beliefs']:
            paired = [call for call in engine.calls if (call['stage'], call['task'])==(stage, task)]
            assert {call['arm'] for call in paired}==set(core.ARMS)
            assert len({call['p'] for call in paired})==1
    cost = costs(row)
    assert cost['physical_detection_stages']==5 and cost['physical_acquisitions']==2
    assert cost['new_confirmation_raw_tiles']==256 and cost['new_confirmation_games']==1
    assert cost['detector_looks']==6 and cost['new_warmup_raw_tiles']==1536
    assert cost['new_actor_raw_tiles']==40 and cost['new_training_environment_observations']==1576
    assert cost['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS, 1681)
    assert cost['processed_training_samples']==dict(SOURCE=0, CONTEXT_MC=8, CONTEXT_LOCAL=8)
    assert cost['new_evaluation_games']==864 and cost['excluded_tail_raw_tiles']==6
    assert cost['private_head_weight_bytes_created']['CONTEXT_LOCAL']==2*cost['private_head_weight_bytes_created']['CONTEXT_MC']
    assert cost['old_target_training_raw_reused']==0 and cost['new_sequence_compute_closed']
