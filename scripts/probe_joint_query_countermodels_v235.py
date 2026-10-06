"""Fixed post-qualification countermodels in seven canonical terminal regions."""
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from acfqp.science import joint_query_evidence_v235 as core

DIRECTORY = ROOT/'reports/joint_query_qualification_v235'
V232 = ROOT/'reports/kernel_query_profile_v232'
V234 = ROOT/'reports/shared_prefix_score_v234'
EPS, MARGIN = 1e-12, 1e-8
ROSTER = ((0, 58, 'ORACLE_BALANCED'), (0, 58, 'ORACLE_GAP'),
          (1, 56, 'ORACLE_BALANCED'), (1, 56, 'ORACLE_GAP'),
          (2, 55, 'ORACLE_BALANCED'), (2, 55, 'ORACLE_GAP'),
          (2, 44, 'ORACLE_GAP'))
COORDINATES = {'S_D_FULL': (('S', 'DELIVERY'), ('D_FULL', 'DELIVERY'), ('D_FULL', 'RECOVERY')),
               'D_REC_R': (('D_REC', 'RECOVERY'), ('R', 'DELIVERY'))}


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


def read_rows(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def key(row):
    return row['life'], row['index'], row['arm']


def coordinates(parameters, family):
    return [float(parameters[name][category]) for name, category in COORDINATES[family]]


def parameters(values, family):
    if family == 'S_D_FULL':
        s, d, recovery = values
        return {'S': {'DELIVERY': s, 'LOST': 1-s},
                'D_FULL': {'DELIVERY': d, 'RECOVERY': recovery, 'LOST': 1-d-recovery}}
    recovery, retry = values
    return {'D_REC': {'RECOVERY': recovery, 'OTHER': 1-recovery},
            'R': {'DELIVERY': retry, 'LOST': 1-retry}}


def mle(counts, smooth=False):
    result = {}
    for name, row in counts.items():
        n, dimension = sum(row.values()), len(row)
        probabilities = {category: F(count, n) if n else F(1, dimension)
                         for category, count in row.items()}
        result[name] = ({category: (float(p)+EPS)/(1+dimension*EPS)
                         for category, p in probabilities.items()} if smooth else probabilities)
    return result


def objective(values, row):
    """Constant-scaled negative log likelihood and its analytic gradient."""
    counts, family = row['projected_counts'], row['family']
    p = parameters(values, family)
    size = max(1, sum(sum(counts.values()) for counts in counts.values()))
    loss = -sum(k*np.log(max(float(p[name][cat]), 1e-15))
                for name, counts in counts.items() for cat, k in counts.items())/size
    gradient = []
    for name, category in COORDINATES[family]:
        residual = 'LOST' if name != 'D_REC' else 'OTHER'
        gradient.append((-counts[name][category]/max(float(p[name][category]), 1e-15)
                         +counts[name][residual]/max(float(p[name][residual]), 1e-15))/size)
    return float(loss), np.array(gradient)


def floating_gap(values, row):
    if row['family'] == 'S_D_FULL':
        short, detour, recovery = values
        sc, dc = core.COST_PRIOR[row['case']['operating']]
        sign = 1 if row['other'] == 'SHORT' else -1
        return sign*(float(dc-sc)+8*short-8*detour-4*recovery), sign*np.array([8., -8., -4.])
    recovery, retry = values
    sign = 1 if row['other'] == 'DETOUR_RETRY' else -1
    continuation = 8*retry-4-float(F(row['case']['retry_cost']))
    return sign*recovery*continuation, sign*np.array([continuation, 8*recovery])


def geometry(counts, candidate):
    """Conditional empirical KL and observed likelihood geometry only."""
    empirical = mle(counts)
    row_kl, loss_lower, loss_upper, excess_lower, excess_upper = {}, F(0), F(0), F(0), F(0)

    def compact_bounds(lower, upper):
        with localcontext() as context:
            context.prec, context.rounding = 80, ROUND_FLOOR
            lo = Decimal(lower.numerator)/Decimal(lower.denominator)
            context.rounding = ROUND_CEILING
            hi = Decimal(upper.numerator)/Decimal(upper.denominator)
        return dict(lower=str(lo), upper=str(hi))

    for name, row in counts.items():
        n, kl_lower, kl_upper, maximum_lower, maximum_upper = sum(row.values()), F(0), F(0), F(0), F(0)
        for category, count in row.items():
            if count:
                p = empirical[name][category]
                lo, hi = map(F, core.log_bounds(p/F(candidate[name][category])))
                kl_lower += p*lo
                kl_upper += p*hi
                lo, hi = map(F, core.log_bounds(p))
                maximum_lower += count*lo
                maximum_upper += count*hi
        row_kl[name] = dict(n=n, **compact_bounds(kl_lower, kl_upper))
        loss_lower += n*kl_lower
        loss_upper += n*kl_upper
        mlower, mupper = map(F, core.log_bounds(core.mixture_normalizer(tuple(row.values()))))
        excess_lower += maximum_lower-mupper
        excess_upper += maximum_upper-mlower
    return dict(log_mle_minus_log_bad=compact_bounds(loss_lower, loss_upper),
                log_mle_minus_log_mixture=compact_bounds(excess_lower, excess_upper),
                per_row_kl_empirical_to_bad=row_kl,
                scope='conditional_observed_geometry_not_true_KL_or_new_sample_guarantee')


def accepted(row, candidate):
    if any(sum(p.values()) != 1 or min(p.values()) < 0 for p in candidate.values()):
        return None
    gap = core.gap(row['case'], row['query'], row['chosen'], row['other'], candidate)
    if gap <= core.REGRET:
        return None
    member = core.membership(row['projected_counts'], candidate)
    if not member['exact_inside']:
        return None
    return dict(parameters=candidate, gap=gap, membership=member,
                geometry=geometry(row['projected_counts'], candidate))


def probe(row):
    attempts = []
    output = {key: row[key] for key in ('life', 'index', 'arm', 'kind', 'phase', 'case',
                                       'query', 'chosen', 'other', 'family', 'projected_counts')}
    answer = dict(output, found=False, valid=False, attempts=attempts,
        scope='canonical_terminal_only', new_observations=0, new_paid_samples=0)
    constraints = [dict(type='ineq', fun=lambda x: floating_gap(x, row)[0]-.05-MARGIN,
                        jac=lambda x: floating_gap(x, row)[1])]
    if row['family'] == 'S_D_FULL':
        constraints.append(dict(type='ineq', fun=lambda x: 1-x[1]-x[2]-EPS,
                                jac=lambda x: np.array([0., -1., -1.])))
    for initial in row['initials']:
        result = minimize(lambda x: objective(x, row), np.array(initial['coordinates']), jac=True,
            method='SLSQP', constraints=constraints,
            bounds=[(EPS, 1-EPS)]*len(COORDINATES[row['family']]),
            options=dict(maxiter=200, ftol=1e-12))
        attempts.append(dict(initial=initial['name'], iterations=int(result.nit),
                             optimizer_success=bool(result.success)))
        if not np.isfinite(result.x).all():
            continue
        candidate = parameters([F(str(float(value))) for value in result.x], row['family'])
        checked = accepted(row, candidate)
        if checked is not None:
            return dict(answer, found=True, valid=True, **checked)
    return answer


def inputs():
    tapes = {key(row): row for row in read_rows(DIRECTORY/'tapes.jsonl.gz')}
    frozen = {key(row): row for row in read_rows(DIRECTORY/'records.jsonl.gz')}
    old = {key(row): row for row in json.loads((V232/'countermodels.json').read_text()) if row['found']}
    rectangles = {key(row): row for row in json.loads((V234/'diagnosis.json').read_text())['terminal_rectangle_witnesses']}
    selected = []
    for identity in ROSTER:
        tape = tapes[identity]
        chosen, other = ('DETOUR_RETURN', 'SHORT') if identity != ROSTER[-1] else ('DETOUR_RETURN', 'DETOUR_RETRY')
        comparison = next(c for c in frozen[identity]['queries']['risk']['comparisons'] if c['other'] == other)
        if frozen[identity]['queries']['risk']['policy'] != chosen or comparison['certified']:
            raise ValueError('the seven fixed comparisons must remain unresolved with unchanged policies')
        family = core.canonical_family('risk', chosen, other)
        counts = core.project_counts(tape['operators'], family)
        if identity == ROSTER[-1]:
            existing = rectangles[identity]
            p, q = F(existing['p']), F(existing['q'])
            prior = {'D_REC': {'RECOVERY': p, 'OTHER': 1-p}, 'R': {'DELIVERY': q, 'LOST': 1-q}}
            initial_name = 'saved_bad_witness'
        elif identity in old:
            existing = old[identity]
            if (existing['query'], existing['chosen_policy'], existing['alternative_policy']) != ('risk', chosen, other):
                raise ValueError('the saved bad witness must match this fixed comparison')
            prior = core.project_parameters(existing['kernel'], family)
            initial_name = 'saved_bad_witness'
        else:
            prior = {name: dict.fromkeys(row, F(1, len(row))) for name, row in counts.items()}
            initial_name = 'uniform'
        selected.append(dict(**{field: tape[field] for field in ('life', 'index', 'arm', 'kind', 'phase', 'case')},
            query='risk', chosen=chosen, other=other, family=family, projected_counts=counts,
            initials=[dict(name='projected_mle_smoothed', coordinates=coordinates(mle(counts, smooth=True), family)),
                      dict(name=initial_name, coordinates=coordinates(prior, family))],
            saved_initial_parameters=prior))
    return selected


def run():
    started = perf_counter()
    selected = inputs()
    phases = ['protocol_frozen']
    protocol = dict(complete=False, phases=phases, selected=[{field: row[field] for field in
        ('life', 'index', 'arm', 'kind', 'phase', 'query', 'chosen', 'other', 'family')} for row in selected],
        optimizer='SLSQP', maxiter=200, ftol=1e-12, proposal_margin=MARGIN,
        coordinate_bounds=[EPS, 1-EPS], full_detour_sum_upper=1-EPS,
        mle_smoothing=EPS, objective_scaling='negative_log_likelihood_divided_by_required_sample_total',
        initial_order='projected_mle_smoothed_then_saved_bad_witness_or_uniform',
        accept='exact_simplex_AND_gap_gt_1/20_AND_M_le_960L', failure_to_find='unknown',
        scope='canonical_terminal_only', new_observations=0, new_paid_samples=0, scientific_gate_changed=False)
    save(DIRECTORY/'countermodel_protocol.json', protocol)
    save(DIRECTORY/'countermodel_inputs.json', selected)
    source_paths = ('scripts/probe_joint_query_countermodels_v235.py',
        'scripts/audit_joint_query_countermodels_v235.py',
        'src/acfqp/science/joint_query_evidence_v235.py',
        'src/acfqp/science/continual_route_kernels_v202.py',
        'tests/test_joint_query_countermodels_v235.py',
        'tests/test_joint_query_countermodels_v235_audit.py',
        'specs/JOINT_QUERY_COUNTERMODELS_V235.md')
    for relative in source_paths:
        destination = DIRECTORY/'countermodel_source_code'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    save(DIRECTORY/'countermodel_source_manifest.json', list(source_paths))
    phases.append('inputs_frozen')
    save(DIRECTORY/'countermodel_protocol.json', protocol)
    results = [probe(row) for row in selected]
    save(DIRECTORY/'countermodels.json', results)
    phases.append('witnesses_checked')
    save(DIRECTORY/'countermodel_protocol.json', protocol)
    summary = dict(cases=len(results), found=sum(row['found'] for row in results),
        unknown=sum(not row['found'] for row in results),
        groups={kind: dict(cases=sum(row['kind'] == kind for row in results),
            found=sum(row['kind'] == kind and row['found'] for row in results)) for kind in ('failure', 'positive')},
        attempts=sum(len(row['attempts']) for row in results), scope='canonical_terminal_only',
        new_observations=0, new_paid_samples=0, scientific_gate_changed=False,
        elapsed_seconds=perf_counter()-started)
    save(DIRECTORY/'countermodel_summary.json', summary)
    phases.append('complete')
    protocol['complete'] = True
    save(DIRECTORY/'countermodel_protocol.json', protocol)
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    run()
