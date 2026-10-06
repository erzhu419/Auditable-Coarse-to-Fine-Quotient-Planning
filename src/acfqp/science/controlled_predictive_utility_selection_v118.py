"""Select an update from complete, paired source utility validation games."""
from math import isfinite

CANDIDATES = ('KEEP', 'NEW_SHARED', 'NEW_SPLIT')


def select_utility(rows, queries=('reward', 'risk_goal'), replicas=4):
    """Keep the incumbent unless a complete update improves without query harm.

    Each query weighs its replicas equally and candidates weigh queries equally.
    An incomplete roster, mismatched seed or unfinished game invalidates the
    whole comparison; no candidate is chosen from a partial mean.
    """
    queries = tuple(queries)
    if not queries or len(set(queries)) != len(queries) or replicas < 1:
        raise ValueError('selection requires distinct queries and positive replicas')
    expected = {(name, query, replica) for name in CANDIDATES
        for query in queries for replica in range(replicas)}
    indexed, problems = {}, set()
    for row in rows:
        key = (row['candidate'], row['query'], row['replica'])
        if key not in expected:
            problems.add('unexpected_rows')
            continue
        if key in indexed:
            problems.add('duplicate_rows')
            continue
        indexed[key] = row
        if row['result']['status'] not in ('WON', 'LOST'):
            problems.add('nonterminal_games')
        if not isfinite(row['result']['utility']):
            problems.add('nonfinite_utility')
    if set(indexed) != expected:
        problems.add('missing_rows')
    for replica in range(replicas):
        seeds = {row['seed'] for (name, query, index), row in indexed.items() if index == replica}
        if len(seeds) > 1:
            problems.add('unpaired_seeds')

    complete = not problems
    summaries = {}
    for name in CANDIDATES:
        per_query = {}
        for query in queries:
            values = [indexed[(name, query, replica)]['result']['utility']
                if (name, query, replica) in indexed
                and indexed[(name, query, replica)]['result']['status'] in ('WON', 'LOST')
                and isfinite(indexed[(name, query, replica)]['result']['utility']) else None
                for replica in range(replicas)]
            per_query[query] = dict(mean_utility=sum(values) / replicas if complete else None,
                per_replica=values)
        summaries[name] = dict(queries=per_query, mean_utility=sum(
            value['mean_utility'] for value in per_query.values()) / len(queries) if complete else None)

    acceptance = {}
    for name in CANDIDATES[1:]:
        improved, harmed, equal = [], [], []
        if complete:
            for query in queries:
                candidate = summaries[name]['queries'][query]['mean_utility']
                incumbent = summaries['KEEP']['queries'][query]['mean_utility']
                if candidate > incumbent:
                    improved.append(query)
                elif candidate < incumbent:
                    harmed.append(query)
                else:
                    equal.append(query)
        acceptance[name] = dict(eligible=complete and not harmed and bool(improved),
            improved_queries=improved, harmed_queries=harmed, equal_queries=equal)
    eligible = [name for name in CANDIDATES[1:] if acceptance[name]['eligible']]
    selected = max(eligible, key=lambda name: summaries[name]['mean_utility']) if eligible else 'KEEP'
    reason = ('incomplete_paired_validation: ' + ', '.join(sorted(problems)) if not complete else
        'maximum_eligible_query_mean_with_shared_tie_priority' if eligible else 'no_eligible_update')
    return dict(selected_candidate=selected, selection_complete=complete,
        summaries=summaries, acceptance=acceptance, reason=reason)
