"""Paired reward/risk ranking noise on retained V164 semantic strata."""
from collections import Counter
from copy import deepcopy
from math import sqrt

from .controlled_predictive_policy_modules_v151 import QUERIES, utility
from .controlled_predictive_program_headroom_v165 import semantic_key

LIVES = (0, 1, 2, 3)
SUFFIXES = (0, 1, 2, 3)
GROUPS = dict(half01=(0, 1), half23=(2, 3), full03=SUFFIXES)
CONTRASTS = {'A-B': ('A', 'B'), 'A-H2': ('A', 'H2'), 'B-H2': ('B', 'H2')}
METRICS = ('utility', 'reward', 'failure', 'success', 'reward_effect', 'failure_effect', 'success_effect', 'risk_effect')
SEMANTIC_FIELDS = ('first_action', 'probe_action', 'true_suffix', 'false_suffix')
OUTCOME_FIELDS = ('score', 'steps', 'status', 'components', 'utility')
NONE_PATH_FIELDS = ('actual_word', 'actual_probe', 'prefix_steps', 'attempts', 'exit_reason', 'exit_step')
DISCORDANCE = ('utility_discordant', 'failure_discordant', 'terminal_discordant', 'utility_failure_preference_discordant')
DECOMPOSITION = ('utility', 'reward', 'risk')


def _issue(issues, name):
    if name not in issues:
        issues.append(name)


def _coordinate(row):
    return row['heldout_life'], row['root_id'], row['suffix'], row['mode']


def build_roster(candidates, programs, roots, screen_roster):
    """Union selected original semantics; freeze first matching donor metadata."""
    candidate_cells = {(cell['heldout_life'], cell['query']): cell for cell in candidates}
    program_cells = {(cell['heldout_life'], cell['query']): cell for cell in programs}
    index, duplicates = {}, set()
    for branch in screen_roster:
        key = _coordinate(branch)
        if key in index:
            duplicates.add(key)
        index[key] = branch
    work = Counter(metadata_branches_indexed=len(screen_roster), semantic_candidates_examined=0,
                   metadata_branch_lookups=0)
    strata = []
    for query in QUERIES:
        seen = {}
        for life in LIVES:
            frozen = program_cells.get((life, query), {}).get('programs', {}).get('LEARNED')
            selected_id = None if frozen is None else frozen['candidate_id']
            source = next((candidate for candidate in candidate_cells.get((life, query), {}).get('candidates', [])
                           if candidate['candidate_id'] == selected_id), None)
            available = source is not None and all(field in source for field in SEMANTIC_FIELDS)
            key = semantic_key(source) if available else None
            if available and key in seen:
                stratum = seen[key]
            else:
                stratum = dict(stratum_id=f'S{len(strata)}', query=query,
                    source_semantics=None if not available else {field: deepcopy(source[field]) for field in SEMANTIC_FIELDS},
                    selected_by=[], histories=[], issues=[] if available else ['selected_source_semantics_missing'])
                strata.append(stratum)
                if available:
                    seen[key] = stratum
            stratum['selected_by'].append(dict(target_life=life, candidate_id=selected_id))
    for stratum in strata:
        query, source = stratum['query'], stratum['source_semantics']
        for life in LIVES:
            issues, donor = list(stratum['issues']), None
            if source is not None:
                for fold in LIVES:
                    if fold == life:
                        continue
                    for position, candidate in enumerate(candidate_cells.get((fold, query), {}).get('candidates', [])):
                        work['semantic_candidates_examined'] += 1
                        if all(field in candidate for field in SEMANTIC_FIELDS) and semantic_key(candidate) == semantic_key(source):
                            donor = dict(heldout_life=fold, candidate_id=candidate['candidate_id'], candidate_position=position)
                            break
                    if donor is not None:
                        break
                if donor is None:
                    _issue(issues, 'semantic_donor_missing')
            pool = [root for root in roots if (root['life'], root['query']) == (life, query)]
            if len(pool) != 4 or len({root['root_id'] for root in pool}) != 4:
                _issue(issues, 'own_history_root_roster')
            retained = []
            for root in pool:
                item = {key: deepcopy(value) for key, value in root.items() if key != 'board'}
                item.update(branches=[], issues=list(issues))
                if donor is not None:
                    for suffix in SUFFIXES:
                        triple = []
                        for mode in ('H2', donor['candidate_id']+'_A', donor['candidate_id']+'_B'):
                            key = donor['heldout_life'], root['root_id'], suffix, mode
                            work['metadata_branch_lookups'] += 1
                            branch = index.get(key)
                            if branch is None:
                                _issue(item['issues'], 'missing_branch_metadata')
                            elif key in duplicates:
                                _issue(item['issues'], 'duplicate_branch_metadata')
                            if branch is not None:
                                triple.append(branch)
                                item['branches'].append(deepcopy(branch))
                        if len(triple) == 3 and len({branch['seed'] for branch in triple}) != 1:
                            _issue(item['issues'], 'paired_seed_metadata_mismatch')
                item['complete'] = not item['issues']
                retained.append(item)
            stratum['histories'].append(dict(life=life, donor=donor, roots=retained, issues=issues,
                complete=not issues and all(root['complete'] for root in retained)))
        stratum['complete'] = not stratum['issues'] and all(history['complete'] for history in stratum['histories'])
    retained = [root for stratum in strata for history in stratum['histories'] for root in history['roots']]
    references = [branch for root in retained for branch in root['branches']]
    counts = dict(semantic_strata=len(strata), strata_per_query={query: sum(s['query'] == query for s in strata) for query in QUERIES},
        semantic_roots=len(retained), unique_root_states=len({root['root_id'] for root in retained}),
        logical_triplets=len(retained)*4, logical_branch_references=len(retained)*12,
        present_branch_references=len(references), unique_physical_branch_rows=len({branch['branch_id'] for branch in references}))
    return dict(schema='acfqp.program_ranking.v166.roster', strata=strata, counts=counts,
        complete=bool(strata) and all(stratum['complete'] for stratum in strata), logical_work=dict(work))


