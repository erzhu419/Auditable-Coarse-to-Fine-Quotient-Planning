"""Compute frozen impossibility bounds on all paid V256 execution snapshots."""
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
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
from acfqp.science import coupled_impossibility_v257 as core
from acfqp.science import scoped_route_task_v228 as task
from scripts.run_conditioned_mechanisms_v205 import exact_json, save
from scripts.run_endpoint_regions_v248 import read, rows
from scripts.run_oracle_gap_lifecycle_v231 import oracle_goal
from scripts.run_shared_probe_timing_v249 import activate_cold_caches

BASELINE = ROOT/'reports/trajectory_lifecycle_v256'
OUTPUT = ROOT/'reports/coupled_impossibility_v257'
LIVES, ARMS = (0,1,2), ('TRAJECTORY_REUSE','TRAJECTORY_REBUILD')
TARGETS = tuple(range(3,27))+tuple(range(30,78))
EXPECTED_SNAPSHOTS, EXPECTED_PRIMARY = 949, 16


def filename(kind, life, arm):
    return OUTPUT/f'{kind}_life_{life:02d}_{arm}.jsonl.gz'


def write_row(stream, row):
    begun = perf_counter()
    stream.write(json.dumps(exact_json(row),separators=(',',':'))+'\n')
    stream.flush()
    return perf_counter()-begun


def collect_snapshots():
    """Retained observable decisions choose the roster before any new bound."""
    snapshots, terminals, primary, fees = [], [], [], []
    for life in LIVES:
        for arm in ARMS:
            record_file = f'records_life_{life:02d}_{arm}.jsonl.gz'
            retained = list(rows(BASELINE/record_file))
            if [row['index'] for row in retained] != list(TARGETS):
                raise ValueError('the complete chronological V256 target roster is required')
            for record_position, row in enumerate(retained):
                plans = [row['initial_plan']]+[batch['plan'] for batch in row['batches']]
                ids = []
                for position, plan in enumerate(plans):
                    sid = len(snapshots)
                    ids.append(sid)
                    snapshots.append(dict(snapshot_id=sid,life=life,arm=arm,index=row['index'],identity=row['identity'],
                        case=deepcopy(row['case']),prefix_position=position,spent=0 if position==0 else row['batches'][position-1]['spent'],
                        is_terminal=position==len(plans)-1,plan=deepcopy(plan),
                        baseline_provenance=dict(directory='trajectory_lifecycle_v256',record_file=record_file,
                            record_position=record_position,plan_path='initial_plan' if position==0 else f'batches[{position-1}].plan')))
                if plans[-1] != row['terminal_plan']:
                    raise ValueError('each terminal must be the last initial/member plan')
                selected = arm==ARMS[0] and row['case']['stage']=='B' and row['query_certified'] and not row['execution_resolved']
                terminal = dict(snapshot_id=ids[-1],life=life,arm=arm,index=row['index'],identity=row['identity'],case=deepcopy(row['case']),
                    snapshot_ids=ids,primary=selected,spent=row['spent'],query_certified=row['query_certified'],
                    execution_certified=row['execution_certified'],execution_resolved=row['execution_resolved'],
                    old_goal_impossible=row['goal_impossible'],joint_completed=row['joint_completed'],
                    retained_budget_terminal=deepcopy(row['budget_terminal']),retained_budget_after=deepcopy(row['budget_after']),
                    baseline_provenance=deepcopy(snapshots[-1]['baseline_provenance']))
                terminals.append(terminal)
                if selected:
                    primary.append(dict(life=life,arm=arm,index=row['index'],identity=row['identity'],
                        snapshot_ids=ids,terminal_snapshot_id=ids[-1],baseline_provenance=deepcopy(terminal['baseline_provenance']),
                        retained_record=deepcopy(row)))
            artifact_file = f'worker_artifacts_life_{life:02d}_{arm}.json'
            artifact = read(BASELINE/artifact_file)
            fees.append(dict(life=life,arm=arm,fees=deepcopy(artifact['fees']),total_samples=sum(artifact['fees'].values()),
                baseline_provenance=dict(directory='trajectory_lifecycle_v256',worker_artifact_file=artifact_file)))
    if len(snapshots)!=EXPECTED_SNAPSHOTS or len(primary)!=EXPECTED_PRIMARY:
        raise ValueError('all949 initial/member snapshots and the16 observable primary terminals are required')
    return snapshots, terminals, primary, fees


