"""Replicate two frozen first-action policies on exactly the same boards.

No labels select actions here. Relative full-vector coefficients and exact
current rewards fix TREE and ONE choices before fresh suffixes are drawn.
SOURCE games, rather than roots or suffixes, are the variance units.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from math import isfinite, sqrt
from statistics import mean, variance

from . import controlled_predictive_consequence_partition_v172 as partition
from .controlled_predictive_consequence_partition_v172 import ACTIONS, EPSILON, MIN_ACTION_ROOTS

SCHEMA = 'acfqp.fixed_board_replication.v175'
LIVES = (0, 1, 2, 3)
COHORTS = ('TRAIN', 'FRESH')
MODES = ('TREE', 'ONE')
SUFFIXES = 16
REFERENCE_SUFFIXES = 4
SOURCE_COUNTS = {'TRAIN': 12, 'FRESH': 8}
METRICS = ('utility', 'reward', 'failure', 'success')
Z95 = 1.96


def _utility(vector):
    return vector[0]-vector[1]+vector[2]


def _metrics(vector):
    return dict(zip(METRICS, [_utility(vector), *vector]))


def supported_action(payload, root, work):
    """Strict fixed-model choice, including support for a single legal action."""
    if payload['life'] != root['life']:
        raise ValueError('root and model must use the same frozen history')
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']):
        raise ValueError('distinct legal canonical actions required')
    local = Counter(selection_decisions=1, selection_legal_action_reads=len(legal))
    leaf_id = partition._route(payload, root['canonical_board'], local)
    leaf = None
    for candidate in payload['leaves']:
        local['selection_leaf_records_examined'] += 1
        if candidate['leaf_id'] == leaf_id:
            leaf = candidate
            break
    action_counts = {action: len(leaf['action_root_ids'][action]) if leaf else 0 for action in legal}
    components = leaf['connected_components'] if leaf else [[action] for action in ACTIONS]
    component_id = {action: index for index, group in enumerate(components) for action in group}
    local.update(selection_action_support_lookups=len(legal),
                 selection_component_membership_lookups=len(legal))
    connected = len({component_id[action] for action in legal}) == 1
    complete = leaf is not None and connected and all(action_counts[action] >= MIN_ACTION_ROOTS for action in legal)
    support = dict(action_root_counts=action_counts, connected_components=deepcopy(components),
                   required_actions=legal, connected=connected, complete=complete)
    selected, best, predicted = None, None, {}
    if complete:
        for action in legal:
            vector = list(leaf['coefficients'][action])
            vector[0] += root['immediate_rewards'][action]
            predicted[action] = vector
            value = _utility(vector)
            local.update(selection_coefficient_component_reads=3, selection_immediate_reward_reads=1,
                         selection_utility_evaluations=1)
            if best is None or value > best+EPSILON:
                selected, best = action, value
        reason = 'selected'
    else:
        reason = ('missing_partition_leaf' if leaf is None else
                  'insufficient_action_support' if any(count < MIN_ACTION_ROOTS for count in action_counts.values()) else
                  'disconnected_required_actions')
    work.update(local)
    return dict(canonical_action=selected, leaf=leaf_id, support=support, reason=reason,
                predicted_components=predicted, work=dict(local))


def freeze_selections(roots, models):
    """Freeze both supported actions and the original four-suffix reference.

