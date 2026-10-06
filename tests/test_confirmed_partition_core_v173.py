"""Pure fixed-policy confirmation and top-down composition witnesses."""
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_confirmed_partition_v173 as core


def leaf(node_id, preferred='DOWN', roots=8):
    ids = [f'discovery:{index}' for index in range(roots)]
    coefficients = {action: [0., 0., 0.] for action in ('DOWN', 'LEFT', 'RIGHT', 'UP')}
    coefficients['DOWN'][0] = .5 if preferred == 'DOWN' else -.5
    coefficients['LEFT'][0] = -coefficients['DOWN'][0]
    return dict(leaf_id=node_id, root_ids=ids, source_ids=['discovery_source:0', 'discovery_source:1'],
        coefficients=coefficients,
        action_root_ids={action: list(ids) if action in ('DOWN', 'LEFT') else [] for action in coefficients},
        pair_root_ids={'DOWN|LEFT': list(ids), 'DOWN|RIGHT': [], 'DOWN|UP': [],
                       'LEFT|RIGHT': [], 'LEFT|UP': [], 'RIGHT|UP': []},
        connected_components=[['DOWN', 'LEFT'], ['RIGHT'], ['UP']], loss=0.,
        pair_observations=4*roots, total_pair_weight=float(roots))


def proposal(deeper=False):
    nodes = [dict(node_id=0, kind='split', cell=0, threshold=0, left=1, right=2, gain=1.),
             dict(node_id=1, kind='leaf', leaf_id=1), dict(node_id=2, kind='leaf', leaf_id=2)]
    fits = {'0': leaf(0), '1': leaf(1, 'LEFT'), '2': leaf(2)}
    if deeper:
        nodes[1] = dict(node_id=1, kind='split', cell=1, threshold=0, left=3, right=4, gain=1.)
        nodes += [dict(node_id=3, kind='leaf', leaf_id=3), dict(node_id=4, kind='leaf', leaf_id=4)]
        fits.update({'3': leaf(3), '4': leaf(4, 'LEFT')})
    terminal = [deepcopy(fits[str(node['leaf_id'])]) for node in nodes if node['kind'] == 'leaf']
    return dict(schema=core.SCHEMA, life=0, query='risk1', mode='PART_UNPRUNED', nodes=nodes,
                groups={}, leaves=terminal, node_fits=fits, fit_counts={'frozen_fit_work': 123},
                node_fit_counts={'frozen_node_work': 45}, constants={'min_action_roots': 4})


def confirm_root(source, index, side=0, subside=0):
    board = [0]*16; board[0], board[1], board[15] = side, subside, 2
    return dict(root_id=f'confirm:{source}:{index}', life=0, source_id=f'confirm_source:{source}',
                canonical_board=board, legal_actions=['DOWN', 'LEFT'],
                actions=[dict(canonical_action=action, actual_action=action) for action in ('DOWN', 'LEFT')],
                immediate_rewards={'DOWN': 0., 'LEFT': 0.}, teacher_action='DOWN')


def roots_pair():
    return [confirm_root(source, side, side) for source in range(8) for side in (0, 1)]


def outcomes(roots, vectors):
    rows = []
    for root in roots:
        for suffix in range(4):
            for action in root['legal_actions']:
                vector = list(vectors(root, suffix, action))
                status = 'WON' if vector[2] else 'LOST'
                rows.append(dict(root_id=root['root_id'], life=0, query='risk1', phase='CONFIRM',
                    suffix=suffix, canonical_action=action, actual_action=action,
                    seed=1000+int(root['source_id'].split(':')[-1])*100+int(root['root_id'].split(':')[-1])*10+suffix,
                    components=vector, utility=vector[0]-vector[1]+vector[2], score=vector[0]*2048,
                    status=status, steps=2, module=dict(mode='FORCED_H2', life=0, forced_decisions=1, h2_calls=1)))
    return rows


def choices(model, roots):
    return core.freeze_node_choices({0: model}, roots)[0]


def true_vectors(root, suffix, action):
    preferred = 'LEFT' if root['canonical_board'][0] == 0 else 'DOWN'
    return [2., 0., 1.] if action == preferred else [0., 1., 0.]


