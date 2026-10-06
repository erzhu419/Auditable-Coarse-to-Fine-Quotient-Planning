"""One paid online task lifecycle; truth scores only after all decisions freeze."""
from collections import Counter
from fractions import Fraction
from copy import deepcopy
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import constrained_acquisition_v208 as core
from acfqp.science import mechanism_switch_task_v205 as task
from scripts import run_conditioned_mechanisms_v205 as saved

OUTPUT = ROOT/'reports/constrained_acquisition_v208'
ARMS = ('REVISED', 'LOCAL', 'GLOBAL')
SOURCE_FILES = (
 'src/acfqp/science/structured_route_task_v201.py',
 'src/acfqp/science/continual_route_kernels_v202.py',
 'src/acfqp/science/robust_route_planning_v203.py',
 'src/acfqp/science/target_risk_acquisition_v204.py',
 'src/acfqp/science/conditioned_mechanisms_v205.py',
 'src/acfqp/science/mechanism_switch_task_v205.py',
 'src/acfqp/science/online_lifecycle_v206.py',
 'scripts/run_conditioned_mechanisms_v205.py',
 'scripts/analyze_conditioned_mechanisms_v205.py',
 'src/acfqp/science/constrained_acquisition_v208.py',
 'scripts/run_constrained_acquisition_v208.py',
 'scripts/analyze_constrained_acquisition_v208.py',
 'tests/test_constrained_acquisition_v208.py',
 'specs/CONSTRAINED_ACQUISITION_V208.md',
 'reports/v208_runtime_tmp/run_stage.py')
save = saved.save
mean = saved.mean

