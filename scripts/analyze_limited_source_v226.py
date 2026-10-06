"""Independent source-budget, parameter-memory and cumulative-CS replay."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import analyze_mixture_confidence_v225 as cs_math

OUTPUT = ROOT/'reports/limited_source_v226'
ARMS = ('FULL_FIXED', 'LOW_FIXED', 'LOW_PARAM', 'LOW_UNION')
OPERATORS, SUPPORT = cs_math.OPERATORS, cs_math.SUPPORT
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
empty, world, queries = cs_math.empty, cs_math.world, cs_math.queries
same, score, query_score = cs_math.same, cs_math.score, cs_math.query_score
settled = cs_math.settled


def prepare(anchors, arm):
    state = cs_math.prepare(anchors, arm)
    if arm == 'LOW_PARAM':
        state.update(counts=deepcopy(anchors), commits=[0]*len(anchors))
    return state


def point_bank(anchors, arm, state):
    return state['counts'] if arm == 'LOW_PARAM' else anchors


def make_plan(member, anchors, case, arm, state, work, force_member=False):
    return cs_math.make_plan(member, point_bank(anchors, arm, state), case, arm,
                             state, work, force_member=force_member)


def choose(member, anchors, case, arm, plan, spent, work, state):
    return cs_math.choose(member, point_bank(anchors, arm, state), case, arm,
                          plan, spent, work)


def advance(state, member, anchors, arm, plan):
    if arm == 'LOW_PARAM':
        if plan['mode'] != 'library' or len(plan['candidates']) != 1:
            return None
        index = plan['candidates'][0]
        for op in OPERATORS:
            for cat in SUPPORT[op]:
                state['counts'][index][op][cat] += member[op][cat]
        state['commits'][index] += 1
        return dict(source_index=index, samples=sum(sum(row.values()) for row in member.values()))
    if arm != 'LOW_UNION':
        return None
    state['members'].append(deepcopy(member))
    problem = cs_math.raw_problem(anchors, state['members'])
    result = cs_math.outer_union(problem, anchors, state['members'])
    state.update(result)
    return result


def reconstruct_sources(rows, worlds, work):
    lookup = {(row['life'], row['index'], row['operator'], row['draw_start']): row for row in rows}
    complete = len(rows) == len(lookup) == 2592 and all(
        (life, index, op, start) in lookup for life in range(12) for index in range(3)
        for op in OPERATORS for start in range(0,384,16))
    flags = dict(complete=complete, seeds=True, increments=True, budgets=True)
    libraries = []
    for life in range(12):
        full, low = [], []
        for index in range(3):
            complete_counts, limited_counts = empty(), empty()
            for j, op in enumerate(OPERATORS):
                seed = 232000+(life*3+index)*3+j
                prefix = settled.generate_prefix(seed, 384, worlds[life][1][index][op], SUPPORT[op], work)
                for start in range(0,384,16):
                    row = lookup[life, index, op, start]
                    increments = dict.fromkeys(SUPPORT[op], 0)
                    for cat in prefix[start:start+16]:
                        increments[cat] += 1
                    flags['seeds'] &= row['seed'] == seed
                    flags['increments'] &= row['draw_end'] == start+16 and row['increments'] == increments
                    for cat, count in increments.items():
                        complete_counts[op][cat] += count
                        if start < 128:
                            limited_counts[op][cat] += count
                flags['budgets'] &= sum(complete_counts[op].values()) == 384
                flags['budgets'] &= sum(limited_counts[op].values()) == 128
            full.append(complete_counts)
            low.append(limited_counts)
        libraries.append(dict(life=life, full=full, low=low))
    return libraries, flags


def summary(results, frozen, work, source_costs):
    arms = {}
    for arm in ARMS:
        rows = [row for row in results if row['arm'] == arm]
        late = [row for row in rows if row['index'] >= 15]
        points = [point for row in rows for point in row['history']]
        source, target = sum(source_costs[arm]), sum(row['spent'] for row in rows)
        observed = [row for row in frozen if row['arm'] == arm]
        arms[arm] = dict(total_samples=source+target,source_samples=source,target_samples=target,
            source_revisit_samples=0,late_samples=sum(row['spent'] for row in late),
            late_certified=sum(row['certified'] for row in late),
            late_transferred=sum(row['transferred'] and row['transfer_correct'] for row in late),
            late_identified=sum(row['identified'] and row['identity_correct'] for row in late),
            wrong_transfers=sum(row['transferred'] and not row['transfer_correct'] for row in rows),
            late_utility=settled.mean(float(row['terminal']['actual_utility']) for row in late),
            late_post_regret=settled.mean(float(q['regret']) for row in late for q in row['query_post'].values()),
            history_violations=sum(point['violation'] for point in points),
            max_failure=max(float(point['actual'][1]) for point in points),
            coverage=settled.mean(point['coverage'] for point in points),
            member_fallbacks=sum(row['fallback'] for row in rows),
            retained_targets=len(rows) if arm == 'LOW_UNION' else 0,
            retained_target_samples=target if arm == 'LOW_UNION' else 0,
            param_committed_targets=sum(row['committed'] for row in rows),
            param_committed_samples=sum(row['commit_samples'] for row in rows),
            wrong_param_commits=sum(row['committed'] and not row['commit_correct'] for row in rows),
            target_operator_samples={op: sum(sum(row['member'][op].values()) for row in observed)
                                     for op in OPERATORS},
            library_coverage=settled.mean(row['library_coverage'] for row in rows),
            library_lost_masks=sum(not row['library_true_masks'] for row in rows),
            no_feasible=sum(row['library_no_feasible'] for row in rows))
    keys = ('fixed_minus_union_samples','param_minus_union_samples','full_minus_union_samples',
            'fixed_minus_param_samples','full_minus_union_target_samples',
            'union_minus_fixed_utility','union_minus_param_utility','union_minus_full_utility',
            'param_minus_fixed_utility','union_minus_fixed_regret','union_minus_param_regret',
            'union_minus_full_regret','param_minus_fixed_regret','union_minus_fixed_late_certified',
            'union_minus_param_late_certified','union_minus_full_late_certified')
    contrasts = {key: [] for key in keys}
    for life in range(12):
        rows = [row for row in results if row['life'] == life]
        target = {arm: sum(row['spent'] for row in rows if row['arm'] == arm) for arm in ARMS}
        total = {arm: source_costs[arm][life]+target[arm] for arm in ARMS}
        late = {arm: [row for row in rows if row['arm'] == arm and row['index'] >= 15] for arm in ARMS}
        utility = {arm: settled.mean(float(row['terminal']['actual_utility']) for row in late[arm]) for arm in ARMS}
        regret = {arm: settled.mean(float(q['regret']) for row in late[arm] for q in row['query_post'].values()) for arm in ARMS}
        cert = {arm: sum(row['certified'] for row in late[arm]) for arm in ARMS}
        values = dict(
            fixed_minus_union_samples=total['LOW_FIXED']-total['LOW_UNION'],
            param_minus_union_samples=total['LOW_PARAM']-total['LOW_UNION'],
            full_minus_union_samples=total['FULL_FIXED']-total['LOW_UNION'],
            fixed_minus_param_samples=total['LOW_FIXED']-total['LOW_PARAM'],
            full_minus_union_target_samples=target['FULL_FIXED']-target['LOW_UNION'],
            union_minus_fixed_utility=utility['LOW_UNION']-utility['LOW_FIXED'],
            union_minus_param_utility=utility['LOW_UNION']-utility['LOW_PARAM'],
            union_minus_full_utility=utility['LOW_UNION']-utility['FULL_FIXED'],
            param_minus_fixed_utility=utility['LOW_PARAM']-utility['LOW_FIXED'],
            union_minus_fixed_regret=regret['LOW_UNION']-regret['LOW_FIXED'],
            union_minus_param_regret=regret['LOW_UNION']-regret['LOW_PARAM'],
            union_minus_full_regret=regret['LOW_UNION']-regret['FULL_FIXED'],
            param_minus_fixed_regret=regret['LOW_PARAM']-regret['LOW_FIXED'],
            union_minus_fixed_late_certified=cert['LOW_UNION']-cert['LOW_FIXED'],
            union_minus_param_late_certified=cert['LOW_UNION']-cert['LOW_PARAM'],
            union_minus_full_late_certified=cert['LOW_UNION']-cert['FULL_FIXED'])
        for key in keys:
            contrasts[key].append(values[key])
    randomizer = random.Random(232900)
    samples = {key: [] for key in keys}
    for _ in range(5000):
        indices = [randomizer.randrange(12) for _ in range(12)]
        work['bootstrap_index_draws'] += 12
        for key in keys:
            samples[key].append(settled.mean(contrasts[key][i] for i in indices))
            work['bootstrap_mean_terms'] += 12
    intervals = {key: dict(mean=settled.mean(rows),
                           ci=[sorted(samples[key])[124],sorted(samples[key])[4874]])
                 for key,rows in contrasts.items()}
    tested = arms['LOW_UNION']
    points = [point for row in results for point in row['history']]
    conditions = dict(
        RISK=all(point['actual'][1] <= F(1,20) and point['risk_upper'] <= F(1,20) for point in points)
             and all(arm['wrong_transfers'] == 0 and arm['wrong_param_commits'] == 0
                     and arm['library_coverage'] == 1 and arm['library_lost_masks'] == 0
                     and arm['no_feasible'] == 0 for arm in arms.values()),
        QUALITY=tested['late_certified'] >= 108 and tested['late_utility'] >= 2
                and all(tested['late_certified'] >= arms[arm]['late_certified']
                        for arm in ('LOW_FIXED','LOW_PARAM','FULL_FIXED'))
                and all(intervals['union_minus_'+name+'_utility']['ci'][0] >= -.05
                        for name in ('fixed','param','full')),
        APPLICABILITY=tested['late_transferred'] >= 108 and tested['late_post_regret'] <= .05)
    for gate,name in (('LEARNING_EFFECT','fixed'),('PARAMETER_REFERENCE','param'),('FULL_REFERENCE','full')):
        effect = intervals[name+'_minus_union_samples']
        conditions[gate] = (effect['mean'] >= 64 and effect['ci'][0] > 0
                            and intervals['union_minus_'+name+'_regret']['ci'][1] <= .01)
    return dict(complete=True,arms=arms,contrasts=contrasts,bootstrap=intervals,conditions=conditions,
        confidence=dict(scope='per_arm_per_lifecycle',source_family=1512,source_delta=3/220,
                        source_beta=cs_math.SOURCE_BETA,member_streams=168,member_delta=1/88,
                        member_threshold=cs_math.MEMBER_THRESHOLD,pool_streams=21,pool_delta=.025,
                        pool_threshold=cs_math.POOL_THRESHOLD,construction='jeffreys_beta_binomial_mixture',
                        arm_delta=dict.fromkeys(ARMS,.05)),
        decision='LIMITED_SOURCE_LEARNING_SUPPORTED' if all(conditions.values())
                 else 'LIMITED_SOURCE_LEARNING_NOT_SUPPORTED')


def analyze():
    started = perf_counter()
    work, actual, planning = Counter(), Counter(), Counter()
    union_calls, retained_samples = Counter(), Counter()
    parameter_commits, parameter_samples = Counter(), Counter()
    checks = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
    def read(name):
        return json.loads((OUTPUT/name).read_text())
    try:
        check('complete_limited_source_code_manifest',read('source_manifest.json') ==
              [dict(path=path) for path in SOURCE_FILES])
        worlds = [world(life) for life in range(12)]
        check('fixed_public_cases_and_private_worlds', same(read('cases.json'),
              [dict(life=life, cases=worlds[life][0]) for life in range(12)]))
        libraries, source_flags = reconstruct_sources(read('source_records.json'), worlds, work)
        for key, flag in source_flags.items():
            check('fresh_full_and_first128_source_'+key, flag)
        check('full_and_low_libraries_from_actual_shared_source_prefixes',
              same(read('source_evidence.json'), libraries))
        historical = {arm: [3456 if arm == 'FULL_FIXED' else 1152]*12 for arm in ARMS}
        rows = read('records.json')
        lookup = {(row['life'], row['index'], row['arm']): row for row in rows}
        check('complete_unique_four_arm_fresh_targets', len(rows) == len(lookup) == 1152 and all(
            (life, index, arm) in lookup for life in range(12) for index in range(3,27) for arm in ARMS))
        paired, maximum = True, Counter()
        for row in rows:
            life, index = row['life'], row['index']
            seeds = {op: 233000+(life*27+index)*3+j for j, op in enumerate(OPERATORS)}
            paired &= row['seeds'] == seeds
            for op in OPERATORS:
                n = 16*sum(batch['operator'] == op for batch in row['batches'])
                maximum[life, index, op] = max(maximum[life, index, op], n)
        check('four_arm_shared_fresh_target_prefixes', paired)
        prefixes = {key: settled.generate_prefix(
            233000+(key[0]*27+key[1])*3+OPERATORS.index(key[2]), n,
            worlds[key[0]][1][key[1]][key[2]], SUPPORT[key[2]], work)
            for key, n in maximum.items()}
        frozen = []
        for life in range(12):
            cases = worlds[life][0]
            anchors = {arm: libraries[life]['full' if arm == 'FULL_FIXED' else 'low'] for arm in ARMS}
            states = {arm: prepare(anchors[arm], arm) for arm in ARMS}
            initial_bounds = {arm: deepcopy(states[arm]['bounds']) for arm in ARMS}
            flags = dict(plans=True, choices=True, counts=True, queries=True, state=True)
            for index in range(3,27):
                case = cases[index]
                for arm in ARMS:
                    row, state, library = lookup[life,index,arm], states[arm], anchors[arm]
                    before = deepcopy(state)
                    flags['state'] &= same(row['library_before'], before)
                    member, spent, consumed = empty(), 0, Counter()
                    plan = make_plan(member, library, case, arm, state, work)
                    planning[arm] += 1
                    flags['plans'] &= same(row['case'], case) and same(row['initial_plan'], plan)
                    pre = queries(plan)
                    flags['queries'] &= same(row['initial_query'], pre)
                    history = [(0,plan)]
                    for batch in row['batches']:
                        choice = choose(member, library, case, arm, plan, spent, work, state)
                        flags['choices'] &= choice is not None and same(batch['choice'], choice)
                        op = choice['operator']
                        increments = dict.fromkeys(SUPPORT[op], 0)
                        for cat in prefixes[life,index,op][consumed[op]:consumed[op]+16]:
                            increments[cat] += 1
                        flags['counts'] &= batch['operator'] == op and batch['scope'] == 'TARGET'
                        flags['counts'] &= batch['source_index'] is None and batch['draw_start'] == consumed[op]
                        flags['counts'] &= batch['increments'] == increments and sum(increments.values()) == 16
                        for cat, count in increments.items():
                            member[op][cat] += count
                        consumed[op] += 16
                        spent += 16
                        actual[arm] += 16
                        flags['counts'] &= batch['draw_end'] == consumed[op] and batch['spent'] == spent
                        flags['counts'] &= batch['member_spent'] == spent and batch['source_spent'] == 0
                        plan = make_plan(member, library, case, arm, state, work)
                        planning[arm] += 1
                        flags['plans'] &= same(batch['plan'], plan)
                        history.append((spent,plan))
                    flags['choices'] &= choose(member, library, case, arm, plan, spent, work, state) is None
                    flags['choices'] &= 0 <= spent <= 384
                    fallback = len(plan['candidates']) != 1 and not plan['query_ready']
                    if fallback:
                        plan = make_plan(member, library, case, arm, state, work, force_member=True)
                        planning[arm] += 1
                        history.append((spent,plan))
                    certified = plan['utility_lower'] >= 2
                    identified = len(plan['candidates']) == 1 and certified
                    transferred = certified and plan['mode'] == 'library' and (identified or plan['query_ready'])
                    stop = ('member_budget' if fallback else 'query_set' if transferred and not identified else
                            'identified' if identified else 'member_certified' if certified else 'budget')
                    flags['choices'] &= row['stop'] == stop and row['fallback'] == fallback
                    flags['plans'] &= row['spent'] == spent and row['member_spent'] == spent and row['source_spent'] == 0
                    flags['plans'] &= row['certified'] == certified and row['identified'] == identified
                    flags['plans'] &= row['transferred'] == transferred and same(row['member'], member)
                    flags['plans'] &= same(row['terminal_plan'], plan)
                    post = queries(plan)
                    flags['queries'] &= same(row['terminal_query'], post)
                    flags['state'] &= state == before
                    event = advance(state, member, library, arm, plan)
                    flags['state'] &= same(row['advance'], event) and same(row['library_after'], state)
                    if arm == 'LOW_UNION':
                        union_calls[arm] += 1
                        retained_samples[arm] += spent
                        flags['state'] &= len(state['members']) == index-2
                    else:
                        flags['state'] &= state['bounds'] == initial_bounds[arm]
                    if arm == 'LOW_PARAM' and event is not None:
                        parameter_commits[arm] += 1
                        parameter_samples[arm] += event['samples']
                    frozen.append(dict(life=life,index=index,arm=arm,spent=spent,
                        certified=certified,identified=identified,transferred=transferred,
                        fallback=fallback,plan=plan,history=history,pre=pre,post=post,
                        after=deepcopy(state),member=deepcopy(member),event=event))
            for name, flag in flags.items():
                check(f'life_{life}_independent_{name}', flag)
        results = []
        for row in frozen:
            life,index,arm = row['life'],row['index'],row['arm']
            cases,laws,identities = worlds[life]
            plan,state,event = row['plan'],row['after'],row['event']
            history = [score(p,laws[index],cases[index],spent,work) for spent,p in row['history']]
            results.append(dict(life=life,index=index,arm=arm,spent=row['spent'],
                source_spent=0,member_spent=row['spent'],certified=row['certified'],
                identified=row['identified'],identity_correct=row['identified'] and plan['candidates'][0] == identities[index],
                transferred=row['transferred'],transfer_correct=row['transferred'] and identities[index] in plan['candidates'],
                fallback=row['fallback'],history=history,terminal=history[-1],
                query_pre=query_score(row['pre'],laws[index],cases[index]),
                query_post=query_score(row['post'],laws[index],cases[index]),
                library_coverage=cs_math.union_math.coverage(state['bounds'],laws),
                library_true_masks=all(identities[3+j] in mask for j,mask in enumerate(state['masks'])),
                library_no_feasible=state['no_feasible'],
                committed=arm == 'LOW_PARAM' and event is not None,
                commit_samples=event['samples'] if arm == 'LOW_PARAM' and event is not None else 0,
                commit_correct=arm == 'LOW_PARAM' and event is not None and event['source_index'] == identities[index]))
        check('delayed_true_history_queries_libraries_and_parameter_commits', same(read('results.json'),results))
        stats = Counter()
        expected = summary(results,frozen,stats,historical)
        check('source_budget_statistics_strong_baselines_and_frozen_gates',same(read('summary.json'),expected))
        run = read('run.json')
        check('full_low_source_fees_separate_from_fresh_targets',same(run['source_costs'],historical))
        check('actual_fresh_source_generation_costs',all(run['source_generation_costs'].get(key,0) == 41472
            for key in ('controlled_samples','controlled_resets','environment_random_draws')))
        check('actual_target_sample_reset_draw_and_planning_costs',sum(actual.values()) <= 442368 and all(
            run['arm_costs'][arm].get(key,0) == actual[arm] for arm in ARMS
            for key in ('controlled_samples','controlled_resets','environment_random_draws'))
            and all(run['arm_costs'][arm]['planning_calls'] == planning[arm] for arm in ARMS))
        check('full_union_retention_unique_parameter_memory_and_preparations',all(
            run['arm_costs'][arm].get('union_retained_targets',0) == union_calls[arm]
            and run['arm_costs'][arm].get('union_retained_samples',0) == retained_samples[arm]
            and run['arm_costs'][arm].get('parameter_committed_targets',0) == parameter_commits[arm]
            and run['arm_costs'][arm].get('parameter_committed_samples',0) == parameter_samples[arm]
            and run['arm_costs'][arm].get('limited_source_preparations',0) == 12
            and run['arm_costs'][arm].get('mixture_preparations',0) == 12 for arm in ARMS))
        check('actual_source_budget_bootstrap_costs',run['bootstrap_costs'] == dict(stats))
        check('oracle_scoring_after_all_decisions',run['phases'] == [
            'protocol_frozen','all_decisions_frozen','oracle_evaluated','complete'])
        complete = True
    except Exception as error:
        check('reconstruction',False)
        checks[-1]['error'] = f'{type(error).__name__}: {error}'
        complete = False
    output = dict(valid=complete and all(check['passed'] for check in checks),complete=complete,
                  checks=checks,costs=dict(work),seconds=perf_counter()-started)
    (OUTPUT/'analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(valid=output['valid'],complete=complete,checks=len(checks))))
    return output


if __name__ == '__main__':
    raise SystemExit(0 if analyze()['valid'] else 1)
