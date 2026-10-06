"""Independent arithmetic audit of the retained V165 intervention assay.

No production-core imports, planner calls or trajectory replay are required.
"""
from collections import Counter, defaultdict
import argparse
import json
import math
from pathlib import Path

LIVES = range(4)
QUERIES = ('risk1', 'risk8')
MAPS = ('AA', 'AB', 'BA', 'BB')
METRICS = ('utility', 'reward', 'failure', 'success')
SPLITS = {'primary': ((0, 1), (2, 3)), 'reverse': ((2, 3), (0, 1))}


def _key(row):
    return row['heldout_life'], row['root_id'], row['suffix'], row['mode']


def _semantics(candidate):
    return [candidate['first_action'], candidate['probe_action'],
            list(candidate['true_suffix']), list(candidate['false_suffix'])]


def _mapping(code):
    return {'true': code[0], 'false': code[1]}


def _average(numbers):
    return math.fsum(numbers)/len(numbers)


def _utility(vector, query):
    weight = 1 if query == 'risk1' else 8
    return vector[0] - weight*vector[1] + weight*vector[2]


def _values(row, query):
    return dict(zip(METRICS, [_utility(row['components'], query), *row['components']]))


def _equal(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and _equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(_equal(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10)
    return actual == expected


def independent_roster(candidates, programs, roots, branches):
    """Match by exact actions, before examining any outcome labels."""
    cells, issues = [], []
    candidate_cells = {(c['heldout_life'], c['query']): c for c in candidates}
    program_cells = {(c['heldout_life'], c['query']): c for c in programs}
    counts = Counter(_key(row) for row in branches)
    index = {_key(row): row for row in branches}
    for life in LIVES:
        for query in QUERIES:
            reasons, donor = [], None
            fitted = program_cells.get((life, query), {}).get('programs', {})
            learned, global_rule = fitted.get('LEARNED'), fitted.get('GLOBAL')
            original = None if learned is None else next((c for c in candidate_cells.get((life, query), {}).get('candidates', [])
                                                        if c['candidate_id'] == learned['candidate_id']), None)
            if original is None:
                reasons.append('selected_source_semantics_missing')
            else:
                matches = [(fold, position, c) for fold in LIVES if fold != life
                           for position, c in enumerate(candidate_cells.get((fold, query), {}).get('candidates', []))
                           if _semantics(c) == _semantics(original)]
                if matches:
                    fold, position, match = min(matches, key=lambda match: match[:2])
                    donor = {'heldout_life': fold, 'candidate_id': match['candidate_id'], 'candidate_position': position}
                else:
                    reasons.append('semantic_donor_missing')
            if learned is None or learned.get('mapping') not in [_mapping(code) for code in MAPS]:
                reasons.append('learned_mapping_missing')
            if (global_rule is None or learned is None or global_rule['candidate_id'] != learned['candidate_id']
                    or global_rule.get('mapping') not in [_mapping('AA'), _mapping('BB')]):
                reasons.append('global_mapping_not_constant_same_candidate')
            pool = [r for r in roots if r['life'] == life and r['query'] == query]
            if len(pool) != 4 or len({r['root_id'] for r in pool}) != 4:
                reasons.append('own_history_root_roster')
            selected_roots = []
            for root in pool:
                root_reasons, selected = list(reasons), []
                if donor is not None:
                    for suffix in range(4):
                        group = []
                        for mode in ('H2', donor['candidate_id']+'_A', donor['candidate_id']+'_B'):
                            key = donor['heldout_life'], root['root_id'], suffix, mode
                            if counts[key] != 1:
                                root_reasons.append('missing_or_duplicate_branch_metadata')
                            else:
                                group.append(index[key]); selected.append(index[key])
                        if len(group) == 3 and len({r['seed'] for r in group}) != 1:
                            root_reasons.append('paired_seed_metadata_mismatch')
                selected_roots.append({'root_id': root['root_id'], 'life': life, 'query': query,
                                       'branches': selected, 'complete': not root_reasons, 'issues': sorted(set(root_reasons))})
                issues.extend(root_reasons)
            cells.append({'target_life': life, 'query': query,
                          'selected_candidate_id': None if learned is None else learned['candidate_id'],
                          'source_semantics': None if original is None else dict(zip(('first_action', 'probe_action', 'true_suffix', 'false_suffix'), _semantics(original))),
                          'learned_mapping': None if learned is None else learned.get('mapping'),
                          'global_mapping': None if global_rule is None else global_rule.get('mapping'),
                          'donor': donor, 'roots': selected_roots, 'complete': not reasons and all(r['complete'] for r in selected_roots)})
            issues.extend(reasons)
    return {'cells': cells, 'complete': not issues, 'root_count': sum(len(c['roots']) for c in cells), 'issues': sorted(set(issues))}


def _triplets(roster, rows):
    groups, problems = {}, []
    counts = Counter(_key(r) for r in rows)
    indexed = {_key(r): r for r in rows}
    for cell in roster['cells']:
        for root in cell['roots']:
            triples, errors = {}, list(root['issues'])
            for plan in root['branches']:
                key = _key(plan)
                if counts[key] != 1:
                    errors.append('missing_or_duplicate_outcome'); continue
                row = indexed[key]
                arm = 'H2' if row['mode'] == 'H2' else row['mode'].rsplit('_', 1)[1]
                triples.setdefault(row['suffix'], {})[arm] = row
                if row['seed'] != plan['seed'] or row['root_id'] != root['root_id'] or row['query'] != cell['query']:
                    errors.append('outcome_identity_mismatch')
                if row['status'] not in ('WON', 'LOST') or row['utility'] is None:
                    errors.append('nonterminal_outcome')
                elif not math.isclose(row['utility'], _utility(row['components'], cell['query']), abs_tol=1e-10):
                    errors.append('utility_vector_mismatch')
            for suffix in range(4):
                triple = triples.get(suffix, {})
                if set(triple) != {'H2', 'A', 'B'}:
                    errors.append('incomplete_triplet'); continue
                a, b = triple['A'], triple['B']
                if a['module']['predicate'] != b['module']['predicate']:
                    errors.append('predicate_mismatch')
                if a['module']['predicate'] is None:
                    fields = ('score', 'steps', 'status', 'components', 'utility')
                    paths = ('actual_word', 'actual_probe', 'prefix_steps', 'attempts', 'exit_reason', 'exit_step')
                    if any(a[k] != b[k] for k in fields) or any(a['module'][k] != b['module'][k] for k in paths):
                        errors.append('none_path_or_outcome_mismatch')
            groups[root['root_id']] = triples
            problems.extend((root['root_id'], problem) for problem in sorted(set(errors)))
    return groups, problems


def _mapped(triple, mapping):
    predicate = triple['A']['module']['predicate']
    arm = 'A' if predicate is None else mapping['true' if predicate else 'false']
    return triple[arm]


def _arm_means(triples, suffixes, query):
    return {arm: {'components': [_average([triples[s][arm]['components'][k] for s in suffixes]) for k in range(3)],
                  'utility': _average([_utility(triples[s][arm]['components'], query) for s in suffixes])}
            for arm in ('A', 'B')}


def _moments(values):
    mean = _average(values)
    variance = _average([(v-mean)**2 for v in values])*len(values)/(len(values)-1)
    return {'n': len(values), 'complete': True, 'mean': mean, 'sample_variance': variance,
            'mean_variance': variance/len(values)}


def _pool(moments):
    mean = _average([r['mean'] for r in moments])
    variance = math.fsum(r['mean_variance'] for r in moments)/len(moments)**2
    error = math.sqrt(variance)
    return {'complete': True, 'mean': mean, 'mean_variance': variance,
            'conditional_suffix_se': error, 'conditional_suffix_ci95': [mean-1.96*error, mean+1.96*error]}


def independent_evaluate(roster, rows):
    triples, issues = _triplets(roster, rows)
    if not roster['complete'] or issues:
        return {'complete': False, 'issues': issues, 'splits': {}}
    splits = {}
    for split, (selection, scoring) in SPLITS.items():
        cells, root_rows = [], []
        for cell in roster['cells']:
            query, pool = cell['query'], cell['roots']
            support = Counter('true' if triples[r['root_id']][s]['A']['module']['predicate'] else 'false'
                              for r in pool for s in selection if triples[r['root_id']][s]['A']['module']['predicate'] is not None)
            allowed = [code for code in MAPS if all(support[leaf] or _mapping(code)[leaf] == cell['learned_mapping'][leaf]
                                                   for leaf in ('true', 'false'))]
            def score(code):
                return _average([_average([_utility(_mapped(triples[r['root_id']][s], _mapping(code))['components'], query)
                                           for s in selection]) for r in pool])
            map_scores = {code: score(code) for code in MAPS}
            score_details = []
            for code in MAPS:
                vector = [_average([_average([_mapped(triples[r['root_id']][s], _mapping(code))['components'][k]
                                              for s in selection]) for r in pool]) for k in range(3)]
                baseline = [_average([_average([triples[r['root_id']][s]['H2']['components'][k]
                                                for s in selection]) for r in pool]) for k in range(3)]
                delta = [value-reference for value, reference in zip(vector, baseline)]
                score_details.append({'mapping_code': code, 'mapping': _mapping(code), 'component_mean': vector,
                                      'selection_utility': map_scores[code], 'component_delta_vs_H2': delta,
                                      'selection_gain_vs_H2': _utility(delta, query)})
            evidence = {}
            for leaf in ('true', 'false'):
                delta = [_average([_average([(triples[r['root_id']][s]['A']['components'][k]-triples[r['root_id']][s]['B']['components'][k])
                                             if triples[r['root_id']][s]['A']['module']['predicate'] is (leaf == 'true') else 0.
                                             for s in selection]) for r in pool]) for k in range(3)] if support[leaf] else None
                evidence[leaf] = {'support': support[leaf], 'prior_assignment': cell['learned_mapping'][leaf],
                                  'component_delta_A_minus_B': delta,
                                  'utility_delta_A_minus_B': None if delta is None else _utility(delta, query),
                                  'allowed_assignments': ['A', 'B'] if support[leaf] else [cell['learned_mapping'][leaf]]}
            best_bit = min(allowed, key=lambda code: (-map_scores[code], MAPS.index(code)))
            best_global = min(('AA', 'BB'), key=lambda code: (-map_scores[code], MAPS.index(code)))
            cells.append({'target_life': cell['target_life'], 'query': query, 'bit_refit_mapping': _mapping(best_bit),
                          'global_refit_mapping': _mapping(best_global), 'allowed_mapping_codes': allowed,
                          'support': dict(support), 'mapping_scores': score_details, 'leaf_evidence': evidence})
            for root in pool:
                source = triples[root['root_id']]
                fit = _arm_means(source, selection, query); test = _arm_means(source, scoring, query)
                chosen = max(('A', 'B'), key=lambda arm: fit[arm]['utility'])
                oracle = max(('A', 'B'), key=lambda arm: test[arm]['utility'])
                trials = []
                for suffix in scoring:
                    triple = source[suffix]
                    methods = {'H2': triple['H2'], 'A': triple['A'], 'B': triple['B'], 'ROOT': triple[chosen],
                               'TEST_ROOT_MEAN_ORACLE': triple[oracle], 'LEARNED': _mapped(triple, cell['learned_mapping']),
                               'GLOBAL': _mapped(triple, cell['global_mapping']),
                               'BIT_REFIT': _mapped(triple, _mapping(best_bit)), 'GLOBAL_REFIT': _mapped(triple, _mapping(best_global))}
                    trials.append({'suffix': suffix, 'seed': triple['H2']['seed'], 'predicate': triple['A']['module']['predicate'],
                                   'modes': {mode: dict(branch_id=row['branch_id'], components=row['components'], raw_utility=row['utility'], **_values(row, query))
                                             for mode, row in methods.items()}})
                root_rows.append({'root_id': root['root_id'], 'life': root['life'], 'query': query, 'selected_arm': chosen,
                                  'train_arm_means': fit, 'test_arm_means': test, 'test_mean_oracle_arm': oracle, 'test_trials': trials})
        splits[split] = {'selection_suffixes': list(selection), 'scoring_suffixes': list(scoring), 'cells': cells, 'root_rows': root_rows}
    return {'complete': True, 'issues': [], 'splits': splits}


def audit(candidates, programs, roots, branches, rows, retained_roster, result):
    expected_roster = independent_roster(candidates, programs, roots, branches)
    independent = independent_evaluate(expected_roster, rows)
    checks = []
    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
    check('full_roster_complete', expected_roster['complete'] and expected_roster['root_count'] == 32)
    check('source_outcome_integrity', independent['complete'])
    check('production_complete', result.get('complete') == independent['complete'])
    check('embedded_roster', _equal(result.get('roster'), retained_roster))
    check('zero_new_environment_or_updates', all(result.get(k) == 0 for k in ('new_environment_samples', 'new_model_samples', 'native_planner_calls', 'real_training_updates')))
    for expected, actual in zip(expected_roster['cells'], retained_roster.get('cells', [])):
        projection = {k: expected[k] for k in ('target_life', 'query', 'selected_candidate_id', 'source_semantics', 'learned_mapping', 'global_mapping', 'donor')}
        check(f"roster:{expected['target_life']}:{expected['query']}", _equal(actual, projection) and
              _equal(actual.get('roots'), [{k: r[k] for k in ('root_id', 'life', 'query', 'branches', 'complete')} for r in expected['roots']]))
    check('eight_retained_cells', len(retained_roster.get('cells', [])) == 8)
    if independent['complete']:
        for split, expected in independent['splits'].items():
            actual = result['splits'][split]
            check(f'{split}:fixed_suffix_split', _equal(actual, {k: expected[k] for k in ('selection_suffixes', 'scoring_suffixes')}))
            actual_roots = {r['root_id']: r for r in actual['root_rows']}
            check(f'{split}:full_root_roster', len(actual['root_rows']) == 32 and len(actual_roots) == 32)
            for root in expected['root_rows']:
                check(f"{split}:root:{root['root_id']}", _equal(actual_roots.get(root['root_id']), root))
                recorded = actual_roots.get(root['root_id'], {})
                valid_moments = True
                for kind in ('modes', 'contrasts'):
                    for label, moments in recorded.get(kind, {}).items():
                        if kind == 'modes':
                            values = {metric: [t['modes'][label][metric] for t in root['test_trials']] for metric in METRICS}
                        else:
                            left, right = label.split('-', 1)
                            values = {metric: [t['modes'][left][metric]-t['modes'][right][metric] for t in root['test_trials']] for metric in METRICS}
                        valid_moments = valid_moments and _equal(moments, {metric: _moments(v) for metric, v in values.items()})
                check(f"{split}:root_moments:{root['root_id']}", valid_moments)
            actual_cells = {(c['target_life'], c['query']): c for c in actual['cells']}
            for cell in expected['cells']:
                fitted = actual_cells.get((cell['target_life'], cell['query']), {})
                check(f"{split}:fit:{cell['target_life']}:{cell['query']}", _equal(fitted, {k: cell[k] for k in ('target_life', 'query', 'bit_refit_mapping', 'global_refit_mapping', 'allowed_mapping_codes')}))
                check(f"{split}:leaf_support:{cell['target_life']}:{cell['query']}", all(fitted.get('leaf_evidence', {}).get(leaf, {}).get('support') == cell['support'].get(leaf, 0) for leaf in ('true', 'false')))
                check(f"{split}:fit_scores:{cell['target_life']}:{cell['query']}", _equal(fitted.get('mapping_scores'), cell['mapping_scores']))
                check(f"{split}:leaf_estimates:{cell['target_life']}:{cell['query']}", _equal(fitted.get('leaf_evidence'), cell['leaf_evidence']))
            for kind, key in (('comparisons', 'contrast'), ('modes', 'mode')):
                labels = {(s['query'], s[key]) for s in actual[kind]}
                required = ('ROOT-BIT_REFIT', 'ROOT-GLOBAL_REFIT', 'BIT_REFIT-GLOBAL_REFIT', 'ROOT-LEARNED', 'ROOT-GLOBAL', 'ROOT-H2') if key == 'contrast' else tuple(expected['root_rows'][0]['test_trials'][0]['modes'])
                check(f'{split}:{kind}:required_cohorts', all((q, label) in labels for q in QUERIES for label in required))
                for summary in actual[kind]:
                    query, label = summary['query'], summary[key]
                    samples = defaultdict(list)
                    for root in expected['root_rows']:
                        if root['query'] != query: continue
                        for metric in METRICS:
                            if key == 'contrast':
                                left, right = label.split('-', 1)
                                values = [t['modes'][left][metric]-t['modes'][right][metric] for t in root['test_trials']]
                            else:
                                values = [t['modes'][label][metric] for t in root['test_trials']]
                            samples[(root['life'], metric)].append(_moments(values))
                    histories = [{'life': life, 'roots': 4, 'metrics': {metric: _pool(samples[(life, metric)]) for metric in METRICS}} for life in LIVES]
                    aggregate = {metric: _pool([h['metrics'][metric] for h in histories]) for metric in METRICS}
                    point_only = 'TEST_ROOT_MEAN_ORACLE' in label
                    if point_only:
                        for metrics in [aggregate]+[h['metrics'] for h in histories]:
                            for moment in metrics.values():
                                moment.update(mean_variance=None, conditional_suffix_se=None, conditional_suffix_ci95=None)
                    check(f'{split}:{kind}:{query}:{label}', _equal(summary, {'roots': 16, 'complete': True, 'point_only': point_only, 'metrics': aggregate, 'per_history': histories}))
    return {'schema': 'acfqp.program_headroom.v165.audit', 'valid': all(c['passed'] for c in checks),
            'checks': checks, 'passed_checks': sum(c['passed'] for c in checks), 'total_checks': len(checks),
            'issues': independent['issues'], 'new_environment_samples': 0, 'real_training_updates': 0}


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'roster', 'result', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    read = lambda name: json.loads((args.source/name).read_text())
    candidates, programs, roots, inputs = [read(n) for n in ('generated_candidates.json', 'frozen_programs.json', 'train_roots.json', 'screening_inputs.json')]
    roster = independent_roster(candidates, programs, roots, inputs['branch_roster'])
    wanted = {_key(b) for c in roster['cells'] for r in c['roots'] for b in r['branches']}
    rows = [r for life in LIVES for r in read(f'screening/life_{life}/outcomes.json') if _key(r) in wanted]
    result = audit(candidates, programs, roots, inputs['branch_roster'], rows,
                   json.loads(args.roster.read_text()), json.loads(args.result.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'valid': result['valid'], 'passed': result['passed_checks'], 'checks': result['total_checks']}))
    raise SystemExit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
