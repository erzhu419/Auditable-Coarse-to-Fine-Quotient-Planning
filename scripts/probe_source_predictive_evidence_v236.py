"""One frozen source-predictive feasibility test of nine retained witnesses."""
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import source_predictive_evidence_v236 as core

V235 = ROOT/'reports/joint_query_qualification_v235'
V234 = ROOT/'reports/shared_prefix_score_v234'
OUTPUT = ROOT/'reports/source_predictive_evidence_v236'


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


def key(row):
    return row['life'], row['index'], row['arm']


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def prepare(witness, tape, origin):
    chosen, other = witness['chosen'], witness['other']
    family = core.canonical_family(witness['query'], chosen, other)
    if origin == 'V235_countermodel':
        parameters = {name: {category: F(value) for category, value in row.items()}
                      for name, row in witness['parameters'].items()}
    else:
        p, q = F(witness['p']), F(witness['q'])
        parameters = {'D_REC': {'RECOVERY': p, 'OTHER': 1-p},
                      'R': {'DELIVERY': q, 'LOST': 1-q}}
    split = core.split_tape(tape)
    return dict(**{field: tape[field] for field in (
        'life', 'index', 'arm', 'kind', 'phase', 'case', 'identity', 'fees', 'changed_operator')},
        origin=origin, query=witness['query'], chosen=chosen, other=other, family=family,
        training_counts=core.project_counts(split['training'], family),
        validation_counts=core.project_counts(split['validation'], family),
        parameters=parameters, previously_reported_gap=F(witness['gap']),
        row_lengths={op: len(values) for op, values in tape['operators'].items()},
        training_lengths={op: len(values) for op, values in split['training'].items()},
        validation_lengths={op: len(values) for op, values in split['validation'].items()},
        training_segments=split['training_segments'], validation_segments=split['validation_segments'],
        new_observations=0, new_paid_samples=0)


def classify(row):
    gap = core.gap(row['case'], row['query'], row['chosen'], row['other'], row['parameters'])
    if gap != row['previously_reported_gap'] or gap <= core.REGRET:
        raise ValueError('the frozen witness must preserve its exact bad gap')
    member = core.membership(row['training_counts'], row['validation_counts'], row['parameters'])
    geometry = core.observed_geometry(row['training_counts'], row['validation_counts'], row['parameters'])
    return dict(row, gap=gap, membership=member, geometry=geometry,
        interpretation=('admitted_bad_witness_prevents_this_query_certificate'
                        if member['exact_inside'] else 'excluded_fixed_witness_only'))


def capture():
    paths = ('scripts/probe_source_predictive_evidence_v236.py',
        'scripts/audit_source_predictive_evidence_v236.py',
        'scripts/audit_joint_query_evidence_v235.py',
        'scripts/audit_joint_query_qualification_v235.py',
        'scripts/audit_kernel_query_profile_v232.py',
        'src/acfqp/science/source_predictive_evidence_v236.py',
        'src/acfqp/science/joint_query_evidence_v235.py',
        'src/acfqp/science/continual_route_kernels_v202.py',
        'tests/test_source_predictive_evidence_v236.py',
        'tests/test_source_predictive_evidence_v236_audit.py',
        'tests/test_source_predictive_evidence_runner_v236.py',
        'specs/SOURCE_PREDICTIVE_EVIDENCE_V236.md',
        'reports/v236_runtime_tmp/source_predictive_proof.md')
    for relative in paths:
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(OUTPUT/'source_manifest.json', list(paths))


def run():
    started = perf_counter()
    for path in (V235/'analysis.json', V235/'countermodel_analysis.json', V234/'analysis.json'):
        if not json.loads(path.read_text())['valid']:
            raise ValueError('the retained input evidence must already be audited')
    tapes = {key(row): row for row in read_rows(V235/'tapes.jsonl.gz')}
    witnesses = [row for row in json.loads((V235/'countermodels.json').read_text()) if row['found']]
    rectangles = json.loads((V234/'diagnosis.json').read_text())['terminal_rectangle_witnesses']
    if len(tapes) != 24 or len(witnesses) != 6 or len(rectangles) != 3:
        raise ValueError('the frozen inputs are 24 tapes, six V235 witnesses and three V234 rectangles')
    selected = [(row, 'V235_countermodel') for row in witnesses]+[(row, 'V234_rectangle') for row in rectangles]
    phases = ['protocol_frozen']
    protocol = dict(complete=False, phases=phases, threshold=960, event_count_per_life_arm=48,
        delta_per_life_arm='1/20', family_count=8,
        families={name: list(rows) for name, rows in core.FAMILIES.items()},
        training_rule='A_source_for_A_and_unchanged_B_rows__B_source_for_changed_B_row',
        denominator='validation_only', numerator='M_training_plus_validation_divided_by_M_training',
        selected=[dict(**{field: row[field] for field in ('life', 'index', 'arm', 'kind')}, origin=origin)
                  for row, origin in selected],
        qualification_only=True, witness_feasibility_only=True, query_certificates_obtained=False,
        scientific_gate_changed=False, new_observations=0, new_paid_samples=0)
    save(OUTPUT/'protocol.json', protocol)
    save(OUTPUT/'input_references.json', dict(paid_tapes=str(V235/'tapes.jsonl.gz'),
        source_tape_audit=str(V235/'analysis.json'), v235_witnesses=str(V235/'countermodels.json'),
        v235_witness_audit=str(V235/'countermodel_analysis.json'),
        v234_rectangles=str(V234/'diagnosis.json'), source_fees='original_cumulative_fees_retained_not_additive'))
    inputs = [prepare(row, tapes[key(row)], origin) for row, origin in selected]
    save(OUTPUT/'records.json', inputs)
    capture()
    phases.append('evidence_frozen')
    save(OUTPUT/'protocol.json', protocol)
    results = [classify(row) for row in inputs]
    save(OUTPUT/'records.json', results)
    phases.append('witnesses_checked')
    save(OUTPUT/'protocol.json', protocol)
    groups = {}
    for origin in ('V235_countermodel', 'V234_rectangle'):
        subset = [row for row in results if row['origin'] == origin]
        groups[origin] = dict(witnesses=len(subset),
            admitted=sum(row['membership']['exact_inside'] for row in subset),
            excluded=sum(row['membership']['excluded'] for row in subset),
            by_kind={kind: dict(witnesses=sum(row['kind'] == kind for row in subset),
                admitted=sum(row['kind'] == kind and row['membership']['exact_inside'] for row in subset),
                excluded=sum(row['kind'] == kind and row['membership']['excluded'] for row in subset))
                for kind in ('failure', 'positive')})
    main = [row for row in results if row['origin'] == 'V235_countermodel']
    eligible = all(row['membership']['excluded'] for row in main)
    summary = dict(complete=True, records=9, groups=groups,
        primary_risk_blockers=dict(cases=6, admitted=sum(row['membership']['exact_inside'] for row in main),
                                  excluded=sum(row['membership']['excluded'] for row in main)),
        full_qualification_eligible=eligible,
        qualification_status='eligible_not_run' if eligible else 'skipped_primary_bad_witness_still_admitted',
        qualification_only=True, query_certificates_obtained=False, scientific_gate_changed=False,
        new_observations=0, new_paid_samples=0, elapsed_seconds=perf_counter()-started)
    save(OUTPUT/'summary.json', summary)
    phases.append('complete')
    protocol['complete'] = True
    save(OUTPUT/'protocol.json', protocol)
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    run()