def _mean(values):
    values = tuple(values)
    return sum(values)/len(values)


def _moments(values):
    values = tuple(values)
    complete = bool(values) and all(value is not None for value in values)
    average = _mean(values) if complete else None
    variance = sum((value-average)**2 for value in values)/(len(values)-1) if complete and len(values)>1 else 0. if complete else None
    return dict(n=len(values), complete=complete, mean=average, sample_variance=variance,
                mean_variance=variance/len(values) if complete else None)


def _pool(stats, expected):
    complete = len(stats) == expected and all(row['complete'] for row in stats)
    average = _mean(row['mean'] for row in stats) if complete else None
    variance = sum(row['mean_variance'] for row in stats)/expected**2 if complete else None
    se = sqrt(variance) if complete else None
    return dict(complete=complete, mean=average, mean_variance=variance, conditional_suffix_se=se,
                conditional_suffix_ci95=None if se is None else [average-1.96*se, average+1.96*se])


def _sign(value):
    return None if value is None else 1 if value > 0 else -1 if value < 0 else 0


def _validated_roots(roster, outcomes, work):
    index, duplicates = {}, set()
    for row in outcomes:
        key = _coordinate(row)
        if key in index:
            duplicates.add(key)
        index[key] = row
    result = []
    for stratum in roster['strata']:
        for history in stratum['histories']:
            for root in history['roots']:
                issues, triples = list(root['issues']), {}
                plans = {(row['suffix'], row['mode']): row for row in root['branches']}
                if history['donor'] is not None:
                    donor = history['donor']
                    for suffix in SUFFIXES:
                        work['logical_triplets_examined'] += 1
                        triple = {}
                        for arm, mode in (('H2', 'H2'), ('A', donor['candidate_id']+'_A'), ('B', donor['candidate_id']+'_B')):
                            key = donor['heldout_life'], root['root_id'], suffix, mode
                            row, plan = index.get(key), plans.get((suffix, mode))
                            if row is None:
                                _issue(issues, 'missing_outcome')
                            elif key in duplicates:
                                _issue(issues, 'duplicate_outcome')
                            if row is not None:
                                triple[arm] = row
                                if plan is None or row['seed'] != plan['seed']:
                                    _issue(issues, 'outcome_seed_mismatch')
                                if row['status'] not in ('WON', 'LOST') or row['utility'] is None:
                                    _issue(issues, 'nonterminal_outcome')
                                else:
                                    if row['utility'] != utility(row['components'], root['query']):
                                        _issue(issues, 'recorded_utility_mismatch')
                                    if row['components'][0] != row['score']/2048. or row['components'][1:] != [float(row['status'] == 'LOST'), float(row['status'] == 'WON')]:
                                        _issue(issues, 'terminal_component_mismatch')
                        triples[suffix] = triple
                        if len(triple) != 3:
                            continue
                        a, b = triple['A'], triple['B']
                        predicate = a['module']['predicate']
                        if predicate != b['module']['predicate']:
                            _issue(issues, 'predicate_mismatch')
                        if predicate is None and any(a[key] != b[key] for key in OUTCOME_FIELDS):
                            _issue(issues, 'none_outcome_mismatch')
                        if predicate is None and any(a['module'][key] != b['module'][key] for key in NONE_PATH_FIELDS):
                            _issue(issues, 'none_path_mismatch')
                result.append(dict(stratum_id=stratum['stratum_id'], query=stratum['query'], life=history['life'],
                    root=root, donor=history['donor'], triples=triples, issues=issues,
                    complete=not issues and len(triples) == 4))
    return result