Models are indexed by history, then TREE/ONE. Roots carry TRAIN/FRESH cohort,
canonical current board, legal actions, exact rewards and reference_trials.
An unsupported root stops the whole cohort; it is never removed or supplied
an invented teacher action.
"""
    choices, issues, work, seen = [], [], Counter(), set()
    for root in roots:
        identity = (root['cohort'], root['root_id'])
        if root['cohort'] not in COHORTS or root['life'] not in LIVES:
            raise ValueError('fixed TRAIN/FRESH cohorts and four histories required')
        if identity in seen:
            issues.append(f'duplicate_root:{identity}')
        seen.add(identity)
        decisions = {mode: supported_action(models[root['life']][mode], root, work) for mode in MODES}
        complete = all(decision['support']['complete'] for decision in decisions.values())
        row = dict(cohort=root['cohort'], root_id=root['root_id'], life=root['life'], source_id=root['source_id'],
                   canonical_board=list(root['canonical_board']), legal_actions=list(root['legal_actions']),
                   immediate_rewards=deepcopy(root['immediate_rewards']), decisions=decisions,
                   complete=complete, changed=False, old_suffix_differences=[],
                   old_difference_components=None, reference_seeds=[])
        work['selection_roots'] += 1
        if not complete:
            issues.append(f'unsupported_policy:{identity}')
            choices.append(row)
            continue
        actions = [decisions[mode]['canonical_action'] for mode in MODES]
        row['changed'] = actions[0] != actions[1]
        trials = sorted(root['reference_trials'], key=lambda item: item['suffix'])
        if len(trials) != REFERENCE_SUFFIXES or [trial['suffix'] for trial in trials] != list(range(REFERENCE_SUFFIXES)):
            raise ValueError('four distinct frozen reference suffixes required')
        for trial in trials:
            row['reference_seeds'].append(trial['seed'])
            work['reference_trials_read'] += 1
            if row['changed']:
                left, right = (trial['action_components'][action] for action in actions)
                if len(left) != 3 or len(right) != 3:
                    raise ValueError('complete reference terminal vectors required')
                difference = [float(left[index])-float(right[index]) for index in range(3)]
                work.update(reference_terminal_vector_reads=2, reference_component_subtractions=3)
            else:
                difference = [0., 0., 0.]
                work['reference_same_action_suffixes_zeroed'] += 1
            row['old_suffix_differences'].append(dict(suffix=trial['suffix'], components=difference))
        row['old_difference_components'] = [mean(item['components'][index] for item in row['old_suffix_differences'])
                                            for index in range(3)]
        choices.append(row)
    return dict(schema=SCHEMA, choices=choices, complete=not issues, issues=issues, work=dict(work))


def _moments(values, suffix_mean_variance):
    average, sampling_variance = mean(values), variance(values)/len(values)
    se, suffix_se = sqrt(sampling_variance), sqrt(suffix_mean_variance)
    return dict(mean=average, source_mean_variance=sampling_variance,
                conditional_source_se=se, conditional_source_ci95=[average-Z95*se, average+Z95*se],
                conditional_suffix_mean_variance=suffix_mean_variance, conditional_suffix_se=suffix_se,
                conditional_suffix_ci95=[average-Z95*suffix_se, average+Z95*suffix_se])


def _pool(histories):
    metrics = {}
    for metric in METRICS:
        average = mean(row['metrics'][metric]['mean'] for row in histories)
        sampling_variance = sum(row['metrics'][metric]['source_mean_variance'] for row in histories)/len(LIVES)**2
        suffix_mean_variance = sum(row['metrics'][metric]['conditional_suffix_mean_variance'] for row in histories)/len(LIVES)**2
        se, suffix_se = sqrt(sampling_variance), sqrt(suffix_mean_variance)
        metrics[metric] = dict(mean=average, source_mean_variance=sampling_variance,
                              conditional_source_se=se, conditional_source_ci95=[average-Z95*se, average+Z95*se],
                              conditional_suffix_mean_variance=suffix_mean_variance, conditional_suffix_se=suffix_se,
                              conditional_suffix_ci95=[average-Z95*suffix_se, average+Z95*suffix_se])
    return metrics


def _comparison(cohort, roots, field, work):
    groups = defaultdict(list)
    for root in roots:
        if root['cohort'] == cohort:
            groups[root['life'], root['source_id']].append(root)
    clusters, histories = [], []
    for life in LIVES:
        local = []
        for (history, source), rows in sorted(groups.items()):
            if history != life:
                continue
            vector = [mean(row[field][index] for row in rows) for index in range(3)]
            # The observed four-suffix reference is fixed in this replication.
            # This does not make its unknown original expectation error-free.
            suffix_variances = {metric: (0. if field == 'old_difference_components' else
                sum(row['suffix_mean_variances'][metric] for row in rows)/len(rows)**2) for metric in METRICS}
            item = dict(life=life, source_id=source, roots=len(rows), metrics=_metrics(vector),
                        conditional_suffix_mean_variance=suffix_variances)
            local.append(item); clusters.append(item)
            work['source_root_component_reads'] += 3*len(rows)
            work['source_cluster_vector_means'] += 1
            work['conditional_suffix_source_variance_aggregations'] += len(METRICS)
            if field != 'old_difference_components':
                work['root_suffix_mean_variance_reads'] += len(METRICS)*len(rows)
        histories.append(dict(life=life, source_clusters=len(local),
            metrics={metric: _moments([row['metrics'][metric] for row in local],
                sum(row['conditional_suffix_mean_variance'][metric] for row in local)/len(local)**2)
                for metric in METRICS}))
    return dict(complete=True, metrics=_pool(histories), per_history=histories, clusters=clusters)


def _cross_cohort(left, right):
    """FRESH minus TRAIN; their retained SOURCE clusters are disjoint."""
    histories = []
    for fresh, train in zip(left['per_history'], right['per_history']):
        metrics = {}
        for metric in METRICS:
            average = fresh['metrics'][metric]['mean']-train['metrics'][metric]['mean']
            sampling_variance = (fresh['metrics'][metric]['source_mean_variance']+
                                 train['metrics'][metric]['source_mean_variance'])
            suffix_mean_variance = (fresh['metrics'][metric]['conditional_suffix_mean_variance']+
                                   train['metrics'][metric]['conditional_suffix_mean_variance'])
            se, suffix_se = sqrt(sampling_variance), sqrt(suffix_mean_variance)
            metrics[metric] = dict(mean=average, source_mean_variance=sampling_variance,
                                  conditional_source_se=se, conditional_source_ci95=[average-Z95*se, average+Z95*se],
                                  conditional_suffix_mean_variance=suffix_mean_variance, conditional_suffix_se=suffix_se,
                                  conditional_suffix_ci95=[average-Z95*suffix_se, average+Z95*suffix_se])
        histories.append(dict(life=fresh['life'], fresh_source_clusters=fresh['source_clusters'],
                              train_source_clusters=train['source_clusters'], metrics=metrics))
    return dict(complete=True, contrast='FRESH-TRAIN', metrics=_pool(histories), per_history=histories)


def summarize_replication(frozen, outcomes, suffixes=SUFFIXES):
    """Summarize new replication, paired old-reference change and board contrast.

