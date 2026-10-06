"""Shared rank/merge/block geometry from frozen oriented-afterstate caches.

Pure packing and once-only pair masks are no-spawn geometric signatures, not
complete future actions. No swipe, spawn or merge output is computed here.
"""
from collections import Counter
from math import sqrt

from .controlled_predictive_consequence_partition_v172 import ACTIONS
from .controlled_predictive_shared_consequences_v179 import FEATURE_NAMES as AGGREGATE_NAMES

SCHEMA = 'acfqp.merge_relations.v190'
GOAL_RANK = 11
DIRECTIONS = ('LEFT', 'RIGHT', 'UP', 'DOWN')
RANK_BASES = ('rank_over_goal', 'goal_value_fraction')
NODE_NORMALIZER, PAIR_NORMALIZER = 4., sqrt(120.)
NODE_MOMENT_NAMES = ('count', 'zeros_left', 'zeros_right', 'zeros_up', 'zeros_down',
                     'adjacent_zero_left', 'adjacent_zero_right', 'adjacent_zero_up', 'adjacent_zero_down')
PAIR_MOMENT_NAMES = (
    'same_row', 'same_col', 'row_blocker_count', 'col_blocker_count', 'row_blocker_rank', 'col_blocker_rank',
    'row_gap', 'col_gap', 'row_col_product',
    *(f'packing_{d.lower()}_gap' for d in DIRECTIONS),
    *(f'packing_{d.lower()}_clear_alignment' for d in DIRECTIONS),
    *(f'packing_{d.lower()}_blocker_rank' for d in DIRECTIONS),
    *(f'packing_{d.lower()}_blocker_{end}' for d in DIRECTIONS for end in ('first', 'last')),
    *(f'once_pair_{d.lower()}' for d in DIRECTIONS))
VACANCY_MOMENT_NAMES = tuple(f'vacancy_neighbor_{d.lower()}_rank_{rank}' for d in DIRECTIONS for rank in (1, 2))
FEATURE_NAMES = (*AGGREGATE_NAMES,
    *(f'{basis}:{kind}:{name}' for basis in RANK_BASES
      for kind, names in (('node', NODE_MOMENT_NAMES), ('pair', PAIR_MOMENT_NAMES)) for name in names),
    *VACANCY_MOMENT_NAMES)


def basis_metadata():
    return dict(columns=98, intercept=False, representation='oriented_afterstate_merge_relations', goal_rank=GOAL_RANK,
        rank_bases=['rank/11', '2^(rank-11)'], node_normalizer=NODE_NORMALIZER, pair_normalizer=PAIR_NORMALIZER,
        directions=list(DIRECTIONS), node_moments=list(NODE_MOMENT_NAMES), pair_moments=list(PAIR_MOMENT_NAMES),
        vacancy_moments=list(VACANCY_MOMENT_NAMES), vacancy_normalizer=4., packing_merges=False, packing_spawns=False)


def _neighbor(position, direction):
    row, col = divmod(position, 4)
    dr, dc = {'LEFT': (0, -1), 'RIGHT': (0, 1), 'UP': (-1, 0), 'DOWN': (1, 0)}[direction]
    row, col = row+dr, col+dc
    return 4*row+col if 0 <= row < 4 and 0 <= col < 4 else None


def _between(first, second):
    ra, ca = divmod(first, 4); rb, cb = divmod(second, 4)
    if ra == rb:
        return [4*ra+c for c in range(min(ca, cb)+1, max(ca, cb))]
    if ca == cb:
        return [4*r+ca for r in range(min(ra, rb)+1, max(ra, rb))]
    return []


