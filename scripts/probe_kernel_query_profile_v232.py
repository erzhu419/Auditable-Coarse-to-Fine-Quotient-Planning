"""Zero-observation, exact accepted bad kernels for the fixed V232 failures."""
from decimal import Decimal, localcontext
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
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import kernel_query_profile_v232 as core
from acfqp.science import scoped_route_task_v228 as task

DIRECTORY = ROOT/'reports/kernel_query_profile_v232'
QUERY_ORDER = ('risk', 'goal', 'reward')
MARGIN = 1e-8


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str)+'\n')


def vector(kernel):
    s, d, r = core.OPERATORS
    return np.array([float(kernel[s]['DELIVERY']), float(kernel[d]['DELIVERY']),
                     float(kernel[d]['RECOVERY']), float(kernel[r]['DELIVERY'])])


def probabilities(x):
    s, d, rec, r = x
    return core._kernel(short=s, delivery=d, recovery=rec, retry=r)


def exact_kernel(x):
    return probabilities([F(str(float(value))) for value in x])


def verify(prefixes, kernel):
    if any(sum(row.values()) != 1 or min(row.values()) < 0 for row in kernel.values()):
        return None
    checks = []
    for prefix in prefixes:
        mixture, likelihood = F(1), F(1)
        for op in prefix['operators']:
            counts = prefix['counts'][op]
            mixture *= core.joint.mixture_normalizer(tuple(counts.values()))
            for category, count in counts.items():
                likelihood *= kernel[op][category]**count
        if mixture > prefix['threshold']*likelihood:
            return None
        with localcontext() as context:
            context.prec = 60
            ratio = prefix['threshold']*likelihood/mixture
            slack = (Decimal(ratio.numerator)/Decimal(ratio.denominator)).ln()
        checks.append(dict(prefix=prefix['name'], exact_inside=True, log_slack=str(slack)))
    return checks


def constraints(prefixes):
    functions = [dict(type='ineq', fun=lambda x: 1-x[1]-x[2]-1e-12,
                      jac=lambda x: np.array([0., -1., -1., 0.]))]
    for prefix in prefixes:
        cutoff = sum(float(core._log_bounds(core.joint.mixture_normalizer(
            tuple(prefix['counts'][op].values())))[1]) for op in prefix['operators'])
        cutoff -= np.log(prefix['threshold'])

        def log_likelihood(x, prefix=prefix, cutoff=cutoff):
            kernel = probabilities(x)
            return sum(count*np.log(max(float(kernel[op][cat]), 1e-15))
                       for op in prefix['operators']
                       for cat, count in prefix['counts'][op].items())-cutoff-MARGIN

        def jacobian(x, prefix=prefix):
            s, d, rec, r = x
            grad = np.zeros(4)
            for op in prefix['operators']:
                k = prefix['counts'][op]
                if op == core.OPERATORS[0]:
                    grad[0] += k['DELIVERY']/max(s, 1e-15)-k['LOST']/max(1-s, 1e-15)
                elif op == core.OPERATORS[1]:
                    lost = k['LOST']/max(1-d-rec, 1e-15)
                    grad[1] += k['DELIVERY']/max(d, 1e-15)-lost
                    grad[2] += k['RECOVERY']/max(rec, 1e-15)-lost
                else:
                    grad[3] += k['DELIVERY']/max(r, 1e-15)-k['LOST']/max(1-r, 1e-15)
            return grad
        functions.append(dict(type='ineq', fun=log_likelihood, jac=jacobian))
    return functions


