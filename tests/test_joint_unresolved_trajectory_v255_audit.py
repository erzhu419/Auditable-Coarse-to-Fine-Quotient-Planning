"""Independent filtered sampling, retained-prefix reuse and actual cost tests."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import io
import json

from scripts import audit_joint_unresolved_trajectory_v255 as audit
from scripts import run_joint_unresolved_trajectory_v255 as producer


def outcomes():
    return [{audit.S: short, audit.D: detour, audit.R: retry} for short, detour, retry in (
        ('DELIVERY', 'DELIVERY', None), ('LOST', 'DELIVERY', None),
        ('DELIVERY', 'RECOVERY', 'DELIVERY'), ('DELIVERY', 'LOST', None),
        ('LOST', 'RECOVERY', 'LOST'), ('DELIVERY', 'DELIVERY', None))]


def evidence(ready):
    return dict(all_ready=ready, threshold=4320,
        queries={query: dict(policy=policy, certified=ready or query == 'reward', comparisons=[])
                 for query, policy in (('reward', 'WAIT'), ('goal', 'SHORT'), ('risk', 'DETOUR_RETURN'))})


def record(item, ready, paid=4608, check_id=0):
    return dict(deepcopy(item), check_id=check_id, queries={query: dict(policy=decision['policy'])
        for query, decision in evidence(ready)['queries'].items()}, trajectory=evidence(ready),
        total_paid_samples=paid, source_paid_samples=4608, acquisition_paid_samples=paid-4608,
        model_seconds=dict(point_vectors=1., trajectory=2.))


def test_filtered_cursor_preserves_RR_order_and_current_all_cost_readiness_can_regress():
    for cursor in range(7):
        assert audit.choose_type(cursor, [0, 1, 2]) == cursor % 3
        for eligible in ([0, 2], [1], [1, 2]):
            assert producer.core.select_type(cursor, eligible) == (audit.choose_type(cursor, eligible), audit.choose_type(cursor, eligible)+1)
    checks = [dict(identity=identity, cost_index=cost, trajectory=evidence(identity != 1))
              for identity in range(3) for cost in range(4)]
    assert audit.current_ready_by_type(checks) == [True, False, True]
    checks[0]['trajectory']['all_ready'] = False
    checks[4]['trajectory']['all_ready'] = True
    assert audit.current_ready_by_type(checks) == [False, False, True]
    assert audit.current_ready_by_type(checks) == producer.core.ready_by_type(checks)
    assert audit.acquisition_end(7552, 14144) == 7680
    assert audit.acquisition_end(14080, 14144) == 14144


def test_actual_conditional_batches_independently_replay_filtered_types_offsets_tails_and_fees(monkeypatch):
    for module, source, acquisition in ((audit, 'SOURCE_BASE', 'ACQUISITION_BASE'), (producer, 'SOURCE_BASE', 'TARGET_BASE')):
        monkeypatch.setattr(module, source, 123000)
        monkeypatch.setattr(module, acquisition, 124000)
    _, laws, _, _ = producer.task.world(0)
    arm, work = audit.ARMS[1], Counter()
    states, paid = [producer.evidence.new_type_state() for _ in range(3)], [0, 0, 0]
    simulator, tape, rounds = producer.PrimitiveSimulator(0, laws[:3], work), io.StringIO(), io.StringIO()
    step, round_id, cursor, batches = 0, 0, 0, []
    snapshots = []
    schedule = [(0, 17, [0, 1, 2]), (1, 31, [0, 2]), (2, 43, [1])]
    for batch_id, target, eligible in schedule:
        sampled = producer.sample_batch(0, arm, batch_id, target, eligible, states, simulator,
            step, round_id, cursor, paid, tape, rounds, work)
        step, round_id, cursor = (sampled[field] for field in ('step', 'round_id', 'cursor'))
        batches.append(dict(sampled['batch'], prior_check_id=None if batch_id == 0 else batch_id-1))
        snapshots.append(deepcopy(states))
    primitive_rows = [json.loads(line) for line in tape.getvalue().splitlines()]
    round_rows = [json.loads(line) for line in rounds.getvalue().splitlines()]
    state, checks = audit.initial_state(0), []
    for batch, snapshot, (batch_id, target, eligible) in zip(batches, snapshots, schedule):
        expected = audit.replay_batch(0, arm, batch_id, target, eligible, state, primitive_rows, round_rows,
            laws, lambda name, ok: checks.append((name, ok)))
        assert expected == batch
        assert state['native'] == [item['native_counts'] for item in snapshot]
        assert state['complete'] == [item['rounds'] for item in snapshot]
        assert state['tails'] == [item['tail_s_samples'] for item in snapshot]
    assert all(ok for _, ok in checks)
    assert len(primitive_rows) == work['controlled_samples'] == 43
    assert sum(paid) == 26 and state['acquisition_paid_by_type'] == paid
    assert sum(state['tails']) > 0 and any(row['operator'] == audit.R for row in primitive_rows)
    later = next(row for row in primitive_rows if row['batch_id'] == 2)
    assert later['identity'] == 1 and later['seed'] == 124003
    invalid = deepcopy(primitive_rows)
    invalid[later['step_index']-1]['seed'] += 1
    failures, state = [], audit.initial_state(0)
    for batch_id, target, eligible in schedule:
        audit.replay_batch(0, arm, batch_id, target, eligible, state, invalid, round_rows, laws,
            lambda name, ok: failures.append(name) if not ok else None)
    assert failures == ['own_actual_primitive_seed_continuous_offset_filtered_cursor_and_conditional_path']


def test_complete_actual_prefix_proof_cache_reuses_exact_proof_and_detects_changed_payload(monkeypatch):
    observations, case = outcomes(), audit.case_for(0, audit.ARMS[1], 0, 0)
    chosen = audit.mathematics.point_queries(audit.mathematics.empirical_vectors(observations, case))
    queries = {query: dict(policy=policy) for query, policy in chosen.items()}
    saved = producer.evidence.trajectory_certificates(observations, case, queries, {})
    cache, checks, calls = {}, [], []
    original = audit.mathematics.audit_trajectory_certificate
    def evaluate(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(audit.mathematics, 'audit_trajectory_certificate', evaluate)
    checker = lambda name, ok: checks.append((name, ok))
    first = audit.audit_direct_evidence(0, observations, case, chosen, saved, cache, checker)
    assert audit.audit_direct_evidence(0, observations, case, chosen, deepcopy(saved), cache, checker) == first
    assert len(calls) == 1 and all(ok for _, ok in checks)
    invalid = deepcopy(saved)
    invalid['queries']['goal']['comparisons'][0]['n'] = 2
    failures = []
    audit.audit_direct_evidence(0, observations, case, chosen, invalid, cache,
        lambda name, ok: failures.append(name) if not ok else None)
    assert failures == ['same_actual_prefix_cost_and_direction_reuses_exact_audited_direct_proof']
    extended = observations+[observations[0]]
    new_chosen = audit.mathematics.point_queries(audit.mathematics.empirical_vectors(extended, case))
    fresh = producer.evidence.trajectory_certificates(extended, case,
        {query: dict(policy=policy) for query, policy in new_chosen.items()}, {})
    audit.audit_direct_evidence(0, extended, case, new_chosen, fresh, cache, checker)
    assert len(calls) == 2 and len(cache) == 2 and all(ok for _, ok in checks)


def test_all12_actual_queries_bind_native_prefix_and_point_cache_without_repeating_unchanged_types(monkeypatch):
    arm, state = audit.ARMS[1], audit.initial_state(0)
    state['step'] = audit.SOURCE_COST
    for identity in range(3):
        state['complete'][identity] = outcomes()
        state['last_ids'][identity] = identity+1
        for observation in outcomes():
            for operator, outcome in observation.items():
                if outcome is not None:
                    state['native'][identity][operator][outcome] += 1
    work, score_cache, checks = Counter(), {}, []
    saved = []
    for identity in range(3):
        producer_state = producer.evidence.new_type_state()
        for n, observation in enumerate(outcomes(), 1):
            producer.evidence.observe_round(producer_state, observation, identity+1)
        for cost in range(4):
            saved.append(producer.check_case(0, arm, 0, identity, cost, producer_state, 4608, score_cache, work))
    vector_calls, original = [], audit.mathematics.empirical_vectors
    def vectors(*args):
        vector_calls.append(1)
        return original(*args)
    monkeypatch.setattr(audit.mathematics, 'empirical_vectors', vectors)
    proof_cache, point_cache, score_keys = {}, {}, {}
    check = lambda name, ok: checks.append((name, ok))
    first = audit.audit_check(0, arm, 0, saved, state, proof_cache, point_cache, score_keys, check)
    second_records = deepcopy(saved)
    for item in second_records:
        item['check_id'] = 1
    second = audit.audit_check(0, arm, 1, second_records, state, proof_cache, point_cache, score_keys, check)
    assert all(ok for _, ok in checks) and len(vector_calls) == len(point_cache) == 12
    assert first['ready_by_type'] == second['ready_by_type']
    assert len(second['case_refs']) == 12 and all(item['check_id'] == 1 for item in second['case_refs'])
    assert len(score_keys) == len(score_cache)
    invalid = deepcopy(second_records)
    invalid[0]['source_paid_samples'] = 0
    failures = []
    audit.audit_check(0, arm, 1, invalid, state, proof_cache, point_cache, score_keys,
        lambda name, ok: failures.append(name) if not ok else None)
    assert failures == ['current_check_own_native_prefix_joint_rounds_tails_fees_and_shared_choices']


def test_public_roster_and_stopped_projection_keep_actual_paid_source_and_original_evidence():
    roster = audit.public_roster()
    assert roster == producer.public_roster({life: producer.task.world(life) for life in audit.LIVES})
    assert len(roster) == 360 and Counter(item['kind'] for item in roster) == dict(CHECKPOINT=216, RETURN_PROJECTION=144)
    item = next(item for item in roster if item['kind'] == 'RETURN_PROJECTION')
    original = record(dict(life=item['life'], arm=item['arm'], kind='INTERMEDIATE_CHECK', identity=item['identity'],
        cost_index=item['cost_index'], index=None, case=audit.case_for(item['life'], item['arm'], item['identity'], item['cost_index'])),
        True, paid=4864, check_id=1)
    saved = deepcopy(original)
    projected = audit.project(original, item)
    assert original == saved
    assert projected['source_paid_samples'] == 4608 and projected['acquisition_paid_samples'] == 256
    assert projected['total_paid_samples'] == 4864 and not projected['checkpoint_reached']
    assert projected['selected_check_id'] == 1 and projected['trajectory'] == saved['trajectory']
    assert projected['case'] == item['case'] and not any(projected['model_seconds'].values())


def test_all_intermediate_postfreeze_score_cases_normalize_and_mutated_regret_is_detected():
    _, laws, _, _ = audit.mathematics.trajectory.world(0)
    case = audit.case_for(0, audit.ARMS[1], 0, 0)
    item = record(dict(life=0, arm=audit.ARMS[1], kind='INTERMEDIATE_CHECK', identity=0, cost_index=0,
        index=None, case=case), False)
    expected = producer.score_record(item, laws[0])
    serialized = json.loads(json.dumps([expected], default=str))
    checks = []
    independent = audit.score_rows([item], serialized, laws, lambda name, ok: checks.append((name, ok)))
    assert all(ok for _, ok in checks) and independent[0]['kind'] == 'INTERMEDIATE_CHECK'
    invalid = deepcopy(serialized)
    invalid[0]['queries']['goal']['regret'] = str(F(invalid[0]['queries']['goal']['regret'])+F(1, 100))
    checks = []
    audit.score_rows([item], invalid, laws, lambda name, ok: checks.append((name, ok)))
    assert checks == [('normalized_postfreeze_truth_queries_and_all_false_certificate_counts', False)]


def test_summary_charges_both_sources_and_requires_joint_gain_cost_and_all_intermediate_errors():
    records = [record(item, item['identity'] != (1, 2, 1)[item['life']] or item['arm'] == audit.ARMS[1] and item['life'] == 0)
               for item in audit.public_roster()]
    artifacts = []
    for life in audit.LIVES:
        for arm in audit.ARMS:
            paid = audit.CAPS[life]-(100 if arm == audit.ARMS[1] else 0)
            artifacts.append(dict(life=life, arm=arm, primitive_samples=paid, source_samples=4608,
                acquisition_samples=paid-4608, acquisition_paid_by_type=[paid-4608, 0, 0], intermediate_records=12,
                stop_reason='full_cap', final_ready_by_type=[True, False, True], acquisition_batches=1,
                timings=dict.fromkeys(producer.MODEL_SCOPES, 1.), observation_seconds=2., output_seconds=3.,
                cache_statistics={}, work={}))
    scores = [dict(arm=arm, false_certificates=0) for arm in audit.ARMS]
    result = audit.summarize(records, scores, scores, artifacts)
    assert result == producer.summarize(records, scores, scores, artifacts)
    assert result['positive_qualification_signal'] and result['physical_source_samples'] == 27648
    assert result['physical_observations'] == 96468 and result['terminal_paired']['query_ready']['gains'] == 8
    assert result['methods'][audit.ARMS[0]]['terminal']['query_ready'] == 48
    assert result['methods'][audit.ARMS[1]]['terminal']['query_ready'] == 56
    intermediate_failure = [dict(arm=audit.ARMS[1], false_certificates=1)]
    assert not audit.summarize(records, scores, intermediate_failure, artifacts)['positive_qualification_signal']
    expensive = deepcopy(artifacts)
    for item in expensive:
        if item['arm'] == audit.ARMS[1]:
            item['primitive_samples'] += 101
    assert not audit.summarize(records, scores, scores, expensive)['positive_qualification_signal']
