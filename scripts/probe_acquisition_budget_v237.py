"""One frozen oracle lower-bound diagnostic; no observations are generated."""
from fractions import Fraction as F
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import acquisition_budget_v237 as core
from acfqp.science import scoped_route_task_v228 as task
from acfqp.science.joint_query_evidence_v235 import project_parameters

V236 = ROOT/'reports/source_predictive_evidence_v236'
V231 = ROOT/'reports/oracle_gap_lifecycle_v231'
OUTPUT = ROOT/'reports/acquisition_budget_v237'
ROSTER = ((0, 58), (1, 56), (2, 55))


def exact(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {key: exact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact(item) for item in value]
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exact(value), ensure_ascii=False, separators=(',', ':'))+'\n')


def load(path):
    return json.loads(path.read_text())


def prepare_inputs():
    rows = load(V236/'records.json')
    selected = [row for row in rows if row['origin'] == 'V235_countermodel' and row['arm'] == 'ORACLE_GAP']
    if tuple((row['life'], row['index']) for row in selected) != ROSTER:
        raise ValueError('the three original GAP risk blockers are fixed')
    costs = {(row['life'], row['arm']): row for row in load(V231/'summary.json')['life_summaries']}
    result = []
    for row in selected:
        life = row['life']
        balanced, gap = (costs[(life, arm)] for arm in ('ORACLE_BALANCED', 'ORACLE_GAP'))
        reference = dict(source_paid_samples_per_arm=gap['source_samples'],
            balanced_total=balanced['total_samples'], gap_total=gap['total_samples'],
            headroom=balanced['total_samples']-gap['total_samples'],
            scope='same_V231_life_GAP_vs_BALANCED_both_reuse_not_REBUILD')
        result.append(dict(**{field: row[field] for field in (
            'life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees', 'query',
            'chosen', 'other', 'family', 'training_counts', 'validation_counts', 'parameters')},
            budget_reference=reference))
    return result


def load_truth(inputs):
    result = []
    for row in inputs:
        cases, laws, identities, _ = task.world(row['life'])
        index = row['index']
        if exact(cases[index]) != row['case'] or identities[index] != row['identity']:
            raise ValueError('the saved known-type task must match its original world')
        result.append(dict(row, truth_parameters=project_parameters(laws[index], row['family'])))
    return result


def evaluate(row):
    initial = core.exact_e0(row['training_counts'], row['validation_counts'], row['parameters'])
    bounds = core.budget_bounds(initial, row['truth_parameters'], row['parameters'],
                                row['budget_reference']['headroom'])
    return dict(row, bounds=bounds, new_observations=0, new_paid_samples=0,
        interpretation=('fixed_suffix_budget_insufficient_for_planned_power'
                        if bounds['budget_insufficient'] else 'not_ruled_out_by_necessary_bound'))


def capture():
    paths = ('scripts/probe_acquisition_budget_v237.py', 'scripts/audit_acquisition_budget_v237.py',
        'src/acfqp/science/acquisition_budget_v237.py',
        'src/acfqp/science/source_predictive_evidence_v236.py',
        'src/acfqp/science/joint_query_evidence_v235.py',
        'src/acfqp/science/scoped_route_task_v228.py',
        'scripts/analyze_scoped_lifecycle_v229.py', 'scripts/audit_source_predictive_evidence_v236.py',
        'tests/test_acquisition_budget_v237.py', 'tests/test_acquisition_budget_v237_audit.py',
        'tests/test_acquisition_budget_runner_v237.py', 'specs/ACQUISITION_BUDGET_V237.md',
        'reports/v237_runtime_tmp/budget_bound_proof.md')
    for relative in paths:
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(OUTPUT/'source_manifest.json', list(paths))


def run():
    started = perf_counter()
    if not load(V236/'analysis.json')['valid'] or not load(V231/'analysis.json')['valid']:
        raise ValueError('both retained evidence and matched lifecycle costs require their prior audits')
    inputs = prepare_inputs()
    phases = ['protocol_frozen']
    protocol = dict(complete=False, phases=phases, threshold=960, event_count_per_life_arm=48,
        target_power='3/4', batch=16, bisection_steps=64,
        selected=[{field: row[field] for field in ('life', 'index', 'arm')} for row in inputs],
        cost_scope='fresh_suffix_added_to_fixed_lifecycle_costs',
        probability_scope='conditional_fixed_bad_witness_exclusion_not_whole_query',
        oracle_truth_scope='diagnostic_bound_only_not_learner_or_acquisition',
        matched_rebuild_reference_available=False, new_observations=0, new_paid_samples=0,
        scientific_gate_changed=False, query_certificates_obtained=False)
    save(OUTPUT/'protocol.json', protocol)
    save(OUTPUT/'inputs.json', inputs)
    save(OUTPUT/'input_references.json', dict(evidence=str(V236/'records.json'),
        evidence_audit=str(V236/'analysis.json'), costs=str(V231/'summary.json'),
        cost_audit=str(V231/'analysis.json'), truth_module='acfqp.science.scoped_route_task_v228.world'))
    capture()
    phases.append('inputs_frozen')
    save(OUTPUT/'protocol.json', protocol)
    truth_inputs = load_truth(inputs)
    save(OUTPUT/'oracle_inputs.json', truth_inputs)
    phases.append('oracle_truth_loaded')
    save(OUTPUT/'protocol.json', protocol)
    results = [evaluate(row) for row in truth_inputs]
    save(OUTPUT/'records.json', results)
    phases.append('bounds_frozen')
    save(OUTPUT/'protocol.json', protocol)
    lower_sum = sum((F(row['bounds']['expected_samples_lower']) for row in results), F(0))
    headroom = sum(row['budget_reference']['headroom'] for row in results)
    summary = dict(complete=True, records=3, budget_insufficient_lives=[row['life'] for row in results
        if row['bounds']['budget_insufficient']], necessary_expected_samples_lower_sum=lower_sum,
        matched_total_headroom=headroom, total_budget_insufficient=lower_sum > headroom,
        matched_rebuild_reference_available=False, new_observations=0, new_paid_samples=0,
        query_certificates_obtained=False, scientific_gate_changed=False,
        qualification_only=True, planning_requirement='each_fixed_case_exclusion_probability_at_least_3/4',
        scope='necessary_bound_for_fixed_suffix_not_redesigned_lifecycle',
        elapsed_seconds=perf_counter()-started)
    save(OUTPUT/'summary.json', summary)
    phases.append('complete')
    protocol['complete'] = True
    save(OUTPUT/'protocol.json', protocol)
    print(json.dumps(exact(summary)), flush=True)
    return summary


if __name__ == '__main__':
    run()
