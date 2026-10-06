"""Fit observed suffix consequences and retain source assignments where unseen."""
from collections import Counter
from copy import deepcopy

from .controlled_predictive_consequence_program_v163 import (
    LIVES, MAPPING_CODES, TRAIN_ROOTS_PER_HISTORY, TRAIN_SUFFIXES,
    _mapping_score, _mean, build_program, generate_candidates, run_branch)
from .controlled_predictive_policy_modules_v151 import utility


def _predicate_effect(predicate, pairs, histories, query, work):
    """Full-roster indicator-weighted A−B; unseen leaves have no estimate."""
    root_means = []
    for root, outcomes in pairs:
        deltas = []
        for _, a, b in outcomes:
            deltas.append([x-y for x, y in zip(a['components'], b['components'], strict=True)]
                          if a['module']['predicate'] is predicate else [0., 0., 0.])
            work['evidence_vector_selections'] += 1
        root_means.append((root['life'], [_mean(row[k] for row in deltas) for k in range(3)]))
        work['evidence_root_means'] += 1
    history_means = []
    for life in histories:
        rows = [vector for root_life, vector in root_means if root_life == life]
        history_means.append([_mean(row[k] for row in rows) for k in range(3)])
        work['evidence_history_means'] += 1
    vector = [_mean(row[k] for row in history_means) for k in range(3)]
    work['evidence_estimates'] += 1
    return vector, utility(vector, query)


def learn_programs(cells, roots, compact_outcomes):
    """Optimize identified leaves without assigning terminal labels to unseen ones."""
    result = []
    for cell in cells:
        heldout, query = cell['heldout_life'], cell['query']
        histories = [life for life in LIVES if life != heldout]
        pool = [root for root in roots if root['life'] in histories and root['query'] == query]
        index = {(row['root_id'], row['suffix'], row['mode']): row for row in compact_outcomes
                 if row['heldout_life'] == heldout and row['query'] == query}
        roster_complete = all(sum(root['life'] == life for root in pool) == TRAIN_ROOTS_PER_HISTORY
                              for life in histories)
        work = Counter(weight_updates=0, terminal_supported_assignments=0, retained_source_assignments=0)
        scores = []
        for candidate in cell['candidates']:
            candidate_id = candidate['candidate_id']
            issues = [] if roster_complete else ['root_roster']
            condition_counts, pairs = Counter(true=0, false=0, none=0), []
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
            complete, evidence = not issues, {}
            for name, predicate, prior in (('true', True, 'A'), ('false', False, 'B')):
                support = condition_counts[name]
                estimated = complete and support > 0
                vector, value = _predicate_effect(predicate, pairs, histories, query, work) if estimated else (None, None)
                evidence[name] = dict(support=support,
                    provenance='terminal_estimated' if estimated else 'terminal_incomplete' if support else 'source_prior',
                    component_delta_A_minus_B=vector, utility_delta_A_minus_B=value,
                    prior_assignment=prior,
                    allowed_assignments=['A', 'B'] if estimated else [prior] if complete else [])
                if complete:
                    work['terminal_supported_assignments' if support else 'retained_source_assignments'] += 1
            allowed = [code for code in MAPPING_CODES if code[0] in evidence['true']['allowed_assignments']
                       and code[1] in evidence['false']['allowed_assignments']] if complete else []
            mapping_scores = [_mapping_score(code, pairs, histories, query, work)
                              for code in MAPPING_CODES] if complete else []
            learned = min((row for row in mapping_scores if row['mapping_code'] in allowed),
                          key=lambda row: (-row['train_gain'], MAPPING_CODES.index(row['mapping_code']))) if complete else None
            global_score = min((row for row in mapping_scores if row['mapping_code'] in ('AA', 'BB')),
                               key=lambda row: (-row['train_gain'], MAPPING_CODES.index(row['mapping_code']))) if complete else None
            scores.append(dict(candidate_id=candidate_id, complete=complete,
                condition_counts=dict(condition_counts), issues=issues, predicate_evidence=evidence,
                allowed_mapping_codes=allowed,
                all_predicates_identified=complete and bool(condition_counts['true'] and condition_counts['false']),
                mapping_scores=mapping_scores, learned_mapping=None if learned is None else learned['mapping_code'],
                global_mapping=None if global_score is None else global_score['mapping_code']))
        complete = bool(scores) and all(score['complete'] for score in scores)
        programs, selected_identified = {}, False
        if complete:
            work['learned_branch_tables'] += 1
            by_id = {candidate['candidate_id']: candidate for candidate in cell['candidates']}
            def score_for(item, code):
                return next(row for row in item['mapping_scores'] if row['mapping_code'] == code)
            modal = min(enumerate(scores), key=lambda item: (-score_for(item[1], 'AB')['train_gain'], item[0]))[1]
            learned = min(enumerate(scores), key=lambda item: (-score_for(item[1], item[1]['learned_mapping'])['train_gain'], item[0]))[1]
            selected_identified = learned['all_predicates_identified']
            for name, item, code in (
                    ('MODAL', modal, 'AB'), ('LEARNED', learned, learned['learned_mapping']),
                    ('MATCH_MODAL', learned, 'AB'), ('GLOBAL', learned, learned['global_mapping'])):
                selected = score_for(item, code); candidate = by_id[item['candidate_id']]
                programs[name] = dict(candidate_id=item['candidate_id'], mapping=deepcopy(selected['mapping']),
                    program=build_program(candidate, selected['mapping']), train_gain=selected['train_gain'])
            programs['FIXED'] = dict(candidate_id=learned['candidate_id'], mapping=None,
                program=deepcopy(by_id[learned['candidate_id']]), train_gain=None)
        result.append(dict(heldout_life=heldout, query=query, complete=complete, train_lives=histories,
            candidate_scores=scores, programs=programs, learning_counts=dict(work),
            all_predicates_identified=complete and all(score['all_predicates_identified'] for score in scores),
            selected_program_all_predicates_identified=selected_identified))
    return result
