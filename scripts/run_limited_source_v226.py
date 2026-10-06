"""Fresh lifecycles with limited initial evidence and a fully supplied reference."""
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
from acfqp.science import limited_source_v226 as core
from acfqp.science import latent_route_task_v213 as task
from scripts.run_conditioned_mechanisms_v205 import save, mean, draw
from scripts.run_persistent_evidence_v221 import score, query_score

OUTPUT = ROOT/'reports/limited_source_v226'
ARMS = core.ARMS
REFERENCES = ('LOW_FIXED', 'LOW_PARAM', 'FULL_FIXED')
CONTRASTS = (
    'fixed_minus_union_samples', 'param_minus_union_samples', 'full_minus_union_samples',
    'fixed_minus_param_samples', 'full_minus_union_target_samples',
    'union_minus_fixed_utility', 'union_minus_param_utility', 'union_minus_full_utility',
    'param_minus_fixed_utility', 'union_minus_fixed_regret', 'union_minus_param_regret',
    'union_minus_full_regret', 'param_minus_fixed_regret',
    'union_minus_fixed_late_certified', 'union_minus_param_late_certified',
    'union_minus_full_late_certified',
)
SOURCE_FILES = (
    'src/acfqp/science/limited_source_v226.py',
    'src/acfqp/science/mixture_confidence_v225.py',
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
    'scripts/run_limited_source_v226.py',
    'scripts/analyze_assignment_union_v222.py',
    'scripts/analyze_fixed_source_acquisition_v219.py',
    'scripts/analyze_mixture_confidence_v225.py',
    'scripts/analyze_limited_source_v226.py',
    'tests/test_limited_source_v226.py',
    'specs/LIMITED_SOURCE_V226.md',
    'reports/v226_runtime_tmp/run_stage.py',
)


def acquire_sources(life, laws, work):
    full, low, records = [], [], []
    for index in range(3):
        anchor, prefix = core.empty(), core.empty()
        for j, op in enumerate(core.OPERATORS):
            seed = 232000+(life*3+index)*3+j
            rng = random.Random(seed)
            progress = dict(draw_end=0, n=0)
            for start in range(0, 384, 16):
                increments = dict.fromkeys(core.ALPHABETS[op], 0)
                draw(rng, laws[index], op, increments, 16, work, progress)
                for cat, k in increments.items():
                    anchor[op][cat] += k
                    if start < 128:
                        prefix[op][cat] += k
                records.append(dict(life=life, index=index, operator=op, seed=seed,
                    draw_start=start, draw_end=progress['draw_end'], increments=increments))
        full.append(anchor); low.append(prefix)
    return dict(life=life, full=full, low=low), records


