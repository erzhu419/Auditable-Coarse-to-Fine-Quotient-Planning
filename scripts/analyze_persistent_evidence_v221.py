"""Independent chronological evidence replay with raw-CI intersections only."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import analyze_fixed_source_acquisition_v219 as prior

OUTPUT = ROOT/'reports/persistent_evidence_v221'
ARMS = ('PERSIST','FROZEN','LOCAL','ORACLE')
OPERATORS, SUPPORT = prior.OPERATORS, prior.SUPPORT
F = Fraction
empty, world, queries = prior.empty, prior.world, prior.queries
score, query_score, same = prior.score, prior.query_score, prior.same
settled = prior.settled
independent = prior.prior.independent
reconstruct_source = prior.reconstruct_source


def prepare(anchors, work):
    return dict(counts=deepcopy(anchors),
                bounds=[settled.boxes(anchor,work) for anchor in anchors],
                commits=[0]*len(anchors))


def make_plan(member, anchors, case, arm, work, identity=None, force_member=False,
              state=None):
    if arm != 'PERSIST':
        return prior.make_plan(member,anchors,case,'SET' if arm == 'FROZEN' else arm,
                               work,identity,force_member)
    cumulative = state['counts']
    if force_member:
        return prior.make_plan(member,cumulative,case,'SET',work,identity,True)
    raw = settled.boxes(member,work)
    candidates, blocks = [], {}
    for index,reference in enumerate(state['bounds']):
        block = deepcopy(raw)
        compatible = True
        for op in OPERATORS:
            for cat in SUPPORT[op]:
                a,b = raw[op]['bounds'][cat],reference[op]['bounds'][cat]
                pair = (max(a[0],b[0]),min(a[1],b[1]))
                compatible &= pair[0] <= pair[1]
                block[op]['bounds'][cat] = pair
        if compatible:
            candidates.append(index)
            blocks[index] = block
    if candidates:
        risks = [settled.risk_bounds(block) for block in blocks.values()]
        goals = [settled.goal_bounds(block,case) for block in blocks.values()]
        upper = {policy: max(F(0),*(r[policy] for r in risks)) for policy in risks[0]}
        lower = {policy: min(g[policy] for g in goals) for policy in goals[0]}
        means = [independent.posterior({op: {
            cat: member[op][cat]+cumulative[index][op][cat] for cat in SUPPORT[op]}
            for op in OPERATORS}) for index in candidates]
        probabilities = {op: {cat: sum(p[op][cat] for p in means)/len(means)
                              for cat in SUPPORT[op]} for op in OPERATORS}
        envelope = deepcopy(raw)
        for op in OPERATORS:
            envelope[op]['bounds'] = {cat: (
                min(block[op]['bounds'][cat][0] for block in blocks.values()),
                max(block[op]['bounds'][cat][1] for block in blocks.values()))
                for cat in SUPPORT[op]}
        mode = 'library'
    else:
        envelope, mode = raw, 'member'
        upper,lower = settled.risk_bounds(raw),settled.goal_bounds(raw,case)
        probabilities = independent.posterior(member)
    pure = settled.vectors(case,probabilities)
    plan = dict(settled.optimize(pure,upper,lower,work),envelopes=envelope,
                risks=upper,goals_lower=lower,pure_vectors=pure,candidates=candidates,
                candidate_envelopes=blocks,mode=mode)
    value = prior.prior.proxy(member,cumulative,case,plan)
    plan['query_proxy'] = value
    plan['query_ready'] = mode == 'library' and plan['utility_lower'] >= 2 and value is not None and value <= F(1,20)
    return plan


def choose(member, anchors, case, arm, plan, spent, work, state=None):
    library = state['counts'] if arm == 'PERSIST' else anchors
    return prior.choose(member,library,case,'SET' if arm in ('PERSIST','FROZEN') else arm,
                        plan,spent,work)


def commit(state, member, plan, work):
    if plan['utility_lower'] < 2 or plan['mode'] != 'library' or len(plan['candidates']) != 1:
        return None
    index = plan['candidates'][0]
    raw = settled.boxes(member,work)
    for op in OPERATORS:
        for cat in SUPPORT[op]:
            state['counts'][index][op][cat] += member[op][cat]
            old,new = state['bounds'][index][op]['bounds'][cat],raw[op]['bounds'][cat]
            state['bounds'][index][op]['bounds'][cat] = (max(old[0],new[0]),min(old[1],new[1]))
    state['commits'][index] += 1
    return dict(source_index=index,samples=sum(sum(row.values()) for row in member.values()))


def summary(results, work, historical):
    arms = {}
    for arm in ARMS:
        rows = [r for r in results if r['arm'] == arm]
        late = [r for r in rows if r['index'] >= 15]
        points = [p for r in rows for p in r['history']]
        arms[arm] = dict(total_samples=sum(historical[arm])+sum(r['spent'] for r in rows),
            source_samples=sum(historical[arm]),
            target_samples=sum(r['member_spent'] for r in rows),
            source_revisit_samples=0,
            late_samples=sum(r['spent'] for r in late),
            late_certified=sum(r['certified'] for r in late),
            late_transferred=sum(r['transferred'] and r['transfer_correct'] for r in late),
            late_identified=sum(r['identified'] and r['identity_correct'] for r in late),
            wrong_transfers=sum(r['transferred'] and not r['transfer_correct'] for r in rows),
            late_utility=settled.mean(float(r['terminal']['actual_utility']) for r in late),
            late_post_regret=settled.mean(float(v['regret']) for r in late for v in r['query_post'].values()),
            history_violations=sum(p['violation'] for p in points),
            max_failure=max(float(p['actual'][1]) for p in points),
            coverage=settled.mean(p['coverage'] for p in points),
            member_fallbacks=sum(r['fallback'] for r in rows),
            committed_targets=sum(r['commit'] is not None for r in rows),
            committed_target_samples=sum(r['commit']['samples'] for r in rows if r['commit'] is not None),
            wrong_commits=sum(r['commit'] is not None and not r['commit_correct'] for r in rows))
    contrasts = {key: [] for key in ('local_minus_persist_samples','frozen_minus_persist_samples',
        'persist_minus_local_late_utility','persist_minus_frozen_post_regret','persist_minus_oracle_samples',
        'persist_minus_frozen_late_utility','persist_minus_frozen_late_certified')}
    for life in range(12):
        rows = [r for r in results if r['life'] == life]
        costs = {arm: historical[arm][life]+sum(r['spent'] for r in rows if r['arm'] == arm) for arm in ARMS}
        utility = {arm: settled.mean(float(r['terminal']['actual_utility']) for r in rows
                        if r['arm'] == arm and r['index'] >= 15) for arm in ARMS}
        regret = {arm: settled.mean(float(v['regret']) for r in rows if r['arm'] == arm
                        and r['index'] >= 15 for v in r['query_post'].values()) for arm in ARMS}
        contrasts['local_minus_persist_samples'].append(costs['LOCAL']-costs['PERSIST'])
        contrasts['frozen_minus_persist_samples'].append(costs['FROZEN']-costs['PERSIST'])
        contrasts['persist_minus_oracle_samples'].append(costs['PERSIST']-costs['ORACLE'])
        contrasts['persist_minus_local_late_utility'].append(utility['PERSIST']-utility['LOCAL'])
        contrasts['persist_minus_frozen_late_utility'].append(utility['PERSIST']-utility['FROZEN'])
        contrasts['persist_minus_frozen_late_certified'].append(
            sum(r['certified'] for r in rows if r['arm'] == 'PERSIST' and r['index'] >= 15)
            -sum(r['certified'] for r in rows if r['arm'] == 'FROZEN' and r['index'] >= 15))
        contrasts['persist_minus_frozen_post_regret'].append(regret['PERSIST']-regret['FROZEN'])
    rng = random.Random(225900)
    samples = {key: [] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]
        for key,rows in contrasts.items():
            samples[key].append(settled.mean(rows[i] for i in indices))
        work['bootstrap_index_draws'] += 12
        work['bootstrap_mean_terms'] += 84
    intervals = {key: dict(mean=settled.mean(rows),
        ci=[sorted(samples[key])[124],sorted(samples[key])[4874]]) for key,rows in contrasts.items()}
    target = arms['PERSIST']
    points = [p for r in results if r['arm'] == 'PERSIST' for p in r['history']]
    conditions = dict(
        COST=intervals['local_minus_persist_samples']['mean'] >= 64
             and intervals['local_minus_persist_samples']['ci'][0] > 0,
        QUALITY=target['late_certified'] >= 108
                and target['late_certified'] >= arms['LOCAL']['late_certified']
                and target['late_utility'] >= 2
                and intervals['persist_minus_local_late_utility']['ci'][0] >= -.05,
        RISK=all(p['actual'][1] <= F(1,20) and p['risk_upper'] <= F(1,20) for p in points)
             and target['wrong_commits'] == 0,
        APPLICABILITY=target['late_transferred'] >= 108 and target['late_post_regret'] <= .05,
        TARGET_EFFECT=intervals['frozen_minus_persist_samples']['ci'][0] > 0
                    and intervals['persist_minus_frozen_post_regret']['ci'][1] <= .01,
        REFERENCE_QUALITY=target['late_certified'] >= arms['FROZEN']['late_certified']
                    and intervals['persist_minus_frozen_late_utility']['ci'][0] >= -.05)
    return dict(complete=True,arms=arms,contrasts=contrasts,bootstrap=intervals,conditions=conditions,
        decision='PERSISTENT_EVIDENCE_SUPPORTED' if all(conditions.values()) else 'PERSISTENT_EVIDENCE_NOT_SUPPORTED')


def analyze():
    begun = perf_counter()
    work,actual,planning = Counter(),Counter(),Counter()
    checks = []
    def check(name, value): checks.append(dict(name=name,passed=bool(value)))
    def read(name): return json.loads((OUTPUT/name).read_text())
    try:
        worlds = [world(life) for life in range(12)]
        check('fixed_opaque_private_worlds',same(read('cases.json'),
              [dict(life=life,cases=worlds[life][0]) for life in range(12)]))
        source_rows = read('source_evidence.json')
        sources = {(r['life'],r['index'],r['arm']): r for r in source_rows}
        check('only_complete_actual_initial_full_and_local_sources',
            len(source_rows) == len(sources) == 72 and all(
                (life,index,arm) in sources for life in range(12)
                for index in range(3) for arm in ('FULL','LOCAL')))
        maximum = Counter()
        for row in source_rows:
            for op in OPERATORS:
                n = 16*sum(b['operator'] == op for b in row['batches'])
                key = row['life'],row['index'],op
                maximum[key] = max(maximum[key],n)
        source_prefixes = {key: settled.generate_prefix(
            223000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]),n,
            worlds[key[0]][1][key[1]][key[2]],SUPPORT[key[2]],work)
            for key,n in maximum.items()}
        libraries = []
        source_costs = {arm: [0]*12 for arm in ('FULL','LOCAL')}
        for life in range(12):
            anchors = []
            flags = dict(plans=True,counts=True,choices=True,queries=True)
            for index in range(3):
                for arm in ('FULL','LOCAL'):
                    row = sources[life,index,arm]
                    member,spent,verified = reconstruct_source(
                        row,worlds[life][0][index],source_prefixes,work)
                    for key,value in verified.items(): flags[key] &= value
                    source_costs[arm][life] += spent
                    if arm == 'FULL': anchors.append(deepcopy(member))
            libraries.append(dict(life=life,anchors=anchors))
            for key,value in flags.items(): check(f'life_{life}_historical_source_{key}',value)
        historical = {arm: list(source_costs['LOCAL' if arm == 'LOCAL' else 'FULL']) for arm in ARMS}
        check('actual_historical_source_costs',source_costs['FULL'] == [3456]*12
              and sum(source_costs['LOCAL']) == 12640)
        check('frozen_library_from_actual_full_source_prefixes',same(read('libraries.json'),libraries))
        rows = read('records.json')
        lookup = {(r['life'],r['index'],r['arm']): r for r in rows}
        check('complete_unique_fresh_targets',len(rows) == len(lookup) == 1152
              and all((life,index,arm) in lookup for life in range(12)
                      for index in range(3,27) for arm in ARMS))
        paired = True
        for life in range(12):
            for index in range(3,27):
                seeds = {op: 226000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
                paired &= all(lookup[life,index,arm]['seeds'] == seeds for arm in ARMS)
        check('four_arm_shared_fresh_target_prefix_seeds',paired)
        maximum = Counter()
        for row in rows:
            for op in OPERATORS:
                n = 16*sum(b['operator'] == op for b in row['batches'])
                key = row['life'],row['index'],op
                maximum[key] = max(maximum[key],n)
        prefixes = {key: settled.generate_prefix(
            226000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]),n,
            worlds[key[0]][1][key[1]][key[2]],SUPPORT[key[2]],work)
            for key,n in maximum.items()}
        frozen = []
        persistent_plans, committed_tasks, committed_samples = 0,0,0
        for life in range(12):
            cases,_,identities = worlds[life]
            anchors = libraries[life]['anchors']
            state = prepare(anchors,work)
            decisions_ok = allocation_ok = counts_ok = plans_ok = state_ok = True
            for index in range(3,27):
                case = cases[index]
                seeds = {op: 226000+(life*27+index)*3+i for i,op in enumerate(OPERATORS)}
                for arm in ARMS:
                    row = lookup[life,index,arm]
                    active_state = state if arm == 'PERSIST' else None
                    before = deepcopy(active_state)
                    state_ok &= same(row['library_before'],before)
                    member = empty()
                    library = [] if arm == 'LOCAL' else anchors
                    identity = identities[index] if arm == 'ORACLE' else None
                    plan = make_plan(member,library,case,arm,work,identity,state=active_state)
                    planning[arm] += 1
                    persistent_plans += int(arm == 'PERSIST')
                    plans_ok &= same(row['case'],case) and row['seeds'] == seeds
                    plans_ok &= same(row['initial_plan'],plan)
                    pre = queries(plan)
                    decisions_ok &= same(row['initial_query'],pre)
                    history = [(0,plan)]
                    spent,consumed = 0,Counter()
                    for batch in row['batches']:
                        choice = choose(member,library,case,arm,plan,spent,work,state=active_state)
                        allocation_ok &= choice is not None and same(batch['choice'],choice)
                        op = choice['operator']
                        allocation_ok &= choice['scope'] == 'TARGET' and choice['source_index'] is None
                        increments = dict.fromkeys(SUPPORT[op],0)
                        for cat in prefixes[life,index,op][consumed[op]:consumed[op]+16]:
                            increments[cat] += 1
                        counts_ok &= batch['operator'] == op and batch['scope'] == 'TARGET'
                        counts_ok &= batch['source_index'] is None and batch['draw_start'] == consumed[op]
                        counts_ok &= batch['increments'] == increments and sum(increments.values()) == 16
                        for cat,k in increments.items(): member[op][cat] += k
                        consumed[op] += 16; spent += 16; actual[arm] += 16
                        counts_ok &= batch['draw_end'] == consumed[op] and batch['spent'] == spent
                        counts_ok &= batch['member_spent'] == spent and batch['source_spent'] == 0
                        plan = make_plan(member,library,case,arm,work,identity,state=active_state)
                        planning[arm] += 1
                        persistent_plans += int(arm == 'PERSIST')
                        plans_ok &= same(batch['plan'],plan)
                        history.append((spent,plan))
                    allocation_ok &= choose(member,library,case,arm,plan,spent,work,state=active_state) is None
                    allocation_ok &= 0 <= spent <= 384
                    fallback = arm != 'LOCAL' and len(plan['candidates']) != 1 and not (arm in ('PERSIST','FROZEN') and plan['query_ready'])
                    if fallback:
                        plan = make_plan(member,library,case,arm,work,identity,force_member=True,state=active_state)
                        planning[arm] += 1
                        history.append((spent,plan))
                    certified = plan['utility_lower'] >= 2
                    identified = arm != 'LOCAL' and len(plan['candidates']) == 1 and certified
                    transferred = arm != 'LOCAL' and certified and plan['mode'] == 'library' and (identified or arm in ('PERSIST','FROZEN') and plan['query_ready'])
                    stop = ('member_budget' if fallback else 'query_set' if transferred and not identified else
                            'identified' if identified else 'member_certified' if certified else 'budget')
                    allocation_ok &= row['stop'] == stop and row['fallback'] == fallback
                    plans_ok &= row['spent'] == spent and row['member_spent'] == spent and row['source_spent'] == 0
                    plans_ok &= row['certified'] == certified and row['identified'] == identified
                    plans_ok &= row['transferred'] == transferred and same(row['member'],member)
                    plans_ok &= same(row['terminal_plan'],plan)
                    post = queries(plan)
                    decisions_ok &= same(row['terminal_query'],post)
                    # No library change is visible to any plan of this target.
                    state_ok &= active_state == before
                    event = commit(state,member,plan,work) if arm == 'PERSIST' else None
                    state_ok &= same(row['commit'],event) and same(row['library_after'],active_state)
                    if event is not None:
                        committed_tasks += 1
                        committed_samples += event['samples']
                        state_ok &= event['samples'] == spent
                    frozen.append(dict(life=life,index=index,arm=arm,spent=spent,
                        certified=certified,identified=identified,transferred=transferred,
                        fallback=fallback,plan=plan,history=history,pre=pre,post=post,commit=event))
            for name,flag in [('full_policy_queries',decisions_ok),('choices_stops_and_target_only_budget',allocation_ok),
                              ('actual_paired_fresh_target_prefixes',counts_ok),('raw_member_and_persistent_intersection_plans',plans_ok),
                              ('chronological_once_only_commits_and_source_provenance',state_ok)]:
                check(f'life_{life}_{name}',flag)
        # Private identities and laws evaluate already frozen target decisions only.
        results = []
        for row in frozen:
            life,index,arm = row['life'],row['index'],row['arm']
            cases,laws,identities = worlds[life]
            plan,event = row['plan'],row['commit']
            points = [score(p,laws[index],cases[index],spent,work) for spent,p in row['history']]
            results.append(dict(life=life,index=index,arm=arm,spent=row['spent'],
                source_spent=0,member_spent=row['spent'],certified=row['certified'],identified=row['identified'],
                identity_correct=row['identified'] and plan['candidates'][0] == identities[index],
                transferred=row['transferred'],transfer_correct=row['transferred'] and identities[index] in plan['candidates'],
                fallback=row['fallback'],history=points,terminal=points[-1],commit=event,
                commit_correct=event is not None and event['source_index'] == identities[index],
                query_pre=query_score(row['pre'],laws[index],cases[index]),
                query_post=query_score(row['post'],laws[index],cases[index])))
        check('frozen_history_true_joint_and_own_query_results',same(read('results.json'),results))
        stats = Counter()
        expected = summary(results,stats,historical)
        check('total_lifecycle_statistics_and_frozen_gates',same(read('summary.json'),expected))
        run = read('run.json')
        check('historical_source_fee_is_separate_from_fresh_sampling',same(run['historical_source_costs'],historical))
        check('actual_fresh_target_and_planning_costs',sum(actual.values()) <= 442368 and all(
            run['arm_costs'][arm].get(key,0) == actual[arm]
            for arm in ARMS for key in ('controlled_samples','controlled_resets','environment_random_draws'))
            and all(run['arm_costs'][arm]['planning_calls'] == planning[arm] for arm in ARMS)
            and all(expected['arms'][arm]['source_samples'] == sum(historical[arm])
                    and expected['arms'][arm]['target_samples'] == actual[arm]
                    and expected['arms'][arm]['total_samples'] == sum(historical[arm])+actual[arm]
                    and expected['arms'][arm]['source_revisit_samples'] == 0 for arm in ARMS))
        check('actual_persistent_preparations_plans_and_committed_evidence_costs',
            run['arm_costs']['PERSIST'].get('persistent_preparations',0) == 12
            and run['arm_costs']['PERSIST'].get('persistent_planning_calls',0) == persistent_plans
            and run['arm_costs']['PERSIST'].get('persistent_committed_tasks',0) == committed_tasks
            and run['arm_costs']['PERSIST'].get('persistent_committed_samples',0) == committed_samples
            and all(run['arm_costs'][arm].get(key,0) == 0 for arm in ARMS if arm != 'PERSIST'
                    for key in ('persistent_preparations','persistent_planning_calls',
                                'persistent_committed_tasks','persistent_committed_samples')))
        check('frozen_bootstrap_costs',run['bootstrap_costs'] == dict(stats))
        check('oracle_scoring_after_all_decisions',run['phases'] == [
            'protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'])
        complete = True
    except Exception as error:
        check('reconstruction',False)
        checks[-1]['error'] = f'{type(error).__name__}: {error}'
        complete = False
    output = dict(valid=complete and all(c['passed'] for c in checks),complete=complete,
                  checks=checks,costs=dict(work),seconds=perf_counter()-begun)
    (OUTPUT/'analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(valid=output['valid'],complete=complete,checks=len(checks))))
    return output


if __name__ == '__main__':
    raise SystemExit(0 if analyze()['valid'] else 1)
