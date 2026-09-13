"""Diagnose feature aliasing on the already revealed V76 target cohort."""
import argparse
from collections import Counter, defaultdict
import importlib.util
from itertools import combinations
import json
from pathlib import Path
import sys
from time import perf_counter


TOLERANCE = 1e-12
COLLISION_COUNTS = ('equal_feature_action_groups', 'equal_feature_action_pairs',
    'q_conflicting_action_pairs', 'membership_conflicting_action_pairs',
    'q_conflicting_action_groups', 'membership_conflicting_action_groups',
    'equal_feature_queries', 'q_conflict_queries', 'membership_conflict_queries',
    'unavoidable_lexicographic_error_queries')


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def query_witnesses(inputs, audit, workers):
    boards = {case['name']: case['board'] for case in inputs['cases']}
    result = []
    for case in audit['cases']:
        for left, right in combinations(case['queries'], 2):
            if not set(left['methods']['EXACT']['optimal_actions']).isdisjoint(
                    right['methods']['EXACT']['optimal_actions']):
                continue
            decisions = workers['RULE'][case['name']]['actions']
            if decisions[left['query_name']]['action'] != decisions[right['query_name']]['action']:
                continue
            result.append(dict(case=case['name'], board=boards[case['name']],
                queries=[dict(query_name=row['query_name'], query=inputs['queries'][row['query_name']],
                    optimal_actions=row['methods']['EXACT']['optimal_actions'],
                    rule_action=decisions[row['query_name']]['action'],
                    rule_regret=row['methods']['RULE']['root_decision_regret']) for row in (left, right)],
                interpretation='The saved RULE action does not change although the two ground-optimal action sets are disjoint. This is not an identical-feature collision.'))
            break
        if len(result) == 2:
            break
    return result