def build_contract(record, counts=None):
    """Recover rank-labelled relations and packing coordinates without swipes."""
    work = Counter(relation_contracts_built=1)
    board, seen = [0]*16, set()
    for token in record['tokens']:
        work['relation_token_kind_reads'] += 1
        if token[0] == 'cell':
            _, position, rank = token
            board[position] = rank; seen.add(position)
            work.update(relation_cell_token_records_read=1, relation_cell_positions_read=1, relation_cell_rank_reads=1)
    if seen != set(range(16)):
        raise ValueError('sixteen positioned cell tokens required')
    nodes = []
    for position, rank in enumerate(board):
        work['relation_node_occupancy_tests'] += 1
        if rank == 0:
            continue
        row, col = divmod(position, 4)
        sides = ([4*row+c for c in range(col)], [4*row+c for c in range(col+1, 4)],
                 [4*r+col for r in range(row)], [4*r+col for r in range(row+1, 4)])
        zero_counts = {d: sum(board[p] == 0 for p in side) for d, side in zip(DIRECTIONS, sides)}
        adjacent = {}
        for d in DIRECTIONS:
            neighbor = _neighbor(position, d)
            adjacent[d] = int(neighbor is not None and board[neighbor] == 0)
            work['relation_node_neighbor_tests'] += 1
            if neighbor is not None:
                work['relation_node_neighbor_rank_reads'] += 1
        packed = dict(LEFT=4*row+col-zero_counts['LEFT'], RIGHT=4*row+col+zero_counts['RIGHT'],
                      UP=4*(row-zero_counts['UP'])+col, DOWN=4*(row+zero_counts['DOWN'])+col)
        moments = [1., *[zero_counts[d]/3. for d in DIRECTIONS], *[float(adjacent[d]) for d in DIRECTIONS]]
        nodes.append(dict(node_id=position, rank=rank, row=row, col=col, zeros=zero_counts,
                          adjacent_zero=adjacent, packed_positions=packed, moments=moments))
        work.update(relation_node_records=1, relation_side_rank_reads=sum(map(len, sides)),
                    relation_node_zero_normalizations=4, relation_packed_coordinates_computed=4)
    node_index = {node['node_id']: node for node in nodes}
    packing, once_pairs = {}, {}
    for direction in DIRECTIONS:
        occupants = [None]*16
        for node in nodes:
            occupants[node['packed_positions'][direction]] = node['node_id']
        selected = []
        for line in range(4):
            positions = ([4*line+c for c in range(4)] if direction in ('LEFT', 'RIGHT')
                         else [4*r+line for r in range(4)])
            if direction in ('RIGHT', 'DOWN'):
                positions.reverse()
            ordered = [occupants[p] for p in positions if occupants[p] is not None]
            work.update(relation_once_scan_lines=1, relation_once_packing_cell_reads=4,
                        relation_once_positive_tile_reads=len(ordered))
            cursor = 0
            while cursor+1 < len(ordered):
                first, second = ordered[cursor:cursor+2]
                work['relation_once_rank_comparisons'] += 1
                if node_index[first]['rank'] == node_index[second]['rank']:
                    selected.append(sorted((first, second))); cursor += 2
                    work['relation_once_pairs_selected'] += 1
                else:
                    cursor += 1
        packing[direction] = dict(occupants=occupants)
        once_pairs[direction] = selected
        work['relation_packing_node_placements'] += len(nodes)
    once_sets = {d: {tuple(pair) for pair in once_pairs[d]} for d in DIRECTIONS}
    equal_pairs = []
    for index, first in enumerate(nodes):
        for second in nodes[index+1:]:
            work['relation_equal_rank_pair_tests'] += 1
            if first['rank'] != second['rank']:
                continue
            a, b = first['node_id'], second['node_id']
            same_row, same_col = first['row'] == second['row'], first['col'] == second['col']
            raw_positions = _between(a, b)
            raw_blockers = [p for p in raw_positions if board[p] > 0]
            raw_sum = sum(board[p] for p in raw_blockers)
            dr, dc = second['row']-first['row'], second['col']-first['col']
            moments = [float(same_row), float(same_col), len(raw_blockers)/2. if same_row else 0.,
                len(raw_blockers)/2. if same_col else 0., raw_sum/22. if same_row else 0.,
                raw_sum/22. if same_col else 0., abs(dr)/3., abs(dc)/3., dr*dc/9.]
            projections, gaps, clear, sums, endpoints = {}, [], [], [], []
            for direction in DIRECTIONS:
                pa, pb = first['packed_positions'][direction], second['packed_positions'][direction]
                ra, ca = divmod(pa, 4); rb, cb = divmod(pb, 4)
                aligned = ca == cb if direction in ('LEFT', 'RIGHT') else ra == rb
                gap = abs(ca-cb)/3. if direction in ('LEFT', 'RIGHT') else abs(ra-rb)/3.
                positions = _between(pa, pb) if aligned else []
                occupants = packing[direction]['occupants']
                blockers = [occupants[p] for p in positions if occupants[p] is not None]
                ranks = [node_index[node_id]['rank'] for node_id in blockers]
                projections[direction] = dict(first_position=pa, second_position=pb, aligned=aligned,
                    blockers=blockers, blocker_ranks=ranks)
                gaps.append(gap); clear.append(float(aligned and not ranks)); sums.append(sum(ranks)/22.)
                endpoints.extend((ranks[0]/11. if ranks else 0., ranks[-1]/11. if ranks else 0.))
                work.update(relation_pair_packing_projections=1, relation_pair_packing_coordinate_reads=2,
                    relation_pair_projected_between_cells_read=len(positions), relation_pair_projected_blocker_rank_reads=len(ranks))
            masks = [float((a, b) in once_sets[d]) for d in DIRECTIONS]
            moments += gaps+clear+sums+endpoints+masks
            equal_pairs.append(dict(first=a, second=b, rank=first['rank'], raw_blockers=raw_blockers,
                                    projections=projections, once_masks=dict(zip(DIRECTIONS, masks)), moments=moments))
            work.update(relation_equal_pair_records=1, relation_pair_raw_between_rank_reads=len(raw_positions),
                        relation_once_pair_membership_tests=4)
    vacancy_moments = [0.]*8
    for position, rank in enumerate(board):
        work['relation_vacancy_cell_tests'] += 1
        if rank != 0:
            continue
        for index, direction in enumerate(DIRECTIONS):
            neighbor = _neighbor(position, direction)
            work['relation_vacancy_direction_checks'] += 1
            if neighbor is not None:
                value = board[neighbor]
                work['relation_vacancy_neighbor_rank_reads'] += 1
                if value in (1, 2):
                    vacancy_moments[2*index+value-1] += .25
                    work['relation_vacancy_neighbor_contributions'] += 1
    result = dict(schema=SCHEMA+'.contract', aggregate=list(record['aggregate']), nodes=nodes,
                  equal_pairs=equal_pairs, packing=packing, once_pairs=once_pairs, vacancy_moments=vacancy_moments)
    work['relation_aggregate_values_copied'] += 6
    if counts is not None:
        counts.update(work)
    return result


