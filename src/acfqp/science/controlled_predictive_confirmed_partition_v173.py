"""Confirm frozen DISCOVERY splits with independent paired consequences.

Each candidate compares its collapsed parent with its immediate collapsed
children. Region-exterior roots contribute zero, preserving SOURCE clusters and
telescoping policy differences. CONFIRM never fits coefficients or candidates.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from statistics import NormalDist
from math import sqrt

from . import controlled_predictive_consequence_partition_v172 as discovery
from .controlled_predictive_consequence_partition_v172 import choose_action

SCHEMA = 'acfqp.confirmed_partition.v173'
SOURCE_CLUSTERS = 8
SUFFIXES = 4
MIN_SIDE_SOURCES = 2
MIN_CHANGED_MODEL_SOURCES = 2
FAMILY_ALPHA = .05
METRICS = ('utility', 'reward', 'failure', 'success')


def propose_partition(examples, life):
    """Reuse V172's proposal grammar and freeze every node's DISCOVERY fit."""
    examples = list(examples)
    payload = discovery.fit_partition(examples, life, 'PART_LATE')
    prepared_counts = Counter()
    prepared = discovery._prepare(examples, life, prepared_counts)
    indices = {item['root_id']: index for index, item in enumerate(prepared)}
    leaves = {leaf['leaf_id']: leaf for leaf in payload['leaves']}
    fits = {}

    def freeze(node_id):
        node = payload['nodes'][node_id]
        if node['kind'] == 'leaf':
            fit = deepcopy(leaves[node['leaf_id']])
            prepared_counts['discovery_leaf_fits_reused'] += 1
        else:
            left, right = freeze(node['left']), freeze(node['right'])
            root_ids = sorted(left['root_ids']+right['root_ids'])
            fit = dict(leaf_id=node_id, **discovery._fit_leaf(
                prepared, [indices[root_id] for root_id in root_ids], prepared_counts))
            prepared_counts['discovery_internal_node_fits'] += 1
        fits[str(node_id)] = fit
        return fit

    freeze(0)
    payload.update(schema=SCHEMA, mode='PART_UNPRUNED', node_fits=fits,
                   node_fit_counts=dict(prepared_counts),
                   confirmation_constants=dict(source_clusters=SOURCE_CLUSTERS, suffixes=SUFFIXES,
                       min_side_sources=MIN_SIDE_SOURCES,
                       min_changed_model_sources=MIN_CHANGED_MODEL_SOURCES, family_alpha=FAMILY_ALPHA))
    return payload


def _path(proposal, root, work):
    node_id = 0
    while True:
        node = proposal['nodes'][node_id]
        work['proposal_node_lookups'] += 1
        if node['kind'] == 'leaf':
            return
        side = 'left' if root['canonical_board'][node['cell']] <= node['threshold'] else 'right'
        work['proposal_feature_threshold_tests'] += 1
        yield node_id, side, node[side]
        node_id = node[side]


def _collapsed(proposal, node_id):
    return dict(life=proposal['life'], mode='ONE_LATE', groups={'ALL': node_id},
                leaves=[proposal['node_fits'][str(node_id)]])


def freeze_node_choices(proposals, roots):
    """Freeze parent and one-level-child choices before CONFIRM outcomes."""
    rows, work = [], Counter()
    for root in sorted(roots, key=lambda item: (item['life'], item['root_id'])):
        proposal = proposals[root['life']]
        if proposal['life'] != root['life']:
            raise ValueError('proposal and root must use the same teacher history')
        work['node_choice_roots'] += 1
        for node_id, side, child_id in _path(proposal, root, work):
            parent = choose_action(_collapsed(proposal, node_id), root)
            child = choose_action(_collapsed(proposal, child_id), root)
            work.update(parent['work']); work.update(child['work'])
            work['frozen_node_choice_pairs'] += 1
            rows.append(dict(root_id=root['root_id'], life=root['life'], source_id=root['source_id'],
                             node_id=node_id, side=side, child_node_id=child_id,
                             parent_action=parent['canonical_action'], child_action=child['canonical_action'],
                             parent_decision=parent, child_decision=child))
    return rows, dict(work)


def _moments(values, z, work):
    n = len(values)
    mean = sum(values)/n
    se = sqrt(sum((value-mean)**2 for value in values)/(n-1)/n)
    work.update(confirmation_metric_values=n, confirmation_metric_moments=1)
    return dict(mean=mean, se=se, ci95=[mean-z*se, mean+z*se])


def _bind_confirm(proposal, roots, frozen_choices, outcomes, work):
    life, issues = proposal['life'], []
    selected_roots = []
    for root in roots:
        work['confirmation_roots_examined'] += 1
        if root['life'] == life:
            selected_roots.append(root)
    selected_roots.sort(key=lambda item: item['root_id'])
    root_index = {root['root_id']: root for root in selected_roots}
    if len(root_index) != len(selected_roots):
        issues.append('duplicate_confirm_root')
    sources = sorted({root['source_id'] for root in selected_roots})
    if len(sources) != SOURCE_CLUSTERS:
        issues.append('incomplete_confirm_source_clusters')
    expected_choices = {}
    for root in selected_roots:
        for node_id, side, child_id in _path(proposal, root, work):
            expected_choices[root['root_id'], node_id] = (root, side, child_id)
    choices = {}
    for row in frozen_choices:
        work['confirmation_choice_rows_examined'] += 1
        if row['life'] != life:
            continue
        key = (row['root_id'], row['node_id'])
        if key in choices:
            issues.append('duplicate_frozen_node_choice')
        choices[key] = row
    if set(choices) != set(expected_choices):
        issues.append('incomplete_frozen_node_choices')
    for key in sorted(set(choices) & set(expected_choices)):
        root, side, child_id = expected_choices[key]
        row = choices[key]
        if row['source_id'] != root['source_id'] or row['side'] != side or row['child_node_id'] != child_id:
            issues.append('frozen_node_choice_binding')
        if any(row[f'{label}_action'] not in root['legal_actions'] or
               row[f'{label}_action'] != row[f'{label}_decision']['canonical_action'] for label in ('parent', 'child')):
            issues.append('frozen_node_action_binding')
    expected_outcomes = {(root['root_id'], suffix, action)
                         for root in selected_roots for suffix in range(SUFFIXES) for action in root['legal_actions']}
    index = {}
    for row in outcomes:
        work['confirmation_outcome_rows_examined'] += 1
        if row['life'] != life:
            continue
        key = (row['root_id'], row['suffix'], row['canonical_action'])
        if key in index:
            issues.append('duplicate_confirm_outcome')
        index[key] = row
        if key not in expected_outcomes:
            issues.append('unexpected_confirm_outcome')
            continue
        root = root_index[row['root_id']]
        components = row['components']
        work['confirmation_outcome_component_reads'] += len(components)
        terminal = row['status'] in ('WON', 'LOST')
        if not terminal or len(components) != 3:
            issues.append('incomplete_confirm_terminal_vector')
        elif components != [row['score']/2048., float(row['status'] == 'LOST'), float(row['status'] == 'WON')] or \
                row['utility'] != components[0]-components[1]+components[2]:
            issues.append('confirm_terminal_vector_binding')
        actuals = {action['canonical_action']: action['actual_action'] for action in root['actions']}
        if row['query'] != 'risk1' or row['phase'] != 'CONFIRM' or row['actual_action'] != actuals[row['canonical_action']]:
            issues.append('confirm_outcome_metadata')
        module = row['module']
        if module['mode'] != 'FORCED_H2' or module['life'] != life or module['forced_decisions'] != 1 or \
                module['h2_calls'] != row['steps']-1:
            issues.append('confirm_teacher_binding')
    if set(index) != expected_outcomes:
        issues.append('incomplete_confirm_outcome_cohort')
    for root in selected_roots:
        suffix_seeds = []
        for suffix in range(SUFFIXES):
            seeds = {index[root['root_id'], suffix, action]['seed']
                     for action in root['legal_actions'] if (root['root_id'], suffix, action) in index}
            work['confirmation_suffix_seed_groups'] += 1
            if len(seeds) != 1:
                issues.append('confirm_action_seed_pairing')
            else:
                suffix_seeds.append(next(iter(seeds)))
        if len(set(suffix_seeds)) != SUFFIXES:
            issues.append('confirm_suffix_seed_binding')
    return selected_roots, sources, choices, index, sorted(set(issues))


def confirm_and_prune(proposal, roots, frozen_node_choices, outcomes, total_candidates):
    """Apply only independently confirmed, top-down-reachable frozen splits."""
    work = Counter()
    roots, sources, choices, index, issues = _bind_confirm(proposal, roots, frozen_node_choices, outcomes, work)
    internal = [node for node in proposal['nodes'] if node['kind'] == 'split']
    if total_candidates < len(internal) or total_candidates < 0:
        issues.append('invalid_frozen_family_size')
    z = NormalDist().inv_cdf(1.-FAMILY_ALPHA/(2*total_candidates)) if total_candidates > 0 else None
    source_counts = dict(Counter(root['source_id'] for root in roots))
    record = dict(schema=f'{SCHEMA}.confirmation', life=proposal['life'], complete=not issues,
                  issues=sorted(set(issues)), source_ids=sources, source_root_counts=source_counts,
                  family=dict(alpha=FAMILY_ALPHA, total_candidates=total_candidates, z=z), nodes=[],
                  uncertainty='Bonferroni normal source-cluster bounds conditional on fixed teachers; eight clusters do not establish formal coverage.')
    if issues:
        record['confirmation_work'] = dict(work)
        return None, record
    by_node = {}
    for node in internal:
        node_id = node['node_id']
        sums = {source: [0., 0., 0.] for source in sources}
        side_sources = dict(left=set(), right=set())
        changed_sources, changed_model_sources, in_region = set(), set(), 0
        region_counts = Counter()
        all_supported = True
        for root in roots:
            source_id = root['source_id']
            row = choices.get((root['root_id'], node_id))
            difference = [0., 0., 0.]
            work['confirmation_node_root_visits'] += 1
            if row is not None:
                in_region += 1
                region_counts[source_id] += 1
                side_sources[row['side']].add(source_id)
                supported = row['parent_decision']['support']['complete'] and row['child_decision']['support']['complete']
                all_supported &= supported
                if row['parent_action'] != row['child_action']:
                    changed_sources.add(source_id)
                    if supported:
                        changed_model_sources.add(source_id)
                for suffix in range(SUFFIXES):
                    parent = index[root['root_id'], suffix, row['parent_action']]['components']
                    child = index[root['root_id'], suffix, row['child_action']]['components']
                    for component in range(3):
                        difference[component] += (child[component]-parent[component])/SUFFIXES
                    work.update(confirmation_paired_suffix_differences=1,
                                confirmation_terminal_component_reads=6, confirmation_component_subtractions=3)
            for component in range(3):
                sums[source_id][component] += difference[component]
            work['confirmation_cluster_component_accumulations'] += 3
        clusters = []
        for source_id in sources:
            vector = [value/source_counts[source_id] for value in sums[source_id]]
            clusters.append(dict(source_id=source_id, roots=source_counts[source_id],
                                 in_region_roots=region_counts[source_id], components=vector,
                                 utility=vector[0]-vector[1]+vector[2]))
            work.update(confirmation_cluster_component_normalizations=3, confirmation_cluster_utility_evaluations=1)
        metrics = {'utility': _moments([cluster['utility'] for cluster in clusters], z, work)}
        for component, metric in enumerate(METRICS[1:]):
            metrics[metric] = _moments([cluster['components'][component] for cluster in clusters], z, work)
        eligible = all(len(side_sources[side]) >= MIN_SIDE_SOURCES for side in ('left', 'right')) and \
            len(changed_model_sources) >= MIN_CHANGED_MODEL_SOURCES
        local_pass = eligible and metrics['utility']['ci95'][0] > 0.
        if not all(len(side_sources[side]) >= MIN_SIDE_SOURCES for side in ('left', 'right')):
            reason = 'insufficient_child_source_coverage'
        elif len(changed_model_sources) < MIN_CHANGED_MODEL_SOURCES:
            reason = 'insufficient_changed_model_sources'
        elif not local_pass:
            reason = 'utility_lower_not_positive'
        else:
            reason = 'confirmed'
        result = dict(node_id=node_id, in_region_roots=in_region, source_clusters=len(sources),
                      side_sources={side: sorted(ids) for side, ids in side_sources.items()},
                      changed_sources=sorted(changed_sources), changed_model_sources=sorted(changed_model_sources),
                      all_region_supported=bool(all_supported), eligible=eligible, local_pass=local_pass,
                      reachable=False, retained=False, local_reason=reason, reason='ancestor_rejected',
                      metrics=metrics, clusters=clusters)
        record['nodes'].append(result); by_node[node_id] = result
    confirmed = deepcopy(proposal)
    confirmed['mode'] = 'PART_CONFIRMED'
    active_leaves = []

    def prune(node_id):
        node = proposal['nodes'][node_id]
        if node['kind'] == 'leaf':
            active_leaves.append(deepcopy(proposal['node_fits'][str(node_id)]))
            return
        result = by_node[node_id]
        result.update(reachable=True, retained=result['local_pass'], reason=result['local_reason'])
        work['confirmation_reachable_internal_nodes'] += 1
        if result['local_pass']:
            work['confirmation_splits_retained'] += 1
            prune(node['left']); prune(node['right'])
        else:
            confirmed['nodes'][node_id] = dict(node_id=node_id, kind='leaf', leaf_id=node_id)
            active_leaves.append(deepcopy(proposal['node_fits'][str(node_id)]))
            work['confirmation_splits_pruned'] += 1

    prune(0)
    confirmed['leaves'] = sorted(active_leaves, key=lambda leaf: leaf['leaf_id'])
    confirmed['confirmation_work'] = dict(work)
    record['confirmation_work'] = dict(work)
    return confirmed, record