def run_life_arm(life, arm, snapshots):
    begun = perf_counter()
    normalizers, work = activate_cold_caches(), Counter()
    model_seconds, output_seconds = 0., 0.
    with gzip.open(filename('records',life,arm),'wt') as stream:
        for snapshot in snapshots:
            started = process_time()
            bound = core.upper_bound(snapshot['plan'],snapshot['case'],work)
            elapsed = process_time()-started
            model_seconds += elapsed
            record = {key:deepcopy(snapshot[key]) for key in ('snapshot_id','life','arm','index','identity','case','prefix_position',
                'spent','is_terminal','baseline_provenance')}
            record.update(bound=bound,model_seconds=elapsed)
            output_seconds += write_row(stream,record)
    artifact = dict(life=life,arm=arm,snapshots=len(snapshots),model_seconds=model_seconds,output_seconds=output_seconds,
        worker_wall_seconds=perf_counter()-begun,work=dict(work),
        normalizer_cache_statistics={name:function.cache_info()._asdict() for name,function in normalizers.items()})
    save(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json',artifact)
    print(f'life={life} arm={arm} bounds={len(snapshots)}',flush=True)
    return artifact


def score(record, law):
    optimum = oracle_goal(record['case'],law)
    bound = record['bound']
    return dict(snapshot_id=record['snapshot_id'],life=record['life'],arm=record['arm'],index=record['index'],identity=record['identity'],
        prefix_position=record['prefix_position'],is_terminal=record['is_terminal'],true_optimum=optimum,
        false_old_upper=F(bound['old_goal_upper'])<optimum,false_new_upper=F(bound['upper'])<optimum,
        false_impossible_certificate=bound['new_impossible'] and optimum>=core.GOAL_THRESHOLD,
        truly_impossible=optimum<core.GOAL_THRESHOLD)


def counts(records, results):
    scores = {row['snapshot_id']:row for row in results}
    reductions = [F(row['bound']['reduction']) for row in records]
    return dict(snapshots=len(records),old_impossible=sum(row['bound']['old_impossible'] for row in records),
        new_impossible=sum(row['bound']['new_impossible'] for row in records),
        newly_impossible=sum(row['bound']['new_impossible'] and not row['bound']['old_impossible'] for row in records),
        upper_strictly_reduced=sum(value>0 for value in reductions),bound_reduction_sum=sum(reductions,F(0)),
        mean_bound_reduction=sum(reductions,F(0))/len(records) if records else F(0),max_bound_reduction=max(reductions,default=F(0)),
        false_old_uppers=sum(scores[row['snapshot_id']]['false_old_upper'] for row in records),
        false_new_uppers=sum(scores[row['snapshot_id']]['false_new_upper'] for row in records),
        false_impossible_certificates=sum(scores[row['snapshot_id']]['false_impossible_certificate'] for row in records))


def summarize(records, results, terminals, primary, fees, artifacts):
    indexed = {row['snapshot_id']:row for row in records}
    terminal_records = [indexed[row['snapshot_id']] for row in terminals]
    primary_records = [indexed[row['terminal_snapshot_id']] for row in primary]
    histories = []
    for row in primary:
        path = [indexed[sid] for sid in row['snapshot_ids']]
        first = next((item for item in path if item['bound']['new_impossible'] and not item['bound']['old_impossible']),None)
        histories.append(dict(life=row['life'],arm=row['arm'],index=row['index'],identity=row['identity'],
            terminal_snapshot_id=row['terminal_snapshot_id'],terminal_new_impossible=path[-1]['bound']['new_impossible'],
            earliest_newly_certified_prefix=None if first is None else dict(snapshot_id=first['snapshot_id'],
                prefix_position=first['prefix_position'],spent=first['spent'],upper=first['bound']['upper']),
            retained_terminal_member_samples=row['retained_record']['spent']))
    all_counts = counts(records,results)
    conditions = dict(all_primary_terminal_impossibilities=all(row['bound']['new_impossible'] for row in primary_records),
        nonlooser_bounds=all(F(row['bound']['upper'])<=F(row['bound']['old_goal_upper']) for row in records),
        valid_upper_bounds=all_counts['false_new_uppers']==0,
        valid_impossibility_certificates=all_counts['false_impossible_certificates']==0)
    grouped = []
    for life in LIVES:
        for arm in ARMS:
            for stage in task.STAGES:
                for identity in range(3):
                    own = [row for row in records if (row['life'],row['arm'],row['case']['stage'],row['identity'])==(life,arm,stage,identity)]
                    grouped.append(dict(life=life,arm=arm,stage=stage,identity=identity,
                        all_prefixes=counts(own,results),terminals=counts([row for row in own if row['is_terminal']],results)))
    return dict(complete=True,records=len(records),terminal_records=len(terminals),primary_terminals=len(primary),
        all_prefixes=all_counts,terminals=counts(terminal_records,results),primary=counts(primary_records,results),
        methods={arm:dict(all_prefixes=counts([row for row in records if row['arm']==arm],results),
            terminals=counts([row for row in terminal_records if row['arm']==arm],results)) for arm in ARMS},
        grouped_counts=grouped,primary_histories=histories,retained_fee_ledger=fees,conditions=conditions,
        method_condition_met=all(conditions.values()),independent_audit_required=True,
        model_seconds=sum(job['model_seconds'] for job in artifacts),
        model_seconds_scope='summed_process_CPU_box_vertices_exact_old_LP_dual_paired_reference_and_two_full_D_supports',
        output_seconds=sum(job['output_seconds'] for job in artifacts),worker_wall_seconds=[dict(life=job['life'],arm=job['arm'],
            seconds=job['worker_wall_seconds']) for job in artifacts],work=[dict(life=job['life'],arm=job['arm'],**job['work']) for job in artifacts],
        normalizer_cache_statistics=[dict(life=job['life'],arm=job['arm'],statistics=job['normalizer_cache_statistics']) for job in artifacts],
        new_environment_observations=0,new_event_allocations=0,lifecycle_cost_savings_measured=False,
        acquisition_and_execution_unchanged=True,scientific_gate_changed=False,u006_started=False,diagnostic_only=True)


def capture():
    from scripts import audit_coupled_impossibility_v257
    paths = {'src/acfqp/science/coupled_impossibility_v257.py','scripts/run_coupled_impossibility_v257.py',
        'scripts/audit_coupled_impossibility_v257.py','tests/test_coupled_impossibility_v257_core.py',
        'tests/test_coupled_impossibility_v257_runner.py','tests/test_coupled_impossibility_v257_audit.py',
        'specs/COUPLED_IMPOSSIBILITY_V257.md'}
    for module in tuple(sys.modules.values()):
        source = getattr(module,'__file__',None)
        if source:
            path = Path(source).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):
                paths.add(path.relative_to(ROOT).as_posix())
    for relative in sorted(paths):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,destination)
    save(OUTPUT/'source_manifest.json',sorted(paths))


