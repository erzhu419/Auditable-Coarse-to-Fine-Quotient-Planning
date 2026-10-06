"""Compare original return plans with one fixed paid TWO_WAY evidence view."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter, process_time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import paid_return_views_v253 as core
from scripts.run_endpoint_regions_v248 import read, rows, save
from scripts.run_information_axes_v252 import FEE_FIELDS
from scripts.run_reuse_rebuild_lifecycle_v242 import retain_plan
from scripts.run_shared_probe_timing_v249 import activate_cold_caches, COMPUTATION_CACHE_SCOPE

BASELINE = ROOT/'reports/query_shared_acquisition_v251'
OUTPUT = ROOT/'reports/paid_return_views_v253'
LIVES, ARMS = (0, 1, 2), ('UNIFORM_SHARED', 'QUERY_SHARED')
VIEWS = ('ONE_WAY', 'TWO_WAY')
TARGETS = tuple(range(3, 27))+tuple(range(30, 78))


def worker_filename(kind, life, arm):
    return OUTPUT/f'{kind}_life_{life:02d}_{arm}.jsonl.gz'


def add(counts, operator, increments):
    for category, count in increments.items():
        counts[operator][category] += count


def collect_snapshots():
    """Replay settled native observations up to each own return terminal time."""
    anchors = {item['life']: item for item in read(BASELINE/'source_evidence.json')}
    interfaces = {item['life']: item for item in read(BASELINE/'interfaces.json')}
    snapshots, fees = [], []
    for life in LIVES:
        source = anchors[life]
        interface = interfaces[life]['metadata']
        source_samples = sum(sum(row.values()) for bank in ('a', 'b') for anchor in source[bank] for row in anchor.values())
        for arm in ARMS:
            pools, history, cursor, probe_paid = dict(a=deepcopy(source['a']), b=None), 0, 0, 0
            tape = [json.loads(line) for line in (BASELINE/f'probes_life_{life:02d}_{arm}.jsonl').read_text().splitlines()]
            phase = read(BASELINE/f'a_phase_life_{life:02d}_{arm}.json')
            seen = []
            for row in rows(BASELINE/f'records_life_{life:02d}_{arm}.jsonl.gz'):
                index, identity, context = row['index'], row['identity'], row['case']['context'].lower()
                if index == 30:
                    pools['b'] = deepcopy(source['b'])
                if index in (3, 30):
                    while cursor < len(tape) and tape[cursor]['context'].lower() == context:
                        probe = tape[cursor]
                        add(pools[context][probe['identity']], probe['operator'], probe['increments'])
                        probe_paid += sum(probe['increments'].values())
                        cursor += 1
                member = {op: dict.fromkeys(core.ALPHABETS[op], 0) for op in core.OPERATORS}
                for batch in row['batches']:
                    add(member, batch['operator'], batch['increments'])
                    add(pools[context][identity], batch['operator'], batch['increments'])
                if row['case']['stage'] == 'A_RETURN':
                    b_identity = interface['b_to_a'].index(identity)
                    snapshots.append(dict(life=life, arm=arm, index=index, identity=identity,
                        case=deepcopy(row['case']), member=member,
                        a_source=deepcopy(source['a'][identity]), a_pool=deepcopy(pools['a'][identity]),
                        b_source=deepcopy(source['b'][b_identity]), b_pool=deepcopy(pools['b'][b_identity]),
                        mapped_b_identity=b_identity, interface={key: deepcopy(interface[key]) for key in ('changed_operator', 'b_to_a')},
                        retained_executed_mix=deepcopy(row['executed_mix']), one_way_plan=deepcopy(row['terminal_plan']),
                        baseline_provenance=dict(directory='query_shared_acquisition_v251',
                            record_file=f'records_life_{life:02d}_{arm}.jsonl.gz',
                            profile_file=f'profiles_life_{life:02d}_{arm}.jsonl.gz'),
                        retained_fees={field: row[field] for field in FEE_FIELDS}, spent=row['spent']))
                history += row['spent']
                seen.append(index)
            if seen != list(TARGETS) or cursor != len(tape):
                raise ValueError('all native V251 lifecycle records and shared probes are required')
            fees.append(dict(life=life, arm=arm, source_samples=source_samples,
                ordinary_target_samples=history, a_probe_samples=phase['a_paid_samples'],
                b_probe_samples=probe_paid-phase['a_paid_samples'], probe_samples=probe_paid,
                released_probe_samples=phase['released_delta'], total_samples=source_samples+history+probe_paid))
    expected = Counter({(life, arm): 24 for life in LIVES for arm in ARMS})
    if len(snapshots) != 144 or Counter((row['life'], row['arm']) for row in snapshots) != expected:
        raise ValueError('all 144 original A_RETURN terminal snapshots are required')
    if any([row['index'] for row in snapshots if row['life'] == life and row['arm'] == arm] != list(range(54, 78))
           for life in LIVES for arm in ARMS):
        raise ValueError('all return indices54..77 must be retained and paired')
    return snapshots, fees


def write_row(stream, row):
    begun = perf_counter()
    stream.write(json.dumps(row, default=str, separators=(',', ':'))+'\n')
    stream.flush()
    return perf_counter()-begun


def run_life_arm(life, arm, snapshots):
    begun = perf_counter()
    normalizers, cache, work, profile_ids = activate_cold_caches(), {}, Counter(), {}
    retained, model_seconds, output_seconds = [], 0., 0.
    with (gzip.open(worker_filename('records', life, arm), 'wt') as stream,
          gzip.open(worker_filename('profiles', life, arm), 'wt') as profiles):
        for snapshot in snapshots:
            started = process_time()
            plan = core.make_two_way(snapshot, cache, work)
            seconds = process_time()-started
            model_seconds += seconds
            started = perf_counter()
            two = retain_plan(plan, profiles, profile_ids)
            retention_seconds = perf_counter()-started
            output_seconds += retention_seconds
            record = dict(**{key: deepcopy(snapshot[key]) for key in ('life', 'arm', 'index', 'identity', 'case',
                'baseline_provenance', 'retained_fees', 'spent', 'retained_executed_mix', 'one_way_plan')},
                two_way_plan=two, model_seconds=seconds, output_seconds=retention_seconds)
            output_seconds += write_row(stream, record)
            retained.append(record)
            print(f'life={life} arm={arm} index={snapshot["index"]} '
                f'one_query={snapshot["one_way_plan"]["query_ready"]} two_query={plan["query_ready"]}', flush=True)
    artifact = dict(life=life, arm=arm, records=retained, work=work,
        profiles=len(profile_ids), model_seconds=model_seconds, output_seconds=output_seconds,
        worker_wall_seconds=perf_counter()-begun,
        normalizer_cache_statistics={name: function.cache_info()._asdict() for name, function in normalizers.items()})
    save(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json', {key: value for key, value in artifact.items() if key != 'records'})
    return artifact


def plan_state(plan):
    execution = F(plan['utility_lower']) >= 2 or plan['goal_impossible']
    return dict(query_ready=plan['query_ready'], execution_resolved=execution,
        joint_ready=execution and plan['query_ready'], execution_certified=F(plan['utility_lower']) >= 2,
        goal_impossible=plan['goal_impossible'],
        certified_by_query={query: record['certified'] for query, record in plan['query_evidence']['queries'].items()},
        query_choices={query: record['policy'] for query, record in plan['queries'].items()},
        query_blockers=deepcopy(plan['query_blockers']))


def view_summary(records, view):
    states = [plan_state(row['one_way_plan' if view == 'ONE_WAY' else 'two_way_plan']) for row in records]
    return dict(targets=len(states), **{field: sum(state[field] for state in states) for field in
        ('query_ready', 'execution_resolved', 'joint_ready', 'execution_certified', 'goal_impossible')},
        certified_by_query={query: sum(state['certified_by_query'][query] for state in states) for query in ('reward', 'goal', 'risk')},
        query_choice_counts={query: dict(sorted(Counter(state['query_choices'][query] for state in states).items()))
            for query in ('reward', 'goal', 'risk')},
        query_blocker_counts={query: dict(sorted(Counter(other for state in states for other in state['query_blockers'][query]).items()))
            for query in ('reward', 'goal', 'risk')})


def paired_summary(records):
    metrics = ('query_ready', 'execution_certified', 'execution_resolved', 'goal_impossible', 'joint_ready')
    pairs = [(row, plan_state(row['one_way_plan']), plan_state(row['two_way_plan'])) for row in records]
    result = {}
    for field in metrics:
        gains, losses, changes = 0, 0, []
        for row, old, new in pairs:
            gains += new[field] and not old[field]
            losses += old[field] and not new[field]
            if old[field] != new[field]:
                changes.append(dict(life=row['life'], index=row['index'], identity=row['identity'],
                    before=old[field], after=new[field]))
        result[field] = dict(gains=gains, losses=losses, unchanged=len(records)-gains-losses, changes=changes)
    for category in ('certified_by_query', 'query_choices', 'query_blockers'):
        result[category] = {}
        for query in ('reward', 'goal', 'risk'):
            changes = [dict(life=row['life'], index=row['index'], identity=row['identity'],
                before=old[category][query], after=new[category][query]) for row, old, new in pairs
                if old[category][query] != new[category][query]]
            result[category][query] = dict(changed=len(changes), unchanged=len(records)-len(changes), changes=changes)
            if category == 'certified_by_query':
                result[category][query].update(gains=sum(row['after'] and not row['before'] for row in changes),
                    losses=sum(row['before'] and not row['after'] for row in changes))
    return result


def summarize(records, fees):
    return dict(complete=True, records=len(records), snapshots=len(records), views=VIEWS,
        arm_summaries=[dict(arm=arm, views={view: view_summary([row for row in records if row['arm'] == arm], view) for view in VIEWS},
            paired=paired_summary([row for row in records if row['arm'] == arm])) for arm in ARMS],
        life_summaries=[dict(life=life, arm=arm,
            views={view: view_summary([row for row in records if row['life'] == life and row['arm'] == arm], view) for view in VIEWS},
            paired=paired_summary([row for row in records if row['life'] == life and row['arm'] == arm])) for life in LIVES for arm in ARMS],
        retained_fee_ledger=fees, new_observations=0, new_plans=len(records), one_way_replans=0,
        new_truth_scoring_calls=0, adaptive_policy_changed=False, scientific_gate_changed=False,
        diagnostic_only=True, view_delta_scope='separate_fixed_ONE_WAY_and_TWO_WAY_events_per_life_arm_not_OR_or_selected_union')


def capture():
    from scripts import audit_paid_return_views_v253
    paths = {'src/acfqp/science/paid_return_views_v253.py', 'scripts/run_paid_return_views_v253.py',
        'scripts/audit_paid_return_views_v253.py', 'tests/test_paid_return_views_v253_core.py',
        'tests/test_paid_return_views_v253_runner.py', 'tests/test_paid_return_views_v253_audit.py',
        'specs/PAID_RETURN_VIEWS_V253.md'}
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
    snapshots, fees = collect_snapshots()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    capture()
    jobs = [dict(life=life, arm=arm) for life in LIVES for arm in ARMS]
    protocol = dict(baseline=BASELINE.relative_to(ROOT).as_posix(), arms=ARMS, views=VIEWS, snapshots=144,
        roster=[{key: row[key] for key in ('life', 'arm', 'index', 'identity')} for row in snapshots],
        retained_fee_ledger=fees, prerequisites=dict(v251_complete=True, v251_independent_valid=True),
        one_way_rule='original_audited_terminal_plan_and_original_private_profile_references_unchanged',
        two_way_rule='inverse_B_to_A_compatible_native_B_unchanged_rows_once_at_own_original_terminal_time',
        query_events_per_life_arm_view=48, query_threshold=960, execution_source_pool_threshold=720,
        execution_member_threshold=8640, query_delta_per_life_arm_view='1/20', execution_delta_per_life_arm_view='1/20',
        combined_delta_per_fixed_view_upper='1/10',
        view_delta_scope='separate_fixed_ONE_WAY_and_TWO_WAY_events_per_life_arm_not_OR_or_selected_union',
        computation_cache_scope=COMPUTATION_CACHE_SCOPE, worker_jobs=jobs, max_workers=6,
        data_access='V251_settled_source_records_source_evidence_probe_tapes_probe_ledgers_A_phase_target_records_public_cases_and_interfaces_only',
        profile_namespaces=dict(ONE_WAY='original_V251_private_life_arm_file', TWO_WAY='new_V253_private_life_arm_file'),
        new_observations=0, expected_new_plans=144, one_way_replans=0, new_truth_scoring_calls=0,
        adaptive_policy_changed=False, scientific_gate_changed=False, diagnostic_only=True)
    save(OUTPUT/'snapshots.json', snapshots)
    save(OUTPUT/'run.json', dict(protocol, complete=False, phases=['protocol_frozen', 'all_snapshots_frozen']))
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(run_life_arm, job['life'], job['arm'],
            [row for row in snapshots if row['life'] == job['life'] and row['arm'] == job['arm']]) for job in jobs]
        artifacts = [future.result() for future in futures]
    records = [row for item in artifacts for row in item['records']]
    summary = dict(summarize(records, fees), elapsed_seconds=perf_counter()-begun,
        model_seconds=sum(item['model_seconds'] for item in artifacts),
        model_seconds_scope='summed_process_CPU_144_fixed_TWOWAY_evidence_assembly_and_plan_from_evidence_calls',
        output_seconds=sum(item['output_seconds'] for item in artifacts),
        output_seconds_scope='summed_worker_proof_retention_and_record_write_wall_calls',
        worker_wall_seconds=[dict(life=item['life'], arm=item['arm'], seconds=item['worker_wall_seconds']) for item in artifacts],
        normalizer_cache_statistics=[dict(life=item['life'], arm=item['arm'], statistics=item['normalizer_cache_statistics']) for item in artifacts],
        work=[dict(life=item['life'], arm=item['arm'], counts=item['work']) for item in artifacts],
        profiles=[dict(life=item['life'], arm=item['arm'], profiles=item['profiles']) for item in artifacts])
    save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(protocol, complete=True,
        phases=['protocol_frozen', 'all_snapshots_frozen', 'all_fixed_views_planned', 'complete']))
    print(json.dumps(summary, default=str), flush=True)
    return summary


if __name__ == '__main__':
    run()
