"""Fixed first-eight-spawn control variate, preserving terminal utility."""
from collections import Counter, defaultdict
import math

from . import controlled_predictive_module_precision_v158 as precision

METADATA = ('root_id', 'life', 'query', 'source_method', 'slot')
VARIANCE_FIELDS = ('raw_mean', 'cv_mean', 'control_mean', 'raw_variance',
                   'cv_variance', 'covariance_raw_control')


def spawn_term(afterstate, cell, rank, critic_value):
    """Enumerate the actual spawn law and reuse its observed critic value."""
    empties = [i for i, value in enumerate(afterstate) if value == 0]
    if cell not in empties or rank not in (1, 2):
        raise ValueError('observed spawn is outside the exact spawn law')
    candidates = []
    for index in empties:
        for tile, mass in ((1, .9), (2, .1)):
            board = list(afterstate)
            board[index] = tile
            value = float(critic_value(tuple(board)))
            if not math.isfinite(value):
                raise ValueError('critic value must be finite')
            candidates.append(dict(cell=index, rank=tile,
                probability=mass/len(empties), value=value))
    expected = sum(c['probability']*c['value'] for c in candidates)
    observed = next(c['value'] for c in candidates if c['cell']==cell and c['rank']==rank)
    return dict(observed_value=observed, expected_value=expected,
        correction=observed-expected, candidates=candidates,
        counts=dict(spawn_outcomes_enumerated=len(candidates), critic_calls=len(candidates)))


def branch_correction(row, critic_value):
    """Read retained selected-action afterstates; draw no new transitions."""
    counts = Counter(branch_records_processed=1, corrected_spawn_steps=0,
                     spawn_outcomes_enumerated=0, critic_calls=0)
    steps = []
    for step in range(min(8, len(row['actions']))):
        afterstate = list(row['choices'][step]['afterstate'])
        cell, rank = row['spawned_cells'][step], row['spawned_ranks'][step]
        term = spawn_term(afterstate, cell, rank, critic_value)
        counts.update(term['counts'])
        counts['corrected_spawn_steps'] += 1
        steps.append(dict(step=step, afterstate=afterstate,
            spawned_cell=cell, spawned_rank=rank, **term))
    keys = ('branch_id', *METADATA, 'split', 'suffix', 'mode')
    return dict(**{key: row[key] for key in keys},
        correction=sum(s['correction'] for s in steps), steps=steps, counts=dict(counts))


def build_adjusted_pairs(raw_pairs, corrections):
    """Subtract the paired zero-mean term; do not invent component labels."""
    lookup = {}
    for row in corrections:
        key = row['root_id'], row['split'], row['suffix'], row['mode']
        if key in lookup:
            raise ValueError('duplicate branch correction')
        lookup[key] = row
    expected = {(p['root_id'], p['split'], p['suffix'], mode)
                for p in raw_pairs for mode in precision.MODES}
    if set(lookup) != expected or len(expected) != 2*len(raw_pairs):
        raise ValueError('corrections differ from paired roster')
    result = []
    for pair in raw_pairs:
        h, m = [lookup[pair['root_id'], pair['split'], pair['suffix'], mode]
                for mode in precision.MODES]
        if any(row[key] != pair[key] for row in (h, m) for key in METADATA):
            raise ValueError('correction root identity differs')
        control = m['correction']-h['correction']
        result.append(dict(pair, raw_components=pair['components'], components=None,
            scalar_control=True, raw_advantage=pair['advantage'], control_difference=control,
            advantage=pair['advantage']-control if pair['complete'] else None))
    return result


def freeze_cv_selectors(roots, train_pairs):
    indexed = precision._pair_index(train_pairs, 'TRAIN')
    if set(indexed) != {r['root_id'] for r in roots}:
        raise ValueError('training root roster differs')
    result = []
    for root in sorted(roots, key=precision._order):
        for budget in precision.BUDGETS:
            pairs = [indexed[root['root_id']][s] for s in range(budget)]
            advantage = precision.mean(p['advantage'] for p in pairs) if all(p['complete'] for p in pairs) else None
            result.append(dict(**{key: root[key] for key in METADATA}, budget=budget,
                train_components=None, scalar_control=True, train_advantage=advantage,
                accept=advantage>0. if advantage is not None else None,
                old_accept=bool(root['prediction']['accept']), complete=advantage is not None))
    return result


