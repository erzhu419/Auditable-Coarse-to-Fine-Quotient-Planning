"""Fixed retained-label half selection with independent opposite-half scoring."""
from collections import defaultdict

QUERIES = ('risk1', 'risk8')
SOURCES = ('H2', 'LEARN8')
TARGETS = ('H2', 'GATE')
MODES = ('H_H2', 'M_H2', 'H_GATE', 'M_GATE')
DIRECTIONS = (('A_to_B', 'A', 'B'), ('B_to_A', 'B', 'A'))
HALVES = {'A': tuple(range(8)), 'B': tuple(range(8, 16))}
METRICS = ('accept_rate', 'old_accept_rate', 'decision_change_rate',
    'train_eval_sign_agreement', 'train_advantage', 'eval_advantage',
    'gain_vs_old', 'gain_vs_reject', 'gain_vs_accept',
    'apparent_gain_vs_old', 'selection_optimism')


def utility(components, query):
    weight = 1. if query == 'risk1' else 8.
    return components[0]-weight*components[1]+weight*components[2]


def _root_order(root):
    return root['life'], QUERIES.index(root['query']), SOURCES.index(root['source_method']), root['slot'], root['root_id']


def build_pairs(roots, outcomes):
    """Require sixteen complete terminal quartets for every supplied root."""
    indexed = {root['root_id']: root for root in roots}
    if len(indexed) != len(roots):
        raise ValueError('duplicate root identity')
    records = {}
    for row in outcomes:
        root_id, suffix, mode = row['root_id'], row['suffix'], row['mode']
        if root_id not in indexed or suffix not in range(16) or mode not in MODES:
            raise ValueError('outcome outside the retained root/suffix/mode roster')
        key = root_id, suffix, mode
        if key in records:
            raise ValueError('duplicate outcome in a paired quartet')
        root = indexed[root_id]
        if (any(row[name] != root[name] for name in ('life', 'query', 'source_method', 'slot'))
                or row['root_board'] != root['board']):
            raise ValueError('outcome root identity differs')
        if row['status'] not in ('WON', 'LOST') or len(row['components']) != 3:
            raise ValueError('paired quartets require complete terminal components')
        records[key] = row
    expected = {(root_id, suffix, mode) for root_id in indexed for suffix in range(16) for mode in MODES}
    if set(records) != expected:
        raise ValueError('incomplete paired quartet or suffix roster')
    pairs = []
    for root in sorted(roots, key=_root_order):
        for suffix in range(16):
            quartet = {mode: records[root['root_id'], suffix, mode] for mode in MODES}
            if len({row['seed'] for row in quartet.values()}) != 1:
                raise ValueError('paired quartet does not share one suffix seed')
            components = {target: [quartet[module]['components'][k]-quartet[baseline]['components'][k] for k in range(3)]
                for target, module, baseline in (('H2', 'M_H2', 'H_H2'), ('GATE', 'M_GATE', 'H_GATE'))}
            pairs.append(dict(root_id=root['root_id'], suffix=suffix,
                **{key: root[key] for key in ('life', 'query', 'source_method', 'slot')},
                old_accept=bool(root['prediction']['accept']), components=components,
                advantages={target: utility(value, root['query']) for target, value in components.items()}))
    return pairs


def build_selection_rows(roots, pairs):
    indexed = defaultdict(dict)
    for pair in pairs:
        root_id, suffix = pair['root_id'], pair['suffix']
        if suffix in indexed[root_id]:
            raise ValueError('duplicate paired suffix')
        indexed[root_id][suffix] = pair
    if (set(indexed) != {r['root_id'] for r in roots}
            or any(set(values) != set(range(16)) for values in indexed.values())):
        raise ValueError('selection requires all sixteen paired suffixes per root')
    rows = []
    for root in sorted(roots, key=_root_order):
        half_components = {half: {target: [sum(indexed[root['root_id']][suffix]['components'][target][k]
            for suffix in suffixes)/8 for k in range(3)] for target in TARGETS}
            for half, suffixes in HALVES.items()}
        half_advantages = {half: {target: utility(components, root['query']) for target, components in values.items()}
                           for half, values in half_components.items()}
        for direction, train_half, eval_half in DIRECTIONS:
            for target in TARGETS:
                train_advantage = half_advantages[train_half][target]
                rows.append(dict(root_id=root['root_id'],
                    **{key: root[key] for key in ('life', 'query', 'source_method', 'slot')},
                    direction=direction, train_half=train_half, eval_half=eval_half, target=target,
                    old_accept=bool(root['prediction']['accept']), accept=train_advantage > 0.,
                    train_advantage=train_advantage,
                    eval_advantages=half_advantages[eval_half], train_advantages=half_advantages[train_half],
                    eval_components=half_components[eval_half], train_components=half_components[train_half]))
    return rows


def _mean(values):
    values = list(values)
    return None if not values or any(value is None for value in values) else sum(values)/len(values)


def _row_metrics(row, eval_target):
    accepted, old = int(row['accept']), int(row['old_accept'])
    heldout, apparent = row['eval_advantages'][eval_target], row['train_advantages'][eval_target]
    gain = (accepted-old)*heldout
    apparent_gain = (accepted-old)*apparent
    return dict(accept_rate=accepted, old_accept_rate=old, decision_change_rate=int(accepted != old),
        train_eval_sign_agreement=int(bool(accepted) == (heldout > 0.)),
        train_advantage=row['train_advantage'], eval_advantage=heldout,
        gain_vs_old=gain, gain_vs_reject=accepted*heldout, gain_vs_accept=(accepted-1)*heldout,
        apparent_gain_vs_old=apparent_gain, selection_optimism=apparent_gain-gain)


def summarize(rows):
    """Equal roots within each history, then equal four retained histories; no CI."""
    summaries = []
    for query in QUERIES:
        for target in TARGETS:
            for eval_target in TARGETS:
                for source in ('ALL', *SOURCES):
                    for direction in ('ALL', 'A_to_B', 'B_to_A'):
                        selected = [r for r in rows if r['query'] == query and r['target'] == target
                            and (source == 'ALL' or r['source_method'] == source)
                            and (direction == 'ALL' or r['direction'] == direction)]
                        histories = []
                        for life in range(4):
                            by_root = defaultdict(list)
                            for row in selected:
                                if row['life'] == life:
                                    by_root[row['root_id']].append(_row_metrics(row, eval_target))
                            values = {key: _mean(_mean(value[key] for value in cells) for cells in by_root.values()) for key in METRICS}
                            histories.append(dict(life=life, roots=len(by_root),
                                row_count=sum(len(cells) for cells in by_root.values()), **values))
                        summaries.append(dict(query=query, target=target, eval_target=eval_target,
                            source_method=source, direction=direction,
                            roots=len({r['root_id'] for r in selected}), row_count=len(selected),
                            **{key: _mean(history[key] for history in histories) for key in METRICS},
                            per_history=histories))
    return summaries
