"""Nested fresh-label selectors with one independent paired evaluation pool."""
from collections import defaultdict
import math

QUERIES = ('risk1', 'risk8')
SOURCES = ('H2', 'LEARN8')
BUDGETS = (8, 16, 32)
MODES = ('H_GATE', 'M_GATE')
GAINS = ('vs_old', 'vs_reject', 'vs_accept')
DIAGNOSTICS = ('accept_rate', 'old_accept_rate', 'decision_change_rate',
    'train_eval_sign_agreement', 'train_advantage', 'eval_advantage',
    'apparent_gain_vs_old', 'selection_optimism')


def utility(components, query):
    weight = 1. if query == 'risk1' else 8.
    return components[0]-weight*components[1]+weight*components[2]


def mean(values):
    values = list(values)
    return None if not values or any(v is None for v in values) else sum(values)/len(values)


def moments(samples):
    samples = list(samples); average = mean(samples); complete = average is not None
    variance = sum((v-average)**2 for v in samples)/(len(samples)-1) if complete and len(samples)>1 else (0. if complete else None)
    return dict(samples=samples, complete=complete, mean=average, sample_variance=variance,
                mean_variance=variance/len(samples) if complete else None)


def _order(root):
    return root['life'], QUERIES.index(root['query']), SOURCES.index(root['source_method']), root['slot'], root['root_id']


def _metadata(root):
    return {key: root[key] for key in ('root_id', 'life', 'query', 'source_method', 'slot')}


def build_pairs(roots, outcomes, split):
    if split not in ('TRAIN', 'EVAL'):
        raise ValueError('split must be TRAIN or EVAL')
    indexed = {r['root_id']: r for r in roots}
    if len(indexed) != len(roots): raise ValueError('duplicate root identity')
    records = {}
    for row in outcomes:
        if row['split'] != split: continue
        key = row['root_id'], row['suffix'], row['mode']
        if row['root_id'] not in indexed or row['suffix'] not in range(32) or row['mode'] not in MODES:
            raise ValueError('outcome outside the paired roster')
        if key in records: raise ValueError('duplicate paired outcome')
        root = indexed[row['root_id']]
        if any(row[k] != root[k] for k in ('life', 'query', 'source_method', 'slot')):
            raise ValueError('outcome root identity differs')
        if row['status'] not in ('WON', 'LOST', 'CUTOFF'):
            raise ValueError('outcome status is not final')
        records[key] = row
    expected = {(key, s, mode) for key in indexed for s in range(32) for mode in MODES}
    if set(records) != expected: raise ValueError('incomplete paired outcome roster')
    result = []
    for root in sorted(roots, key=_order):
        for suffix in range(32):
            h, m = (records[root['root_id'], suffix, mode] for mode in MODES)
            if h['seed'] != m['seed']: raise ValueError('paired suffix seeds differ')
            complete = h['status'] != 'CUTOFF' and m['status'] != 'CUTOFF'
            components = [m['components'][k]-h['components'][k] for k in range(3)] if complete else None
            result.append(dict(**_metadata(root), split=split, suffix=suffix, complete=complete,
                components=components, advantage=utility(components, root['query']) if complete else None))
    return result


def _pair_index(pairs, split):
    indexed = defaultdict(dict)
    for pair in pairs:
        if pair['split'] != split: raise ValueError('pair split differs')
        if pair['suffix'] in indexed[pair['root_id']]: raise ValueError('duplicate paired suffix')
        indexed[pair['root_id']][pair['suffix']] = pair
    if any(set(values) != set(range(32)) for values in indexed.values()):
        raise ValueError('all thirty-two paired suffixes must be retained')
    return indexed


def _components(pairs):
    return [mean(p['components'][k] for p in pairs) for k in range(3)] if all(p['complete'] for p in pairs) else None


def freeze_selectors(roots, train_pairs):
    indexed = _pair_index(train_pairs, 'TRAIN')
    if set(indexed) != {r['root_id'] for r in roots}: raise ValueError('training root roster differs')
    result = []
    for root in sorted(roots, key=_order):
        for budget in BUDGETS:
            components = _components([indexed[root['root_id']][s] for s in range(budget)])
            advantage = utility(components, root['query']) if components is not None else None
            result.append(dict(**_metadata(root), budget=budget, train_components=components,
                train_advantage=advantage, accept=advantage>0. if advantage is not None else None,
                old_accept=bool(root['prediction']['accept']), complete=components is not None))
    return result


def _interval(average, variance, complete):
    se = math.sqrt(variance) if complete else None
    return dict(complete=complete, mean=average, conditional_suffix_se=se,
        conditional_suffix_ci95=[average-1.96*se, average+1.96*se] if complete else None)