def summarize(results, source_costs, work, operators):
    arms = {}
    for arm in ARMS:
        rows = [r for r in results if r['arm']==arm]
        late = [r for r in rows if r['index']>=15]
        points = [p for r in rows for p in r['history']]
        source = sum(source_costs[arm]); target = sum(r['spent'] for r in rows)
        arms[arm] = dict(total_samples=source+target, source_samples=source,
            target_samples=target, source_revisit_samples=0,
            late_samples=sum(r['spent'] for r in late),
            late_certified=sum(r['certified'] for r in late),
            late_transferred=sum(r['transferred'] and r['transfer_correct'] for r in late),
            late_identified=sum(r['identified'] and r['identity_correct'] for r in late),
            wrong_transfers=sum(r['transferred'] and not r['transfer_correct'] for r in rows),
            late_utility=mean(float(r['terminal']['actual_utility']) for r in late),
            late_post_regret=mean(float(q['regret']) for r in late for q in r['query_post'].values()),
            history_violations=sum(p['violation'] for p in points),
            max_failure=max(float(p['actual'][1]) for p in points),
            coverage=mean(p['coverage'] for p in points), member_fallbacks=sum(r['fallback'] for r in rows),
            retained_targets=len(rows) if arm=='LOW_UNION' else 0,
            retained_target_samples=target if arm=='LOW_UNION' else 0,
            param_committed_targets=sum(r['committed'] for r in rows),
            param_committed_samples=sum(r['commit_samples'] for r in rows),
            wrong_param_commits=sum(r['committed'] and not r['commit_correct'] for r in rows),
            target_operator_samples=operators[arm],
            library_coverage=mean(r['library_coverage'] for r in rows),
            library_lost_masks=sum(not r['library_true_masks'] for r in rows),
            no_feasible=sum(r['library_no_feasible'] for r in rows))
    contrasts = {key: [] for key in CONTRASTS}
    for life in range(12):
        rows = [r for r in results if r['life']==life]
        target = {a:sum(r['spent'] for r in rows if r['arm']==a) for a in ARMS}
        totals = {a:source_costs[a][life]+target[a] for a in ARMS}
        late = {a:[r for r in rows if r['arm']==a and r['index']>=15] for a in ARMS}
        utility = {a:mean(float(r['terminal']['actual_utility']) for r in late[a]) for a in ARMS}
        regret = {a:mean(float(q['regret']) for r in late[a] for q in r['query_post'].values()) for a in ARMS}
        cert = {a:sum(r['certified'] for r in late[a]) for a in ARMS}
        f, p, h, u = 'LOW_FIXED', 'LOW_PARAM', 'FULL_FIXED', 'LOW_UNION'
        values = (
            totals[f]-totals[u], totals[p]-totals[u], totals[h]-totals[u], totals[f]-totals[p],
            target[h]-target[u], utility[u]-utility[f], utility[u]-utility[p], utility[u]-utility[h],
            utility[p]-utility[f], regret[u]-regret[f], regret[u]-regret[p], regret[u]-regret[h],
            regret[p]-regret[f], cert[u]-cert[f], cert[u]-cert[p], cert[u]-cert[h])
        for key, value in zip(CONTRASTS, values):
            contrasts[key].append(value)
    rng = random.Random(232900); samples = {key:[] for key in CONTRASTS}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]; work['bootstrap_index_draws'] += 12
        for key, rows in contrasts.items():
            samples[key].append(mean(rows[i] for i in indices)); work['bootstrap_mean_terms'] += 12
    intervals = {key:dict(mean=mean(rows), ci=[sorted(samples[key])[124], sorted(samples[key])[4874]])
                 for key, rows in contrasts.items()}
    tested = arms['LOW_UNION']; points = [p for r in results for p in r['history']]
    conditions = dict(
        RISK=all(p['actual'][1]<=F(1,20) and p['risk_upper']<=F(1,20) for p in points)
            and all(a['wrong_transfers']==0 and a['wrong_param_commits']==0 and a['library_coverage']==1
                and a['library_lost_masks']==0 and a['no_feasible']==0 for a in arms.values()),
        QUALITY=tested['late_certified']>=108 and tested['late_utility']>=2
            and all(tested['late_certified']>=arms[a]['late_certified'] for a in REFERENCES)
            and all(intervals[f'union_minus_{name}_utility']['ci'][0]>=-.05
                    for name in ('fixed','param','full')),
        APPLICABILITY=tested['late_transferred']>=108 and tested['late_post_regret']<=.05)
    for gate, name in (('LEARNING_EFFECT','fixed'), ('PARAMETER_REFERENCE','param'), ('FULL_REFERENCE','full')):
        effect = intervals[f'{name}_minus_union_samples']
        conditions[gate] = effect['mean']>=64 and effect['ci'][0]>0 and intervals[f'union_minus_{name}_regret']['ci'][1]<=.01
    return dict(complete=True, arms=arms, contrasts=contrasts, bootstrap=intervals, conditions=conditions,
        confidence=dict(scope='per_arm_per_lifecycle', source_family=1512, source_delta=3/220,
            source_beta=core.SOURCE_BETA, member_streams=168, member_delta=1/88,
            member_threshold=core.MEMBER_THRESHOLD, pool_streams=21, pool_delta=.025,
            pool_threshold=core.POOL_THRESHOLD, construction='jeffreys_beta_binomial_mixture',
            arm_delta=dict.fromkeys(ARMS,.05)),
        decision='LIMITED_SOURCE_LEARNING_SUPPORTED' if all(conditions.values()) else 'LIMITED_SOURCE_LEARNING_NOT_SUPPORTED')


