"""Explore retained selected-action signatures without changing the joint model."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'reports/controlled_predictive_composition_v69'
LABELS = ROOT / 'reports/controlled_predictive_observation_v70'


def read(path):
    return json.loads(path.read_text())


def group_details(members, query_names):
    spreads = [max(m['values'][i] for m in members) - min(m['values'][i] for m in members)
               for i in range(len(query_names))]
    different = any(spread > 0 for spread in spreads)
    material = any(spread > 1e-12 for spread in spreads)
    first = members[0]
    witness = next((m for m in members if m['values'] != first['values']), None)
    examples = []
    if witness is not None:
        query_index = next(i for i in range(len(query_names)) if first['values'][i] != witness['values'][i])
        examples = [dict(case=m['case'], cell=m['cell'], query=query_names[query_index],
                         selected_action=m['actions'][query_index], value=m['values'][query_index])
                    for m in (first, witness)]
    return dict(observations=len(members),
        case_local_exact_cells=len({(m['case'], m['cell']) for m in members}),
        query_value_vectors=len({m['values'] for m in members}),
        unequal_query_values=different, value_spread_above_1e12=material,
        maximum_query_value_spread=max(spreads),
        query_value_spreads=dict(zip(query_names, spreads)), value_difference_example=examples)


def summarize(groups, query_names):
    details = [group_details(members, query_names) for members in groups.values()]
    return dict(observations=sum(row['observations'] for row in details),
        selected_action_signatures=len(details),
        repeated_observation_signature_groups=sum(row['observations'] > 1 for row in details),
        signatures_with_multiple_exact_cells=sum(row['case_local_exact_cells'] > 1 for row in details),
        signatures_with_unequal_query_values=sum(row['unequal_query_values'] for row in details),
        signatures_with_value_spread_above_1e12=sum(row['value_spread_above_1e12'] for row in details),
        observations_in_unequal_value_groups=sum(row['observations'] for row in details if row['unequal_query_values']),
        maximum_query_value_spread=max((row['maximum_query_value_spread'] for row in details), default=0.0))


def run(output):
    started = perf_counter()
    cases = read(MODELS / 'roster.json')['target']
    global_groups, within_groups = defaultdict(list), defaultdict(list)
    per_case, query_names = [], None
    exact_cells = 0
    for case in cases:
        name = case['name']
        model = read(MODELS / name / 'COMPOSED.model.json')
        plans = read(MODELS / name / 'COMPOSED.plans.json')
        names = tuple(sorted(plans))
        if query_names is None:
            query_names = names
        elif names != query_names:
            raise ValueError('retained cases do not share the same query definitions')
        cells = {state for state, h, status in model['cells'] if h == 2 and status == 'ACTIVE'}
        exact_cells += len(cells)
        labels = read(LABELS / name / 'COMPOSED_MAP.package.json')['router']['labels']
        local_groups = defaultdict(list)
        observed_cells = set()
        for h, board, state in labels:
            if h != 2:
                continue
            if state not in cells:
                raise ValueError('retained H2 label does not refer to an active H2 model cell')
            observed_cells.add(state)
            actions = tuple(plans[q]['policy'][str(state)] for q in query_names)
            values = tuple(plans[q]['values'][str(state)] for q in query_names)
            member = dict(case=name, cell=state, actions=actions, values=values)
            local_groups[actions].append(member)
            global_groups[actions].append(member)
            within_groups[name, actions].append(member)
        if observed_cells != cells:
            raise ValueError('retained H2 labels do not cover the complete H2 model cells')
        summary = summarize(local_groups, query_names)
        summary.update(case=name, exact_h2_cells=len(cells))
        per_case.append(summary)
    within = summarize(within_groups, query_names)
    global_summary = summarize(global_groups, query_names)
    profiles = []
    for actions, members in sorted(global_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        profile = group_details(members, query_names)
        profile['selected_actions'] = dict(zip(query_names, actions))
        profiles.append(profile)
    result = dict(schema='acfqp.selected_decision_diagnostic.v75', exploratory=True, complete=True,
        root_cases=len(cases), query_count=len(query_names), query_names=query_names,
        h2_observations=global_summary['observations'], retained_case_local_exact_h2_cells=exact_cells,
        within_case=within, global_support=global_summary, cases=per_case, global_signature_profiles=profiles,
        model_builds=0, ground_calls=0, fit_calls=0, planning_calls=0,
        elapsed_seconds_before_write=perf_counter() - started,
        source_models=str(MODELS), source_labels=str(LABELS),
        signature_definition='The vector of already selected policy actions across the same 14 '
            'retained queries. It does not describe complete argmax sets or unseen queries.',
        value_comparison='Stored numeric query values are compared directly; a separate 1e-12 '
            'spread count distinguishes differences larger than tiny floating-point residuals.',
        scope='Exploratory read-only diagnosis. Shared selected-action signatures suggest possible '
            'decision-pattern reuse on these queries only. Unequal values preclude a single '
            'shared value vector; risk equivalence requires separate verification. Even equal stored values would '
            'not establish joint-transition equivalence or a safe new abstraction. The original '
            'exact joint models, scientific gates, and all policies remain unchanged.')
    with output.open('x') as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in ('complete', 'h2_observations',
        'retained_case_local_exact_h2_cells', 'query_count', 'within_case', 'global_support')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