def run():
    begun = perf_counter()
    if not read(BASELINE/'run.json')['complete'] or not read(BASELINE/'analysis.json')['valid']:
        raise ValueError('complete and independently valid V256 evidence is required')
    snapshots, terminals, primary, fees = collect_snapshots()
    OUTPUT.mkdir(parents=True,exist_ok=False)
    capture()
    with gzip.open(OUTPUT/'snapshots.jsonl.gz','wt') as stream:
        for row in snapshots:
            write_row(stream,row)
    save(OUTPUT/'terminals.json',terminals)
    with gzip.open(OUTPUT/'primary_histories.jsonl.gz','wt') as stream:
        for row in primary:
            write_row(stream,row)
    protocol = dict(baseline=BASELINE.relative_to(ROOT).as_posix(),lives=LIVES,arms=ARMS,snapshots=EXPECTED_SNAPSHOTS,
        terminal_targets=len(terminals),primary_terminals=EXPECTED_PRIMARY,primary_rule='TRAJECTORY_REUSE_B_query_certified_and_not_execution_resolved',
        lambda_rule='exact_old_four_policy_LP_dual_minimum_smallest_lambda_on_ties',
        risk_limit='1/20',goal_threshold=2,strict_impossibility=True,pool_threshold=720,member_threshold=8640,
        confidence_scope='unchanged_V256_per_life_fixed_arm_execution_1/20_event_no_new_alpha',
        final_upper='minimum_of_retained_old_same_lambda_paired_box_and_original_full_D_joint_support',
        data_access='V256_settled_target_records_original_paid_row_regions_envelopes_cases_and_worker_fees_only_before_bounds_frozen',
        truth_scoring='only_after_all949_bounds_and_all432_terminal_references_frozen',
        retained_fee_ledger=fees,new_environment_observations=0,new_event_allocations=0,lifecycle_cost_savings_measured=False,
        scientific_gate_changed=False,u006_started=False,diagnostic_only=True,
        prerequisites=dict(v256_complete=True,v256_independent_valid=True))
    save(OUTPUT/'run.json',dict(protocol,complete=False,phases=['source_captured','all_snapshots_and_primary_histories_frozen']))
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(run_life_arm,life,arm,[row for row in snapshots if row['life']==life and row['arm']==arm])
            for life in LIVES for arm in ARMS]
        artifacts = [future.result() for future in futures]
    records = [row for life in LIVES for arm in ARMS for row in rows(filename('records',life,arm))]
    if len(records)!=EXPECTED_SNAPSHOTS:
        raise ValueError('all949 bounds must be retained before posthoc scoring')
    save(OUTPUT/'run.json',dict(protocol,complete=False,phases=['source_captured','all_snapshots_and_primary_histories_frozen','all_bounds_frozen']))
    laws = {life:task.world(life)[1] for life in LIVES}
    results = []
    for life in LIVES:
        for arm in ARMS:
            with gzip.open(filename('results',life,arm),'wt') as stream:
                for row in records:
                    if row['life']==life and row['arm']==arm:
                        result = score(row,laws[life][row['index']])
                        write_row(stream,result)
                        results.append(result)
    summary = summarize(records,results,terminals,primary,fees,artifacts)
    summary['elapsed_seconds'] = perf_counter()-begun
    save(OUTPUT/'summary.json',summary)
    save(OUTPUT/'run.json',dict(protocol,complete=True,
        phases=['source_captured','all_snapshots_and_primary_histories_frozen','all_bounds_frozen','posthoc_scored','complete'],
        elapsed_seconds=summary['elapsed_seconds'],model_seconds=summary['model_seconds']))
    print(json.dumps(exact_json(summary),separators=(',',':')),flush=True)
    return summary


if __name__=='__main__':
    run()
