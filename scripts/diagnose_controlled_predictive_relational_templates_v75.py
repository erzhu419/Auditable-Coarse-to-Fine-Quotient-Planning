"""Measure safe H2 relation-key reuse using retained exact models only."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'reports/controlled_predictive_composition_v69'


def relation_key(board, goal_rank=11):
    variables, layout = {}, []
    for rank in board:
        if not rank:
            layout.append(0)
            continue
        if rank not in variables:
            variables[rank] = len(variables) + 1
        layout.append(variables[rank])
    bindings = tuple(variables)
    ranks = bindings + (1, 2)
    differences = tuple(left - right if abs(left - right) <= 2 else 'FAR'
                        for i, left in enumerate(ranks) for right in ranks[i + 1:])
    goals = tuple(tuple(rank + offset >= goal_rank for offset in (0, 1, 2))
                  for rank in bindings)
    return (tuple(layout), differences, goals), bindings


def normalized_ids(payload, table, erase_rewards, work):
    """Intern bottom-up semantics after child normalization and mass aggregation."""
    rows = defaultdict(dict)
    for state, action, atoms in payload['rows']:
        rows[state][action] = atoms
    ids = {}
    for state, h, status in sorted(payload['cells'], key=lambda row: (row[1], row[0])):
        action_rows = []
        for action, atoms in sorted(rows[state].items()):
            mass = defaultdict(Fraction)
            for pn, pd, child, rn, rd in atoms:
                target = (ids[child],) if erase_rewards else (ids[child], Fraction(rn, rd))
                mass[target] += Fraction(pn, pd)
                work['normalized_joint_terms'] += 1
            action_rows.append((action, tuple((target, probability)
                for target, probability in sorted(mass.items()) if probability)))
        key = h, status, tuple(action_rows)
        if key not in table:
            table[key] = len(table)
        ids[state] = table[key]
        work['normalized_cells'] += 1
    return ids


def group_summary(groups):
    values = list(groups.values())
    reused = [members for members in values if len(members) > 1]
    rebound = [members for members in reused if len({tuple(m['bindings']) for m in members}) > 1]
    conflicts = [members for members in values if len({m['erased_structure_id'] for m in members}) > 1]
    return dict(observations=sum(len(members) for members in values), keys=len(values),
        redundant_key_occurrences=sum(len(members) - 1 for members in values),
        repeated_key_groups=len(reused), different_binding_groups=len(rebound),
        observations_in_different_binding_groups=sum(map(len, rebound)),
        erased_structure_conflict_groups=len(conflicts)), rebound, conflicts


def witness_groups(groups, limit=3):
    return [[{k: v for k, v in member.items() if k != 'full_contract_id'}
             for member in members[:4]] for members in sorted(groups, key=len, reverse=True)[:limit]]


def run(output):
    started = perf_counter()
    cases = json.loads((REFERENCE / 'roster.json').read_text())['target']
    exact_table, erased_table, global_groups, within_groups = {}, {}, defaultdict(list), defaultdict(list)
    work, per_case, all_members = Counter(), [], []
    for case in cases:
        payload = json.loads((REFERENCE / case['name'] / 'FULL.model.json').read_text())
        exact = normalized_ids(payload, exact_table, False, work)
        erased = normalized_ids(payload, erased_table, True, work)
        local_groups, local_members = defaultdict(list), []
        for horizon, board, state in payload['literal_boards']:
            if horizon != 2:
                continue
            key, bindings = relation_key(board)
            member = dict(case=case['name'], state=state, board=board, bindings=list(bindings),
                full_contract_id=exact[state], erased_structure_id=erased[state])
            local_groups[key].append(member)
            global_groups[key].append(member)
            within_groups[case['name'], key].append(member)
            local_members.append(member)
        summary, _, _ = group_summary(local_groups)
        summary.update(case=case['name'],
            exact_contracts=len({m['full_contract_id'] for m in local_members}),
            reward_erased_contracts=len({m['erased_structure_id'] for m in local_members}))
        per_case.append(summary)
        all_members.extend(local_members)
        work['retained_models_read'] += 1
    within, within_rebound, within_conflicts = group_summary(within_groups)
    global_summary, global_rebound, global_conflicts = group_summary(global_groups)
    result = dict(schema='acfqp.relational_template_diagnostic.v75', complete=True,
        root_cases=len(cases), h2_observations=len(all_members),
        distinct_literal_h2_boards=len({tuple(m['board']) for m in all_members}),
        within_case=within, global_support=global_summary,
        within_case_exact_contracts=sum(c['exact_contracts'] for c in per_case),
        within_case_reward_erased_contracts=sum(c['reward_erased_contracts'] for c in per_case),
        global_exact_contracts=len({m['full_contract_id'] for m in all_members}),
        global_reward_erased_contracts=len({m['erased_structure_id'] for m in all_members}),
        within_case_binding_examples=witness_groups(within_rebound),
        global_binding_examples=witness_groups(global_rebound),
        structural_conflict_examples=witness_groups(within_conflicts + global_conflicts),
        cases=per_case, counts=dict(work), model_builds=0, ground_calls=0, fit_calls=0, planning_calls=0,
        elapsed_seconds_before_write=perf_counter() - started,
        key='First-occurrence nonzero-rank variable layout; every pair in variables plus constants '
            '1 and 2 records exact rank difference in [-2,2] or FAR; per-variable goal flags at offsets 0,1,2.',
        normalization='Exact bottom-up joint laws are interned across all cases, ignoring original '
            'cell IDs and insertion order. Reward erasure occurs recursively, then equal normalized '
            'children are combined with exact Fraction probabilities.',
        scope='Read-only reuse diagnostic on the retained V69 H2 support. Matching reward-erased '
            'structure does not prove a consistent symbolic reward binding or new generalization. '
            'Zero conflicts without different-binding groups provide no empirical binding test.')
    with output.open('x') as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in ('complete', 'h2_observations', 'within_case',
        'global_support', 'within_case_exact_contracts', 'within_case_reward_erased_contracts',
        'global_exact_contracts', 'global_reward_erased_contracts')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
