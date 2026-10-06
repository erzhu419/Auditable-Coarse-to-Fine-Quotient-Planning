"""Classify only the fifteen frozen earlier bad witnesses, without a solver."""
from collections import Counter
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import joint_query_evidence_v235 as core

V232 = ROOT/'reports/kernel_query_profile_v232'
V234 = ROOT/'reports/shared_prefix_score_v234'
OUTPUT = ROOT/'reports/joint_query_evidence_v235'


def exact(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {key: exact(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact(item) for item in value]
    return value


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exact(value), ensure_ascii=False, separators=(',', ':'))+'\n')


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def key(row):
    return row['life'], row['index'], row['arm']


def evidence(witness, tape, previous, origin):
    chosen = witness['chosen_policy'] if origin == 'V232_countermodel' else witness['chosen']
    other = witness['alternative_policy'] if origin == 'V232_countermodel' else witness['other']
    family = core.canonical_family(witness['query'], chosen, other)
    if origin == 'V232_countermodel':
        parameters = core.project_parameters(witness['kernel'], family)
        old_gap = F(witness['regret'])
    else:
        if family != 'D_REC_R':
            raise ValueError('the three frozen V234 witnesses have only D_REC/R parameters')
        p, q = F(witness['p']), F(witness['q'])
        parameters = {'D_REC': {'RECOVERY': p, 'OTHER': 1-p},
                      'R': {'DELIVERY': q, 'LOST': 1-q}}
        old_gap = F(witness['gap'])
    counts = core.project_counts(tape['operators'], family)
    return dict(**{field: tape[field] for field in ('life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees')},
        origin=origin, query=witness['query'], chosen=chosen, other=other, family=family,
        projected_counts=counts, parameters=parameters, previously_reported_gap=old_gap,
        data_comparison=core.compare_prefix_data(counts, family, previous['prefixes']),
        new_observations=0, new_paid_samples=0)


def classify(row):
    measured_gap = core.gap(row['case'], row['query'], row['chosen'], row['other'], row['parameters'])
    if measured_gap != row['previously_reported_gap'] or measured_gap <= core.REGRET:
        raise ValueError('a fixed bad witness must retain its exact earlier gap above .05')
    membership = core.membership(row['projected_counts'], row['parameters'])
    return dict(row, gap=measured_gap, gap_above_regret=True, membership=membership,
        interpretation=('admitted_bad_witness_prevents_this_query_certificate'
                        if membership['exact_inside'] else 'excluded_fixed_witness_only'))


def capture():
    paths = (
        'src/acfqp/science/joint_query_evidence_v235.py',
        'src/acfqp/science/continual_route_kernels_v202.py',
        'scripts/probe_joint_query_evidence_v235.py',
        'scripts/audit_joint_query_evidence_v235.py',
        'tests/test_joint_query_evidence_v235.py',
        'tests/test_joint_query_evidence_v235_audit.py',
        'specs/JOINT_QUERY_EVIDENCE_V235.md',
    )
    for relative in paths:
        target = OUTPUT/'source_code'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, target)
    save(OUTPUT/'source_manifest.json', list(paths))


