"""Real fits with five-stage observed routes, unresolved caps and paid extra detection."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import numpy as np

from acfqp.science import confirmed_context_run_v309 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1]/'reports/confirmed_context_v309/runtime_tests/driver'


def memory_for(n, k):
    memory = SpawnMemory('LIBRARY')
    add_facts(memory, n, k)
    return memory


def add_facts(memory, n, k):
    for index in range(n):
        memory.observe(2 if index<k else 1)


def dataset(stage):
    memory = memory_for(256, 128 if core.TASKS[stage]=='B' else 0)
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
        assert seeds==[309900000000+(100000 if task=='B' else 0)+episode for episode in range(32)]
        self.calls.append(dict(stage=self.stage, arm=arm, task=task, p=p, leaf=leaf,
            weights=leaf.weights, risk=leaf.risk_weights if arm=='CONTEXT_LOCAL' else None))
        utility = float(leaf.weights.sum())
        if arm=='CONTEXT_LOCAL':
            utility+=float(leaf.risk_weights.sum())
        return dict(game_summaries=[dict(seed=seed, status='LOST', utility=utility, steps=1)
                    for seed in seeds], counts=dict(environment={}, planning={}), seconds=0., cpu_seconds=0.)


def fixture(monkeypatch, plans=None, capped=()):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    template = QueryTD(QueryParent(source, core.QUERY, core.QUERY, .5), 'PRIOR', BUILD)
    template.freeze(); engine = Evaluator(template)
    plans = plans or {stage:[(256, 128 if core.TASKS[stage]=='B' else 0)] for stage in core.STAGES}
    events, acquisitions, facts = [], [], {}
    def acquire(leaf, life, parent, stage, router, emit, runtime, **kw):
        assert leaf is template and leaf.updates==0 and not leaf.weights.flags.writeable
        assert (life, parent)==(0, 0) and kw['p_four']==core.PROBABILITIES[core.TASKS[stage]]
        index = core.STAGES.index(stage)
        assert kw['warmup_seed_base']==309100000000+index*100000
        assert kw['training_seed_base']==309200000000+index*100000 and kw['raw_budget']==131072
        memory = SpawnMemory('LIBRARY'); decision = None
        prototypes = deepcopy(router.banks)
        for look, (n, k) in enumerate(plans[stage]):
            add_facts(memory, n, k)
            payload = memory.to_payload()
            assert not set(payload).intersection(('task', 'stage', 'phase', 'true_p_four', 'context_id'))
            decision = router.probe(payload)
            assert prototypes==router.banks
            if look<len(plans[stage])-1:
                assert decision['decision']=='PENDING_CONFIRMATION'
        if stage in capped:
            assert memory.observations_seen>=4096 and decision['decision']=='PENDING_CONFIRMATION'
            decision = dict(decision, decision='CAP_REUSE_UNRESOLVED', created=False)
        route = router.commit(payload, decision)
        assert route['statistics']==dict(observations=sum(n for n, _ in plans[stage]),
                                         fours=sum(k for _, k in plans[stage]))
        if stage in capped:
            assert router.banks==prototypes
        p = memory.predict(); engine.stage = stage
        events.append((stage, 'DETECTION', route['context_id']))
        data = dataset(stage) if route['created'] else None; facts[stage] = data
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


def test_normal_five_stage_routes_reuse_exact_fitted_parameters_and_fixed_evaluation_facts(monkeypatch):
    values = fixture(monkeypatch); row = run_fixture(values)
    template, engine, acquisitions, fits, events = values
    assert [route['context_id'] for _, route, _ in acquisitions]==[0, 1, 0, 1, 0]
    assert [route['created'] for _, route, _ in acquisitions]==[True, True, False, False, False]
    assert events==[('A1', 'DETECTION', 0), ('A1', 'FIT', 'CONTEXT_MC'), ('A1', 'FIT', 'CONTEXT_LOCAL'),
        ('B1', 'DETECTION', 1), ('B1', 'FIT', 'CONTEXT_MC'), ('B1', 'FIT', 'CONTEXT_LOCAL'),
        ('A2', 'DETECTION', 0), ('B2', 'DETECTION', 1), ('A3', 'DETECTION', 0)]
    assert template.updates==0 and np.array_equal(template.weights, template.parent.source.weights)
    assert row['evaluation_beliefs']['A']['estimated_p_four']==1/258
    assert row['evaluation_beliefs']['B']['estimated_p_four']==.5
    assert len(engine.calls)==27
    for call in engine.calls:
        assert call['p']==row['evaluation_beliefs'][call['task']]['estimated_p_four']
    for arm in core.LEARNERS:
        assert [record['stage'] for record in fits[arm]]==['A1', 'B1']
        for record in fits[arm]:
            assert record['leaf'].updates==4
            np.testing.assert_array_equal(record['weights'], record['fitted_weights'])
            if arm=='CONTEXT_LOCAL':
                np.testing.assert_array_equal(record['risk'], record['fitted_risk'])
        for task, index in [('A', 0), ('B', 1)]:
            selected = [call for call in engine.calls if call['arm']==arm and call['task']==task]
            assert len(selected)==(5 if task=='A' else 4)
            assert all(call['weights'] is fits[arm][index]['weights'] for call in selected)
            if arm=='CONTEXT_LOCAL':
                assert all(call['risk'] is fits[arm][index]['risk'] for call in selected)
        for stage in ('A2', 'B2', 'A3'):
            assert row['stages'][stage]['dataset'] is None
            assert row['stages'][stage]['arms'][arm]['fit']['method']=='NONE'
            assert row['stages'][stage]['context_updates_before'][arm]==row['stages'][stage]['context_updates_after'][arm]
    for arm in core.ARMS:
        first = {'A':row['stages']['A1']['arms'][arm]['evaluations']['A'],
                 'B':row['stages']['B1']['arms'][arm]['evaluations']['B']}
        for stage in core.STAGES:
            for task, evaluated in row['stages'][stage]['arms'][arm]['evaluations'].items():
                assert evaluated==first[task]
    for stage in core.STAGES:
        for task, route in row['stages'][stage]['evaluation_routes'].items():
            assert route['kind']==('ACTUAL_STAGE_ROUTE' if task==core.TASKS[stage] else 'READ_ONLY_FIRST_DETECTOR')
    assert row['context_bank']['counts']['probe_calls']==5
    assert row['context_bank']['counts']['prototype_commits']==5
    assert row['context_bank']['counts']['select_calls']==4
    assert [bank['visits'] for bank in row['context_bank']['banks']]==[3, 2]


def test_confirmed_false_new_a_return_is_paid_fitted_and_evaluated_without_an_oracle_override(monkeypatch):
    plans = {stage:[(256, 128 if core.TASKS[stage]=='B' else 0)] for stage in core.STAGES}
    plans['A2']=[(256, 256)]
    values = fixture(monkeypatch, plans); row = run_fixture(values)
    _, engine, acquisitions, fits, _ = values
    assert [route['context_id'] for _, route, _ in acquisitions]==[0, 1, 2, 1, 0]
    actual = row['stages']['A2']; assert actual['context_route']['decision']=='CONFIRMED_NEW'
    assert actual['context_route']['novelty_posterior']>=.99
    assert actual['dataset'] is not None
    assert actual['evaluation_routes']['A']==dict(kind='ACTUAL_STAGE_ROUTE', context_id=2)
    assert actual['evaluation_routes']['B']['context_id']==1
    for arm in core.LEARNERS:
        assert [record['stage'] for record in fits[arm]]==['A1', 'B1', 'A2']
        returned = next(call for call in engine.calls if call['stage']=='A2' and call['arm']==arm and call['task']=='A')
        final = next(call for call in engine.calls if call['stage']=='A3' and call['arm']==arm and call['task']=='A')
        assert returned['weights'] is fits[arm][2]['weights'] and final['weights'] is fits[arm][0]['weights']
        assert all(record['leaf'].updates==4 for record in fits[arm])
    cost = costs(row)
    assert cost['physical_acquisitions']==3 and cost['new_actor_raw_tiles']==60
    assert cost['processed_training_samples']==dict(SOURCE=0, CONTEXT_MC=12, CONTEXT_LOCAL=12)
    assert cost['total_contexts_created']==3 and cost['context_prototype_commits']==5


def test_cap_fallback_retains_unresolved_actual_route_without_prototype_commit_or_refit(monkeypatch):
    plans = dict(A1=[(300, 30)], B1=[(300, 150)], A2=[(300, 60), (3796, 590)],
                 B2=[(256, 128)], A3=[(256, 26)])
    values = fixture(monkeypatch, plans, capped=('A2',)); row = run_fixture(values)
    _, engine, acquisitions, fits, _ = values
    assert [route['context_id'] for _, route, _ in acquisitions]==[0, 1, 0, 1, 0]
    stage = row['stages']['A2']; route = stage['context_route']
    assert route['decision']=='CAP_REUSE_UNRESOLVED' and not route['created']
    assert not route['prototype_committed'] and route['prototype_before']==route['prototype_after']
    assert route['prototype_after']==dict(context_id=0, observations=300, fours=30, visits=1)
    assert route['novelty_posterior']<.99 and all(score['log_bayes_factor']<0. for score in route['scores'])
    assert route['statistics']==dict(observations=4096, fours=650)
    assert stage['dataset'] is None and stage['fit_snapshot'] is None
    assert stage['acquisition']['training'] is None
    assert stage['evaluation_routes']['A']==dict(kind='ACTUAL_STAGE_ROUTE', context_id=0)
    for arm in core.LEARNERS:
        assert [record['stage'] for record in fits[arm]]==['A1', 'B1']
        assert stage['arms'][arm]['fit']['method']=='NONE'
        assert stage['context_updates_before'][arm]==stage['context_updates_after'][arm]
        returned = next(call for call in engine.calls if call['stage']=='A2' and call['arm']==arm and call['task']=='A')
        assert returned['weights'] is fits[arm][0]['weights']
    cost = costs(row)
    assert cost['context_prototype_commits']==4 and cost['total_contexts_created']==2
    assert cost['unresolved_cap_stages']==[dict(lifecycle=0, stage='A2')]
    assert cost['context_decisions']['CAP_REUSE_UNRESOLVED']==1
    assert cost['new_confirmation_raw_tiles']==3796 and cost['new_confirmation_games']==1
    assert cost['new_initial_detector_raw_tiles']==1412 and cost['new_warmup_raw_tiles']==5208
    assert cost['new_actor_raw_tiles']==40 and cost['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS, 5353)


def test_paid_confirmation_and_shared_fit_inventory_close_economics_without_equal_head_capacity(monkeypatch):
    plans = {stage:[(256, 128 if core.TASKS[stage]=='B' else 0)] for stage in core.STAGES}
    plans['B1']=[(256, 8), (256, 248)]
    values = fixture(monkeypatch, plans); row = run_fixture(values)
    _, _, acquisitions, fits, _ = values
    assert row['stages']['B1']['context_route']['decision']=='CONFIRMED_NEW'
    assert row['stages']['B1']['context_route']['statistics']==dict(observations=512, fours=256)
    for index in range(2):
        assert fits['CONTEXT_MC'][index]['data'] is fits['CONTEXT_LOCAL'][index]['data']
        assert fits['CONTEXT_MC'][index]['data'] is acquisitions[index][2]
    cost = costs(row)
    assert cost['physical_detection_stages']==5 and cost['physical_acquisitions']==2
    assert cost['new_initial_detector_raw_tiles']==1280
    assert cost['new_confirmation_raw_tiles']==256 and cost['new_confirmation_games']==1
    assert cost['detector_looks']==6 and cost['new_warmup_raw_tiles']==1536
    assert cost['new_actor_raw_tiles']==40 and cost['new_training_environment_observations']==1576
    assert cost['new_raw_tiles_by_stage']==dict(A1=276, B1=532, A2=256, B2=256, A3=256)
    assert cost['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS, 1681)
    assert cost['new_training_environment_counts']['actual_spawns']==1576
    assert cost['excluded_tail_raw_tiles']==6 and cost['old_target_training_raw_reused']==0
    assert cost['processed_training_samples']==dict(SOURCE=0, CONTEXT_MC=8, CONTEXT_LOCAL=8)
    assert cost['new_evaluation_games']==864 and cost['total_contexts_created']==2
    assert cost['private_head_weight_bytes_created']['CONTEXT_LOCAL']==2*cost['private_head_weight_bytes_created']['CONTEXT_MC']
    assert cost['context_prototype_commits']==5 and cost['unresolved_cap_stages']==[]
    assert cost['new_sequence_compute_closed']