def evaluate_control(raw_selectors, cv_selectors, raw_eval_pairs):
    """Judge both frozen selectors on the unchanged independent terminal labels."""
    result = {}
    for name, selectors in (('raw', raw_selectors), ('cv', cv_selectors)):
        rows, summary, comparisons = precision.evaluate(selectors, raw_eval_pairs)
        result[name] = dict(rows=rows, summary=summary, comparisons=comparisons)
    raw_lookup = {(r['root_id'], r['budget']): r for r in raw_selectors}
    pairs = precision._pair_index(raw_eval_pairs, 'EVAL')
    differences = []
    for cv in cv_selectors:
        raw = raw_lookup[cv['root_id'], cv['budget']]
        coefficient = int(cv['accept'])-int(raw['accept']) if cv['complete'] and raw['complete'] else None
        samples = [None if coefficient is None or not pairs[cv['root_id']][s]['complete'] else
                   coefficient*pairs[cv['root_id']][s]['advantage'] for s in range(32)]
        differences.append(dict(**{key: cv[key] for key in METADATA}, budget=cv['budget'],
                                gain=precision.moments(samples)))
    contrasts = []
    for query in precision.QUERIES:
        for budget in precision.BUDGETS:
            for source in ('ALL', *precision.SOURCES):
                selected = [r for r in differences if r['query']==query and r['budget']==budget
                            and (source=='ALL' or r['source_method']==source)]
                histories = [dict(life=life, roots=sum(r['life']==life for r in selected),
                    gain=precision._root_gain([r['gain'] for r in selected if r['life']==life]))
                    for life in range(4)]
                gain = precision._history_gain([h['gain'] for h in histories])
                contrasts.append(dict(query=query, budget=budget, source_method=source,
                    contrast='CV-RAW', roots=len(selected), complete=gain['complete'],
                    gain=gain, per_history=histories))
    result['contrasts'] = contrasts
    return result


def _variance_stats(pairs):
    complete = all(p['complete'] for p in pairs)
    if not complete:
        return dict.fromkeys(VARIANCE_FIELDS)
    raw, cv, control = ([p[key] for p in pairs] for key in
                        ('raw_advantage', 'advantage', 'control_difference'))
    r, v, c = map(precision.mean, (raw, cv, control))
    return dict(raw_mean=r, cv_mean=v, control_mean=c,
        raw_variance=sum((x-r)**2 for x in raw)/(len(raw)-1),
        cv_variance=sum((x-v)**2 for x in cv)/(len(cv)-1),
        covariance_raw_control=sum((x-r)*(y-c) for x, y in zip(raw, control))/(len(raw)-1))


def _ratio(stats):
    raw, cv = stats['raw_variance'], stats['cv_variance']
    return cv/raw if raw is not None and raw > 0. and cv is not None else None


def variance_report(adjusted_pairs):
    """Paired sample variance: equal roots, then equal four histories, no fit."""
    groups = []
    for split in ('TRAIN', 'EVAL'):
        indexed = precision._pair_index([p for p in adjusted_pairs if p['split']==split], split)
        root_rows = []
        for values in indexed.values():
            pairs = [values[s] for s in range(32)]
            root_rows.append(dict(**{key: pairs[0][key] for key in METADATA}, samples=32,
                complete=all(p['complete'] for p in pairs), stats=_variance_stats(pairs)))
        for query in precision.QUERIES:
            for source in ('ALL', *precision.SOURCES):
                selected = [r for r in root_rows if r['query']==query
                            and (source=='ALL' or r['source_method']==source)]
                histories = []
                for life in range(4):
                    local = [r for r in selected if r['life']==life]
                    means = {k: precision.mean(r['stats'][k] for r in local) for k in VARIANCE_FIELDS}
                    histories.append(dict(life=life, roots=len(local),
                        complete=bool(local) and all(r['complete'] for r in local),
                        means=means, variance_ratio=_ratio(means),
                        per_root=[{k: r[k] for k in ('root_id', 'samples', 'complete', 'stats')} for r in local]))
                means = {k: precision.mean(h['means'][k] for h in histories) for k in VARIANCE_FIELDS}
                groups.append(dict(split=split, query=query, source_method=source,
                    roots=len(selected), complete=all(h['complete'] for h in histories),
                    means=means, variance_ratio=_ratio(means), per_history=histories))
    return groups
