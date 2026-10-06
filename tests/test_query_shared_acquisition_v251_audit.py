from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import gzip
from io import StringIO
import json
import random

from scripts import audit_query_shared_acquisition_v251 as audit


def test_released_A_cap_becomes_ordinary_budget_B_quota_remains_reserved():
    early = audit.budget_values(0, 3, 0, 768, 2304)
    assert early == dict(source_paid=3456, available=7616, pending_probe=1152,
        released=2304, future_source=1152, reference_paid=4224, adaptive_after=7616)
    later = audit.budget_values(0, 30, 128, 1920, 2304, 16)
    assert later['pending_probe'] == later['future_source'] == 0
    assert later['available'] == 7488 and later['adaptive_after'] == 7472
    assert later['reference_paid'] == 4608+128+1920+16
    full = audit.budget_values(0, 3, 0, 3072, 0)
    assert full['available'] == 5312 and full['pending_probe'] == 1152


def test_focused_type_total_then_row_balance_and_fixed_ready_continuation():
    s, d = audit.OPERATORS[:2]
    rows = [{s: 16, d: 0}, {s: 0, d: 0}, {s: 0, d: 0}]
    assert audit.original_query_choice(rows, [False, True, False], False) == dict(
        identity=2, operator=s, reason='unresolved_type_balanced_row', unresolved_types=[0, 2], all_ready=False)
    rows[2][s] = 16
    assert audit.original_query_choice(rows, [False, True, False], False) == dict(
        identity=0, operator=d, reason='unresolved_type_balanced_row', unresolved_types=[0, 2], all_ready=False)
    assert audit.original_query_choice(rows, [True]*3, False) is None
    assert audit.original_query_choice(rows, [True]*3, True) == dict(
        identity=0, operator=d, reason='all_ready_balanced_all_rows', unresolved_types=[], all_ready=True)
    # A later update can restore an unready type and must restore focused choice.
    assert audit.original_query_choice(rows, [True, True, False], True) == dict(
        identity=2, operator=d, reason='unresolved_type_balanced_row', unresolved_types=[2], all_ready=False)


def retained_preview_fixture():
    directory = audit.ROOT/'reports/shared_probe_timing_v249'
    with gzip.open(directory/'records_life_00_BEFORE_SHARED.jsonl.gz', 'rt') as stream:
        row = json.loads(next(stream))
    with gzip.open(directory/'results_life_00_BEFORE_SHARED.jsonl.gz', 'rt') as stream:
        result = json.loads(next(stream))
    original = row['initial_plan']
    preview = {field: deepcopy(original[field]) for field in (
        'case', 'evidence_counts', 'posterior', 'pure_vectors', 'queries', 'query_evidence', 'query_ready')}
    cost = (row['case']['operating'], row['case']['retry_cost'])
    preview.update(life=0, arm='QUERY_SHARED', preview_id=0, identity=row['identity'],
                   cost_index=audit.COSTS.index(cost), after_probe_batch=0)
    maximum = max(reference['profile_id'] for query in ('goal', 'risk')
                  for reference in preview['query_evidence']['queries'][query]['comparisons'])
    profiles = []
    with gzip.open(directory/'profiles_life_00_BEFORE_SHARED.jsonl.gz', 'rt') as stream:
        for line in stream:
            profiles.append(json.loads(line))
            if len(profiles) > maximum:
                break
    decisions = {profile['profile_id']: profile['certificate']['certified'] for profile in profiles}
    state = dict(a=[audit.paid.empty() for _ in range(3)], b=None, a_switch=None)
    state['a'][row['identity']] = deepcopy(preview['evidence_counts'])
    return row, preview, state, profiles, decisions, result