def _contrast(left, right, query):
    reward, failure, success = [x-y for x, y in zip(left['components'], right['components'], strict=True)]
    weights = QUERIES[query]
    reward_effect = weights['reward_weight']*reward
    failure_effect = -weights['failure_penalty']*failure
    success_effect = weights['goal_bonus']*success
    value = utility([reward, failure, success], query)
    return dict(utility=value, reward=reward, failure=failure, success=success,
        reward_effect=reward_effect, failure_effect=failure_effect, success_effect=success_effect,
        risk_effect=failure_effect+success_effect, component_delta=[reward, failure, success],
        utility_discordant=value != 0, failure_discordant=failure != 0,
        terminal_discordant=left['status'] != right['status'],
        utility_failure_preference_discordant=value*(-failure) < 0)


def _decomposition(trials, contrast, complete):
    n = len(trials)
    result = dict(n=n, complete=complete)
    values = {name: [trial['contrasts'][contrast]['utility' if name == 'utility' else name+'_effect'] for trial in trials]
              for name in DECOMPOSITION} if complete else {}
    for name in DECOMPOSITION:
        stats = _moments(values[name]) if complete else _moments([None]*n)
        result[name+'_sample_variance'] = stats['sample_variance']
        result[name+'_mean_variance'] = stats['mean_variance']
    covariance = sum((a-_mean(values['reward']))*(b-_mean(values['risk']))
                     for a, b in zip(values['reward'], values['risk'], strict=True))/(n-1) if complete else None
    result.update(reward_risk_sample_covariance=covariance,
                  reward_risk_mean_covariance=None if covariance is None else covariance/n)
    return result


def _decomposition_pool(rows, expected):
    complete = len(rows) == expected and all(row['complete'] for row in rows)
    return dict(complete=complete, **{key: sum(row[key] for row in rows)/expected**2 if complete else None
        for key in [name+'_mean_variance' for name in DECOMPOSITION]+['reward_risk_mean_covariance']})


def _counts(trials, contrast, complete):
    return dict(pairs=len(trials), complete=complete,
                **{key: sum(trial['contrasts'][contrast][key] for trial in trials) if complete else None for key in DISCORDANCE})


def _count_pool(rows):
    complete = bool(rows) and all(row['complete'] for row in rows)
    return dict(pairs=sum(row['pairs'] for row in rows), complete=complete,
                **{key: sum(row[key] for row in rows) if complete else None for key in DISCORDANCE})


def _group(roster, validated, suffixes, work):
    root_rows = []
    for item in validated:
        trials = []
        for suffix in suffixes:
            triple = item['triples'].get(suffix, {})
            raw = {arm: {key: deepcopy(row[key]) for key in ('branch_id', 'seed', *OUTCOME_FIELDS, 'module')}
                   for arm, row in triple.items()}
            contrasts = {name: _contrast(triple[left], triple[right], item['query'])
                         for name, (left, right) in CONTRASTS.items()} if item['complete'] else {}
            trials.append(dict(suffix=suffix, outcomes=raw, contrasts=contrasts))
            work['logical_contrast_vectors'] += len(contrasts)
        stats = {name: {key: _moments(trial['contrasts'][name][key] for trial in trials)
                       if item['complete'] else _moments([None]*len(suffixes)) for key in METRICS} for name in CONTRASTS}
        root_rows.append(dict(stratum_id=item['stratum_id'], root_id=item['root']['root_id'],
            life=item['life'], query=item['query'], donor=deepcopy(item['donor']), complete=item['complete'],
            issues=list(item['issues']), pairs=trials, contrasts=stats,
            variance_decomposition={name: _decomposition(trials, name, item['complete']) for name in CONTRASTS},
            discordance={name: _counts(trials, name, item['complete']) for name in CONTRASTS}))
    summaries = []
    for stratum in roster['strata']:
        pool = [row for row in root_rows if row['stratum_id'] == stratum['stratum_id']]
        for contrast in CONTRASTS:
            histories = []
            for life in LIVES:
                selected = [row for row in pool if row['life'] == life]
                histories.append(dict(life=life, roots=len(selected),
                    metrics={key: _pool([row['contrasts'][contrast][key] for row in selected], 4) for key in METRICS},
                    variance_decomposition=_decomposition_pool([row['variance_decomposition'][contrast] for row in selected], 4),
                    discordance=_count_pool([row['discordance'][contrast] for row in selected])))
            metrics = {key: _pool([history['metrics'][key] for history in histories], 4) for key in METRICS}
            summaries.append(dict(stratum_id=stratum['stratum_id'], query=stratum['query'], contrast=contrast,
                roots=len(pool), complete=all(metric['complete'] for metric in metrics.values()), metrics=metrics,
                variance_decomposition=_decomposition_pool([history['variance_decomposition'] for history in histories], 4),
                discordance=_count_pool([history['discordance'] for history in histories]), per_history=histories))
    return dict(suffixes=list(suffixes), root_rows=root_rows, stratum_summaries=summaries,
                complete=all(summary['complete'] for summary in summaries))