def bootstrap(contrasts, work):
    rng = random.Random(208900); values = {key: [] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        work['bootstrap_index_draws'] += 12
        for key, rows in contrasts.items():
            values[key].append(mean(rows[i] for i in indices))
            work['bootstrap_mean_terms'] += 12
    return {key: dict(mean=mean(rows), ci=[sorted(values[key])[124], sorted(values[key])[4874]])
            for key, rows in contrasts.items()}

def summarize(results, queries, old, models, work):
    arms = {}; retention = {}; late_regret = {}
    for arm in ARMS:
        rows = [row for row in results if row['arm'] == arm]
        late = [row for row in rows if row['task_index'] >= 8]
        points = [point for row in rows for point in row['history']]
        arms[arm] = dict(total_samples=sum(row['spent'] for row in rows),
            early_samples=sum(row['spent'] for row in rows if row['task_index'] < 8),
            late_samples=sum(row['spent'] for row in late),
            all_restored=sum(row['certified'] for row in rows), late_restored=sum(row['certified'] for row in late),
            late_utility=mean(row['terminal']['actual_utility'] for row in late),
            history_violations=sum(point['violation'] for point in points),
            max_failure=max(point['actual'][1] for point in points),
            coverage=mean(point['coverage'] for point in points),
            pilot_batches=sum(row['pilot_batches'] for row in rows))
        initial = mean(q['regret'] for row in queries if row['arm'] == arm and row['task_index'] < 4
                       and row['stage'] == 'POST' for q in row['queries'].values())
        final = mean(q['regret'] for row in old if row['arm'] == arm for q in row['queries'].values())
        retention[arm] = dict(initial_regret=initial, final_regret=final, change=final-initial)
        late_regret[arm] = mean(q['regret'] for row in queries if row['arm'] == arm
                               and row['task_index'] >= 8 and row['stage'] == 'PRE' for q in row['queries'].values())
    contrasts = {key: [] for key in ('local_minus_revised_samples', 'global_minus_revised_samples', 'revised_minus_local_late_utility')}
    for life in range(12):
        rows = [row for row in results if row['life'] == life]
        totals = {arm: sum(row['spent'] for row in rows if row['arm'] == arm) for arm in ARMS}
        contrasts['local_minus_revised_samples'].append(totals['LOCAL']-totals['REVISED'])
        contrasts['global_minus_revised_samples'].append(totals['GLOBAL']-totals['REVISED'])
        utility = {arm: mean(row['terminal']['actual_utility'] for row in rows
                           if row['arm'] == arm and row['task_index'] >= 8) for arm in ARMS}
        contrasts['revised_minus_local_late_utility'].append(utility['REVISED']-utility['LOCAL'])
    intervals = bootstrap(contrasts, work)
    fields = {op: sum(row['models']['REVISED']['selected_fields'][op] == ['weather'] for row in models)
              for op in core.OPERATORS[:2]}
    chosen = arms['REVISED']; points = [p for row in results if row['arm'] == 'REVISED' for p in row['history']]
    conditions = dict(
        COST=intervals['local_minus_revised_samples']['mean'] >= 64 and intervals['local_minus_revised_samples']['ci'][0] > 0,
        QUALITY=chosen['late_restored'] >= 36 and chosen['late_restored'] >= arms['LOCAL']['late_restored']
            and chosen['late_utility'] >= 2 and intervals['revised_minus_local_late_utility']['ci'][0] >= -.05,
        RISK_RETENTION=all(Fraction(p['risk_upper']) <= Fraction(1,20) and not p['violation'] for p in points)
            and retention['REVISED']['change'] <= .01,
        LEARNING=all(n >= 10 for n in fields.values()) and late_regret['REVISED'] <= .05)
    return dict(complete=True, arms=arms, retention=retention, late_pre_query_regret=late_regret,
        final_weather_lifecycles=fields, contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        decision='CONSTRAINED_ACQUISITION_SUPPORTED' if all(conditions.values()) else 'CONSTRAINED_ACQUISITION_NOT_SUPPORTED')

def run():
    begun = perf_counter(); OUTPUT.mkdir(parents=True, exist_ok=False)
    manifest = []
    for name in SOURCE_FILES:
        target = OUTPUT/'source_code'/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target); manifest.append(dict(path=name))
    save(OUTPUT/'source_manifest.json', manifest)
    roster = task.roster()
    cases = ([c for c in roster if c['weather'] == 'normal']+
             [c for c in roster if c['weather'] != 'normal' and c['operating'] == 'high']+
             [c for c in roster if c['weather'] != 'normal' and c['operating'] == 'low'])
    save(OUTPUT/'cases.json', cases)
    work = {arm: Counter() for arm in ARMS}
    histories, queries, old, models = [], [], [], []
    phases = ['protocol_frozen']
    for life in range(12):
        state = {arm: core.fit(core.empty(), arm, work[arm]) for arm in ARMS}
        for index, case in enumerate(cases):
            seeds = {op: 209000+(life*12+index)*3+i for i, op in enumerate(core.OPERATORS)}
            for arm in ARMS:
                model = state[arm]
                decision = saved.query_decision(life, case, arm, model, work[arm], 'PRE')
                decision['task_index'] = index; queries.append(decision)
                plan = core.make_plan(model, case, work[arm]); rng = {op: random.Random(seed) for op, seed in seeds.items()}
                record = dict(life=life, task_index=index, context_id=case['id'], arm=arm, seeds=seeds,
                              initial_plan=plan, initial_fields=deepcopy(model['selected_fields']), batches=[])
                spent = 0; consumed = Counter()
                for step in range(24):
                    choice = core.choose(model, case, plan, work[arm]); op = choice['operator']
                    increments = dict.fromkeys(core.ALPHABETS[op], 0)
                    progress = dict(draw_end=consumed[op], operator_n=consumed[op], spent=spent)
                    saved.draw(rng[op], task.laws(case, work[arm]), op, increments, 16, work[arm], progress)
                    batch = dict(choice=choice, operator=op, draw_start=consumed[op], increments=increments, **progress)
                    core.update(model, case, op, increments, work[arm])
                    model = core.fit(model, arm, work[arm]); plan = core.make_plan(model, case, work[arm])
                    batch.update(plan=plan, selected_fields=deepcopy(model['selected_fields']))
                    record['batches'].append(batch); spent = progress['spent']; consumed[op] = progress['operator_n']
                    if plan['utility_lower'] >= 2:
                        break
                record.update(spent=spent, certified=plan['utility_lower'] >= 2, terminal_plan=plan)
                histories.append(record); state[arm] = model
                decision = saved.query_decision(life, case, arm, model, work[arm], 'POST')
                decision['task_index'] = index; queries.append(decision)
        for case in cases[:4]:
            for arm in ARMS:
                old.append(saved.query_decision(life, case, arm, state[arm], work[arm], 'FINAL'))
        models.append(dict(life=life, models=state))
        save(OUTPUT/'histories.json', histories); save(OUTPUT/'queries.json', queries)
        save(OUTPUT/'old_decisions.json', old); save(OUTPUT/'models.json', models)
        print(json.dumps(dict(life=life, samples=sum(w['controlled_samples'] for w in work.values()))), flush=True)
    phases.append('all_decisions_frozen')
    save(OUTPUT/'run.json', dict(phases=phases, arm_costs=work, source_samples=0))
    evaluation = Counter(); refs, laws = {}, {}
    for case in cases:
        refs[case['id']], laws[case['id']] = saved.true_reference(case, evaluation)
    results = []
    for row in histories:
        case = cases[row['task_index']]; ref, law = refs[case['id']], laws[case['id']]
        points = [saved.score_hard(row['initial_plan'], ref, law, 0, evaluation)]
        points += [saved.score_hard(batch['plan'], ref, law, batch['spent'], evaluation) for batch in row['batches']]
        results.append(dict(life=row['life'], task_index=row['task_index'], arm=row['arm'], spent=row['spent'],
            certified=row['certified'], history=points, terminal=points[-1],
            pilot_batches=sum(b['choice']['pilot'] for b in row['batches'])))
    scored = []
    for row in queries:
        q = saved.score_queries(row, refs[row['context_id']], evaluation)
        q['task_index'] = row['task_index']; scored.append(q)
    old_scores = [saved.score_queries(row, refs[row['context_id']], evaluation) for row in old]
    stats = Counter(); summary = summarize(results, scored, old_scores, models, stats)
    save(OUTPUT/'results.json', results); save(OUTPUT/'query_results.json', scored)
    save(OUTPUT/'old_results.json', old_scores); save(OUTPUT/'summary.json', summary)
    phases += ['oracle_evaluated', 'complete']
    save(OUTPUT/'run.json', dict(phases=phases, arm_costs=work, evaluation_costs=evaluation,
        bootstrap_costs=stats, source_samples=0, seconds=perf_counter()-begun))
    print(json.dumps(summary), flush=True)

if __name__ == '__main__':
    run()