def _root_gain(stats):
    complete = bool(stats) and all(s['complete'] for s in stats)
    return _interval(mean(s['mean'] for s in stats),
        sum(s['mean_variance'] for s in stats)/len(stats)**2 if complete else None, complete)


def _history_gain(stats):
    complete = len(stats)==4 and all(s['complete'] for s in stats)
    return _interval(mean(s['mean'] for s in stats),
        sum(s['conditional_suffix_se']**2 for s in stats)/16 if complete else None, complete)


def _diagnostics(row):
    return dict(accept_rate=None if row['accept'] is None else int(row['accept']),
        old_accept_rate=int(row['old_accept']), decision_change_rate=row['decision_change'],
        **{k: row[k] for k in DIAGNOSTICS if k not in ('accept_rate', 'old_accept_rate', 'decision_change_rate')})


def _summary(rows, query, budget, source):
    histories = []
    for life in range(4):
        local = [r for r in rows if r['life']==life]; diagnostics = [_diagnostics(r) for r in local]
        histories.append(dict(life=life, roots=len(local), complete=bool(local) and all(r['complete'] for r in local),
            means={k: mean(d[k] for d in diagnostics) for k in DIAGNOSTICS},
            gains={name: _root_gain([r['gains'][name] for r in local]) for name in GAINS}))
    return dict(query=query, budget=budget, source_method=source, roots=len(rows),
        complete=all(h['complete'] for h in histories),
        means={k: mean(h['means'][k] for h in histories) for k in DIAGNOSTICS},
        gains={name: _history_gain([h['gains'][name] for h in histories]) for name in GAINS}, per_history=histories)


def evaluate(selectors, eval_pairs):
    indexed = _pair_index(eval_pairs, 'EVAL')
    if set(indexed) != {r['root_id'] for r in selectors}: raise ValueError('evaluation root roster differs')
    lookup = {(r['root_id'], r['budget']): r for r in selectors}
    if len(lookup) != len(selectors) or set(lookup) != {(key, n) for key in indexed for n in BUDGETS}:
        raise ValueError('selector budget roster differs')
    rows = []
    for selector in selectors:
        values = [indexed[selector['root_id']][s] for s in range(32)]
        components = _components(values); advantage = utility(components, selector['query']) if components is not None else None
        accepted, old = selector['accept'], int(selector['old_accept'])
        coefficients = dict(vs_old=None if accepted is None else int(accepted)-old,
            vs_reject=None if accepted is None else int(accepted), vs_accept=None if accepted is None else int(accepted)-1)
        gains = {name: moments([None if coefficient is None or not p['complete'] else coefficient*p['advantage'] for p in values])
                 for name, coefficient in coefficients.items()}
        apparent = None if accepted is None else (int(accepted)-old)*selector['train_advantage']
        heldout_gain = gains['vs_old']['mean']
        row = dict(selector, complete=selector['complete'] and components is not None,
            eval_components=components, eval_advantage=advantage,
            train_eval_sign_agreement=None if accepted is None or advantage is None else int(accepted==(advantage>0.)),
            decision_change=None if accepted is None else int(accepted!=selector['old_accept']),
            apparent_gain_vs_old=apparent, selection_optimism=None if apparent is None or heldout_gain is None else apparent-heldout_gain,
            gains=gains)
        rows.append(row)
    summaries = []
    for query in QUERIES:
        for budget in BUDGETS:
            for source in ('ALL', *SOURCES):
                selected = [r for r in rows if r['query']==query and r['budget']==budget and (source=='ALL' or r['source_method']==source)]
                summaries.append(_summary(selected, query, budget, source))
    differences = []
    for root_id in indexed:
        high, low = lookup[root_id, 32], lookup[root_id, 8]
        coefficient = int(high['accept'])-int(low['accept']) if high['complete'] and low['complete'] else None
        stats = moments([None if coefficient is None or not indexed[root_id][s]['complete'] else
            coefficient*indexed[root_id][s]['advantage'] for s in range(32)])
        differences.append(dict(**_metadata(high), gain=stats))
    comparisons = []
    for query in QUERIES:
        for source in ('ALL', *SOURCES):
            selected = [r for r in differences if r['query']==query and (source=='ALL' or r['source_method']==source)]
            histories = [dict(life=life, roots=sum(r['life']==life for r in selected),
                gain=_root_gain([r['gain'] for r in selected if r['life']==life])) for life in range(4)]
            gain = _history_gain([h['gain'] for h in histories])
            comparisons.append(dict(query=query, source_method=source, contrast='32-8', roots=len(selected),
                complete=gain['complete'], gain=gain, per_history=histories))
    return rows, summaries, comparisons