Each changed root has exactly two physical actions under each new paired seed.
Same-action roots contribute exact zero to every SOURCE denominator without
physical branches. This returns diagnostic intervals, never a strategy gate.
"""
    if suffixes != SUFFIXES:
        raise ValueError('sixteen frozen replication suffixes required')
    roots, outcomes = deepcopy(frozen['choices']), list(outcomes)
    issues, work = list(frozen['issues']), Counter()
    if not frozen['complete']:
        issues.append('incomplete_frozen_selection')
    root_index = {(root['cohort'], root['root_id']): root for root in roots}
    if len(root_index) != len(roots):
        issues.append('duplicate_frozen_root')
    for cohort in COHORTS:
        for life in LIVES:
            sources = {root['source_id'] for root in roots if root['cohort'] == cohort and root['life'] == life}
            if len(sources) != SOURCE_COUNTS[cohort]:
                issues.append(f'source_roster_mismatch:{cohort}:{life}')
    for life in LIVES:
        groups = [{root['source_id'] for root in roots if root['cohort'] == cohort and root['life'] == life}
                  for cohort in COHORTS]
        if groups[0] & groups[1]:
            issues.append(f'overlapping_cohort_sources:{life}')
    expected = set()
    for root in roots:
        if root['complete'] and root['changed']:
            for suffix in range(suffixes):
                for mode in MODES:
                    expected.add((root['cohort'], root['root_id'], suffix, root['decisions'][mode]['canonical_action']))
    index = {}
    for row in outcomes:
        work['summary_outcome_rows_indexed'] += 1
        key = (row['cohort'], row['root_id'], row['suffix'], row['canonical_action'])
        if key in index:
            issues.append(f'duplicate_outcome:{key}')
        index[key] = row
        if key not in expected:
            issues.append(f'unexpected_outcome:{key}')
            continue
        root = root_index[row['cohort'], row['root_id']]
        if row['life'] != root['life'] or row['source_id'] != root['source_id']:
            issues.append(f'outcome_metadata_mismatch:{key}')
        vector = row['components']
        if row['status'] not in ('WON', 'LOST'):
            issues.append(f'nonterminal_outcome:{key}')
        elif (len(vector) != 3 or not all(isfinite(value) for value in vector) or
              vector[1:] != ([0, 1] if row['status'] == 'WON' else [1, 0])):
            issues.append(f'terminal_component_mismatch:{key}')
    missing = expected-set(index)
    if missing:
        issues.append(f'missing_outcomes:{len(missing)}')
    if not issues:
        for root in roots:
            differences = []
            if root['changed']:
                pair_seeds = []
                for suffix in range(suffixes):
                    left, right = (index[root['cohort'], root['root_id'], suffix,
                                         root['decisions'][mode]['canonical_action']] for mode in MODES)
                    work['paired_suffix_seed_checks'] += 1
                    if left['seed'] != right['seed']:
                        issues.append(f'unpaired_suffix_seed:{root["cohort"]}:{root["root_id"]}:{suffix}')
                    if left['seed'] in root['reference_seeds'] or right['seed'] in root['reference_seeds']:
                        issues.append(f'reused_reference_seed:{root["cohort"]}:{root["root_id"]}:{suffix}')
                    pair_seeds.append(left['seed'])
                    differences.append([left['components'][component]-right['components'][component] for component in range(3)])
                    work.update(new_terminal_vector_reads=2, new_component_subtractions=3)
                if len(set(pair_seeds)) != suffixes:
                    issues.append(f'repeated_replication_seed:{root["cohort"]}:{root["root_id"]}')
                root['new_difference_components'] = [mean(vector[component] for vector in differences) for component in range(3)]
                suffix_metrics = [_metrics(vector) for vector in differences]
                root['suffix_mean_variances'] = {metric: variance(row[metric] for row in suffix_metrics)/suffixes
                                                for metric in METRICS}
                work.update(suffix_root_metric_variances=len(METRICS), suffix_utility_evaluations=suffixes)
                work['new_root_vector_means'] += 1
            else:
                root['new_difference_components'] = [0., 0., 0.]
                root['suffix_mean_variances'] = {metric: 0. for metric in METRICS}
                work['same_action_roots_zeroed'] += 1
            root['new_minus_old_components'] = [root['new_difference_components'][component]-root['old_difference_components'][component]
                                                 for component in range(3)]
            work['new_old_component_subtractions'] += 3
    diagnostics = []
    for cohort in COHORTS:
        for life in LIVES:
            local = [root for root in roots if root['cohort'] == cohort and root['life'] == life]
            diagnostics.append(dict(cohort=cohort, life=life, roots=len(local),
                source_clusters=len({root['source_id'] for root in local}), changed_roots=sum(root['changed'] for root in local),
                same_action_roots=sum(root['complete'] and not root['changed'] for root in local),
                unsupported_roots=sum(not root['complete'] for root in local)))
    result = dict(schema=SCHEMA, complete=not issues, issues=issues, suffixes=suffixes,
                  reference_suffixes=REFERENCE_SUFFIXES, physical_outcomes=len(outcomes),
                  expected_physical_outcomes=len(expected), diagnostics=diagnostics, cohorts={}, cross_cohort={},
                  work=dict(work), scope=('fixed first-action policies then the same-history H2 continuation; '
                    'SOURCE heterogeneity normal intervals and fixed-board conditional suffix-noise normal intervals; '
                    'the observed OLD reference is fixed for conditional suffix-noise intervals'))
    if issues:
        return result
    for cohort in COHORTS:
        result['cohorts'][cohort] = {
            'new': _comparison(cohort, roots, 'new_difference_components', work),
            'old': _comparison(cohort, roots, 'old_difference_components', work),
            'new_minus_old': _comparison(cohort, roots, 'new_minus_old_components', work),
        }
    for kind in ('new', 'old', 'new_minus_old'):
        result['cross_cohort'][kind] = _cross_cohort(result['cohorts']['FRESH'][kind], result['cohorts']['TRAIN'][kind])
    result['work'] = dict(work)
    return result
