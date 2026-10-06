"""Independent retained-record audit of semantic-stratum action rankings."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

LIVES = range(4)
QUERIES = ('risk1', 'risk8')
GROUPS = {'half01': (0, 1), 'half23': (2, 3), 'full03': (0, 1, 2, 3)}
CONTRASTS = {'A-B': ('A', 'B'), 'A-H2': ('A', 'H2'), 'B-H2': ('B', 'H2')}
METRICS = ('utility', 'reward', 'failure', 'success', 'reward_effect', 'failure_effect', 'success_effect', 'risk_effect')


def _coordinate(row):
    return row['heldout_life'], row['root_id'], row['suffix'], row['mode']


def _semantics(candidate):
    return {k: candidate[k] for k in ('first_action', 'probe_action', 'true_suffix', 'false_suffix')}


def _signature(candidate):
    return (candidate['first_action'], candidate['probe_action'], tuple(candidate['true_suffix']), tuple(candidate['false_suffix']))


def _mean(values):
    return math.fsum(values)/len(values)


def _utility(vector, query):
    weight = 1 if query == 'risk1' else 8
    return vector[0] + weight*(vector[2]-vector[1])


def _equal(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and _equal(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(_equal(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and math.isclose(actual, expected, abs_tol=1e-10, rel_tol=1e-10)
    return actual == expected


def independent_roster(candidates, programs, roots, branches):
    """Keep every selected semantic class; choose first donors without labels."""
    candidate_cells = {(c['heldout_life'], c['query']): c for c in candidates}
    program_cells = {(c['heldout_life'], c['query']): c for c in programs}
    strata, all_issues = [], []
    indexed = {_coordinate(b): b for b in branches}
    counts = Counter(_coordinate(b) for b in branches)
    for query in QUERIES:
        semantic_union = {}
        for life in LIVES:
            selected = program_cells.get((life, query), {}).get('programs', {}).get('LEARNED')
            candidate = None if selected is None else next((c for c in candidate_cells.get((life, query), {}).get('candidates', [])
                                                          if c['candidate_id'] == selected['candidate_id']), None)
            if candidate is None:
                all_issues.append('selected_semantics_missing'); continue
            signature = _signature(candidate)
            if signature not in semantic_union:
                semantic_union[signature] = {'source_semantics': _semantics(candidate), 'selected_by': []}
            semantic_union[signature]['selected_by'].append({'target_life': life, 'candidate_id': selected['candidate_id']})
        for union_item in semantic_union.values():
            histories = []
            for life in LIVES:
                matches = [(fold, position, c) for fold in LIVES if fold != life
                           for position, c in enumerate(candidate_cells.get((fold, query), {}).get('candidates', []))
                           if _signature(c) == _signature(union_item['source_semantics'])]
                donor = None
                reasons = []
                if matches:
                    fold, position, candidate = min(matches, key=lambda m: m[:2])
                    donor = {'heldout_life': fold, 'candidate_id': candidate['candidate_id'], 'candidate_position': position}
                else:
                    reasons.append('semantic_donor_missing')
                pool = [r for r in roots if r['life'] == life and r['query'] == query]
                if len(pool) != 4 or len({r['root_id'] for r in pool}) != 4:
                    reasons.append('own_history_root_roster')
                retained = []
                for root in pool:
                    root_issues, selected = list(reasons), []
                    if donor is not None:
                        for suffix in range(4):
                            triple = []
                            for mode in ('H2', donor['candidate_id']+'_A', donor['candidate_id']+'_B'):
                                key = donor['heldout_life'], root['root_id'], suffix, mode
                                if counts[key] != 1:
                                    root_issues.append('missing_or_duplicate_branch_metadata')
                                else:
                                    triple.append(indexed[key]); selected.append(indexed[key])
                            if len(triple) == 3 and len({row['seed'] for row in triple}) != 1:
                                root_issues.append('paired_seed_metadata_mismatch')
                    retained.append({'root_id': root['root_id'], 'life': life, 'query': query,
                                     'branches': selected, 'complete': not root_issues, 'issues': sorted(set(root_issues))})
                    all_issues.extend(root_issues)
                histories.append({'life': life, 'donor': donor, 'roots': retained, 'complete': not reasons and all(r['complete'] for r in retained)})
                all_issues.extend(reasons)
            strata.append({'stratum_id': f'S{len(strata)}', 'query': query, **union_item, 'histories': histories,
                           'complete': all(h['complete'] for h in histories)})
    references = [b for s in strata for h in s['histories'] for r in h['roots'] for b in r['branches']]
    return {'strata': strata, 'complete': not all_issues,
            'counts': {'semantic_strata': len(strata), 'semantic_roots': sum(len(h['roots']) for s in strata for h in s['histories']),
                       'logical_triplets': len(references)//3, 'logical_branch_references': len(references),
                       'unique_physical_branch_rows': len({_coordinate(b) for b in references})}, 'issues': sorted(set(all_issues))}


def _read_triplets(roster, rows):
    counts = Counter(_coordinate(r) for r in rows)
    indexed = {_coordinate(r): r for r in rows}
    triples, issues = {}, []
    for stratum in roster['strata']:
        for history in stratum['histories']:
            for root in history['roots']:
                source, problems = {}, list(root['issues'])
                for plan in root['branches']:
                    key = _coordinate(plan)
                    if counts[key] != 1:
                        problems.append('missing_or_duplicate_outcome'); continue
                    row = indexed[key]
                    arm = 'H2' if row['mode'] == 'H2' else row['mode'].rsplit('_', 1)[1]
                    source.setdefault(row['suffix'], {})[arm] = row
                    if row['seed'] != plan['seed'] or row['query'] != stratum['query']:
                        problems.append('outcome_identity_mismatch')
                    if row['status'] not in ('WON', 'LOST') or row['utility'] is None:
                        problems.append('nonterminal_outcome')
                    elif not math.isclose(row['utility'], _utility(row['components'], stratum['query']), abs_tol=1e-10):
                        problems.append('utility_vector_mismatch')
                    if (row['components'][1:] != [float(row['status'] == 'LOST'), float(row['status'] == 'WON')]
                            or not math.isclose(row['components'][0], row['score']/2048., abs_tol=1e-10)):
                        problems.append('terminal_vector_mismatch')
                for suffix in range(4):
                    group = source.get(suffix, {})
                    if set(group) != {'A', 'B', 'H2'}:
                        problems.append('incomplete_triplet'); continue
                    a, b = group['A'], group['B']
                    if a['module']['predicate'] != b['module']['predicate']:
                        problems.append('predicate_mismatch')
                    if a['module']['predicate'] is None:
                        terminal = ('score', 'steps', 'status', 'components', 'utility')
                        path = ('actual_word', 'actual_probe', 'prefix_steps', 'attempts', 'exit_reason', 'exit_step')
                        if any(a[k] != b[k] for k in terminal) or any(a['module'][k] != b['module'][k] for k in path):
                            problems.append('none_path_or_outcome_mismatch')
                triples[(stratum['stratum_id'], root['root_id'])] = source
                issues.extend((stratum['stratum_id'], root['root_id'], problem) for problem in sorted(set(problems)))
    return triples, issues


def _difference(left, right, query):
    reward, failure, success = [a-b for a, b in zip(left['components'], right['components'])]
    weight = 1 if query == 'risk1' else 8
    risk = weight*(success-failure)
    utility = reward+risk
    return dict(zip(METRICS, [utility, reward, failure, success, reward, -weight*failure, weight*success, risk]),
                component_delta=[reward, failure, success], utility_discordant=utility != 0., failure_discordant=failure != 0.,
                terminal_discordant=left['status'] != right['status'], utility_failure_preference_discordant=utility*failure > 0.)


def _moments(values):
    mean = _mean(values)
    variance = math.fsum((v-mean)**2 for v in values)/(len(values)-1)
    return {'n': len(values), 'complete': True, 'mean': mean, 'sample_variance': variance, 'mean_variance': variance/len(values)}


def _pool(values):
    mean = _mean([v['mean'] for v in values])
    variance = math.fsum(v['mean_variance'] for v in values)/len(values)**2
    se = math.sqrt(variance)
    return {'complete': True, 'mean': mean, 'mean_variance': variance,
            'conditional_suffix_se': se, 'conditional_suffix_ci95': [mean-1.96*se, mean+1.96*se]}


def _decomposition(differences):
    rewards, risks, utilities = [[d[k] for d in differences] for k in ('reward_effect', 'risk_effect', 'utility')]
    mr, mk = _mean(rewards), _mean(risks)
    rv = _moments(rewards)['sample_variance']; kv = _moments(risks)['sample_variance']; uv = _moments(utilities)['sample_variance']
    covariance = math.fsum((r-mr)*(k-mk) for r, k in zip(rewards, risks))/(len(rewards)-1)
    n = len(rewards)
    return {'n': n, 'complete': True, 'utility_sample_variance': uv, 'reward_sample_variance': rv,
            'risk_sample_variance': kv, 'reward_risk_sample_covariance': covariance, 'utility_mean_variance': uv/n,
            'reward_mean_variance': rv/n, 'risk_mean_variance': kv/n, 'reward_risk_mean_covariance': covariance/n}


def _pool_decomposition(values):
    keys = ('utility_mean_variance', 'reward_mean_variance', 'risk_mean_variance', 'reward_risk_mean_covariance')
    return {'complete': True, **{k: math.fsum(v[k] for v in values)/len(values)**2 for k in keys}}


def _sign(value):
    return 1 if value > 0 else -1 if value < 0 else 0


def _discordance(pairs, contrast):
    keys = ('utility_discordant', 'failure_discordant', 'terminal_discordant', 'utility_failure_preference_discordant')
    return {'pairs': len(pairs), 'complete': True,
            **{key: sum(pair['contrasts'][contrast][key] for pair in pairs) for key in keys}}


def _pool_discordance(values):
    keys = ('pairs', 'utility_discordant', 'failure_discordant', 'terminal_discordant', 'utility_failure_preference_discordant')
    return {'complete': True, **{key: sum(v[key] for v in values) for key in keys}}


def _rank_comparison(first, second):
    a, b = _sign(first), _sign(second)
    return {'complete': True, 'half01_mean': first, 'half23_mean': second, 'half01_sign': a, 'half23_sign': b,
            'sign_flip': a*b < 0, 'tie_change': a != b and (a == 0 or b == 0), 'sign_change': a != b}


def _stability(groups):
    first = {(r['stratum_id'], r['root_id']): r for r in groups['half01']['root_rows']}
    second = {(r['stratum_id'], r['root_id']): r for r in groups['half23']['root_rows']}
    full = {(r['stratum_id'], r['root_id']): r for r in groups['full03']['root_rows']}
    roots = []
    for key, row in first.items():
        roots.append({k: row[k] for k in ('stratum_id', 'root_id', 'life', 'query')} |
                     {'contrasts': {contrast: _rank_comparison(row['contrasts'][contrast]['utility']['mean'],
                                                               second[key]['contrasts'][contrast]['utility']['mean']) for contrast in CONTRASTS},
                      'discordance': full[key]['discordance']})
    second_histories = {(s['stratum_id'], s['contrast'], h['life']): h for s in groups['half23']['stratum_summaries'] for h in s['per_history']}
    histories = []
    for summary in groups['half01']['stratum_summaries']:
        for history in summary['per_history']:
            other = second_histories[(summary['stratum_id'], summary['contrast'], history['life'])]
            selected = [r['contrasts'][summary['contrast']] for r in roots if r['stratum_id'] == summary['stratum_id'] and r['life'] == history['life']]
            histories.append({'stratum_id': summary['stratum_id'], 'query': summary['query'], 'life': history['life'],
                              'contrast': summary['contrast'], **_rank_comparison(history['metrics']['utility']['mean'], other['metrics']['utility']['mean']),
                              **{f'root_{plural}': sum(r[singular] for r in selected) for plural, singular in
                                 [('sign_flips', 'sign_flip'), ('tie_changes', 'tie_change'), ('sign_changes', 'sign_change')]}})
    strata = []
    for summary in groups['half01']['stratum_summaries']:
        selected = [h for h in histories if h['stratum_id'] == summary['stratum_id'] and h['contrast'] == summary['contrast']]
        strata.append({'stratum_id': summary['stratum_id'], 'query': summary['query'], 'contrast': summary['contrast'], 'complete': True,
                       'history_sign_flips': sum(h['sign_flip'] for h in selected), 'history_tie_changes': sum(h['tie_change'] for h in selected),
                       'root_sign_flips': sum(h['root_sign_flips'] for h in selected), 'root_tie_changes': sum(h['root_tie_changes'] for h in selected)})
    return {'root_rows': roots, 'history_rows': histories, 'stratum_rows': strata}


def independent_evaluate(roster, rows):
    triples, issues = _read_triplets(roster, rows)
    if not roster['complete'] or issues:
        return {'complete': False, 'issues': issues, 'groups': {}}
    groups = {}
    for name, suffixes in GROUPS.items():
        root_rows = []
        for stratum in roster['strata']:
            for history in stratum['histories']:
                for root in history['roots']:
                    source = triples[(stratum['stratum_id'], root['root_id'])]
                    trials = []
                    for suffix in suffixes:
                        triple = source[suffix]
                        trials.append({'suffix': suffix, 'outcomes': {arm: {k: row[k] for k in ('branch_id', 'seed', 'score', 'steps', 'status', 'components', 'utility', 'module')}
                                                                     for arm, row in triple.items()},
                                       'contrasts': {label: _difference(triple[left], triple[right], stratum['query'])
                                                     for label, (left, right) in CONTRASTS.items()}})
                    contrasts = {label: {metric: _moments([t['contrasts'][label][metric] for t in trials]) for metric in METRICS}
                                 for label in CONTRASTS}
                    decomposition = {label: _decomposition([t['contrasts'][label] for t in trials]) for label in CONTRASTS}
                    root_rows.append({'stratum_id': stratum['stratum_id'], 'root_id': root['root_id'], 'life': root['life'],
                                      'query': stratum['query'], 'pairs': trials, 'contrasts': contrasts, 'variance_decomposition': decomposition,
                                      'discordance': {label: _discordance(trials, label) for label in CONTRASTS}})
        summaries = []
        for stratum in roster['strata']:
            for label in CONTRASTS:
                histories = []
                for life in LIVES:
                    selected = [r for r in root_rows if r['stratum_id'] == stratum['stratum_id'] and r['life'] == life]
                    histories.append({'life': life, 'roots': 4,
                                      'metrics': {metric: _pool([r['contrasts'][label][metric] for r in selected]) for metric in METRICS},
                                      'variance_decomposition': _pool_decomposition([r['variance_decomposition'][label] for r in selected]),
                                      'discordance': _pool_discordance([r['discordance'][label] for r in selected])})
                summaries.append({'stratum_id': stratum['stratum_id'], 'query': stratum['query'], 'contrast': label,
                                  'roots': 16, 'complete': True, 'metrics': {metric: _pool([h['metrics'][metric] for h in histories]) for metric in METRICS},
                                  'variance_decomposition': _pool_decomposition([h['variance_decomposition'] for h in histories]),
                                  'discordance': _pool_discordance([h['discordance'] for h in histories]), 'per_history': histories})
        groups[name] = {'suffixes': list(suffixes), 'root_rows': root_rows, 'stratum_summaries': summaries}
    return {'complete': True, 'issues': [], 'groups': groups, 'stability': _stability(groups)}


def audit(candidates, programs, roots, branches, rows, retained_roster, result):
    roster = independent_roster(candidates, programs, roots, branches)
    expected = independent_evaluate(roster, rows)
    checks = []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
    check('complete_semantic_roster', roster['complete'])
    check('physical_logical_counts', _equal(retained_roster.get('counts'), roster['counts']))
    check('complete_source_outcomes', expected['complete'])
    check('production_complete', result.get('complete') == expected['complete'])
    check('embedded_roster', _equal(result.get('roster'), retained_roster))
    check('zero_new_environment_or_updates', all(result.get(k) == 0 for k in ('new_environment_samples', 'new_model_samples', 'native_planner_calls', 'real_training_updates')))
    check('all_strata_retained', len(retained_roster.get('strata', [])) == len(roster['strata']))
    for stratum, actual in zip(roster['strata'], retained_roster.get('strata', [])):
        projection = {k: stratum[k] for k in ('stratum_id', 'query', 'source_semantics', 'selected_by')}
        check(f"metadata:{stratum['stratum_id']}", _equal(actual, projection))
        for history, got in zip(stratum['histories'], actual.get('histories', [])):
            check(f"donor_roots:{stratum['stratum_id']}:{history['life']}", _equal(got, {k: history[k] for k in ('life', 'donor')}) and
                  _equal(got.get('roots'), [{k: r[k] for k in ('root_id', 'life', 'query', 'branches', 'complete')} for r in history['roots']]))
    if expected['complete']:
        for name, group in expected['groups'].items():
            actual = result['groups'][name]
            check(f'{name}:fixed_suffixes', _equal(actual.get('suffixes'), group['suffixes']))
            expected_roots = {(r['stratum_id'], r['root_id']): r for r in group['root_rows']}
            actual_roots = {(r['stratum_id'], r['root_id']): r for r in actual['root_rows']}
            check(f'{name}:full_root_roster', len(actual['root_rows']) == len(expected_roots) and set(actual_roots) == set(expected_roots))
            for key, root in expected_roots.items():
                check(f'{name}:root:{key[0]}:{key[1]}', _equal(actual_roots.get(key), root))
            check(f'{name}:stratum_summaries', _equal(actual.get('stratum_summaries'), group['stratum_summaries']))
            check(f'{name}:no_unpaired_query_ci', not actual.get('query_summaries'))
        actual_stability = result.get('stability', {})
        for kind, fields in [('root_rows', ('stratum_id', 'root_id')), ('history_rows', ('stratum_id', 'life', 'contrast')),
                             ('stratum_rows', ('stratum_id', 'contrast'))]:
            actual_rows = actual_stability.get(kind, [])
            actual_by_key = {tuple(row[k] for k in fields): row for row in actual_rows}
            expected_by_key = {tuple(row[k] for k in fields): row for row in expected['stability'][kind]}
            check(f'all_rank_stability:{kind}', len(actual_rows) == len(expected_by_key) and set(actual_by_key) == set(expected_by_key)
                  and all(_equal(actual_by_key[key], row) for key, row in expected_by_key.items()))
    return {'schema': 'acfqp.program_ranking.v166.audit', 'valid': all(c['passed'] for c in checks),
            'checks': checks, 'passed_checks': sum(c['passed'] for c in checks), 'total_checks': len(checks),
            'issues': expected['issues'], 'new_environment_samples': 0, 'real_training_updates': 0}


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'roster', 'result', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    read = lambda name: json.loads((args.source/name).read_text())
    candidates, programs, roots, inputs = [read(n) for n in ('generated_candidates.json', 'frozen_programs.json', 'train_roots.json', 'screening_inputs.json')]
    roster = independent_roster(candidates, programs, roots, inputs['branch_roster'])
    wanted = {_coordinate(b) for s in roster['strata'] for h in s['histories'] for r in h['roots'] for b in r['branches']}
    rows = [r for life in LIVES for r in read(f'screening/life_{life}/outcomes.json') if _coordinate(r) in wanted]
    checked = audit(candidates, programs, roots, inputs['branch_roster'], rows,
                    json.loads(args.roster.read_text()), json.loads(args.result.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(checked, indent=2)+'\n')
    print(json.dumps({'valid': checked['valid'], 'passed': checked['passed_checks'], 'checks': checked['total_checks']}))
    raise SystemExit(0 if checked['valid'] else 1)


if __name__ == '__main__':
    main()