def test_real_retained_proofs_bind_query_only_preview_without_execution_events():
    row, preview, state, profiles, decisions, _ = retained_preview_fixture()
    original = deepcopy(state)
    used, work, keys, checks = set(), Counter(), set(), []
    ready = audit.audit_preview(preview, row['identity'], preview['cost_index'], state,
        profiles, decisions, used, work, keys, lambda name, ok: checks.append((name, ok)))
    assert all(ok for _, ok in checks) and ready == preview['query_ready']
    assert state == original and work['aux_query_previews'] == 1
    assert work['online_query_comparison_calls'] == 6
    assert used == {reference['profile_id'] for query in ('goal', 'risk')
                    for reference in preview['query_evidence']['queries'][query]['comparisons']}
    assert not ({'member', 'joint_constraints', 'mix', 'envelopes'} & set(preview))
    assert not any('project' in key or 'execution' in key for key in work)
    mutated = deepcopy(preview)
    mutated['evidence_counts'][audit.OPERATORS[0]]['DELIVERY'] += 16
    checks = []
    audit.audit_preview(mutated, row['identity'], preview['cost_index'], state,
        profiles, decisions, set(), Counter(), set(), lambda name, ok: checks.append((name, ok)))
    assert any(name == 'auxiliary_public_cost_native_counts_and_original_posterior_selection'
               and not ok for name, ok in checks)


def test_auxiliary_truth_score_is_original_query_regret_without_execution_score():
    row, preview, _, _, _, result = retained_preview_fixture()
    _, laws, _, _ = audit.paid.world(0)
    queries, false = audit.actual_query_scores(preview, laws[row['index']])
    assert queries == audit.fractions(result['history'][0]['queries'])
    assert false == result['history'][0]['false_query_certificates']
    assert set(queries) == {'reward', 'goal', 'risk'}


def test_eleven_conditions_include_auxiliary_errors_and_actual_shared_payment():
    method = dict(joint_completed=132, total_samples=47000,
                  late_b=dict(query_certified=27), a_return=dict(query_certified=54))
    method.update(dict.fromkeys(('false_query_certificates', 'aux_false_query_certificates',
        'false_execution_certificates', 'false_impossible_certificates',
        'false_goal_uppers', 'risk_violations', 'executed_risk_violations'), 0))
    methods = {arm: deepcopy(method) for arm in audit.ARMS}
    methods['UNIFORM_SHARED']['total_samples'] += 16
    assert len(audit.conditions(methods)) == 11 and all(audit.conditions(methods).values())
    methods['QUERY_FIXED']['aux_false_query_certificates'] = 1
    assert not audit.conditions(methods)['valid_certificates_and_execution']
    methods['QUERY_FIXED']['aux_false_query_certificates'] = 0
    methods['QUERY_SHARED']['total_samples'] += 16
    result = audit.conditions(methods)
    assert not result['actual_acquisition_saving_vs_uniform_shared']
    assert not result['actual_acquisition_nondegrading_vs_query_fixed']


def test_actual_fresh_source_and_uniform_A_B_tapes_replay_native_fees():
    from scripts import run_query_shared_acquisition_v251 as producer
    source_rows, bundles, work = [], {}, Counter()
    for life in audit.LIVES:
        cases, laws, identities, metadata = audit.paid.world(life)
        a, _ = producer.sources(life, 'A', laws, source_rows, work)
        b, _ = producer.sources(life, 'B', laws, source_rows, work)
        bundles[life] = dict(cases=cases, laws=laws, identities=identities, metadata=metadata, a=a, b=b)
    checks = []
    check = lambda name, ok: checks.append((name, ok))
    sources = audit.source_replay(source_rows, check)
    assert len(source_rows) == 864 and all(ok for _, ok in checks)
    assert sources == {life: {context: bundle[context] for context in ('a', 'b')}
                       for life, bundle in bundles.items()}
    life, arm, bundle = 0, 'UNIFORM_SHARED', bundles[0]
    state = producer.core.prepare(bundle['a'], life, 'ONE_WAY', work)
    independent = dict(a=deepcopy(bundle['a']), b=None, a_switch=None)
    original_sources = deepcopy(sources)
    profiles, previews, probes = StringIO(), StringIO(), StringIO()
    ledger = audit.ledger(0)
    generators, offsets = {}, {}
    result = producer.shared_a(life, arm, state, bundle, work, {}, profiles, {},
                               previews, probes, ledger, generators, offsets)
    saved = iter(json.loads(line) for line in probes.getvalue().splitlines())
    paid, released = audit.audit_shared_phase(result['phase'], saved, [], life, arm,
        independent, bundle['laws'], [], {}, set(), Counter(), set(), check)
    assert paid == 3072 and released == 0 and next(saved, None) is None
    assert all(ok for _, ok in checks) and state['a']['pools'] == independent['a']
    assert profiles.getvalue() == previews.getvalue() == ''
    producer.core.begin_b(state, bundle['b'], bundle['metadata']['changed_operator'], bundle['metadata']['b_to_a'], work)
    independent['a_switch'], independent['b'] = deepcopy(independent['a']), deepcopy(bundle['b'])
    switch = deepcopy(state['a_at_switch'])
    probes = StringIO()
    sequence = 192
    for identity in range(3):
        for _ in range(24):
            sequence += 1
            producer.observe_probe(life, arm, 'B', identity, bundle['metadata']['changed_operator'],
                state, bundle, 0, ledger, work, probes, generators, offsets, sequence)
    saved = iter(json.loads(line) for line in probes.getvalue().splitlines())
    paid = audit.replay_fixed_b(saved, life, arm, independent, bundle['laws'],
                               bundle['metadata'], 0, paid, released, check)
    assert paid == 4224 and next(saved, None) is None and all(ok for _, ok in checks)
    assert ledger == audit.ledger(4224) and state['b']['pools'] == independent['b']
    assert state['a_at_switch'] == switch and sources == original_sources
    assert state['a']['sources'] == bundle['a'] and state['b']['sources'] == bundle['b']
    counts = audit.prior.evidence_counts(independent, bundle['cases'][30], bundle['identities'][30],
                                         'ONE_WAY', bundle['metadata'])
    assert counts == producer.core.point_counts(bundle['cases'][30], state, bundle['identities'][30])