def diagnose(directory):
    started = perf_counter()
    reads = Counter()

    def read(name):
        text = (directory / name).read_text()
        reads['files'] += 1
        reads['bytes'] += len(text.encode())
        return json.loads(text)

    inputs, tree, audit = read('inputs.json'), read('tree.json'), read('audit.json')
    workers = {method: {case['name']: case for case in read(method + '.json')['cases']}
               for method in ('RULE', 'SELECTIVE')}
    frozen = directory / 'source/src/acfqp/science'
    dynamics = module(frozen / 'controlled_predictive_relational_dynamics_v69.py', 'v76_diagnostic_dynamics')
    predictor = module(frozen / 'controlled_predictive_decision_rule_v76.py', 'v76_diagnostic_features')
    rule = dynamics.LearnedDynamics.from_payload(read('learned_rule.json'))
    truth = {case['name']: case for case in audit['cases']}
    feature_work, counts, collisions = Counter(), Counter(), []
    counts.update({name: 0 for name in COLLISION_COUNTS})
    affected = {}
    for case in inputs['cases']:
        base = predictor.features(case['board'], rule, feature_work)
        casesum = Counter()
        affected_queries = defaultdict(list)
        for row in truth[case['name']]['queries']:
            name = row['query_name']
            query = inputs['queries'][name]
            oracle = row['methods']['EXACT']
            optimal = set(oracle['optimal_actions'])
            groups = defaultdict(list)
            for action, features in base.items():
                vector = predictor.query_features(features, query)
                groups[vector].append(action)
            aliases = [sorted(actions) for actions in groups.values() if len(actions) > 1]
            counts['board_queries'] += 1
            counts['legal_action_feature_vectors'] += len(base)
            q_conflict = membership_conflict = False
            for vector, actions in groups.items():
                if len(actions) < 2:
                    continue
                actions = sorted(actions)
                values = {action: oracle['oracle_actions'][action]['value'] for action in actions}
                gap = max(values.values()) - min(values.values())
                mixed = bool(optimal.intersection(actions)) and not set(actions) <= optimal
                counts['equal_feature_action_groups'] += 1
                counts['equal_feature_action_pairs'] += len(tuple(combinations(actions, 2)))
                counts['q_conflicting_action_pairs'] += sum(abs(values[a] - values[b]) > TOLERANCE
                    for a, b in combinations(actions, 2))
                counts['membership_conflicting_action_pairs'] += sum((a in optimal) != (b in optimal)
                    for a, b in combinations(actions, 2))
                if gap > TOLERANCE:
                    q_conflict = True
                    counts['q_conflicting_action_groups'] += 1
                if mixed:
                    membership_conflict = True
                    counts['membership_conflicting_action_groups'] += 1
                    collisions.append(dict(case=case['name'], board=case['board'], query_name=name,
                        query=query, identical_41_features=list(vector), max_q_difference=gap,
                        actions=[dict(action=action, q=values[action], optimal=action in optimal)
                                 for action in actions], optimal_actions=sorted(optimal),
                        predictions={method: workers[method][case['name']]['actions'][name]
                                     for method in workers},
                        existing_errors={method: not row['methods'][method]['root_action_optimal_membership']
                                         for method in workers}))
            # Every scorer f(41 features) gives equal scores inside each group.
            # Under lexicographic ties only that group's first action can win.
            unavoidable = not any(min(actions) in optimal for actions in groups.values())
            flags = dict(equal_feature_queries=bool(aliases), q_conflict_queries=q_conflict,
                membership_conflict_queries=membership_conflict,
                unavoidable_lexicographic_error_queries=unavoidable)
            for key, present in flags.items():
                if present:
                    counts[key] += 1
                    casesum[key] += 1
                    affected_queries[key].append(name)
            for method in workers:
                error = not row['methods'][method]['root_action_optimal_membership']
                counts[method + '_errors'] += error
                for key, present in flags.items():
                    counts[method + '_errors_on_' + key] += error and present
                    casesum[method + '_errors_on_' + key] += error and present
                action = workers[method][case['name']]['actions'][name]['action']
                selected_aliases_optimal = error and any(action in group and optimal.intersection(group)
                                                        for group in aliases)
                counts[method + '_wrong_selected_action_aliases_an_optimal_action'] += selected_aliases_optimal
        qrows = truth[case['name']]['queries']
        obligations = sum(set(left['methods']['EXACT']['optimal_actions']).isdisjoint(
            right['methods']['EXACT']['optimal_actions']) for left, right in combinations(qrows, 2))
        counts['strict_query_pair_obligations'] += obligations
        counts['boards_requiring_query_action_switch'] += obligations > 0
        counts['rule_boards_with_multiple_query_actions'] += len({row['action']
            for row in workers['RULE'][case['name']]['actions'].values()}) > 1
        if affected_queries:
            affected[case['name']] = dict(counts=dict(casesum), queries=dict(affected_queries))
    for key in ('equal_feature_queries', 'q_conflict_queries', 'membership_conflict_queries',
                'unavoidable_lexicographic_error_queries'):
        counts[key.replace('_queries', '_boards')] = sum(key in row['queries'] for row in affected.values())
    witnesses, used_boards = [], set()
    for row in sorted(collisions, key=lambda row: (-row['max_q_difference'], row['case'], row['query_name'])):
        if row['case'] not in used_boards:
            witnesses.append(row)
            used_boards.add(row['case'])
        if len(witnesses) == 2:
            break
    features = tree['feature_names']
    base_count = len(tree['base_feature_names'])
    splits = Counter(index for index in tree['tree']['feature'] if index >= 0)
    query_columns = [dict(index=index, name=features[index], split_nodes=splits[index],
                          importance=tree['feature_importance'][index])
                     for index in range(base_count, len(features))]
    return dict(schema='acfqp.decision_feature_diagnostic.v76',
        scope='Post-result diagnosis on the exposed V76 cohort; no new validation, fitting, threshold adjustment or ground acquisition.',
        equality_rule='All 41 raw feature values exactly equal within the same board and query; no tolerance, rounding or leaf-ID surrogate.',
        q_difference_tolerance=TOLERANCE, cases=len(inputs['cases']), counts=dict(counts),
        tree=dict(training=tree['training'], declared_feature_columns=len(features),
            base_feature_columns=base_count, query_feature_columns=len(query_columns),
            split_nodes=sum(splits.values()), used_feature_columns=len(splits),
            unused_feature_names=[name for index, name in enumerate(features) if not splits[index]],
            query_split_nodes=sum(row['split_nodes'] for row in query_columns),
            query_importance=sum(row['importance'] for row in query_columns), query_columns=query_columns,
            query_invariant_scorer=not any(row['split_nodes'] for row in query_columns),
            column_scope='The saved fitted model declares all 41 supplied columns. Split use is separate from inclusion in its input matrix.'),
        affected_boards=affected, witnesses=witnesses,
        query_response_witnesses=query_witnesses(inputs, audit, workers),
        reads=dict(reads), feature_work=dict(feature_work),
        new_fit_calls=0, new_ground_calls=0, tree_prediction_calls=0,
        elapsed_seconds_before_write=perf_counter() - started,
        interpretation='Different optimal labels inside an identical feature group cannot be represented by any actionwise scorer of these features. The strict local lower bound additionally requires every feature group to begin with a nonoptimal action under the fixed lexicographic tie rule. Mere overlap between a prediction error and a conflicting group does not prove that the conflict caused that error. Unused query columns establish query invariance of this fitted tree, not impossibility for other trained trees.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.input)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(counts=result['counts'], tree={key: result['tree'][key] for key in
        ('declared_feature_columns', 'used_feature_columns', 'query_split_nodes', 'query_importance',
         'query_invariant_scorer')}, witnesses=[dict(case=row['case'], query=row['query_name'],
            actions=row['actions']) for row in result['witnesses']]), indent=2))