def test_discovery_proposal_freezes_internal_fits_and_reuses_leaf_coefficients():
    examples = []
    for index in range(16):
        side = int(index >= 8)
        board = [0]*16; board[0], board[15] = side, 2
        preferred = 'LEFT' if not side else 'DOWN'
        examples.append(dict(root_id=f'discovery:{index}', life=0, source_id=f'discovery_source:{index//4}',
            canonical_board=board, legal_actions=['DOWN', 'LEFT'], immediate_rewards={'DOWN': 0., 'LEFT': 0.},
            suffix_trials=[dict(suffix=suffix, seed=100*index+suffix,
                action_components={action: [4., 0., 1.] if action == preferred else [0., 1., 0.]
                                   for action in ('DOWN', 'LEFT')}) for suffix in range(4)]))
    proposed = core.propose_partition(examples, 0)
    assert proposed['mode'] == 'PART_UNPRUNED' and len(proposed['node_fits']) == 3
    assert proposed['node_fit_counts']['discovery_internal_node_fits'] == 1
    assert proposed['node_fit_counts']['discovery_leaf_fits_reused'] == 2
    for terminal in proposed['leaves']:
        assert terminal == proposed['node_fits'][str(terminal['leaf_id'])]
    assert len(proposed['node_fits']['0']['root_ids']) == 16
    assert proposed['node_fits']['0']['coefficients']['DOWN'] == pytest.approx([0., 0., 0.], abs=1e-12)


def test_independent_suffix_noise_rejects_the_discovery_action_preference():
    model, roots = proposal(), roots_pair()
    rows = outcomes(roots, lambda root, suffix, action: [4. if action == 'DOWN' else (8. if suffix % 2 == 0 else 0.), 1., 0.])
    confirmed, record = core.confirm_and_prune(model, roots, choices(model, roots), rows, 1)
    node = record['nodes'][0]
    assert record['complete'] and node['eligible'] and not node['local_pass']
    assert node['metrics']['utility']['mean'] == 0. and node['metrics']['utility']['ci95'][0] == 0.
    assert confirmed['nodes'][0] == dict(node_id=0, kind='leaf', leaf_id=0)
    assert confirmed['leaves'] == [model['node_fits']['0']]


def test_true_policy_heterogeneity_passes_with_one_complete_vector_and_four_suffixes():
    model, roots = proposal(), roots_pair()
    rows = outcomes(roots, true_vectors)
    confirmed, record = core.confirm_and_prune(model, roots, choices(model, roots), rows, 32)
    node = record['nodes'][0]
    assert node['eligible'] and node['local_pass'] and node['retained']
    assert node['metrics']['utility']['mean'] == 2.
    assert node['metrics']['reward']['mean'] == 1.
    assert node['metrics']['failure']['mean'] == -.5 and node['metrics']['success']['mean'] == .5
    assert len(node['clusters']) == 8 and all(row['components'] == [1., -.5, .5] for row in node['clusters'])
    assert confirmed['nodes'][0]['kind'] == 'split' and len(confirmed['leaves']) == 2
    assert record['confirmation_work']['confirmation_paired_suffix_differences'] == len(roots)*4


def test_ancestor_rejection_blocks_a_locally_positive_descendant_without_refitting():
    model = proposal(deeper=True)
    roots = [confirm_root(source, index, side, subside) for source in range(8)
             for index, side, subside in ((0, 0, 0), (1, 0, 1), (2, 1, 0))]
    rows = outcomes(roots, lambda root, suffix, action: [2. if action == 'DOWN' else 0., 1., 0.])
    confirmed, record = core.confirm_and_prune(model, roots, choices(model, roots), rows, 2)
    bynode = {node['node_id']: node for node in record['nodes']}
    assert not bynode[0]['local_pass']
    assert bynode[1]['local_pass'] and not bynode[1]['reachable'] and not bynode[1]['retained']
    assert bynode[1]['reason'] == 'ancestor_rejected'
    assert confirmed['leaves'] == [model['node_fits']['0']]
    assert confirmed['node_fits'] == model['node_fits']


def test_parent_confirmation_uses_direct_child_not_a_selected_grandchild_policy():
    model = proposal(deeper=True)
    root = confirm_root(0, 0, 0, 0)
    frozen = choices(model, [root])
    root_node = next(row for row in frozen if row['node_id'] == 0)
    assert root_node['child_node_id'] == 1 and root_node['child_action'] == 'LEFT'
    assert core.choose_action(model, root)['canonical_action'] == 'DOWN'