def test_complete_648_summary_schema_charges_actual_probes_and_all_model_scopes():
    from scripts import run_query_shared_acquisition_v251 as producer
    records, auxiliary, ledgers = [], [], []
    for life in audit.LIVES:
        cases, _, identities, _ = audit.paid.world(life)
        for arm in audit.ARMS:
            for index in audit.TARGETS:
                point = dict(false_query_certificates=0, false_execution_certificate=False,
                    false_impossible_certificate=False, goal_upper_ok=True, violation=False, coverage=True)
                records.append(dict(life=life, index=index, arm=arm, identity=identities[index],
                    stage=cases[index]['stage'], spent=16, query_certified=True, joint_completed=True,
                    execution_certified=True, goal_impossible=False, fallback=False,
                    budget_exhausted=False, model_seconds=.01, history=[point],
                    executed=dict(violation=False, actual_utility=3)))
            a_paid = 768 if arm == 'QUERY_SHARED' else 3072
            ledgers.append(dict(life=life, arm=arm, cap_samples=4224, paid_samples=a_paid+1152,
                pending_reserved_samples=0, released_samples=3072-a_paid,
                by_context=dict(A=a_paid, B=1152), probe_batches=(a_paid+1152)//16))
            if arm != 'UNIFORM_SHARED':
                auxiliary.extend(dict(life=life, arm=arm, false_aux_query_certificates=0) for _ in range(12))
    scopes = ('planning', 'initialization', 'begin_b', 'probe_pool_updates', 'query_previews',
              'shared_acquisition', 'acquisition', 'observation', 'probe_draw')
    timings = {scope: {arm: {life: (1. if scope in ('query_previews', 'shared_acquisition') else 0.)
                            for life in audit.LIVES} for arm in audit.ARMS} for scope in scopes}
    actual = producer.summarize(records, auxiliary, timings, ledgers)
    saved_timings = {scope: {arm: {str(life): seconds for life, seconds in times.items()}
                            for arm, times in arms.items()} for scope, arms in timings.items()}
    methods, lives, conditions, paired = audit.summaries(records, saved_timings, ledgers, auxiliary)
    assert actual['methods'] == methods and actual['life_summaries'] == lives
    assert actual['conditions'] == conditions and actual['paired'] == paired
    assert actual['records'] == 648 and actual['physical_probe_samples'] == 31104
    assert actual['new_environment_observations'] == 55296
    assert methods['QUERY_SHARED']['model_seconds'] == 6
    assert methods['QUERY_SHARED']['released_probe_samples'] == 6912
    assert methods['QUERY_SHARED']['total_samples'] == 23040
