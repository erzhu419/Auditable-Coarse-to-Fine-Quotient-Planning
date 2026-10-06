"""Diagnose three fixed information-axis kernels at all frozen V251 endpoints."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import information_axes_v252 as core
from scripts.run_endpoint_regions_v248 import read, rows, save, status_counts, group_summary

BASELINE = ROOT/'reports/query_shared_acquisition_v251'
OUTPUT = ROOT/'reports/information_axes_v252'
LIVES, ARMS = (0, 1, 2), ('UNIFORM_SHARED', 'QUERY_SHARED')
VARIANTS = core.VARIANTS
COMPARISON = dict(query='goal', chosen='SHORT', other='DETOUR_RETRY')
FEE_FIELDS = ('source_paid_samples', 'history_paid_samples', 'ordinary_history_paid_samples',
    'actual_probe_paid_before', 'pending_probe_reserved', 'released_probe_samples',
    'probe_cap_samples', 'probe_quota_samples', 'future_B_source_reserved',
    'current_paid_samples', 'new_paid_samples', 'total_reference_paid_samples',
    'life_budget_remaining_before', 'life_budget_remaining_after')


def endpoints():
    """Freeze every paired failed SHORT-to-RETRY endpoint before candidates."""
    selected, ordinary_paid = [], Counter()
    for life in LIVES:
        for arm in ARMS:
            for row in rows(BASELINE/f'records_life_{life:02d}_{arm}.jsonl.gz'):
                ordinary_paid[life, arm] += row['spent']
                if row['case']['stage'] != 'A_RETURN':
                    continue
                plan = row['terminal_plan']
                goal = plan['query_evidence']['queries']['goal']
                reference = next((item for item in goal.get('comparisons', [])
                    if item['other'] == 'DETOUR_RETRY' and not item['certified']), None)
                if goal['policy'] != 'SHORT' or reference is None:
                    continue
                selected.append(dict(life=life, index=row['index'], arm=arm, identity=row['identity'],
                    case=deepcopy(row['case']), profile_id=reference['profile_id'],
                    evidence_counts=deepcopy(plan['evidence_counts']),
                    joint_constraints=deepcopy(plan['joint_constraints']), member=deepcopy(row['member']),
                    retained_fees={field: row[field] for field in FEE_FIELDS}, spent=row['spent'],
                    budget_exhausted=row['budget_exhausted'], member_cap_exhausted=row['member_cap_exhausted']))
    expected = Counter({(life, arm): 8 for life in LIVES for arm in ARMS})
    if len(selected) != 48 or Counter((row['life'], row['arm']) for row in selected) != expected:
        raise ValueError('all 48 frozen V251 SHORT-to-RETRY failures are required')
    identities = [{(row['life'], row['index']) for row in selected if row['arm'] == arm} for arm in ARMS]
    if identities[0] != identities[1]:
        raise ValueError('both arms must supply the same paired failure identities')
    anchors = {row['life']: row for row in read(BASELINE/'source_evidence.json')}
    probes = {(row['life'], row['arm']): row for row in read(BASELINE/'probe_ledgers.json')}
    fees = []
    for life in LIVES:
        source = sum(sum(counts.values()) for bank in ('a', 'b') for anchor in anchors[life][bank] for counts in anchor.values())
        for arm in ARMS:
            ledger = probes[life, arm]
            fees.append(dict(life=life, arm=arm, source_samples=source,
                ordinary_target_samples=ordinary_paid[life, arm],
                a_probe_samples=ledger['by_context']['A'], b_probe_samples=ledger['by_context']['B'],
                probe_samples=ledger['paid_samples'], released_probe_samples=ledger['released_samples'],
                total_samples=source+ordinary_paid[life, arm]+ledger['paid_samples']))
    return sorted(selected, key=lambda row: (row['life'], row['index'], ARMS.index(row['arm']))), fees


def paired_statuses(records, axis):
    indexed = {(row['life'], row['index'], row['arm'], row['variant']): row for row in records}
    identities = sorted({(row['life'], row['index']) for row in records})
    groups = [(variant, ARMS) for variant in VARIANTS] if axis == 'arms' else [
        (arm, pair) for arm in ARMS for pair in combinations(VARIANTS, 2)]
    summaries = []
    for group, pair in groups:
        counts, changes = Counter(), []
        for life, index in identities:
            keys = ([(life, index, arm, group) for arm in pair] if axis == 'arms'
                    else [(life, index, group, variant) for variant in pair])
            before, after = [indexed[key]['status'] for key in keys]
            counts[before+'->'+after] += 1
            if before != after:
                changes.append(dict(life=life, index=index, before=before, after=after))
        summaries.append(dict(group=group, pair=pair, pairs=len(identities),
            status_transitions=dict(sorted(counts.items())), status_changes=changes))
    return summaries


def summarize(records, fees):
    unions = []
    for arm in ARMS:
        identities = sorted({(row['life'], row['index']) for row in records
            if row['arm'] == arm and row['status'] == 'full_region_bad_witness'})
        unions.append(dict(arm=arm, distinct_full_bad_endpoints=len(identities),
            endpoint_references=[dict(life=life, index=index) for life, index in identities],
            same_evidence_query_certificate_ceiling=72-len(identities), required_a_return_queries=54))
    return dict(complete=True, records=len(records), endpoints=len(records)//len(VARIANTS),
        arms=ARMS, variants=VARIANTS, comparison=COMPARISON, status_counts=status_counts(records),
        arm_variant_summaries=[dict(arm=arm, variant=variant,
            **group_summary([row for row in records if row['arm'] == arm and row['variant'] == variant]))
            for arm in ARMS for variant in VARIANTS],
        life_summaries=[dict(life=life, arm=arm, variant=variant,
            **group_summary([row for row in records if row['life'] == life and row['arm'] == arm and row['variant'] == variant]))
            for life in LIVES for arm in ARMS for variant in VARIANTS],
        paired_arm_statuses=paired_statuses(records, 'arms'),
        within_arm_variant_statuses=paired_statuses(records, 'variants'), retained_fee_ledger=fees,
        arm_full_bad_endpoint_unions=unions,
        certificate_ceiling_scope='same_terminal_evidence_original_query_and_execution_regions_and_times',
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0, posthoc_scoring_calls=0,
        scientific_gate_changed=False, diagnostic_only=True)


def capture():
    from scripts import audit_information_axes_v252
    paths = {'scripts/run_information_axes_v252.py', 'scripts/audit_information_axes_v252.py',
        'src/acfqp/science/information_axes_v252.py', 'tests/test_information_axes_v252_core.py',
        'tests/test_information_axes_v252_runner.py', 'tests/test_information_axes_v252_audit.py',
        'specs/INFORMATION_AXES_V252.md'}
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
    if not read(BASELINE/'run.json')['complete'] or not read(BASELINE/'analysis.json')['valid']:
        raise ValueError('V251 must be complete and independently valid')
    selected, fees = endpoints()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    capture()
    roster = [{field: row[field] for field in ('life', 'index', 'arm', 'identity', 'profile_id')} for row in selected]
    protocol = dict(baseline=BASELINE.relative_to(ROOT).as_posix(), arms=ARMS, variants=VARIANTS,
        comparison=COMPARISON, roster=roster, retained_fee_ledger=fees, endpoints=48,
        expected_classifications=144, query_threshold=960,
        execution_thresholds='retained_source720_pool720_member8640', strict_gap='50001/1000000',
        candidate_rules=dict(RETAINED='unchanged_V248_retained_recovery_and_one_SHORT_repair',
            R_CENTERED='unchanged_V248_empirical_R_same_recovered_D_and_one_SHORT_repair',
            SD_CENTERED='native_empirical_full_S_D_rows_and_one_analytic_R_DELIVERY_solve_without_clipping'),
        data_access='V251_retained_source_records_source_evidence_probe_tapes_probe_ledgers_A_phase_target_records_profiles_public_cases_and_interfaces_only',
        prerequisites=dict(v251_complete=True, v251_independent_valid=True),
        new_observations=0, new_optimizer_calls=0, new_query_certificates=0, posthoc_scoring_calls=0,
        scientific_gate_changed=False, diagnostic_only=True)
    save(OUTPUT/'run.json', dict(protocol, complete=False, phases=['protocol_frozen', 'roster_frozen']))
    save(OUTPUT/'endpoints.json', selected)
    records = []
    for life in LIVES:
        for arm in ARMS:
            needed = {row['profile_id'] for row in selected if row['life'] == life and row['arm'] == arm}
            filename = f'profiles_life_{life:02d}_{arm}.jsonl.gz'
            profiles = {row['profile_id']: row for row in rows(BASELINE/filename) if row['profile_id'] in needed}
            for row in selected:
                if row['life'] != life or row['arm'] != arm:
                    continue
                certificate = profiles[row['profile_id']]['certificate']
                result = core.classify(row['evidence_counts'], row['joint_constraints'], row['case'], certificate)
                provenance = dict(directory='query_shared_acquisition_v251', file=filename,
                    profile_id=row['profile_id'], **COMPARISON, family='S_D_FULL_R', witness_kind=certificate['witness_kind'])
                for variant in VARIANTS:
                    records.append(dict(deepcopy(row), variant=variant, profile_provenance=deepcopy(provenance),
                        empirical_rows=result['empirical_rows'], distances=result['distances'][variant], **result['variants'][variant]))
                save(OUTPUT/'records.json', records)
                print(f'life={life} index={row["index"]} arm={arm} '
                    + ' '.join(f'{variant}={result["variants"][variant]["status"]}' for variant in VARIANTS), flush=True)
    summary = dict(summarize(records, fees), elapsed_seconds=perf_counter()-begun)
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol, complete=True,
        phases=['protocol_frozen', 'roster_frozen', 'all_endpoints_diagnosed', 'complete']))
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    run()
