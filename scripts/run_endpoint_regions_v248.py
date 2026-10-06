"""Check two fixed bad-kernel variants at all frozen V247 failure endpoints."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import endpoint_region_v248 as core

BASELINE = ROOT/'reports/joint_prediction_return_v247'
OUTPUT = ROOT/'reports/endpoint_regions_v248'
LIVES, ARMS = (0, 1, 2), ('ONE_WAY', 'JOINT_PREDICTION')
VARIANTS = ('RETAINED', 'R_CENTERED')
STATUSES = ('unknown', 'paid_constraints_reject_candidate', 'full_region_bad_witness')
COMPARISON = dict(query='goal', chosen='SHORT', other='DETOUR_RETRY')


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with gzip.open(path, 'rt') as stream:
        yield from map(json.loads, stream)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, default=str, separators=(',', ':'))+'\n')


def endpoints():
    """Select the complete paired failure roster without constructing kernels."""
    selected, new_fees = [], Counter()
    for life in LIVES:
        for row in rows(BASELINE/f'records_life_{life:02d}.jsonl.gz'):
            if row['arm'] not in ARMS or row['case']['stage'] != 'A_RETURN':
                continue
            new_fees[life, row['arm']] += row['spent']
            plan = row['terminal_plan']
            goal = plan['query_evidence']['queries']['goal']
            reference = next((item for item in goal.get('comparisons', [])
                if item['other'] == 'DETOUR_RETRY' and not item['certified']), None)
            if goal['policy'] != 'SHORT' or reference is None:
                continue
            fee_fields = ('source_paid_samples', 'history_paid_samples', 'current_paid_samples',
                'total_reference_paid_samples', 'life_budget_remaining_before', 'life_budget_remaining_after')
            selected.append(dict(life=life, index=row['index'], arm=row['arm'], identity=row['identity'],
                case=deepcopy(row['case']), profile_id=reference['profile_id'],
                evidence_counts=deepcopy(plan['evidence_counts']),
                joint_constraints=deepcopy(plan['joint_constraints']), member=deepcopy(row['member']),
                retained_fees={field: row[field] for field in fee_fields}, spent=row['spent'],
                budget_exhausted=row['budget_exhausted'], member_cap_exhausted=row['member_cap_exhausted']))
    expected = Counter({(life, arm): 8 for life in LIVES for arm in ARMS})
    if len(selected) != 48 or Counter((row['life'], row['arm']) for row in selected) != expected:
        raise ValueError('all 48 frozen V247 SHORT-to-RETRY failures are required')
    paired = [{(row['life'], row['index']) for row in selected if row['arm'] == arm} for arm in ARMS]
    if paired[0] != paired[1]:
        raise ValueError('both arms must supply the same paired failure identities')
    prefix = {row['life']: row for row in read(BASELINE/'prefix_ledgers.json')}
    fees = [dict(life=life, arm=arm, source_samples=prefix[life]['source_paid_samples'],
        inherited_target_samples=prefix[life]['history_paid_samples'],
        new_return_samples=new_fees[life, arm],
        total_samples=prefix[life]['total_prefix_paid_samples']+new_fees[life, arm])
        for life in LIVES for arm in ARMS]
    return sorted(selected, key=lambda row: (row['life'], row['index'], ARMS.index(row['arm']))), fees


def status_counts(records):
    counts = Counter(row['status'] for row in records)
    return {status: counts[status] for status in STATUSES}


def group_summary(records):
    query_rejections, execution_rejections = Counter(), Counter()
    for row in records:
        query_rejections.update(family for family, result in row['query_regions'].items()
                                if not result['exact_inside'])
        execution_rejections.update(f'{("source", "pool", "member")[event["position"]]}:{event["operator"]}'
            for event in row['execution_regions'] if not event['membership']['exact_inside'])
    return dict(records=len(records), status_counts=status_counts(records),
        canonical_admitted=sum(row['canonical_inside'] is True for row in records),
        all_query_admitted=sum(row['all_query_inside'] is True for row in records),
        all_execution_admitted=sum(row['all_execution_inside'] is True for row in records),
        query_rejection_counts=dict(sorted(query_rejections.items())),
        execution_rejection_counts=dict(sorted(execution_rejections.items())))


def paired_statuses(records, axis):
    """Report the observed status changes across arms or across fixed variants."""
    indexed = {(row['life'], row['index'], row['arm'], row['variant']): row for row in records}
    identities = sorted({(row['life'], row['index']) for row in records})
    summaries = []
    for group in (VARIANTS if axis == 'arms' else ARMS):
        counts, changes = Counter(), []
        for life, index in identities:
            keys = ([(life, index, arm, group) for arm in ARMS] if axis == 'arms'
                    else [(life, index, group, variant) for variant in VARIANTS])
            before, after = [indexed[key]['status'] for key in keys]
            counts[before+'->'+after] += 1
            if before != after:
                changes.append(dict(life=life, index=index, before=before, after=after))
        summaries.append(dict(group=group, pairs=len(identities), status_transitions=dict(sorted(counts.items())),
            status_changes=changes))
    return summaries


def summarize(records, fees):
    bad_unions = []
    for arm in ARMS:
        identities = sorted({(row['life'], row['index']) for row in records
            if row['arm'] == arm and row['status'] == 'full_region_bad_witness'})
        bad_unions.append(dict(arm=arm, distinct_full_bad_endpoints=len(identities),
            endpoint_references=[dict(life=life, index=index) for life, index in identities],
            same_evidence_query_certificate_ceiling=72-len(identities), required_a_return_queries=54))
    return dict(complete=True, records=len(records), endpoints=len(records)//len(VARIANTS),
        arms=ARMS, variants=VARIANTS, comparison=COMPARISON, status_counts=status_counts(records),
        arm_variant_summaries=[dict(arm=arm, variant=variant,
            **group_summary([row for row in records if row['arm'] == arm and row['variant'] == variant]))
            for arm in ARMS for variant in VARIANTS],
        life_summaries=[dict(life=life, arm=arm, variant=variant,
            **group_summary([row for row in records
                if row['life'] == life and row['arm'] == arm and row['variant'] == variant]))
            for life in LIVES for arm in ARMS for variant in VARIANTS],
        paired_arm_statuses=paired_statuses(records, 'arms'),
        within_arm_variant_statuses=paired_statuses(records, 'variants'), retained_fee_ledger=fees,
        arm_full_bad_endpoint_unions=bad_unions,
        certificate_ceiling_scope='same_terminal_evidence_original_query_and_execution_regions_and_times',
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0, posthoc_scoring_calls=0,
        scientific_gate_changed=False, diagnostic_only=True)


def capture():
    from scripts import audit_endpoint_regions_v248
    paths = {'scripts/run_endpoint_regions_v248.py', 'scripts/audit_endpoint_regions_v248.py',
        'src/acfqp/science/endpoint_region_v248.py', 'tests/test_endpoint_region_v248.py',
        'tests/test_endpoint_regions_v248_runner.py', 'tests/test_endpoint_regions_v248_audit.py',
        'specs/ENDPOINT_REGIONS_V248.md'}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):
                paths.add(path.relative_to(ROOT).as_posix())
    for relative in sorted(paths):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(OUTPUT/'source_manifest.json', sorted(paths))


def run():
    begun = perf_counter()
    baseline_run, analysis = read(BASELINE/'run.json'), read(BASELINE/'analysis.json')
    if not baseline_run['complete'] or not analysis['valid']:
        raise ValueError('V247 must be complete and independently valid')
    selected, fees = endpoints()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    capture()
    roster = [{field: row[field] for field in ('life', 'index', 'arm', 'profile_id')} for row in selected]
    protocol = dict(baseline=BASELINE.relative_to(ROOT).as_posix(), arms=ARMS, variants=VARIANTS,
        comparison=COMPARISON, roster=roster, retained_fee_ledger=fees, endpoints=48,
        expected_classifications=96, query_threshold=960,
        execution_thresholds='retained_source720_pool720_member8640', strict_gap='50001/1000000',
        candidate_rule='two_frozen_variants_of_one_retained_maximum_dual_leaf_or_bad_null_mle',
        repair='one_algebraic_SHORT_DELIVERY_update_without_clipping_per_variant',
        data_access='retained_records_profiles_public_interfaces_common_prefix_states_prefix_ledgers_only',
        prerequisites=dict(v247_complete=True, v247_independent_valid=True),
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0, posthoc_scoring_calls=0,
        scientific_gate_changed=False, diagnostic_only=True)
    save(OUTPUT/'run.json', dict(protocol, complete=False, phases=['protocol_frozen', 'roster_frozen']))
    save(OUTPUT/'endpoints.json', selected)
    records = []
    for life in LIVES:
        needed = {row['profile_id'] for row in selected if row['life'] == life}
        profiles = {row['profile_id']: row for row in rows(BASELINE/f'profiles_life_{life:02d}.jsonl.gz')
                    if row['profile_id'] in needed}
        for row in selected:
            if row['life'] != life:
                continue
            certificate = profiles[row['profile_id']]['certificate']
            result = core.classify(row['evidence_counts'], row['joint_constraints'], row['case'], certificate)
            for variant in VARIANTS:
                records.append(dict(deepcopy(row), variant=variant,
                    empirical_rows=result['empirical_rows'], distances=result['distances'][variant],
                    **result['variants'][variant]))
            save(OUTPUT/'records.json', records)
            print(f'life={life} index={row["index"]} arm={row["arm"]} '
                + ' '.join(f'{variant}={result["variants"][variant]["status"]}' for variant in VARIANTS), flush=True)
    summary = dict(summarize(records, fees), elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol, complete=True,
        phases=['protocol_frozen', 'roster_frozen', 'all_endpoints_diagnosed', 'complete']))
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    run()
