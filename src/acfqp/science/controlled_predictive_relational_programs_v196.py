"""Conditional short continuations with both parents of every merged tile.

These witnesses execute the frozen learned rewrite without future spawns.
They are inputs to SOURCE calibration, not stochastic success certificates.
Only word outcomes enter the learner; cell IDs belong to the retained trace.
"""
from collections import Counter
from dataclasses import dataclass
from itertools import product

SCHEMA = 'acfqp.relational_programs.v196'
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
WORDS = tuple((action,) for action in ACTIONS) + tuple(product(ACTIONS, repeat=2))
VALUE_NAMES = ('goal_now',) + tuple(
    f'{"_".join(word)}:{name}' for word in WORDS
    for name in ('valid', 'goal', 'linked_goal', 'score'))


@dataclass(frozen=True)
class Tile:
    identity: int
    rank: int
    origins: tuple
    created_step: int = 0


def _cells(action, line):
    if action == 'DOWN':
        return tuple(4 * row + line for row in range(3, -1, -1))
    if action == 'UP':
        return tuple(4 * row + line for row in range(4))
    if action == 'LEFT':
        return tuple(4 * line + col for col in range(4))
    return tuple(4 * line + col for col in range(3, -1, -1))


def _swipe(tiles, action, program, step, merge_count, goal_rank, counts):
    """Execute the observed pack/once rule, preserving both merge parents."""
    counts.update(program_swipe_calls=1, program_line_rewrites=4)
    output, events, score, linked = [None] * 16, [], 0, False
    for line in range(4):
        cells = _cells(action, line)
        values = [tiles[cell] for cell in cells if tiles[cell] is not None]
        counts.update(program_tile_reads=4, program_packed_tiles=len(values))
        rewritten, index = [], 0
        while index < len(values):
            left = values[index]
            if index + 1 < len(values):
                right = values[index + 1]
                counts['program_merge_relation_checks'] += 1
                merges = program._merges(left.rank, right.rank)
            else:
                merges = False
            if merges:
                rank, reward = program._merge(left.rank, right.rank)
                origins = tuple(sorted(left.origins + right.origins))
                tile = Tile(16 + merge_count + len(events), rank, origins, step)
                events.append(dict(id=tile.identity, left=left.identity, right=right.identity,
                    left_rank=left.rank, right_rank=right.rank, rank=rank, reward=reward,
                    origins=list(origins), step=step, line=line, cell=cells[len(rewritten)]))
                counts.update(program_merges=1, program_dependency_edges=2,
                    program_origin_items_read=len(origins), program_score_additions=1)
                score += reward
                if rank >= goal_rank and any(0 < parent.created_step < step for parent in (left, right)):
                    linked = True
                index += 2
            else:
                tile = left
                index += 1
            rewritten.append(tile)
        for position, tile in enumerate(rewritten):
            output[cells[position]] = tile
            counts['program_tile_placements'] += 1
    # Ranks define legality; genealogy identity alone never makes a legal move.
    before = tuple(tile.rank if tile else 0 for tile in tiles)
    after = tuple(tile.rank if tile else 0 for tile in output)
    counts.update(program_rank_comparison_reads=32)
    return tuple(output), score, before != after, events, linked


def trace_afterstate(board, rule, counts=None):
    """Build a shared 20-word prefix DAG from one oriented afterstate."""
    counts = counts if counts is not None else Counter()
    program = rule.program
    if not program.pack or program.consumption != 'once':
        raise ValueError('V196 executes the inherited pack/once learned rule')
    tiles = tuple(Tile(cell, rank, (cell,)) if rank else None for cell, rank in enumerate(board))
    counts.update(program_initial_cell_reads=16, program_contracts_built=1)
    initial = [dict(id=tile.identity, cell=cell, rank=tile.rank)
               for cell, tile in enumerate(tiles) if tile is not None]
    goal_ids = [tile.identity for tile in tiles if tile and tile.rank >= rule.goal_rank]
    counts.update(program_goal_rank_reads=len(initial))
    root = dict(id=0, parent=None, action=None, executed=False, valid=True,
                goal=bool(goal_ids), linked_goal=False, score=0., events=[], goal_ids=goal_ids)
    prefixes, words, values = [root], [], [float(root['goal'])]
    states = {(): (tiles, 0, 0)}  # tiles, cumulative integer score, path merge count
    index_of = {(): 0}
    for word in WORDS:
        parent_word = word[:-1]
        parent = prefixes[index_of[parent_word]]
        inherited_tiles, previous_score, merge_count = states[parent_word]
        prefix_id = len(prefixes)
        executed = parent['valid'] and not parent['goal']
        if executed:
            moved, gained, valid, events, linked = _swipe(
                inherited_tiles, word[-1], program, len(word), merge_count, rule.goal_rank, counts)
            total_score = previous_score + gained
            counts['program_prefix_score_additions'] += 1
            goal_ids = [tile.identity for tile in moved if tile and tile.rank >= rule.goal_rank]
            counts['program_goal_rank_reads'] += sum(tile is not None for tile in moved)
            goal = bool(goal_ids)
            linked_goal = parent['linked_goal'] or linked
            merge_count += len(events)
        else:
            moved, total_score, valid, events = inherited_tiles, previous_score, parent['valid'], []
            goal, linked_goal, goal_ids = parent['goal'], parent['linked_goal'], parent['goal_ids']
            counts['program_stopped_prefix_reuses'] += 1
        prefix = dict(id=prefix_id, parent=parent['id'], action=word[-1], executed=executed,
            valid=valid, goal=goal, linked_goal=linked_goal, score=total_score / 2048.,
            events=events, goal_ids=list(goal_ids))
        prefixes.append(prefix)
        index_of[word] = prefix_id
        states[word] = (moved, total_score, merge_count)
        words.append(dict(actions=list(word), prefix_id=prefix_id,
            **{name: prefix[name] for name in ('valid', 'goal', 'linked_goal', 'score')}))
        values.extend((float(valid), float(goal), float(linked_goal), prefix['score']))
        counts.update(program_word_records=1, program_feature_values_written=4)
    counts.update(program_prefix_records=21, program_feature_values_written=1)
    return dict(schema=SCHEMA+'.contract', goal_now=root['goal'], initial_tiles=initial,
                prefixes=prefixes, words=words, values=values)


def cache_roots(roots, rule):
    """Read the positioned cache once, retaining local merge witnesses."""
    counts = Counter()
    for root in roots:
        if 'program_contracts' in root:
            counts['program_cache_hits'] += 1
            continue
        root['program_contracts'] = {
            action: trace_afterstate(root['raw_afterstates'][action], rule, counts)
            for action in ACTIONS if action in root['legal_actions']}
        counts['program_cache_roots_built'] += 1
    return dict(counts)