def run():
    started = perf_counter()
    tapes = {key(row): row for row in read_rows(V234/'tapes.jsonl.gz')}
    previous = {key(row): row for row in read_rows(V232/'records.jsonl.gz')}
    witnesses = [row for row in json.loads((V232/'countermodels.json').read_text()) if row['found']]
    rectangle = json.loads((V234/'diagnosis.json').read_text())['terminal_rectangle_witnesses']
    if len(tapes) != 24 or set(tapes) != set(previous) or len(witnesses) != 12 or len(rectangle) != 3:
        raise ValueError('V235 uses the fixed 24 tapes, twelve V232 witnesses, and three V234 witnesses')
    selected = [(row, 'V232_countermodel') for row in witnesses]+[(row, 'V234_rectangle') for row in rectangle]
    phases = ['protocol_frozen']
    protocol = dict(complete=False, phases=phases, qualification_only=True,
        witness_feasibility_only=True, family_count=8, event_count_per_life_arm=48,
        delta_per_life_arm='1/20', threshold=960,
        families={name: list(rows) for name, rows in core.FAMILIES.items()},
        selected=[dict(**{field: row[field] for field in ('life', 'index', 'arm', 'kind')}, origin=origin)
                  for row, origin in selected],
        new_observations=0, new_paid_samples=0, scientific_gate_changed=False,
        query_certificates_obtained=False)
    save(OUTPUT/'protocol.json', protocol)
    save(OUTPUT/'input_references.json', dict(
        paid_tapes=str(V234/'tapes.jsonl.gz'), v234_tape_audit=str(V234/'analysis.json'),
        v232_records=str(V232/'records.jsonl.gz'), v232_countermodels=str(V232/'countermodels.json'),
        v232_countermodel_audit=str(V232/'countermodel_analysis.json'),
        v234_rectangle_witnesses=str(V234/'diagnosis.json'),
        scope='fixed_bad_witnesses_only_no_optimizer', new_observations=0, new_paid_samples=0))
    rows = [evidence(row, tapes[key(row)], previous[key(row)], origin) for row, origin in selected]
    # All sufficient projections and their old-prefix comparison are saved
    # before any retained witness is tested against the new likelihood ratio.
    save(OUTPUT/'records.json', rows)
    capture()
    phases.append('evidence_frozen')
    save(OUTPUT/'protocol.json', protocol)
    results = [classify(row) for row in rows]
    save(OUTPUT/'records.json', results)
    phases.append('witnesses_checked')
    save(OUTPUT/'protocol.json', protocol)
    groups = {}
    for origin in ('V232_countermodel', 'V234_rectangle'):
        subset = [row for row in results if row['origin'] == origin]
        groups[origin] = dict(witnesses=len(subset),
            admitted=sum(row['membership']['exact_inside'] for row in subset),
            excluded=sum(row['membership']['excluded'] for row in subset),
            by_kind={kind: dict(witnesses=sum(row['kind'] == kind for row in subset),
                admitted=sum(row['kind'] == kind and row['membership']['exact_inside'] for row in subset),
                excluded=sum(row['kind'] == kind and row['membership']['excluded'] for row in subset))
                for kind in ('failure', 'positive')})
    mask_counts = Counter((item['same_projection_mask'], item['same_projected_counts'])
                         for row in results for item in row['data_comparison'])
    main_cases = {(0, 58, 'ORACLE_BALANCED'), (0, 58, 'ORACLE_GAP'),
                  (1, 56, 'ORACLE_BALANCED'), (1, 56, 'ORACLE_GAP'),
                  (2, 55, 'ORACLE_BALANCED'), (2, 55, 'ORACLE_GAP')}
    main = [row for row in results if row['origin'] == 'V232_countermodel'
            and key(row) in main_cases and row['query'] == 'risk'
            and frozenset((row['chosen'], row['other'])) == frozenset(('SHORT', 'DETOUR_RETURN'))]
    if len(main) != 5:
        raise ValueError('the frozen six primary risk blockers have exactly five retained bad witnesses')
    eligibility = all(row['membership']['excluded'] for row in main)
    summary = dict(complete=True, records=len(results), groups=groups,
        admitted=sum(row['membership']['exact_inside'] for row in results),
        excluded=sum(row['membership']['excluded'] for row in results),
        exact_prior_mask_and_count_matches=sum(item['equivalent_evidence']
            for row in results for item in row['data_comparison']),
        prior_comparisons=sum(mask_counts.values()),
        exact_prior_mask_matches=sum(count for (mask, _), count in mask_counts.items() if mask),
        primary_risk_blockers=dict(cases=6, retained_witnesses=5,
            admitted=sum(row['membership']['exact_inside'] for row in main),
            excluded=sum(row['membership']['excluded'] for row in main),
            without_retained_witness=[dict(life=life, index=index, arm=arm)
                for life, index, arm in sorted(main_cases-{key(row) for row in main})]),
        full_qualification_eligible=eligibility,
        qualification_status=('eligible_not_run' if eligibility else 'skipped_primary_bad_witness_still_admitted'),
        new_observations=0, new_paid_samples=0, query_certificates_obtained=False,
        full_bad_null_solver_implemented=False, scientific_gate_changed=False,
        qualification_only=True, elapsed_seconds=perf_counter()-started)
    save(OUTPUT/'summary.json', summary)
    phases.append('complete')
    protocol['complete'] = True
    save(OUTPUT/'protocol.json', protocol)
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    run()