def probe(row, worlds):
    query = next(q for q in QUERY_ORDER if not row['queries'][q]['certified'])
    chosen, prefixes = row['queries'][query]['policy'], row['prefixes']
    truth = worlds[row['life']][row['index']]
    pool = prefixes[0]['counts']
    mle = {op: {cat: (F(count, sum(k.values())) if sum(k.values()) else F(1, len(k)))
                for cat, count in k.items()} for op, k in pool.items()}
    initials = [('truth', vector(truth)), ('pool_mle', vector(mle))]
    attempts = []
    identity = {key: row[key] for key in ('life', 'index', 'arm', 'kind', 'phase')}
    answer = dict(identity, query=query, chosen_policy=chosen, found=False, valid=False,
                  new_observations=0, attempts=attempts)
    for other in core.POLICIES:
        if other == chosen:
            continue
        constant, coefs = core.gap_coefficients(row['case'], query, chosen, other, F(0))
        c, a, b = float(constant), np.array([
            float(coefs[core.OPERATORS[0]]['DELIVERY']),
            float(coefs[core.OPERATORS[1]]['DELIVERY']),
            float(coefs[core.OPERATORS[1]]['RECOVERY'])]), float(
            core.gap(row['case'], query, chosen, other, core._kernel(recovery=F(1), retry=F(1)))
            - core.gap(row['case'], query, chosen, other, core._kernel(recovery=F(1))))
        objective = lambda x: -(c+a @ x[:3]+b*x[2]*x[3])
        gradient = lambda x: -np.array([a[0], a[1], a[2]+b*x[3], b*x[2]])
        for name, initial in initials:
            result = minimize(objective, initial, jac=gradient, method='SLSQP',
                              constraints=constraints(prefixes), bounds=[(1e-12, 1-1e-12)]*4,
                              options=dict(maxiter=200, ftol=1e-12))
            attempts.append(dict(alternative=other, initial=name, iterations=int(result.nit),
                                 optimizer_success=bool(result.success)))
            if not np.isfinite(result.x).all():
                continue
            kernel = exact_kernel(result.x)
            regret = core.gap(row['case'], query, chosen, other, kernel)
            if regret <= core.REGRET_THRESHOLD:
                continue
            feasible = verify(prefixes, kernel)
            if feasible is not None:
                return dict(answer, found=True, valid=True, alternative_policy=other,
                            kernel=kernel, regret=regret, threshold=core.REGRET_THRESHOLD,
                            feasibility=feasible)
    return answer


def main():
    started = perf_counter()
    with gzip.open(DIRECTORY/'records.jsonl.gz', 'rt') as handle:
        rows = [json.loads(line) for line in handle]
    selected = [row for row in rows if row['kind'] == 'failure' or not row['query_ready']]
    protocol = dict(new_observations=0, selected=[{key: row[key] for key in
        ('life', 'index', 'arm', 'kind', 'phase')} for row in selected],
        query_order=QUERY_ORDER, alternative_order=core.POLICIES,
        initial_order=('truth', 'pool_mle'), optimizer='SLSQP', maxiter=200, ftol=1e-12,
        proposal_margin=MARGIN, accept='same rational kernel inside EVERY original prefix AND gap > 1/20',
        failure_to_find='unknown', scientific_gate_changed=False)
    save(DIRECTORY/'countermodel_protocol.json', protocol)
    source = DIRECTORY/'countermodel_source_code'
    for relative in ('scripts/probe_kernel_query_profile_v232.py',
                     'src/acfqp/science/kernel_query_profile_v232.py',
                     'src/acfqp/science/joint_gap_v230.py',
                     'src/acfqp/science/scoped_route_task_v228.py'):
        destination = source/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, destination)
    worlds = {life: task.world(life)[1] for life in range(3)}
    results = []
    for row in selected:
        result = probe(row, worlds)
        results.append(result)
        print(f'countermodel {row["kind"]} life={row["life"]} index={row["index"]} '
              f'arm={row["arm"]} query={result["query"]} found={result["found"]}', flush=True)
    save(DIRECTORY/'countermodels.json', results)
    summary = dict(cases=len(results), found=sum(row['found'] for row in results),
        groups={kind: dict(cases=sum(row['kind'] == kind for row in results),
                          found=sum(row['kind'] == kind and row['found'] for row in results))
                for kind in ('failure', 'positive')},
        exact_prefix_checks=sum(len(row.get('feasibility', [])) for row in results),
        elapsed_seconds=perf_counter()-started, new_observations=0, new_paid_samples=0,
        scientific_gate_changed=False)
    save(DIRECTORY/'countermodel_summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