def _project(contract, work):
    values = list(map(float, contract['aggregate']))
    for basis in range(2):
        node_values, pair_values = [0.]*9, [0.]*33
        for node in contract['nodes']:
            weight = node['rank']/11. if basis == 0 else 2.**(node['rank']-11)
            for index, moment in enumerate(node['moments']):
                node_values[index] += weight*moment
            work.update(relation_rank_basis_evaluations=1, relation_node_moment_accumulations=9)
        for pair in contract['equal_pairs']:
            weight = pair['rank']/11. if basis == 0 else 2.**(pair['rank']-11)
            for index, moment in enumerate(pair['moments']):
                pair_values[index] += weight*moment
            work.update(relation_rank_basis_evaluations=1, relation_pair_moment_accumulations=33)
        values.extend(value/NODE_NORMALIZER for value in node_values)
        values.extend(value/PAIR_NORMALIZER for value in pair_values)
    values.extend(contract['vacancy_moments'])
    work.update(relation_node_projection_normalizations=18, relation_pair_projection_normalizations=66,
                relation_vacancy_projection_values_copied=8, relation_feature_vectors_computed=1)
    return values


def action_features_from_root(root, counts=None):
    work = Counter()
    if 'relation_features' in root:
        features = {a: list(root['relation_features'][a]) for a in ACTIONS if a in root['relation_features']}
        work.update(relation_feature_cache_hits=1, relation_cached_feature_reads=98*len(features))
    else:
        features = {}
        for action in ACTIONS:
            if action in root['layout_features']:
                features[action] = _project(build_contract(root['layout_features'][action], work), work)
        work['relation_feature_maps_derived'] += 1
    if counts is not None:
        counts.update(work)
    return features


def cache_roots(roots):
    work = Counter()
    for root in roots:
        root['relation_features'] = action_features_from_root(root, work)
    return dict(work)
