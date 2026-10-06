"""Fresh comparison against unchanged original SET and matched raw confidence."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import strong_reference_v224 as core
from acfqp.science import latent_route_task_v213 as task
from scripts.run_conditioned_mechanisms_v205 import save, mean, draw
from scripts.run_persistent_evidence_v221 import score, query_score

OUTPUT = ROOT/'reports/strong_reference_v224'
SOURCE = ROOT/'reports/persistent_evidence_v221/libraries.json'
ARMS = core.ARMS
CONTRASTS = (
    'original_minus_union_samples', 'fixed_minus_union_samples', 'fixed_minus_original_samples',
    'union_minus_original_utility', 'union_minus_fixed_utility', 'fixed_minus_original_utility',
    'union_minus_original_regret', 'union_minus_fixed_regret', 'fixed_minus_original_regret',
    'union_minus_original_late_certified', 'union_minus_fixed_late_certified',
)
SOURCE_FILES = (
    'src/acfqp/science/strong_reference_v224.py',
    'src/acfqp/science/assignment_union_v222.py',
    'src/acfqp/science/fixed_source_acquisition_v219.py',
    'src/acfqp/science/joint_acquisition_v218.py',
    'src/acfqp/science/source_stopping_v216.py',
    'src/acfqp/science/query_sufficient_v214.py',
    'src/acfqp/science/latent_mechanisms_v213.py',
    'src/acfqp/science/latent_route_task_v213.py',
    'src/acfqp/science/mechanism_switch_task_v205.py',
    'src/acfqp/science/robust_route_planning_v203.py',
    'src/acfqp/science/target_risk_acquisition_v204.py',
    'scripts/run_conditioned_mechanisms_v205.py',
    'scripts/run_persistent_evidence_v221.py',
    'scripts/run_strong_reference_v224.py',
    'scripts/analyze_assignment_union_v222.py',
    'scripts/analyze_strong_reference_v224.py',
    'tests/test_strong_reference_v224.py',
    'specs/STRONG_REFERENCE_V224.md',
    'reports/v224_runtime_tmp/run_stage.py',
)


def summarize(results, historical, work, operator_samples):
    arms = {}
    for arm in ARMS:
        rows = [r for r in results if r['arm']==arm]; late = [r for r in rows if r['index']>=15]
        points = [p for r in rows for p in r['history']]
        source_cost = sum(historical[arm]); target_cost = sum(r['spent'] for r in rows)
        arms[arm] = dict(total_samples=source_cost+target_cost, source_samples=source_cost,
            target_samples=target_cost, source_revisit_samples=0,
            late_samples=sum(r['spent'] for r in late), late_certified=sum(r['certified'] for r in late),
            late_transferred=sum(r['transferred'] and r['transfer_correct'] for r in late),
            late_identified=sum(r['identified'] and r['identity_correct'] for r in late),
            wrong_transfers=sum(r['transferred'] and not r['transfer_correct'] for r in rows),
            late_utility=mean(float(r['terminal']['actual_utility']) for r in late),
            late_post_regret=mean(float(v['regret']) for r in late for v in r['query_post'].values()),
            history_violations=sum(p['violation'] for p in points),
            max_failure=max(float(p['actual'][1]) for p in points),
            coverage=mean(p['coverage'] for p in points), member_fallbacks=sum(r['fallback'] for r in rows),
            retained_targets=len(rows) if arm=='UNION' else 0,
            retained_target_samples=target_cost if arm=='UNION' else 0,
            target_operator_samples=operator_samples[arm], library_coverage=mean(r['library_coverage'] for r in rows),
            library_lost_masks=sum(not r['library_true_masks'] for r in rows),
            no_feasible=sum(r['library_no_feasible'] for r in rows))
    contrasts = {key: [] for key in CONTRASTS}
    for life in range(12):
        rows = [r for r in results if r['life']==life]
        totals = {a:historical[a][life]+sum(r['spent'] for r in rows if r['arm']==a) for a in ARMS}
        utility = {a:mean(float(r['terminal']['actual_utility']) for r in rows if r['arm']==a and r['index']>=15) for a in ARMS}
        regret = {a:mean(float(v['regret']) for r in rows if r['arm']==a and r['index']>=15 for v in r['query_post'].values()) for a in ARMS}
        cert = {a:sum(r['certified'] for r in rows if r['arm']==a and r['index']>=15) for a in ARMS}
        original, fixed, learned = (totals[a] for a in ARMS)
        values = (
            original-learned, fixed-learned, fixed-original,
            utility['UNION']-utility['ORIGINAL'], utility['UNION']-utility['FIXED'], utility['FIXED']-utility['ORIGINAL'],
            regret['UNION']-regret['ORIGINAL'], regret['UNION']-regret['FIXED'], regret['FIXED']-regret['ORIGINAL'],
            cert['UNION']-cert['ORIGINAL'], cert['UNION']-cert['FIXED'])
        for key, value in zip(CONTRASTS, values):
            contrasts[key].append(value)
    rng = random.Random(229900); samples = {key:[] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]; work['bootstrap_index_draws'] += 12
        for key, rows in contrasts.items():
            samples[key].append(mean(rows[i] for i in indices)); work['bootstrap_mean_terms'] += 12
    intervals = {key:dict(mean=mean(rows), ci=[sorted(samples[key])[124], sorted(samples[key])[4874]])
                 for key, rows in contrasts.items()}
    tested = arms['UNION']; points = [p for r in results for p in r['history']]
    conditions = dict(
        RISK=all(p['actual'][1]<=F(1,20) and p['risk_upper']<=F(1,20) for p in points)
            and all(a['wrong_transfers']==0 and a['library_coverage']==1 and
                    a['library_lost_masks']==0 and a['no_feasible']==0 for a in arms.values()),
        QUALITY=tested['late_certified']>=108 and tested['late_certified']>=arms['ORIGINAL']['late_certified']
            and tested['late_certified']>=arms['FIXED']['late_certified'] and tested['late_utility']>=2
            and intervals['union_minus_original_utility']['ci'][0]>=-.05
            and intervals['union_minus_fixed_utility']['ci'][0]>=-.05,
        APPLICABILITY=tested['late_transferred']>=108 and tested['late_post_regret']<=.05,
        LEARNING_EFFECT=intervals['fixed_minus_union_samples']['mean']>=64
            and intervals['fixed_minus_union_samples']['ci'][0]>0
            and intervals['union_minus_fixed_regret']['ci'][1]<=.01,
        STRONG_REFERENCE=intervals['original_minus_union_samples']['mean']>=64
            and intervals['original_minus_union_samples']['ci'][0]>0
            and intervals['union_minus_original_regret']['ci'][1]<=.01)
    return dict(complete=True, arms=arms, contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        confidence=dict(scope='per_arm_per_lifecycle', source_family=1512, source_delta=3/220,
            source_beta=core.SOURCE_BETA, member_family=4032, member_delta=1/88,
            member_beta=core.MEMBER_BETA, pool_family=13608, pool_delta=.025, pool_beta=core.POOL_BETA,
            original_delta=.05, fixed_delta=.025, union_delta=.05),
        decision='STRONG_REFERENCE_LEARNING_SUPPORTED' if all(conditions.values()) else 'STRONG_REFERENCE_LEARNING_NOT_SUPPORTED')


def run():
    begun = perf_counter(); OUTPUT.mkdir(parents=True, exist_ok=False)
    for name in SOURCE_FILES:
        path = OUTPUT/'source_code'/name; path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, path)
    save(OUTPUT/'source_manifest.json', [dict(path=name) for name in SOURCE_FILES])
    shutil.copyfile(SOURCE, OUTPUT/'source_evidence.json')
    libraries = json.loads((OUTPUT/'source_evidence.json').read_text())
    historical = {arm:[3456]*12 for arm in ARMS}
    work = {arm:Counter() for arm in ARMS}; records = []; cases_saved = []
    arm_seconds = dict.fromkeys(ARMS, 0.)
    core.clear_cache()
    for life in range(12):
        cases, laws, identities = task.world(life); cases_saved.append(dict(life=life, cases=cases))
        anchors = libraries[life]['anchors']
        states = {arm:core.prepare(anchors, arm, work[arm]) for arm in ARMS}
        for index, case in enumerate(cases[3:], start=3):
            seeds = {op:230000+(life*27+index)*3+i for i,op in enumerate(core.OPERATORS)}
            for arm in ARMS:
                arm_begun = perf_counter(); state = states[arm]; before = deepcopy(state)
                member = core.empty(); rng = {op:random.Random(seed) for op,seed in seeds.items()}
                plan = core.make_plan(member, anchors, case, arm, work[arm], state)
                row = dict(life=life, index=index, case=case, arm=arm, seeds=seeds,
                    initial_plan=plan, initial_query=core.queries(plan), batches=[])
                spent = 0
                while True:
                    choice = core.choose(member, anchors, case, arm, plan, spent, work[arm], state)
                    if choice is None:
                        break
                    op = choice['operator']; start = sum(member[op].values())
                    increments = dict.fromkeys(core.ALPHABETS[op], 0); progress = dict(draw_end=start, n=start)
                    draw(rng[op], laws[index], op, increments, 16, work[arm], progress)
                    for cat,k in increments.items():
                        member[op][cat] += k
                    spent += 16; plan = core.make_plan(member, anchors, case, arm, work[arm], state)
                    row['batches'].append(dict(choice=choice, scope='TARGET', source_index=None,
                        operator=op, draw_start=start, increments=increments, draw_end=progress['draw_end'],
                        spent=spent, member_spent=spent, source_spent=0, plan=plan))
                fallback = len(plan['candidates'])!=1 and not plan['query_ready']
                if fallback:
                    plan = core.make_plan(member, anchors, case, arm, work[arm], state, force_member=True)
                certified = plan['utility_lower']>=2; identified = len(plan['candidates'])==1 and certified
                transferred = certified and plan['mode']=='library' and (identified or plan['query_ready'])
                stop = ('member_budget' if fallback else 'query_set' if transferred and not identified
                        else 'identified' if identified else 'member_certified' if certified else 'budget')
                row.update(spent=spent, member_spent=spent, source_spent=0, terminal_plan=plan,
                    terminal_query=core.queries(plan), member=deepcopy(member), certified=certified,
                    identified=identified, transferred=transferred, fallback=fallback, stop=stop)
                row.update(library_before=before, advance=core.advance(state, member, anchors, arm, work[arm]),
                           library_after=deepcopy(state))
                records.append(row); arm_seconds[arm] += perf_counter()-arm_begun
        save(OUTPUT/'records.json', records); save(OUTPUT/'cases.json', cases_saved)
        print(json.dumps(dict(life=life, seconds=perf_counter()-begun,
            target_samples={a:w['controlled_samples'] for a,w in work.items()})), flush=True)
    save(OUTPUT/'run.json', dict(phases=['protocol_frozen','all_decisions_frozen'], arm_costs=work,
        arm_seconds=arm_seconds, historical_source_costs=historical))
    results = []; operators = {a:dict.fromkeys(core.OPERATORS, 0) for a in ARMS}
    for row in records:
        case = row['case']; _,laws,identities = task.world(row['life']); law = laws[row['index']]
        points = [score(row['initial_plan'], law, case, 0)] + [score(b['plan'], law, case, b['spent']) for b in row['batches']]
        if row['fallback']:
            points.append(score(row['terminal_plan'], law, case, row['spent']))
        state = row['library_after']
        library_coverage = len(state['bounds'])==3 and all(lo<=laws[i][op][cat]<=hi
            for i,box in enumerate(state['bounds']) for op in core.OPERATORS for cat,(lo,hi) in box[op]['bounds'].items())
        library_masks = all(identities[3+j] in mask for j,mask in enumerate(state['masks']))
        for op in core.OPERATORS:
            operators[row['arm']][op] += sum(row['member'][op].values())
        results.append(dict(life=row['life'], index=row['index'], arm=row['arm'], spent=row['spent'],
            source_spent=0, member_spent=row['spent'], certified=row['certified'], identified=row['identified'],
            identity_correct=row['identified'] and row['terminal_plan']['candidates'][0]==identities[row['index']],
            transferred=row['transferred'], transfer_correct=row['transferred'] and identities[row['index']] in row['terminal_plan']['candidates'],
            fallback=row['fallback'], history=points, terminal=points[-1],
            query_pre=query_score(row['initial_query'], law, case), query_post=query_score(row['terminal_query'], law, case),
            library_coverage=library_coverage, library_true_masks=library_masks, library_no_feasible=state['no_feasible']))
    stats = Counter(); summary = summarize(results, historical, stats, operators)
    save(OUTPUT/'results.json', results); save(OUTPUT/'summary.json', summary)
    save(OUTPUT/'run.json', dict(phases=['protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'],
        arm_costs=work, arm_seconds=arm_seconds, historical_source_costs=historical,
        bootstrap_costs=stats, seconds=perf_counter()-begun))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    run()
