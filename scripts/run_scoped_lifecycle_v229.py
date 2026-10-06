"""One frozen, fresh paid A/B/A-return comparison of the V228 scoped learner."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import scoped_repair_v228 as core
from acfqp.science import scoped_route_task_v228 as task
from scripts.run_conditioned_mechanisms_v205 import draw, exact_json, save
from scripts.run_persistent_evidence_v221 import score, query_score
from scripts.scoped_lifecycle_v229_stats import summarize

OUTPUT = ROOT/'reports/scoped_lifecycle_v229'
ARMS, OPERATORS = core.ARMS, core.OPERATORS
TARGET_INDEXES = tuple(range(3, 27))+tuple(range(30, 78))
PLAN_FIELDS = ('mix', 'predicted', 'predicted_utility', 'risk_upper', 'utility_lower',
               'envelopes', 'risks', 'goals_lower', 'pure_vectors', 'candidates',
               'candidate_labels', 'mode', 'posterior', 'queries', 'query_certificates',
               'query_ready', 'goal_upper', 'goal_impossible')
FLAGS = ('execution_certified', 'goal_impossible', 'query_certified', 'fallback')
SOURCE_FILES = (
    'scripts/__init__.py',
    'src/acfqp/__init__.py',
    'src/acfqp/science/__init__.py',
    'src/acfqp/artifacts.py',
    'src/acfqp/build_coverage.py',
    'src/acfqp/core.py',
    'src/acfqp/enumeration.py',
    'src/acfqp/domains/__init__.py',
    'src/acfqp/domains/g2048.py',
    'src/acfqp/domains/matching_buffer.py',
    'src/acfqp/domains/semantic.py',
    'src/acfqp/domains/standard_2048.py',
    'src/acfqp/science/latent_resource_2048_v1.py',
    'src/acfqp/science/query_calibration_v215.py',
    'src/acfqp/science/scoped_repair_v228.py',
    'src/acfqp/science/scoped_union_v228.py',
    'src/acfqp/science/scoped_queries_v228.py',
    'src/acfqp/science/scoped_route_task_v228.py',
    'src/acfqp/science/mixture_confidence_v225.py',
    'src/acfqp/science/assignment_union_v222.py',
    'src/acfqp/science/fixed_source_acquisition_v219.py',
    'src/acfqp/science/joint_acquisition_v218.py',
    'src/acfqp/science/source_stopping_v216.py',
    'src/acfqp/science/query_sufficient_v214.py',
    'src/acfqp/science/latent_mechanisms_v213.py',
    'src/acfqp/science/latent_route_task_v213.py',
    'src/acfqp/science/strategic_maintenance_v210.py',
    'src/acfqp/science/contracted_risk_reuse_v209.py',
    'src/acfqp/science/constrained_acquisition_v208.py',
    'src/acfqp/science/online_lifecycle_v206.py',
    'src/acfqp/science/conditioned_mechanisms_v205.py',
    'src/acfqp/science/mechanism_switch_task_v205.py',
    'src/acfqp/science/target_risk_acquisition_v204.py',
    'src/acfqp/science/robust_route_planning_v203.py',
    'src/acfqp/science/continual_route_kernels_v202.py',
    'src/acfqp/science/structured_route_task_v201.py',
    'src/acfqp/science/persistent_evidence_v221.py',
    'scripts/run_conditioned_mechanisms_v205.py',
    'scripts/run_persistent_evidence_v221.py',
    'scripts/analyze_conditioned_mechanisms_v205.py',
    'scripts/analyze_latent_mechanisms_v213.py',
    'scripts/analyze_joint_acquisition_v218.py',
    'scripts/analyze_fixed_source_acquisition_v219.py',
    'scripts/analyze_assignment_union_v222.py',
    'scripts/analyze_mixture_confidence_v225.py',
    'scripts/scoped_repair_v229_math.py',
    'scripts/scoped_lifecycle_v229_stats.py',
    'scripts/run_scoped_lifecycle_v229.py',
    'scripts/analyze_scoped_lifecycle_v229.py',
    'tests/test_scoped_lifecycle_v229.py',
    'tests/test_scoped_lifecycle_v229_replay.py',
    'specs/SCOPED_REPAIR_V228.md',
    'specs/SCOPED_REPAIR_V228_PROOF.md',
    'specs/SCOPED_LIFECYCLE_V229.md',
    'reports/v229_runtime_tmp/run_stage.py',
)


def compact_box(block):
    return {op: dict(bounds=deepcopy(row['bounds'])) for op, row in block.items()}


def compact_bank(bank, scoped=False):
    result = dict(bounds=[compact_box(box) for box in bank['bounds']],
                  masks=deepcopy(bank['masks']), no_feasible=bank['no_feasible'])
    if scoped:
        result['changed_op'] = bank['changed_op']
        if 'permutation' in bank:
            result['permutation'] = bank['permutation']
    return result


def compact_state(state):
    result = dict(a=compact_bank(state['a']),
                  b=None if state['b'] is None else {
                      name: compact_bank(bank, True) for name, bank in state['b'].items()},
                  b_points=deepcopy(state['b_points']))
    if 'a_at_switch' in state:
        result['a_at_switch'] = [compact_box(box) for box in state['a_at_switch']]
    return result


def compact_plan(plan):
    result = {key: deepcopy(plan[key]) for key in PLAN_FIELDS}
    result['envelopes'] = compact_box(result['envelopes'])
    return result


def restored_plan(saved):
    plan = deepcopy(saved)
    for key in ('predicted_utility', 'risk_upper', 'utility_lower', 'goal_upper'):
        plan[key] = F(plan[key])
    plan['mix'] = [(name, F(weight)) for name, weight in plan['mix']]
    for row in plan['envelopes'].values():
        row['bounds'] = {cat: list(map(F, pair)) for cat, pair in row['bounds'].items()}
    for row in plan['query_certificates'].values():
        row['regret_upper'] = F(row['regret_upper'])
    return plan


def same_a_rows(rows):
    by_index = {(row['index'], row['arm']): row for row in rows}
    excluded = {'arm', 'library_before', 'library_after'}
    return all(
        {key: value for key, value in by_index[index, ARMS[0]].items() if key not in excluded}
        == {key: value for key, value in by_index[index, arm].items() if key not in excluded}
        and all(by_index[index, ARMS[0]][key]['a'] == by_index[index, arm][key]['a']
                for key in ('library_before', 'library_after'))
        for index in tuple(range(3, 27))+tuple(range(54, 78)) for arm in ARMS[1:])


def oracle_goal(pure):
    utility = lambda v: v[0]+4*v[2]
    values = [utility(v) for v in pure.values() if v[1] <= F(1, 20)]
    for left, right in combinations(pure.values(), 2):
        if min(left[1], right[1]) < F(1, 20) < max(left[1], right[1]):
            weight = (F(1, 20)-right[1])/(left[1]-right[1])
            values.append(weight*utility(left)+(1-weight)*utility(right))
    return max(values)


def covered(box, law):
    return all(F(lo) <= law[op][cat] <= F(hi) for op, row in box.items()
               for cat, (lo, hi) in row['bounds'].items())


def evaluate(work):
    """Read only frozen plans and compact snapshots; do not call the learner."""
    results = []
    for life in range(12):
        cases, laws, identities, metadata = task.world(life)
        for line in (OUTPUT/f'records_life_{life:02d}.jsonl').read_text().splitlines():
            row = json.loads(line)
            index, arm, case = row['index'], row['arm'], row['case']
            current_law, identity = laws[index], identities[index]
            if case['context'] == 'A':
                branch, bank_name, source_indexes = 'A', 'a', (0, 1, 2)
                member_indexes = [i for i in tuple(range(3, 27))+tuple(range(54, index+1)) if i <= index]
            else:
                branch = ('rebuild' if arm == 'REBUILD_CS' else metadata['changed_operator']+':'+
                          ''.join(map(str, metadata['b_to_a'])))
                bank_name, source_indexes, member_indexes = 'b', (27, 28, 29), list(range(30, index+1))
            key = branch+'/'+str(identity)
            optimum = oracle_goal(core.mechanics.vectors(case, current_law))
            history = []
            before = row['library_before']['a'] if bank_name == 'a' else row['library_before']['b'][branch]
            prior = None
            if len(before['bounds']) == 3:
                prior = {op: dict(bounds={cat: list(map(F, pair)) for cat, pair in block['bounds'].items()})
                         for op, block in before['bounds'][identity].items()}
            member = core.empty()
            points = [(row['initial_plan'], 0, None)]+[(batch['plan'], batch['spent'], batch) for batch in row['batches']]
            for saved, spent, batch in points:
                if batch is not None:
                    for cat, count in batch['increments'].items():
                        member[batch['operator']][cat] += count
                plan = restored_plan(saved)
                point = score(plan, current_law, case, spent)
                queries = query_score(plan['queries'], current_law, case)
                raw = core.confidence.union._project_simplex(core.confidence.boxes(member, work))
                true_box = None if prior is None else core.confidence.union._intersection(prior, [raw])
                point.update(true_candidate=key in plan['candidates'],
                    true_candidate_coverage=key in plan['candidates'] and true_box is not None and covered(true_box, current_law),
                    query_bounds_ok=all(F(0) <= queries[q]['regret'] <= certificate['regret_upper']
                                        for q, certificate in plan['query_certificates'].items()),
                    goal_upper_ok=optimum <= plan['goal_upper'])
                history.append(point)
            after = row['library_after']
            bank = after['a'] if bank_name == 'a' else after['b'][branch]
            retained = not bank['no_feasible'] and len(bank['bounds']) == 3 and all(
                covered(box, laws[source_index]) for box, source_index in zip(bank['bounds'], source_indexes))
            masks = len(bank['masks']) == len(member_indexes) and all(
                identities[i] in mask for i, mask in zip(member_indexes, bank['masks']))
            commit = row['advance'].get('point_commit')
            initial, terminal = row['initial_plan'], row['terminal_plan']
            results.append(dict(life=life, index=index, arm=arm, stage=case['stage'], spent=row['spent'],
                **{flag: row[flag] for flag in FLAGS}, history=history, terminal=history[-1],
                query_pre=query_score(initial['queries'], current_law, case),
                query_post=query_score(terminal['queries'], current_law, case), oracle_goal=optimum,
                true_branch_retained=retained, true_masks_retained=masks,
                point_committed=commit is not None,
                point_commit_correct=commit is not None and commit['index'] == identity))
    return results


def run():
    begun = perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    for name in SOURCE_FILES:
        destination = OUTPUT/'source_code'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    save(OUTPUT/'source_manifest.json', [dict(path=name) for name in SOURCE_FILES])
    work = {arm: Counter() for arm in ARMS}
    source_work = Counter()
    model_seconds = {arm: [0.]*12 for arm in ARMS}
    observation_seconds = {arm: [0.]*12 for arm in ARMS}
    source_seconds = [0.]*12
    source_costs = {arm: [4608]*12 for arm in ARMS}
    source_records, libraries, cases_saved, arm_orders = [], [], [], []
    common_a = True

    def timed(arm, life, operation, *args):
        start = perf_counter()
        result = operation(*args)
        model_seconds[arm][life] += perf_counter()-start
        return result

    def sources(life, indexes, context, laws):
        anchors = []
        for local, index in enumerate(indexes):
            slot = local if context == 'A' else local+3
            anchor = core.empty()
            amount = 384 if context == 'A' else 128
            for j, op in enumerate(OPERATORS):
                seed = 249000+(life*6+slot)*3+j
                rng = random.Random(seed)
                for start in range(0, amount, 16):
                    increments = dict.fromkeys(core.ALPHABETS[op], 0)
                    progress = dict(draw_end=start, n=start)
                    before = perf_counter()
                    draw(rng, laws[index], op, increments, 16, source_work, progress)
                    source_seconds[life] += perf_counter()-before
                    for cat, count in increments.items():
                        anchor[op][cat] += count
                    source_records.append(dict(life=life, context=context, index=index, slot=slot,
                        operator=op, seed=seed, draw_start=start, draw_end=progress['draw_end'], increments=increments))
            anchors.append(anchor)
        save(OUTPUT/'source_records.json', source_records)
        return anchors

    for life in range(12):
        cases, laws, _, _ = task.world(life)
        cases_saved.append(dict(life=life, cases=cases))
        save(OUTPUT/'cases.json', cases_saved)
        offset = life % 3
        order = ARMS[offset:]+ARMS[:offset]
        arm_orders.append(list(order))
        caches = {arm: {} for arm in ARMS}
        a_anchors = sources(life, (0, 1, 2), 'A', laws)
        states = {}
        for arm in order:
            core.confidence.mixture._INTERVAL_CACHE = caches[arm]
            states[arm] = timed(arm, life, core.prepare, a_anchors, arm, work[arm])
        life_rows = []
        with (OUTPUT/f'records_life_{life:02d}.jsonl').open('w') as stream:
            for index in TARGET_INDEXES:
                if index == 30:
                    b_anchors = sources(life, (27, 28, 29), 'B', laws)
                    libraries.append(dict(life=life, a=a_anchors, b=b_anchors))
                    save(OUTPUT/'source_evidence.json', libraries)
                    for arm in order:
                        core.confidence.mixture._INTERVAL_CACHE = caches[arm]
                        timed(arm, life, core.begin_b, states[arm], b_anchors, work[arm])
                case = cases[index]
                seeds = {op: 250000+(life*78+index)*3+j for j, op in enumerate(OPERATORS)}
                for arm in order:
                    core.confidence.mixture._INTERVAL_CACHE = caches[arm]
                    state = states[arm]
                    before = compact_state(state)
                    member, spent = core.empty(), 0
                    rng = {op: random.Random(seed) for op, seed in seeds.items()}
                    plan = timed(arm, life, core.make_plan, member, case, state, work[arm])
                    row = dict(life=life, index=index, case=case, arm=arm, seeds=seeds,
                               initial_plan=compact_plan(plan), batches=[])
                    while True:
                        choice = timed(arm, life, core.choose, member, case, state, plan, spent, work[arm])
                        if choice is None:
                            break
                        op = choice['operator']
                        start = sum(member[op].values())
                        increments = dict.fromkeys(core.ALPHABETS[op], 0)
                        progress = dict(draw_end=start, n=start)
                        observation_start = perf_counter()
                        draw(rng[op], laws[index], op, increments, 16, work[arm], progress)
                        observation_seconds[arm][life] += perf_counter()-observation_start
                        for cat, count in increments.items():
                            member[op][cat] += count
                        spent += 16
                        plan = timed(arm, life, core.make_plan, member, case, state, work[arm])
                        row['batches'].append(dict(choice=choice, operator=op, draw_start=start,
                            draw_end=progress['draw_end'], increments=increments, spent=spent, plan=compact_plan(plan)))
                    final = core.finish(plan)
                    event = timed(arm, life, core.advance, state, member, case, plan, work[arm])
                    row.update(spent=spent, member=deepcopy(member), terminal_plan=compact_plan(plan),
                        advance=event, library_before=before, library_after=compact_state(state),
                        **{flag: final[flag] for flag in FLAGS})
                    normalized = exact_json(row)
                    life_rows.append(normalized)
                    stream.write(json.dumps(normalized, separators=(',', ':'))+'\n')
                    stream.flush()
                if index in (26, 41, 53, 77):
                    print(json.dumps(dict(life=life, index=index, seconds=perf_counter()-begun,
                        target_samples={arm: work[arm]['controlled_samples'] for arm in ARMS})), flush=True)
        common_a &= same_a_rows(life_rows)
    run_data = dict(phases=['protocol_frozen', 'all_decisions_frozen'], arm_costs=work,
        source_costs=source_costs, source_generation_costs=source_work,
        source_generation_seconds=source_seconds, model_seconds=model_seconds,
        observation_seconds=observation_seconds, common_A_path=common_a, arm_orders=arm_orders,
        cache_policy='separate_arm_lifecycle')
    save(OUTPUT/'run.json', run_data)
    oracle_work = Counter()
    results = evaluate(oracle_work)
    stats = Counter()
    summary = summarize(results, source_costs, model_seconds, stats, common_a)
    save(OUTPUT/'results.json', results)
    save(OUTPUT/'summary.json', summary)
    run_data.update(phases=['protocol_frozen', 'all_decisions_frozen', 'oracle_evaluated', 'complete'],
                    bootstrap_costs=stats, oracle_costs=oracle_work, seconds=perf_counter()-begun)
    save(OUTPUT/'run.json', run_data)
    print(json.dumps(dict(decision=summary['decision'], conditions=summary['conditions'],
                         seconds=run_data['seconds'])), flush=True)


if __name__ == '__main__':
    run()