def _sign_comparison(first, second):
    a, b = _sign(first), _sign(second)
    complete = a is not None and b is not None
    return dict(complete=complete, half01_mean=first, half23_mean=second, half01_sign=a, half23_sign=b,
        sign_flip=a*b < 0 if complete else None, tie_change=(a == 0) != (b == 0) if complete else None,
        sign_change=a != b if complete else None)


def _stability(groups, roster):
    roots = []
    halves = [{(row['stratum_id'], row['root_id']): row for row in groups[name]['root_rows']} for name in ('half01', 'half23')]
    for row in groups['full03']['root_rows']:
        key = row['stratum_id'], row['root_id']
        roots.append(dict(stratum_id=row['stratum_id'], root_id=row['root_id'], life=row['life'], query=row['query'],
            contrasts={name: _sign_comparison(halves[0][key]['contrasts'][name]['utility']['mean'],
                                              halves[1][key]['contrasts'][name]['utility']['mean']) for name in CONTRASTS},
            discordance=deepcopy(row['discordance'])))
    summaries = [{(row['stratum_id'], row['contrast']): row for row in groups[name]['stratum_summaries']} for name in ('half01', 'half23')]
    histories, strata = [], []
    for stratum in roster['strata']:
        for contrast in CONTRASTS:
            for life in LIVES:
                first, second = [next(history for history in summary[stratum['stratum_id'], contrast]['per_history']
                                      if history['life'] == life) for summary in summaries]
                selected = [row['contrasts'][contrast] for row in roots
                            if (row['stratum_id'], row['life']) == (stratum['stratum_id'], life)]
                complete = len(selected) == 4 and all(row['complete'] for row in selected)
                histories.append(dict(stratum_id=stratum['stratum_id'], query=stratum['query'], life=life,
                    contrast=contrast, **_sign_comparison(first['metrics']['utility']['mean'], second['metrics']['utility']['mean']),
                    root_sign_flips=sum(row['sign_flip'] for row in selected) if complete else None,
                    root_tie_changes=sum(row['tie_change'] for row in selected) if complete else None,
                    root_sign_changes=sum(row['sign_change'] for row in selected) if complete else None))
            selected = [row for row in histories if (row['stratum_id'], row['contrast']) == (stratum['stratum_id'], contrast)]
            complete = all(row['complete'] and row['root_sign_flips'] is not None for row in selected)
            strata.append(dict(stratum_id=stratum['stratum_id'], query=stratum['query'], contrast=contrast, complete=complete,
                history_sign_flips=sum(row['sign_flip'] for row in selected) if complete else None,
                history_tie_changes=sum(row['tie_change'] for row in selected) if complete else None,
                root_sign_flips=sum(row['root_sign_flips'] for row in selected) if complete else None,
                root_tie_changes=sum(row['root_tie_changes'] for row in selected) if complete else None))
    return dict(root_rows=roots, history_rows=histories, stratum_rows=strata)


def evaluate(roster, rows):
    """Decompose paired rankings on fixed halves; do not fit or adopt a policy."""
    work = Counter(outcome_rows_supplied=len(rows), logical_triplets_examined=0, logical_contrast_vectors=0)
    validated = _validated_roots(roster, rows, work)
    groups = {name: _group(roster, validated, suffixes, work) for name, suffixes in GROUPS.items()}
    return dict(schema='acfqp.program_ranking.v166.evaluation', roster=deepcopy(roster),
        complete=roster['complete'] and all(group['complete'] for group in groups.values()),
        groups=groups, stability=_stability(groups, roster), semantic_root_count=len(validated),
        complete_semantic_root_count=sum(root['complete'] for root in validated), logical_work=dict(work),
        new_environment_samples=0, new_model_samples=0, native_planner_calls=0, real_training_updates=0,
        uncertainty='Normal paired-suffix CI conditional on fixed roots and histories; equal four roots/history and four histories/stratum. Strata sharing H2 are not independent replications; no query aggregate CI.',
        interpretation='Retrospective reward/risk ranking decomposition; no new learner, policy selection, or adoption.')
