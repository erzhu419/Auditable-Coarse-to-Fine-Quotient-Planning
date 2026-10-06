"""Learn a conditional suffix mapping from paired, executable terminal outcomes."""
from collections import Counter
from copy import deepcopy

from .controlled_predictive_feedback_program_v162 import generate_candidates, run_branch
from .controlled_predictive_policy_modules_v151 import utility

LIVES = (0, 1, 2, 3)
TRAIN_SUFFIXES = 4
TRAIN_ROOTS_PER_HISTORY = 4
MAPPING_CODES = ('AA', 'AB', 'BA', 'BB')


def mapping_from_code(code):
    return dict(true=code[0], false=code[1])


def build_program(candidate, mapping):
    """Choose whole observed suffixes; retain the shared first action and probe."""
    program = deepcopy(candidate)
    suffixes = {'A': candidate['true_suffix'], 'B': candidate['false_suffix']}
    program['true_suffix'] = list(suffixes[mapping['true']])
    program['false_suffix'] = list(suffixes[mapping['false']])
    return program


def _mean(values):
    values = tuple(values)
    return sum(values)/len(values)


def _mapping_score(code, pairs, histories, query, work):
    root_means = []
    for root, outcomes in pairs:
        deltas = []
        for baseline, a, b in outcomes:
            predicate = a['module']['predicate']
            selected = a if predicate is None or code[0 if predicate else 1] == 'A' else b
            deltas.append([x-y for x, y in zip(selected['components'], baseline['components'], strict=True)])
            work['mapping_vector_selections'] += 1
        vector = [_mean(row[k] for row in deltas) for k in range(3)]
        root_means.append((root['life'], vector))
        work['mapping_root_means'] += 1
    history_gains = []
    for life in histories:
        rows = [vector for root_life, vector in root_means if root_life == life]
        vector = [_mean(row[k] for row in rows) for k in range(3)]
        history_gains.append(dict(life=life, roots=len(rows), train_gain=utility(vector, query),
                                  component_delta=vector))
        work['mapping_history_means'] += 1
    vector = [_mean(row['component_delta'][k] for row in history_gains) for k in range(3)]
    work['mapping_scores'] += 1
    return dict(mapping_code=code, mapping=mapping_from_code(code), train_gain=utility(vector, query),
                component_delta=vector, history_gains=history_gains)


def learn_programs(cells, roots, compact_outcomes):
    """Select realized mappings on the complete, equally weighted TRAIN roster."""
    result = []
    for cell in cells:
        heldout, query = cell['heldout_life'], cell['query']
        histories = [life for life in LIVES if life != heldout]
        pool = [root for root in roots if root['life'] in histories and root['query'] == query]
        index = {(row['root_id'], row['suffix'], row['mode']): row for row in compact_outcomes
                 if row['heldout_life'] == heldout and row['query'] == query}
        root_roster_complete = all(sum(root['life'] == life for root in pool) == TRAIN_ROOTS_PER_HISTORY
                                   for life in histories)
        work, scores = Counter(weight_updates=0), []
        for candidate in cell['candidates']:
            candidate_id = candidate['candidate_id']
            issues = [] if root_roster_complete else ['root_roster']
            condition_counts = Counter(true=0, false=0, none=0)
            pairs = []
            for root in pool:
                outcomes = []
                for suffix in range(TRAIN_SUFFIXES):
                    rows = [index.get((root['root_id'], suffix, mode))
                            for mode in ('H2', candidate_id+'_A', candidate_id+'_B')]
                    work['candidate_pairs_examined'] += 1
                    if any(row is None for row in rows):
                        if 'missing_pair' not in issues: issues.append('missing_pair')
                        continue
                    baseline, a, b = rows
                    if any(row['status'] not in ('WON', 'LOST') or row['utility'] is None for row in rows):
                        if 'nonterminal_pair' not in issues: issues.append('nonterminal_pair')
                        continue
                    predicate = a['module']['predicate']
                    if predicate != b['module']['predicate']:
                        if 'predicate_mismatch' not in issues: issues.append('predicate_mismatch')
                        continue
                    if predicate is None and any(a[key] != b[key] for key in ('components', 'status', 'utility')):
                        if 'none_outcome_mismatch' not in issues: issues.append('none_outcome_mismatch')
                        continue
                    condition_counts['none' if predicate is None else 'true' if predicate else 'false'] += 1
                    outcomes.append((baseline, a, b))
                pairs.append((root, outcomes))
            if not condition_counts['true'] or not condition_counts['false']:
                issues.append('predicate_support')
            complete = not issues
            mapping_scores = [_mapping_score(code, pairs, histories, query, work)
                              for code in MAPPING_CODES] if complete else []
            learned = min(mapping_scores, key=lambda row: (-row['train_gain'], MAPPING_CODES.index(row['mapping_code']))) if complete else None
            global_score = min((row for row in mapping_scores if row['mapping_code'] in ('AA', 'BB')),
                               key=lambda row: (-row['train_gain'], MAPPING_CODES.index(row['mapping_code']))) if complete else None
            scores.append(dict(candidate_id=candidate_id, complete=complete,
                condition_counts=dict(condition_counts), issues=issues, mapping_scores=mapping_scores,
                learned_mapping=None if learned is None else learned['mapping_code'],
                global_mapping=None if global_score is None else global_score['mapping_code']))
        complete = bool(scores) and all(score['complete'] for score in scores)
        programs = {}
        if complete:
            work['learned_branch_tables'] += 1
            by_id = {candidate['candidate_id']: candidate for candidate in cell['candidates']}
            def score_for(item, code):
                return next(row for row in item['mapping_scores'] if row['mapping_code'] == code)
            modal = min(enumerate(scores), key=lambda item: (-score_for(item[1], 'AB')['train_gain'], item[0]))[1]
            learned = min(enumerate(scores), key=lambda item: (-score_for(item[1], item[1]['learned_mapping'])['train_gain'], item[0]))[1]
            for name, item, code in (
                    ('MODAL', modal, 'AB'), ('LEARNED', learned, learned['learned_mapping']),
                    ('MATCH_MODAL', learned, 'AB'), ('GLOBAL', learned, learned['global_mapping'])):
                selected = score_for(item, code); candidate = by_id[item['candidate_id']]
                programs[name] = dict(candidate_id=item['candidate_id'], mapping=deepcopy(selected['mapping']),
                    program=build_program(candidate, selected['mapping']), train_gain=selected['train_gain'])
            programs['FIXED'] = dict(candidate_id=learned['candidate_id'], mapping=None,
                program=deepcopy(by_id[learned['candidate_id']]), train_gain=None)
        result.append(dict(heldout_life=heldout, query=query, complete=complete, train_lives=histories,
                           candidate_scores=scores, programs=programs, learning_counts=dict(work)))
    return result
