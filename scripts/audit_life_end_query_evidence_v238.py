"""Independent paid-life endpoint and global predictive certificate audit.

No V238 producer is imported. Raw paid batch increments supply endpoint
counts; normalized posterior recursion and old independent weak-dual
arithmetic verify the new certificates without repeating seed replay.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from pathlib import Path
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_joint_query_evidence_v235 as evidence
from scripts import audit_joint_query_qualification_v235 as global_audit
from scripts import audit_source_predictive_evidence_v236 as predictive
from scripts import audit_kernel_query_profile_v232 as arithmetic
from scripts.analyze_scoped_lifecycle_v229 import world

OUTPUT = ROOT/'reports/life_end_query_evidence_v238'
OPERATORS, POLICIES = tuple(evidence.ALPHABETS), global_audit.POLICIES


def raw_paid_banks(source_records, target_rows):
    """Rebuild physical reveal labels and pools directly from retained batches."""
    sources, targets, a_before, costs = defaultdict(list), defaultdict(list), defaultdict(list), Counter()
    latest = {}
    by_scope = defaultdict(list)
    for source in source_records:
        by_scope[source['life'], source['context']].append(source)
    order, current_life, b_seen = 0, None, False

    def reveal_sources(life, context):
        nonlocal order
        for raw in by_scope[life, context]:
            identity = raw['slot'] if context == 'A' else raw['slot']-3
            segment = {field: raw[field] for field in (
                'life', 'context', 'index', 'operator', 'seed', 'draw_start', 'draw_end')}
            segment.update(kind='source', availability_order=order)
            sources[life, context, identity, raw['operator']].append((segment, raw['increments']))
            order += 1

    for row in target_rows:
        life, context, identity, arm = row['life'], row['case']['context'], row['identity'], row['arm']
        if life != current_life:
            current_life, b_seen = life, False
            reveal_sources(life, 'A')
        if context == 'B' and not b_seen:
            reveal_sources(life, 'B')
            b_seen = True
        costs[life, arm] += row['spent']
        latest[life, arm, context, identity] = row['index']
        for raw in row['batches']:
            operator = raw['operator']
            segment = dict(life=life, context=context, index=row['index'], operator=operator,
                seed=row['seeds'][operator], draw_start=raw['draw_start'], draw_end=raw['draw_end'],
                kind='target', arm=arm, availability_order=order)
            batch = segment, raw['increments']
            targets[life, arm, context, identity, operator].append(batch)
            if row['case']['stage'] == 'A':
                a_before[life, arm, identity, operator].append(batch)
            order += 1
    source_costs = Counter()
    for source in source_records:
        source_costs[source['life']] += source['draw_end']-source['draw_start']
    return dict(sources=sources, targets=targets, a_before=a_before, costs=costs,
                source_costs=source_costs, latest=latest)


def endpoint_batches(tape, banks, metadata):
    """B inherits A at switch, while A uses all own same-identity A targets."""
    life, arm, context, identity = tape['life'], tape['arm'], tape['case']['context'], tape['identity']
    result = {}
    for operator in OPERATORS:
        own = banks['sources'][life, context, identity, operator]+banks['targets'][life, arm, context, identity, operator]
        if context == 'B' and operator != metadata['changed_operator']:
            old_identity = metadata['b_to_a'][identity]
            inherited = banks['sources'][life, 'A', old_identity, operator]+banks['a_before'][life, arm, old_identity, operator]
            own = inherited+own
        result[operator] = own
    return result


def raw_segments_match(tape, expected):
    """Every outcome is used once; original metadata and batch counts match."""
    for operator, batches in expected.items():
        provenance, queue = tape['provenance'][operator], tape['operators'][operator]
        if len(provenance) != len(batches):
            return False
        cursor = 0
        for saved, (segment, increments) in zip(provenance, batches):
            amount = sum(increments.values())
            expected_segment = dict(segment, queue_start=cursor, queue_end=cursor+amount)
            if saved != expected_segment or segment['draw_end']-segment['draw_start'] != amount:
                return False
            actual = Counter(queue[cursor:cursor+amount])
            if any(actual[cat] != increments.get(cat, 0) for cat in evidence.ALPHABETS[operator]):
                return False
            cursor += amount
        if cursor != len(queue):
            return False
    return True


def audit_certificate(split, case, query, chosen, other, saved, check):
    cert = arithmetic.fractions(saved)
    family = evidence.relevant_family(query, chosen, other)
    training, validation = (predictive.named_counts(family, split[field]) for field in ('training', 'validation'))
    embedding = global_audit.embedded_counts(validation)
    check('source_training_and_validation_only_sufficient_counts', cert['family'] == family
        and cert['training_counts'] == training and cert['validation_counts'] == validation
        and cert['embedded_counts'] == embedding)
    check('unchanged_comparison_and_confidence_event', (cert['query'], cert['chosen'], cert['other'])
        == (query, chosen, other) and cert['threshold'] == evidence.THRESHOLD
        and cert['regret_threshold'] == evidence.REGRET)
    check('global_gap_preserving_embedding', global_audit.preserved_gap(case, query, chosen, other, family))
    prediction = F(1)
    minimum = F(0)
    for name, row in validation.items():
        value = predictive.posterior_predictive(tuple(training[name][cat] for cat in row), tuple(row.values()))
        prediction *= value
        minimum += arithmetic.logarithm(value)[0]
    check('independent_sequential_predictive_numerator_lower', cert['log_predictive_lower'] <= minimum)
    check('outward_event_threshold_upper', cert['log_threshold_upper'] >= arithmetic.logarithm(evidence.THRESHOLD)[1])
    kind = cert['witness_kind']
    if kind == 'bad_null_mle':
        mle = {op: {cat: F(count, sum(row.values())) if sum(row.values()) else F(1, len(row))
                     for cat, count in row.items()} for op, row in embedding.items()}
        gap = evidence.utility(case, query, other, mle)-evidence.utility(case, query, chosen, mle)
        uniform_counts = {op: dict.fromkeys(categories, 0) for op, categories in evidence.ALPHABETS.items()}
        _, parameters = evidence.named_projection(family, uniform_counts, mle)
        likelihood = F(1)
        for name, row in validation.items():
            for category, count in row.items():
                likelihood *= parameters[name][category]**count
        check('exact_bad_validation_mle_and_predictive_membership', cert['bad_null_kernel'] == mle
            and cert['bad_null_gap'] == gap >= evidence.REGRET and prediction <= likelihood)
        check('mle_is_unknown_with_no_global_certificate', cert['status'] == 'unknown' and not cert['certified']
            and cert['partitions'] == 0 and not cert['leaves']
            and cert['log_bad_likelihood_upper'] is None and cert['log_e_lower'] is None)
        return False
    partitions = 32 if arithmetic.bilinear(case, query, chosen, other) else 1
    leaves = cert['leaves']
    check('fixed_partition_covers_all_retry_probabilities', cert['partitions'] == partitions
        and [leaf['retry_interval'] for leaf in leaves] == [[F(i, partitions), F(i+1, partitions)]
            for i in range(partitions)])
    slope = (arithmetic.gap(case, query, chosen, other, arithmetic.corner_kernel(0, 'RECOVERY', 1))
             -arithmetic.gap(case, query, chosen, other, arithmetic.corner_kernel(0, 'RECOVERY', 0)))
    check('exact_retry_interaction_slope', cert['retry_slope'] == slope)
    uppers = [arithmetic.audit_leaf(case, query, chosen, other, embedding, leaf, check) for leaf in leaves]
    finite = [upper for upper in uppers if upper is not None]
    if not finite:
        ready = kind == 'empty_global_bad_null'
        check('entire_global_bad_null_empty', ready and len(leaves) == partitions
            and cert['log_bad_likelihood_upper'] is None and cert['log_e_lower'] is None)
    else:
        check('global_validation_likelihood_upper', kind == 'global_likelihood_dual'
            and cert['log_bad_likelihood_upper'] >= max(finite))
        check('outward_global_predictive_ratio_lower', cert['log_e_lower']
            <= cert['log_predictive_lower']-cert['log_bad_likelihood_upper'])
        ready = cert['log_e_lower'] > cert['log_threshold_upper']
    check('strict_complete_bad_null_decision', cert['certified'] == ready
          and cert['status'] == ('certified' if ready else 'unknown'))
    return ready


def run():
    begun, checks, failures = perf_counter(), Counter(), []
    location = {}

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(dict(check=name, location=location.copy()))

    key = predictive.key
    raw_directory = ROOT/'reports/oracle_gap_lifecycle_v231'
    old_directory = ROOT/'reports/joint_query_qualification_v235'
    original_directory = ROOT/'reports/kernel_query_profile_v232'
    metadata, summary = evidence.load(OUTPUT/'run.json'), evidence.load(OUTPUT/'summary.json')
    check('paid_inputs_independently_audited', evidence.load(raw_directory/'analysis.json')['valid']
          and evidence.load(old_directory/'analysis.json')['valid'])
    raw_rows = []
    for path in sorted(raw_directory.glob('records_life_*.jsonl.gz')):
        raw_rows.extend(evidence.read_rows(path))
    raw_sources = evidence.load(raw_directory/'source_records.json')
    banks = raw_paid_banks(raw_sources, raw_rows)
    originals = {key(row): row for row in evidence.read_rows(original_directory/'inputs.jsonl.gz')}
    old_tapes = {key(row): row for row in evidence.read_rows(old_directory/'tapes.jsonl.gz')}
    old_results = {key(row): row for row in evidence.read_rows(old_directory/'records.jsonl.gz')}
    truth = {key(row): row for row in evidence.load(ROOT/'reports/paired_query_score_v233/scores.json')}
    scores = {key(row): row for row in evidence.load(OUTPUT/'scores.json')}
    tapes, rows = evidence.read_rows(OUTPUT/'tapes.jsonl.gz'), evidence.read_rows(OUTPUT/'records.jsonl.gz')
    worlds = {life: world(life) for life in range(3)}
    check('frozen_whole_life_endpoint_and_event_budget', metadata['complete']
        and metadata['stream_count'] == 48 and metadata['threshold'] == evidence.THRESHOLD
        and metadata['partitions'] == 32 and metadata['delta_per_life_arm'] == '1/20'
        and metadata['certification_index'] == 77 and metadata['qualification_only']
        and not metadata['scientific_gate_changed'] and metadata['new_observations'] == metadata['new_paid_samples'] == 0
        and metadata['phases'] == ['protocol_frozen', 'tapes_frozen', 'certificates_frozen',
                                  'saved_truth_evaluated', 'complete'])
    check('original_twenty_four_case_roster', len(rows) == len(tapes) == 24
        and [key(row) for row in rows] == [key(row) for row in tapes] == list(originals)
        and metadata['selected'] == [{field: row[field] for field in ('life', 'index', 'arm', 'kind', 'phase')}
                                     for row in tapes])
    cache, false_certificates, comparison_count, leaf_count, raw_segment_count = set(), 0, 0, 0, 0
    statuses, families, witness_kinds = Counter(), Counter(), Counter()
    for tape, row in zip(tapes, rows):
        snapshot, life, arm = key(row), row['life'], row['arm']
        location = dict(life=life, index=row['index'], arm=arm)
        early, original = old_tapes[snapshot], originals[snapshot]
        cases, _, identities, world_metadata = worlds[life]
        check('original_known_case_identity_and_switch_interface', cases[tape['index']] == tape['case']
            and identities[tape['index']] == tape['identity'] and tape['changed_operator'] == world_metadata['changed_operator']
            and all(tape[field] == early[field] for field in ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity')))
        expected = endpoint_batches(tape, banks, world_metadata)
        check('every_endpoint_segment_matches_physical_paid_batch', raw_segments_match(tape, expected))
        raw_segment_count += sum(map(len, expected.values()))
        check('original_outcome_prefix_is_preserved', all(tape['operators'][op][:len(early['operators'][op])]
              == early['operators'][op] for op in OPERATORS))
        latest = banks['latest'][life, arm, tape['case']['context'], tape['identity']]
        scope_end = 53 if tape['case']['context'] == 'B' else 77
        evidence_end = max(segment['index'] for batches in expected.values() for segment, _ in batches)
        check('new_certification_time_and_actual_last_evidence', tape['endpoint_index'] == tape['certificate_index'] == 77
            and tape['evidence_scope_end_index'] == scope_end and tape['latest_pool_index'] == latest
            and tape['evidence_end_index'] == evidence_end <= latest <= scope_end)
        source_fee, target_fee = banks['source_costs'][life], banks['costs'][life, arm]
        fees = dict(source_paid_samples=source_fee, history_paid_samples=target_fee, current_paid_samples=0,
            target_paid_samples=target_fee, total_reference_paid_samples=source_fee+target_fee,
            evidence_samples=sum(len(values) for values in tape['operators'].values()))
        check('complete_life_costs_and_separate_early_reference', tape['fees'] == fees
            and tape['early_fees'] == early['fees'] and source_fee == 4608)
        split = predictive.split_tape(tape)
        check('record_keeps_endpoint_descriptors_and_full_row_lengths', all(row[field] == tape[field] for field in (
            'life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees', 'early_fees', 'endpoint_index',
            'certificate_index', 'evidence_end_index'))
            and row['row_lengths'] == {op: len(values) for op, values in tape['operators'].items()}
            and row['training_row_lengths'] == {op: len(values) for op, values in split['training'].items()}
            and row['validation_row_lengths'] == {op: len(values) for op, values in split['validation'].items()}
            and row['new_observations'] == row['new_paid_samples'] == 0
            and row['old_query_ready'] == original['terminal_plan']['query_ready']
            and row['v235_query_ready'] == old_results[snapshot]['query_ready'])
        reward = row['queries']['reward']
        check('exact_reward_wait_policy', reward == dict(policy='WAIT', certified=True, kind='known_nonnegative_cost')
            and original['terminal_plan']['queries']['reward']['policy'] == 'WAIT')
        before, row_comparisons = len(cache), 0
        for query in ('goal', 'risk'):
            decision, chosen = row['queries'][query], original['terminal_plan']['queries'][query]['policy']
            alternatives = [policy for policy in POLICIES if policy != chosen]
            check('original_policy_with_complete_alternative_roster', decision['policy'] == chosen
                and [cert['other'] for cert in decision['comparisons']] == alternatives)
            ready = []
            for other, cert in zip(alternatives, decision['comparisons']):
                location.update(query=query, chosen=chosen, other=other)
                ready.append(audit_certificate(split, tape['case'], query, chosen, other, cert, check))
                def count_key(name):
                    return tuple(sorted((field, tuple(sorted(values.items()))) for field, values in cert[name].items()))
                cache.add((tape['case']['operating'], F(tape['case']['retry_cost']), query, chosen, other,
                           cert['family'], count_key('training_counts'), count_key('validation_counts'), 32))
                comparison_count += 1
                row_comparisons += 1
                leaf_count += len(cert['leaves'])
                statuses[cert['status']] += 1
                families[cert['family']] += 1
                witness_kinds[cert['witness_kind']] += 1
            check('query_is_complete_comparison_and', decision['certified'] == all(ready))
        check('all_queries_and_and_profile_cache_accounting', row['query_ready'] == all(
            decision['certified'] for decision in row['queries'].values())
            and row['unique_profile_calls'] == len(cache)-before
            and row['profile_cache_hits'] == row_comparisons-(len(cache)-before))
        expected_false = sum(row['queries'][query]['certified'] and F(regret) > evidence.REGRET
                             for query, regret in truth[snapshot]['regrets'].items())
        check('saved_truth_requires_original_policies', scores[snapshot]['regrets'] == truth[snapshot]['regrets']
            and scores[snapshot]['false_certificates'] == expected_false)
        false_certificates += expected_false
    groups = {}
    for kind in ('failure', 'positive'):
        selected = [row for row in rows if row['kind'] == kind]
        blockers = Counter(cert['family'] for row in selected for query in ('goal', 'risk')
                           for cert in row['queries'][query]['comparisons'] if not cert['certified'])
        groups[kind] = dict(targets=len(selected), old_query_ready=sum(row['old_query_ready'] for row in selected),
            v235_query_ready=sum(row['v235_query_ready'] for row in selected), query_ready=sum(row['query_ready'] for row in selected),
            queries={query: sum(row['queries'][query]['certified'] for row in selected) for query in ('reward', 'goal', 'risk')},
            blockers_by_family=dict(blockers), arms={arm: dict(targets=sum(row['arm'] == arm for row in selected),
                query_ready=sum(row['arm'] == arm and row['query_ready'] for row in selected))
                for arm in ('ORACLE_BALANCED', 'ORACLE_GAP')})
    old_costs = evidence.load(raw_directory/'summary.json')['life_summaries']
    life_costs = [dict(life=row['life'], arm=row['arm'], source_samples=banks['source_costs'][row['life']],
        target_samples=banks['costs'][row['life'], row['arm']],
        total_samples=banks['source_costs'][row['life']]+banks['costs'][row['life'], row['arm']]) for row in old_costs]
    check('physical_full_life_costs_are_not_summed_across_cases', summary['life_costs'] == life_costs
        and all(saved['source_samples'] == expected['source_samples'] and saved['total_samples'] == expected['total_samples']
                for saved, expected in zip(life_costs, old_costs)))
    stage = groups['failure']['query_ready'] > 0 and groups['positive']['query_ready'] == 12 and false_certificates == 0
    check('exact_summary_and_fixed_stage_condition', summary['complete'] and summary['records'] == 24
        and summary['groups'] == groups and summary['stage_condition_met'] == stage and summary['certification_index'] == 77
        and summary['unique_profile_calls'] == len(cache) and summary['profile_cache_hits'] == comparison_count-len(cache)
        and summary['false_certificates'] == false_certificates
        and summary['model_seconds'] == sum(row['model_seconds'] for row in rows)
        and summary['qualification_only'] and not summary['scientific_gate_changed']
        and summary['new_observations'] == summary['new_paid_samples'] == 0)
    result = dict(valid=not failures, complete=True, records=24, comparisons=comparison_count,
        independently_checked_leaves=leaf_count, independently_checked_paid_segments=raw_segment_count,
        statuses=dict(statuses), families=dict(families), witness_kinds=dict(witness_kinds),
        unique_profile_calls=len(cache), false_certificates=false_certificates, groups=groups,
        stage_condition_met=stage, physical_source_samples=sum(banks['source_costs'].values()),
        physical_target_samples=sum(banks['costs'].values()), new_observations=0, new_paid_samples=0,
        checks=dict(checks), failures=failures, seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({field: value for field, value in result.items() if field not in ('checks', 'failures')}), flush=True)
    return result


if __name__ == '__main__':
    run()