def run():
    begun = perf_counter(); OUTPUT.mkdir(parents=True, exist_ok=False)
    for name in SOURCE_FILES:
        path = OUTPUT/'source_code'/name; path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, path)
    save(OUTPUT/'source_manifest.json', [dict(path=name) for name in SOURCE_FILES])
    source_costs = {a:[3456 if a=='FULL_FIXED' else 1152]*12 for a in ARMS}
    work = {a:Counter() for a in ARMS}; source_work = Counter()
    records, source_records, libraries, cases_saved = [], [], [], []
    arm_seconds = dict.fromkeys(ARMS,0.); source_seconds = 0.
    core.clear_cache()
    for life in range(12):
        cases, laws, identities = task.world(life)
        cases_saved.append(dict(life=life, cases=cases))
        started = perf_counter(); library, source_rows = acquire_sources(life,laws,source_work)
        source_seconds += perf_counter()-started
        libraries.append(library); source_records.extend(source_rows)
        anchors = {a:library['full' if a=='FULL_FIXED' else 'low'] for a in ARMS}
        states = {a:core.prepare(anchors[a],a,work[a]) for a in ARMS}
        for index, case in enumerate(cases[3:], start=3):
            seeds = {op:233000+(life*27+index)*3+j for j,op in enumerate(core.OPERATORS)}
            for arm in ARMS:
                started = perf_counter(); state = states[arm]; before = deepcopy(state)
                member = core.empty(); rng = {op:random.Random(seed) for op,seed in seeds.items()}
                plan = core.make_plan(member,anchors[arm],case,arm,work[arm],state)
                row = dict(life=life,index=index,case=case,arm=arm,seeds=seeds,
                    initial_plan=plan,initial_query=core.queries(plan),batches=[])
                spent = 0
                while True:
                    choice = core.choose(member,anchors[arm],case,arm,plan,spent,work[arm],state)
                    if choice is None:
                        break
                    op = choice['operator']; start = sum(member[op].values())
                    increments = dict.fromkeys(core.ALPHABETS[op],0); progress = dict(draw_end=start,n=start)
                    draw(rng[op],laws[index],op,increments,16,work[arm],progress)
                    for cat,k in increments.items():
                        member[op][cat] += k
                    spent += 16; plan = core.make_plan(member,anchors[arm],case,arm,work[arm],state)
                    row['batches'].append(dict(choice=choice,scope='TARGET',source_index=None,
                        operator=op,draw_start=start,increments=increments,draw_end=progress['draw_end'],
                        spent=spent,member_spent=spent,source_spent=0,plan=plan))
                fallback = len(plan['candidates'])!=1 and not plan['query_ready']
                if fallback:
                    plan = core.make_plan(member,anchors[arm],case,arm,work[arm],state,force_member=True)
                certified = plan['utility_lower']>=2
                identified = len(plan['candidates'])==1 and certified
                transferred = certified and plan['mode']=='library' and (identified or plan['query_ready'])
                stop = ('member_budget' if fallback else 'query_set' if transferred and not identified
                        else 'identified' if identified else 'member_certified' if certified else 'budget')
                row.update(spent=spent,member_spent=spent,source_spent=0,terminal_plan=plan,
                    terminal_query=core.queries(plan),member=deepcopy(member),certified=certified,
                    identified=identified,transferred=transferred,fallback=fallback,stop=stop)
                row.update(library_before=before,
                    advance=core.advance(state,member,anchors[arm],arm,work[arm],terminal_plan=plan),
                    library_after=deepcopy(state))
                records.append(row); arm_seconds[arm] += perf_counter()-started
        save(OUTPUT/'source_records.json',source_records); save(OUTPUT/'source_evidence.json',libraries)
        save(OUTPUT/'records.json',records); save(OUTPUT/'cases.json',cases_saved)
        print(json.dumps(dict(life=life,seconds=perf_counter()-begun,
            target_samples={a:w['controlled_samples'] for a,w in work.items()})),flush=True)
    run_info = dict(arm_costs=work,arm_seconds=arm_seconds,source_costs=source_costs,
        source_generation_costs=source_work,source_generation_seconds=source_seconds)
    save(OUTPUT/'run.json',dict(phases=['protocol_frozen','all_decisions_frozen'],**run_info))
    results = []; operators = {a:dict.fromkeys(core.OPERATORS,0) for a in ARMS}
    for row in records:
        case = row['case']; _,laws,identities = task.world(row['life']); law = laws[row['index']]
        points = [score(row['initial_plan'],law,case,0)] + [score(b['plan'],law,case,b['spent']) for b in row['batches']]
        if row['fallback']:
            points.append(score(row['terminal_plan'],law,case,row['spent']))
        state = row['library_after']
        library_coverage = len(state['bounds'])==3 and all(lo<=laws[i][op][cat]<=hi
            for i,box in enumerate(state['bounds']) for op in core.OPERATORS for cat,(lo,hi) in box[op]['bounds'].items())
        masks = all(identities[3+j] in mask for j,mask in enumerate(state['masks']))
        event = row['advance']; committed = row['arm']=='LOW_PARAM' and event is not None
        for op in core.OPERATORS:
            operators[row['arm']][op] += sum(row['member'][op].values())
        results.append(dict(life=row['life'],index=row['index'],arm=row['arm'],spent=row['spent'],
            source_spent=0,member_spent=row['spent'],certified=row['certified'],identified=row['identified'],
            identity_correct=row['identified'] and row['terminal_plan']['candidates'][0]==identities[row['index']],
            transferred=row['transferred'],transfer_correct=row['transferred'] and identities[row['index']] in row['terminal_plan']['candidates'],
            committed=committed,commit_samples=event['samples'] if committed else 0,
            commit_correct=committed and event['source_index']==identities[row['index']],
            fallback=row['fallback'],history=points,terminal=points[-1],
            query_pre=query_score(row['initial_query'],law,case),query_post=query_score(row['terminal_query'],law,case),
            library_coverage=library_coverage,library_true_masks=masks,library_no_feasible=state['no_feasible']))
    stats = Counter(); summary = summarize(results,source_costs,stats,operators)
    save(OUTPUT/'results.json',results); save(OUTPUT/'summary.json',summary)
    save(OUTPUT/'run.json',dict(phases=['protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'],
        **run_info,bootstrap_costs=stats,seconds=perf_counter()-begun))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    run()