def test_outside_region_sources_stay_zero_and_cluster_denominator_uses_all_source_roots():
    model = proposal(deeper=True)
    roots = []
    for source in range(8):
        roots.append(confirm_root(source, 2, 1, 0))
        if source < 2:
            roots += [confirm_root(source, 0, 0, 0), confirm_root(source, 1, 0, 1)]
    rows = outcomes(roots, lambda root, suffix, action: [4. if action == 'DOWN' else 0., 1., 0.])
    _, record = core.confirm_and_prune(model, roots, choices(model, roots), rows, 2)
    node = next(row for row in record['nodes'] if row['node_id'] == 1)
    assert len(node['clusters']) == 8
    for cluster in node['clusters']:
        source = int(cluster['source_id'].split(':')[-1])
        assert cluster['utility'] == pytest.approx(4./3. if source < 2 else 0.)
        assert cluster['roots'] == (3 if source < 2 else 1)
        assert cluster['in_region_roots'] == (2 if source < 2 else 0)


def test_family_size_is_frozen_across_histories_including_later_unreachable_nodes():
    model, roots = proposal(), roots_pair()
    rows = outcomes(roots, lambda root, suffix, action: [4.+(4. if int(root['source_id'].split(':')[-1]) >= 4 else 0.)
                                                           if action == 'LEFT' else 4., 1., 0.])
    frozen = choices(model, roots)
    _, single = core.confirm_and_prune(model, roots, frozen, rows, 1)
    _, family = core.confirm_and_prune(model, roots, frozen, rows, 32)
    assert single['nodes'][0]['local_pass'] and not family['nodes'][0]['local_pass']
    assert family['family']['z'] > single['family']['z']
    assert family['nodes'][0]['metrics']['utility']['mean'] == single['nodes'][0]['metrics']['utility']['mean']


def test_supported_model_changes_need_two_sources_but_fallback_roots_are_not_removed():
    model, roots = proposal(), roots_pair()
    frozen = choices(model, roots)
    for row in frozen:
        if row['source_id'] not in ('confirm_source:0', 'confirm_source:1'):
            row['child_decision']['support']['complete'] = False
    rows = outcomes(roots, true_vectors)
    _, record = core.confirm_and_prune(model, roots, frozen, rows, 1)
    node = record['nodes'][0]
    assert not node['all_region_supported'] and node['eligible'] and node['local_pass']
    assert node['changed_model_sources'] == ['confirm_source:0', 'confirm_source:1']
    assert node['metrics']['utility']['mean'] == 2. and len(node['clusters']) == 8
    for row in frozen:
        if row['source_id'] == 'confirm_source:1':
            row['parent_decision']['support']['complete'] = False
    _, insufficient = core.confirm_and_prune(model, roots, frozen, rows, 1)
    assert insufficient['nodes'][0]['local_reason'] == 'insufficient_changed_model_sources'


@pytest.mark.parametrize('fault', ('missing_suffix', 'duplicate', 'cutoff', 'different_pair_seed', 'component_mix'))
def test_incomplete_or_misbound_confirmation_stops_before_pruned_model(fault):
    model, roots = proposal(), roots_pair()
    rows = outcomes(roots, true_vectors)
    if fault == 'missing_suffix':
        rows.pop()
    elif fault == 'duplicate':
        rows.append(deepcopy(rows[0]))
    elif fault == 'cutoff':
        rows[0].update(status='CUTOFF', utility=None)
    elif fault == 'different_pair_seed':
        rows[0]['seed'] += 12345
    else:
        rows[0]['components'][2] = 1.-rows[0]['components'][2]
    confirmed, record = core.confirm_and_prune(model, roots, choices(model, roots), rows, 1)
    assert confirmed is None and not record['complete'] and record['issues']


def test_confirmation_cannot_refit_and_preserves_discovery_counts_and_coefficients(monkeypatch):
    model, roots = proposal(), roots_pair()
    frozen = choices(model, roots)
    before = deepcopy(model)
    def forbidden(*args, **kwargs):
        raise AssertionError('CONFIRM attempted to fit DISCOVERY coefficients')
    monkeypatch.setattr(core.discovery, '_fit_leaf', forbidden)
    monkeypatch.setattr(core.discovery, 'fit_partition', forbidden)
    confirmed, record = core.confirm_and_prune(model, roots, frozen, outcomes(roots, true_vectors), 1)
    assert record['complete'] and model == before
    assert confirmed['fit_counts'] == model['fit_counts']
    assert confirmed['node_fit_counts'] == model['node_fit_counts']
    assert confirmed['node_fits'] == model['node_fits']
    assert not any('sampled' in key or 'spawn' in key for key in record['confirmation_work'])
