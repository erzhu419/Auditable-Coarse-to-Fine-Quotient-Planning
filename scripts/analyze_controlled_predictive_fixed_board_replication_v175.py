"""Independent audit of frozen-policy, fixed-board suffix replication."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import argparse
import gzip
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from scripts import analyze_controlled_predictive_utility_partition_v174 as previous
from scripts import analyze_controlled_predictive_consequence_partition_v172 as physical
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal, _mean

prior = physical.prior
ACTIONS = physical.ACTIONS
LIVES = range(4)
METRICS = ('utility', 'reward', 'failure', 'success')
COHORTS = ('TRAIN', 'FRESH')
BASE = 17500000000


def seed(phase, root, suffix):
    return BASE + {'TRAIN_REPL': 10000000, 'FRESH_REPL': 20000000}[phase] + root['life'] * 1000000 + root['ordinal'] * 1000 + suffix


def branch_roster(roots, frozen, phase):
    cohort = 'TRAIN' if phase == 'TRAIN_REPL' else 'FRESH'
    choices = {(row['cohort'], row['root_id']): row for row in frozen['choices']}
    rows = []
    for root in roots:
        if root['cohort'] != cohort:
            continue
        choice = choices[cohort, root['root_id']]
        if not choice['changed']:
            continue
        actuals = {row['canonical_action']: row['actual_action'] for row in root['actions']}
        actions = [choice['decisions'][mode]['canonical_action'] for mode in ('TREE', 'ONE')]
        for suffix in range(16):
            for action in actions:
                rows.append(dict(branch_id=f"{phase}:{root['root_id']}:{suffix}:{action}", phase=phase, cohort=cohort,
                    root_id=root['root_id'], life=root['life'], query='risk1', source_id=root['source_id'], ordinal=root['ordinal'],
                    suffix=suffix, seed=seed(phase, root, suffix), canonical_action=action, actual_action=actuals[action]))
    return rows


def utility(vector):
    return vector[0] - vector[1] + vector[2]


def supported_action(model, root, work):
    if model['life'] != root['life']:
        raise ValueError('root and model must use the same frozen history')
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    if not legal or len(legal) != len(root['legal_actions']):
        raise ValueError('distinct legal canonical actions required')
    local = Counter(selection_decisions=1, selection_legal_action_reads=len(legal))
    if model['mode'].startswith('PART_'):
        node = 0
        while True:
            row = model['nodes'][node]
            local['partition_node_lookups'] += 1
            if row['kind'] == 'leaf':
                leaf_id = row['leaf_id']; break
            local['partition_feature_threshold_tests'] += 1
            node = row['left'] if root['canonical_board'][row['cell']] <= row['threshold'] else row['right']
    else:
        local['partition_group_lookups'] += 1
        leaf_id = model['groups'].get('ALL')
    leaf = None
    for row in model['leaves']:
        local['selection_leaf_records_examined'] += 1
        if row['leaf_id'] == leaf_id:
            leaf = row; break
    action_counts = {action: len(leaf['action_root_ids'][action]) if leaf else 0 for action in legal}
    groups = leaf['connected_components'] if leaf else [[action] for action in ACTIONS]
    connected = any(set(legal) <= set(group) for group in groups)
    complete = leaf is not None and connected and all(count >= 4 for count in action_counts.values())
    support = dict(action_root_counts=action_counts, connected_components=deepcopy(groups), required_actions=legal,
        connected=connected, complete=complete)
    local.update(selection_action_support_lookups=len(legal), selection_component_membership_lookups=len(legal))
    chosen, predicted, best = None, {}, None
    if complete:
        for action in legal:
            vector = list(leaf['coefficients'][action]); vector[0] += root['immediate_rewards'][action]
            predicted[action] = vector; value = utility(vector)
            local.update(selection_coefficient_component_reads=3, selection_immediate_reward_reads=1, selection_utility_evaluations=1)
            if best is None or value > best + 1e-12:
                chosen, best = action, value
        reason = 'selected'
    else:
        reason = 'missing_partition_leaf' if leaf is None else 'insufficient_action_support' if min(action_counts.values()) < 4 else 'disconnected_required_actions'
    work.update(local)
    return dict(canonical_action=chosen, leaf=leaf_id, support=support, reason=reason, predicted_components=predicted, work=dict(local))


def freeze_selections(roots, models):
    choices, issues, work, seen = [], [], Counter(), set()
    for root in roots:
        identity = root['cohort'], root['root_id']
        if root['cohort'] not in COHORTS or root['life'] not in LIVES:
            raise ValueError('fixed TRAIN/FRESH cohorts and four histories required')
        if identity in seen:
            issues.append(f'duplicate_root:{identity}')
        seen.add(identity)
        decisions = {mode: supported_action(models[root['life']][mode], root, work) for mode in ('TREE', 'ONE')}
        complete = all(row['support']['complete'] for row in decisions.values())
        row = dict(cohort=root['cohort'], root_id=root['root_id'], life=root['life'], source_id=root['source_id'],
            canonical_board=list(root['canonical_board']), legal_actions=list(root['legal_actions']), immediate_rewards=deepcopy(root['immediate_rewards']),
            decisions=decisions, complete=complete, changed=False, old_suffix_differences=[], old_difference_components=None, reference_seeds=[])
        work['selection_roots'] += 1
        if not complete:
            issues.append(f'unsupported_policy:{identity}'); choices.append(row); continue
        tree, one = [decisions[mode]['canonical_action'] for mode in ('TREE', 'ONE')]
        row['changed'] = tree != one
        trials = sorted(root['reference_trials'], key=lambda trial: trial['suffix'])
        if len(trials) != 4 or [trial['suffix'] for trial in trials] != list(range(4)):
            raise ValueError('four distinct frozen reference suffixes required')
        for trial in trials:
            row['reference_seeds'].append(trial['seed']); work['reference_trials_read'] += 1
            if row['changed']:
                left, right = trial['action_components'][tree], trial['action_components'][one]
                if len(left) != 3 or len(right) != 3:
                    raise ValueError('complete reference terminal vectors required')
                vector = [float(a) - float(b) for a, b in zip(left, right)]
                work.update(reference_terminal_vector_reads=2, reference_component_subtractions=3)
            else:
                vector = [0., 0., 0.]; work['reference_same_action_suffixes_zeroed'] += 1
            row['old_suffix_differences'].append(dict(suffix=trial['suffix'], components=vector))
        row['old_difference_components'] = [_mean([trial['components'][k] for trial in row['old_suffix_differences']]) for k in range(3)]
        choices.append(row)
    return dict(schema='acfqp.fixed_board_replication.v175', choices=choices, complete=not issues, issues=issues, work=dict(work))


def _moments(values, suffix_variance):
    mean = _mean(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / ((len(values) - 1) * len(values))
    error = math.sqrt(variance)
    suffix_error = math.sqrt(suffix_variance)
    return dict(mean=mean, source_mean_variance=variance, conditional_source_se=error,
        conditional_source_ci95=[mean - 1.96 * error, mean + 1.96 * error], conditional_suffix_mean_variance=suffix_variance,
        conditional_suffix_se=suffix_error, conditional_suffix_ci95=[mean - 1.96 * suffix_error, mean + 1.96 * suffix_error])


def _pool(histories):
    metrics = {}
    for metric in METRICS:
        means = [row['metrics'][metric]['mean'] for row in histories]
        variance = math.fsum(row['metrics'][metric]['source_mean_variance'] for row in histories) / 16.
        suffix_variance = math.fsum(row['metrics'][metric]['conditional_suffix_mean_variance'] for row in histories) / 16.
        mean, error = _mean(means), math.sqrt(variance)
        suffix_error = math.sqrt(suffix_variance)
        metrics[metric] = dict(mean=mean, source_mean_variance=variance, conditional_source_se=error,
            conditional_source_ci95=[mean - 1.96 * error, mean + 1.96 * error], conditional_suffix_mean_variance=suffix_variance,
            conditional_suffix_se=suffix_error, conditional_suffix_ci95=[mean - 1.96 * suffix_error, mean + 1.96 * suffix_error])
    return metrics


def _comparison(cohort, roots, field, work):
    groups = {}
    for root in roots:
        if root['cohort'] == cohort:
            groups.setdefault((root['life'], root['source_id']), []).append(root)
    clusters, histories = [], []
    for life in LIVES:
        local = []
        for (history, source), rows in sorted(groups.items()):
            if history != life:
                continue
            vector = [_mean([row[field][k] for row in rows]) for k in range(3)]
            suffix_variances = {metric: 0. if field=='old_difference_components' else math.fsum(row['suffix_mean_variances'][metric] for row in rows)/len(rows)**2 for metric in METRICS}
            local.append(dict(life=life, source_id=source, roots=len(rows), metrics=dict(zip(METRICS, [utility(vector), *vector])),
                conditional_suffix_mean_variance=suffix_variances))
            work.update(source_root_component_reads=3 * len(rows), source_cluster_vector_means=1)
            work['conditional_suffix_source_variance_aggregations'] += 4
            if field!='old_difference_components':
                work['root_suffix_mean_variance_reads'] += 4*len(rows)
        clusters.extend(local)
        histories.append(dict(life=life, source_clusters=len(local), metrics={metric: _moments([row['metrics'][metric] for row in local],
            math.fsum(row['conditional_suffix_mean_variance'][metric] for row in local)/len(local)**2) for metric in METRICS}))
    return dict(complete=True, metrics=_pool(histories), per_history=histories, clusters=clusters)


def _cross_cohort(fresh, train):
    histories = []
    for a, b in zip(fresh['per_history'], train['per_history']):
        metrics = {}
        for metric in METRICS:
            mean = a['metrics'][metric]['mean'] - b['metrics'][metric]['mean']
            variance = a['metrics'][metric]['source_mean_variance'] + b['metrics'][metric]['source_mean_variance']
            suffix_variance = a['metrics'][metric]['conditional_suffix_mean_variance'] + b['metrics'][metric]['conditional_suffix_mean_variance']
            error = math.sqrt(variance)
            suffix_error = math.sqrt(suffix_variance)
            metrics[metric] = dict(mean=mean, source_mean_variance=variance, conditional_source_se=error,
                conditional_source_ci95=[mean - 1.96 * error, mean + 1.96 * error], conditional_suffix_mean_variance=suffix_variance,
                conditional_suffix_se=suffix_error, conditional_suffix_ci95=[mean - 1.96 * suffix_error, mean + 1.96 * suffix_error])
        histories.append(dict(life=a['life'], fresh_source_clusters=a['source_clusters'], train_source_clusters=b['source_clusters'], metrics=metrics))
    return dict(complete=True, contrast='FRESH-TRAIN', metrics=_pool(histories), per_history=histories)


def summarize_replication(frozen, outcomes, suffixes=16):
    if suffixes != 16:
        raise ValueError('sixteen frozen replication suffixes required')
    roots, outcomes, work = deepcopy(frozen['choices']), list(outcomes), Counter()
    issues = list(frozen['issues'])
    if not frozen['complete']:
        issues.append('incomplete_frozen_selection')
    lookup = {(row['cohort'], row['root_id']): row for row in roots}
    if len(lookup) != len(roots):
        issues.append('duplicate_frozen_root')
    for cohort in COHORTS:
        for life in LIVES:
            sources = {row['source_id'] for row in roots if row['cohort'] == cohort and row['life'] == life}
            if len(sources) != (12 if cohort == 'TRAIN' else 8):
                issues.append(f'source_roster_mismatch:{cohort}:{life}')
    for life in LIVES:
        source_groups = [{row['source_id'] for row in roots if row['cohort'] == cohort and row['life'] == life} for cohort in COHORTS]
        if source_groups[0] & source_groups[1]:
            issues.append(f'overlapping_cohort_sources:{life}')
    expected = {(root['cohort'], root['root_id'], suffix, root['decisions'][mode]['canonical_action']) for root in roots
        if root['complete'] and root['changed'] for suffix in range(16) for mode in ('TREE', 'ONE')}
    index = {}
    for row in outcomes:
        work['summary_outcome_rows_indexed'] += 1
        key = row['cohort'], row['root_id'], row['suffix'], row['canonical_action']
        if key in index:
            issues.append(f'duplicate_outcome:{key}')
        index[key] = row
        if key not in expected:
            issues.append(f'unexpected_outcome:{key}'); continue
        root = lookup[row['cohort'], row['root_id']]
        if (row['life'], row['source_id']) != (root['life'], root['source_id']):
            issues.append(f'outcome_metadata_mismatch:{key}')
        vector = row['components']
        if row['status'] not in ('WON', 'LOST'):
            issues.append(f'nonterminal_outcome:{key}')
        elif len(vector) != 3 or not all(math.isfinite(value) for value in vector) or vector[1:] != ([0, 1] if row['status'] == 'WON' else [1, 0]):
            issues.append(f'terminal_component_mismatch:{key}')
    missing = expected - set(index)
    if missing:
        issues.append(f'missing_outcomes:{len(missing)}')
    if not issues:
        for root in roots:
            if root['changed']:
                vectors, seeds = [], []
                for suffix in range(16):
                    a, b = [index[root['cohort'], root['root_id'], suffix, root['decisions'][mode]['canonical_action']] for mode in ('TREE', 'ONE')]
                    work['paired_suffix_seed_checks'] += 1
                    if a['seed'] != b['seed']:
                        issues.append(f'unpaired_suffix_seed:{root["cohort"]}:{root["root_id"]}:{suffix}')
                    if a['seed'] in root['reference_seeds'] or b['seed'] in root['reference_seeds']:
                        issues.append(f'reused_reference_seed:{root["cohort"]}:{root["root_id"]}:{suffix}')
                    seeds.append(a['seed']); vectors.append([x - y for x, y in zip(a['components'], b['components'])])
                    work.update(new_terminal_vector_reads=2, new_component_subtractions=3)
                if len(set(seeds)) != 16:
                    issues.append(f'repeated_replication_seed:{root["cohort"]}:{root["root_id"]}')
                root['new_difference_components'] = [_mean([vector[k] for vector in vectors]) for k in range(3)]
                metric_vectors = [[utility(vector), *vector] for vector in vectors]
                root['suffix_mean_variances'] = {}
                for k, metric in enumerate(METRICS):
                    values = [vector[k] for vector in metric_vectors]; mean = _mean(values)
                    root['suffix_mean_variances'][metric] = math.fsum((value-mean)**2 for value in values)/(16*15)
                work.update(suffix_root_metric_variances=4, suffix_utility_evaluations=16)
                work['new_root_vector_means'] += 1
            else:
                root['new_difference_components'] = [0., 0., 0.]; work['same_action_roots_zeroed'] += 1
                root['suffix_mean_variances'] = {metric: 0. for metric in METRICS}
            root['new_minus_old_components'] = [a - b for a, b in zip(root['new_difference_components'], root['old_difference_components'])]
            work['new_old_component_subtractions'] += 3
    diagnostics = []
    for cohort in COHORTS:
        for life in LIVES:
            local = [root for root in roots if root['cohort'] == cohort and root['life'] == life]
            diagnostics.append(dict(cohort=cohort, life=life, roots=len(local), source_clusters=len({row['source_id'] for row in local}),
                changed_roots=sum(row['changed'] for row in local), same_action_roots=sum(row['complete'] and not row['changed'] for row in local),
                unsupported_roots=sum(not row['complete'] for row in local)))
    result = dict(schema='acfqp.fixed_board_replication.v175', complete=not issues, issues=issues, suffixes=16, reference_suffixes=4,
        physical_outcomes=len(outcomes), expected_physical_outcomes=len(expected), diagnostics=diagnostics, cohorts={}, cross_cohort={}, work=dict(work),
        scope='fixed first-action policies then the same-history H2 continuation; SOURCE heterogeneity normal intervals and fixed-board conditional suffix-noise normal intervals; the observed OLD reference is fixed for conditional suffix-noise intervals')
    if issues:
        return result
    for cohort in COHORTS:
        result['cohorts'][cohort] = {kind: _comparison(cohort, roots, field, work) for kind, field in (
            ('new', 'new_difference_components'), ('old', 'old_difference_components'), ('new_minus_old', 'new_minus_old_components'))}
    result['cross_cohort'] = {kind: _cross_cohort(result['cohorts']['FRESH'][kind], result['cohorts']['TRAIN'][kind]) for kind in ('new', 'old', 'new_minus_old')}
    result['work'] = dict(work)
    return result


def extract_source(directory):
    """Read compact inherited inputs; no old trajectory replay or model fit."""
    directory = Path(directory); counts = Counter()
    def read(path):
        counts['json_read_operations'] += 1
        return json.loads(Path(path).read_text())
    run, audit, capsule, stage = [read(path) for path in (
        directory/'run.json', directory/'analysis.json', directory/'source_capsule.json', PROJECT/'reports/v174_runtime_tmp/stage_checks.json')]
    models, records, refs, training = {life: {} for life in LIVES}, {}, [], {}
    for life in LIVES:
        for mode, source_mode in (('TREE', 'PART_UTILITY_UNPRUNED'), ('ONE', 'ONE_LATE')):
            path = directory/f'models/life_{life}/{source_mode}.json'; record = read(path)
            records[life, mode] = record; models[life][mode] = record['payload']
            refs.append(dict(life=life, mode=mode, source_mode=source_mode, source_ref=str(path), model_ref=f'models/life_{life}/{mode}.json'))
        training.update({row['root_id']: row for row in models[life]['TREE']['training_outcomes']})
    discovery, fresh, old_choices = read(directory/'discovery_roots.json'), read(directory/'validation_roots.json')['roots'], read(directory/'frozen_choices.json')
    outcome_refs = [dict(life=row['life'], path=str(directory/row['outcomes_ref'])) for row in run['phases']['VALID']['lifecycles']]
    outcomes = [row for ref in outcome_refs for row in read(ref['path'])]
    counts.update(training_reference_root_records=len(training), fresh_reference_outcome_records=len(outcomes))
    index = {(row['root_id'], row['suffix'], row['canonical_action']): row for row in outcomes}
    roots, issues = [], []
    for cohort, inherited in (('TRAIN', discovery), ('FRESH', fresh)):
        for life in LIVES:
            ordered = sorted((root for root in inherited if root['life'] == life), key=lambda root: root['root_id'])
            for ordinal, original in enumerate(ordered):
                root = deepcopy(original)
                if cohort == 'TRAIN':
                    example = training[root['root_id']]
                    if any(example[key] != root[key] for key in ('life', 'source_id', 'canonical_board', 'legal_actions', 'immediate_rewards')):
                        issues.append('training_reference_root_binding')
                    trials = deepcopy(example['suffix_trials'])
                else:
                    trials = []
                    for suffix in range(4):
                        local = [index[root['root_id'], suffix, action] for action in root['legal_actions']]
                        if len({row['seed'] for row in local}) != 1 or any(row['status'] not in ('WON', 'LOST') for row in local):
                            issues.append('fresh_reference_binding')
                        trials.append(dict(suffix=suffix, seed=local[0]['seed'], action_components={row['canonical_action']: deepcopy(row['components']) for row in local}))
                root.update(cohort=cohort, ordinal=ordinal, reference_trials=trials)
                roots.append(root); counts['reference_roots_assembled'] += 1
    for cohort, total, expected_sources in (('TRAIN', 384, 12), ('FRESH', 256, 8)):
        local = [root for root in roots if root['cohort'] == cohort]
        if len(local) != total:
            issues.append('fixed_root_count:'+cohort)
        for life in LIVES:
            groups = Counter(root['source_id'] for root in local if root['life'] == life)
            if len(groups) != expected_sources or set(groups.values()) != {8}:
                issues.append('fixed_source_roots:'+cohort)
    cost_refs = capsule['cost_refs'] + [dict(path=str(directory/'analysis.json'), fields=['costs'])]
    cost_refs += [dict(path=str(PROJECT/f'reports/v174_runtime_tmp/{kind}_checks.json'), fields=['attempts']) for kind in ('core', 'runner', 'analyzer', 'stage')]
    cost_refs += [dict(path=str(PROJECT/'reports/v174_runtime_tmp/discovery_diagnosis.json'), fields=['costs', 'full_tree_training_effect.costs'])]
    expected_capsule = dict(schema='acfqp.fixed_board_replication.v175.source', snapshots=capsule['snapshots'],
        inherited_run_ref=str(directory/'run.json'), inherited_analysis_ref=str(directory/'analysis.json'), inherited_stage_ref=str(PROJECT/'reports/v174_runtime_tmp/stage_checks.json'),
        inherited_v174_environment_samples=audit['costs']['new_environment_samples'], cost_refs=cost_refs,
        this_stage_test_refs=[str(PROJECT/f'reports/v175_runtime_tmp/{kind}_checks.json') for kind in ('core', 'runner', 'analyzer')])
    manifest = dict(model_refs=refs, train_roots_ref=str(directory/'discovery_roots.json'), fresh_roots_ref=str(directory/'validation_roots.json'),
        fresh_choices_ref=str(directory/'frozen_choices.json'), fresh_outcome_refs=outcome_refs, train_reference='audited TREE payload.training_outcomes',
        roots=dict(TRAIN=len(discovery), FRESH=len(fresh)), counts=dict(counts))
    return dict(source=expected_capsule, manifest=manifest, roots=roots, models=models, model_records=records, old_fresh_choices=old_choices,
        complete=not issues, issues=issues, parent_valid=run['status']=='complete' and audit['valid'] and audit['primary_complete'] and stage['valid'])


def audit_engineering_recovery(directory, ledger, check):
    failed = Path(ledger['failed_directory'])
    manifest = json.loads((directory/'models_manifest.json').read_text())
    files = ['roots.json', 'frozen_choices.json', 'branch_roster.json', 'frozen_inputs.json', 'models_manifest.json',
        'source_capsule.json', 'source_manifest.json'] + [row['model_ref'] for row in manifest]
    check('recovery_exact_frozen_inputs_and_eight_models', len(manifest)==8 and all(
        (directory/name).read_bytes()==(failed/name).read_bytes() for name in files))
    retained, current = [], []
    for life in LIVES:
        name = f'train_repl/life_{life}/branches.jsonl.gz'
        with gzip.open(failed/name, 'rt') as stream:
            rows = [json.loads(line) for line in stream]
        check(f'recovery_life{life}:one_original_terminal_branch', len(rows)==1 and rows[0]['life']==life and
            rows[0]['result']['status'] in ('WON', 'LOST') and not rows[0]['result']['learning_counts'])
        retained.extend(rows)
        with gzip.open(directory/name, 'rt') as stream:
            first = json.loads(next(stream))
        current.append(first)
        check(f'recovery_life{life}:exact_reused_raw_record', len(rows)==1 and first==rows[0])
    counts = dict(sum((Counter(row['result']['environment_counts']) for row in retained), Counter()))
    ids = [row['branch_id'] for row in retained]
    plans = json.loads((directory/'branch_roster.json').read_text())['TRAIN_REPL']
    by_id = {plan['branch_id']: plan for plan in plans}
    check('recovery_original_frozen_seeds_actions_and_first_roster_positions', all(
        all(row.get(key)==value for key,value in by_id[row['branch_id']].items()) and
        row['branch_id']==next(plan['branch_id'] for plan in plans if plan['life']==row['life']) for row in retained))
    check('recovery_four_retained_branches_and_paid_environment_counts', len(retained)==len(set(ids))==ledger['reused_physical_branches']==4 and
        set(ids)==set(ledger['reused_branch_ids']) and len(ledger['reused_branch_ids'])==4 and counts==ledger['reused_environment_counts'] and
        counts['sampled_transitions']==3015 and counts['environment_random_draws']==6030)
    stage = json.loads(Path(ledger['failed_stage_ref']).read_text())
    attempt = stage['attempts'][0]
    check('recovery_failed_attempt_preserved', attempt['stage']=='main' and attempt['exit_code']==1 and
        attempt['seconds']==6.411968872998841)
    return dict(failed_stage_ref=ledger['failed_stage_ref'], failed_main_seconds=attempt['seconds'], reused_physical_branches=4,
        reused_environment_counts=counts, physical_cost_inclusion='reused branches included once in current physical traces',
        extra_teacher_bank_loads=8, original_teacher_load_details_retained=False,
        unchanged_frozen_files=files, source_changes=ledger['source_changes'])


def analyze(directory):
    started = perf_counter(); directory = Path(directory)
    read = lambda name: json.loads((directory/name).read_text())
    run, capsule, frozen_inputs = [read(name) for name in ('run.json', 'source_capsule.json', 'frozen_inputs.json')]
    inherited = extract_source(Path(capsule['inherited_run_ref']).parent)
    checks, phases, cohorts = [], {}, {}
    def check(name, passed):
        checks.append(dict(name=name, passed=bool(passed)))
    recovery = None
    if 'engineering_recovery_ref' in run:
        ledger = json.loads(Path(run['engineering_recovery_ref']).read_text())
        recovery = audit_engineering_recovery(directory, ledger, check)
    full_order = ['INPUTS_FROZEN', 'POLICIES_FROZEN', 'TRAIN_REPL', 'FRESH_REPL']
    check('fixed_phase_order', run['phase_order'] == full_order[:len(run['phase_order'])])
    check('physical_phases_match_order', set(run['phases']) == {phase for phase in run['phase_order'] if phase.endswith('_REPL')})
    check('frozen_settings', frozen_inputs['settings'] == run['settings'])
    check('fixed_replication_protocol', _equal(run['settings'], dict(lifecycles=list(LIVES), queries=['risk1'], workers=4, version_base=BASE,
        max_steps=8192, p_four=.1, cohorts=list(COHORTS), train_roots=384, fresh_roots=256, source_clusters_per_history=dict(TRAIN=12, FRESH=8),
        roots_per_source=8, suffixes=16, reference_suffixes=4, modes=dict(TREE='PART_UTILITY_UNPRUNED', ONE='ONE_LATE'), physical_branch_cap=20480,
        maximum_environment_transitions=167772160, new_source_games=0, new_model_fits=0, new_parameter_updates=0,
        same_action='zero difference and no physical branch; retain root and SOURCE denominator', ordinal='cohort/history complete root_id order before skipping same-action roots',
        uncertainty='SOURCE-cluster and fixed-board paired-suffix normal CI95; old observed reference fixed; cohort variance sums',
        diagnostic_questions=['TRAIN_NEW positive', 'TRAIN_NEW-OLD negative', 'FRESH_NEW direction', 'FRESH_NEW-TRAIN_NEW negative'],
        incomplete='missing, duplicate, nonterminal, misbound or unsupported -> HOLD; no replacement', autonomous_evaluation=False, strategy_promotion=False)))
    check('settled_inherited_v174', inherited['parent_valid'])
    check('exact_inherited_capsule_and_paid_refs', capsule == inherited['source'] and run['inherited_cost_refs'] == capsule['cost_refs'])
    check('compact_source_manifest', read('source_manifest.json') == inherited['manifest'])
    roots, models = inherited['roots'], inherited['models']
    check('all_fixed_boards_ordinals_and_four_suffix_references', read('roots.json') == roots)
    check('exact_eight_models_manifest', read('models_manifest.json') == inherited['manifest']['model_refs'])
    for row in inherited['manifest']['model_refs']:
        check(f"life{row['life']}:{row['mode']}:unchanged_frozen_model", read(row['model_ref']) == inherited['model_records'][row['life'], row['mode']])
    frozen = freeze_selections(roots, models) if inherited['complete'] else None
    if frozen is not None:
        check('independent_strict_fixed_choices_and_reference', _equal(read('frozen_choices.json'), frozen))
    rosters = {}
    if 'POLICIES_FROZEN' in run['phase_order']:
        check('complete_inputs_before_physical_sampling', inherited['complete'] and frozen['complete'])
        old_choices = {(row['root_id'], row['mode']): row for row in inherited['old_fresh_choices']}
        check('unchanged_historical_fresh_actions', all(row['decisions'][mode]['canonical_action'] == old_choices[row['root_id'], source_mode]['canonical_action']
            for row in frozen['choices'] if row['cohort']=='FRESH' for mode, source_mode in (('TREE', 'PART_UTILITY_UNPRUNED'), ('ONE', 'ONE_LATE'))))
        rosters = {phase: branch_roster(roots, frozen, phase) for phase in ('TRAIN_REPL', 'FRESH_REPL')}
        check('exact_new_paired_suffix_rosters_without_same_action_sampling', read('branch_roster.json') == rosters)
        check('selection_work_and_roster_counts', run['selection_work'] == frozen['work'] and run['physical_roster_counts'] == {phase:len(rows) for phase,rows in rosters.items()} and
            run['changed_roots'] == {cohort:sum(row['changed'] for row in frozen['choices'] if row['cohort']==cohort) for cohort in COHORTS})
        with ProcessPoolExecutor(max_workers=4) as pool:
            for phase in ('TRAIN_REPL', 'FRESH_REPL'):
                if phase not in run['phases']:
                    continue
                lifecycles = run['phases'][phase]['lifecycles']
                check(f'{phase}:four_histories', len(lifecycles)==4 and [row['life'] for row in lifecycles]==list(LIVES))
                results = list(pool.map(physical.replay_lifecycle, [(str(directory), phase, row, capsule['snapshots'][row['life']],
                    [plan for plan in rosters[phase] if plan['life']==row['life']], roots) for row in lifecycles]))
                phases[phase] = results
                for result in results:
                    for name, passed in result['checks'].items():
                        check(f'{phase}:life{result["life"]}:{name}', passed)
                compact = [row for result in results for row in result['outcomes']]
                cohorts[phase] = physical.previous.complete_cohort(compact, rosters[phase])
                print(json.dumps(dict(audited_phase=phase, lifecycles=len(results))), flush=True)
    check('incomplete_fixed_inputs_stop_sampling', inherited['complete'] and frozen is not None and frozen['complete'] or not run['phases'])
    check('incomplete_train_stops_fresh', cohorts.get('TRAIN_REPL', False) or 'FRESH_REPL' not in run['phases'])
    summary = None
    if set(phases)=={'TRAIN_REPL', 'FRESH_REPL'} and all(cohorts.values()):
        summary = summarize_replication(frozen, [row for data in phases.values() for result in data for row in result['outcomes']])
        check('independent_source_paired_reference_and_cohort_statistics', _equal(read('summary.json'), summary))
    elif 'FRESH_REPL' in phases:
        check('incomplete_cohort_has_no_summary', not (directory/'summary.json').exists())
    costs = prior.aggregate_costs([row['costs'] for results in phases.values() for row in results])
    costs.update(new_source_games=0, new_model_fits=0, new_native_weight_updates=0, inherited_v174_environment_samples=capsule['inherited_v174_environment_samples'],
        inherited_cost_refs=capsule['cost_refs'], this_stage_test_refs=capsule['this_stage_test_refs'], source_extraction_work=inherited['manifest']['counts'],
        selection_work={} if frozen is None else frozen['work'], summary_work={} if summary is None else summary['work'],
        selection_seconds=run.get('selection_seconds', 0.), summary_seconds=run.get('summary_seconds', 0.),
        physical_phase_costs={phase:prior.aggregate_costs([row['costs'] for row in results]) for phase,results in phases.items()},
        teacher_accounting=[dict(phase=phase, life=row['life'], query=query, **teacher) for phase,data in run['phases'].items() for row in data['lifecycles'] for query,teacher in row['teacher_bank'].items()],
        inherited_trajectory_replays=0)
    if recovery is not None:
        costs.update(engineering_recovery=recovery, engineering_recovery_ref=run['engineering_recovery_ref'],
            engineering_recovery_cost_refs=[dict(path=run['engineering_recovery_ref'], fields=['reused_environment_counts', 'source_changes']),
                dict(path=recovery['failed_stage_ref'], fields=['attempts'])])
    check('no_new_fits_or_parameter_updates', run['new_model_fits']==run['new_parameter_updates']==0)
    check('physical_budget', costs['physical_branches']<=20480 and costs['new_environment_samples']<=167772160)
    if run['status']=='complete':
        check('complete_phase_order_and_rosters', run['phase_order']==full_order and all(cohorts.get(phase, False) for phase in ('TRAIN_REPL', 'FRESH_REPL')) and
            costs['physical_branches']==sum(len(rows) for rows in rosters.values()) and summary is not None and summary['complete'])
    check('terminal_status', run['status']==('complete' if summary is not None and summary['complete'] else 'HOLD'))
    valid = all(row['passed'] for row in checks)
    complete = valid and run['status']=='complete' and summary is not None and summary['complete']
    result = dict(schema='acfqp.fixed_board_replication.v175.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), costs=costs, replication_complete=cohorts,
        cohorts={} if summary is None else summary['cohorts'], cross_cohort={} if summary is None else summary['cross_cohort'],
        diagnostics=[] if summary is None else summary['diagnostics'], strategy_promotion=False, seconds=perf_counter()-started)
    (directory/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=PROJECT/'reports/controlled_predictive_fixed_board_replication_v175')
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(valid=result['valid'], primary_complete=result['primary_complete'], passed=result['passed_checks'], checks=result['total_checks'])))
    raise SystemExit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
