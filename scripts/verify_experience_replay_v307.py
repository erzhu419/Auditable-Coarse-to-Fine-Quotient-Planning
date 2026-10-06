#!/usr/bin/env python3
"""Independent selected-experience and equal supervised-budget replay audit."""
import argparse
from collections import Counter, deque
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_continual_v303 import check_belief
from verify_context_continual_v305 import check_new_head
from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_history_control_v304 import scientific_receipt
from verify_natural_online_value_v286 import planning_counts, terminal
from verify_split_risk_v301 import check_representation, nonpeak

ARMS = ('SOURCE', 'A1_FROZEN', 'NEW_ONLY', 'MIXED_REPLAY')
LEARNERS = ('NEW_ONLY', 'MIXED_REPLAY')
PAIRS = (('MIXED_REPLAY', 'NEW_ONLY'), ('MIXED_REPLAY', 'A1_FROZEN'), ('NEW_ONLY', 'A1_FROZEN'),
    ('MIXED_REPLAY', 'SOURCE'), ('NEW_ONLY', 'SOURCE'), ('A1_FROZEN', 'SOURCE'))
PRIMARY = 'MIXED_REPLAY_minus_NEW_ONLY'
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_A1_AND_V306_CURRENT_DATA_HISTORIES'
OLD, CURRENT = 'OLD_A1', 'CURRENT_DATA'


def source_inventory(dataset, source):
    rows = []; offset = 0
    for index, game in enumerate(dataset['games'][:dataset['fit_game_count']]):
        end = offset+game['steps']
        require(game['status'] in ('WON', 'LOST') and game['split'] == 'FIT', 'only original naturally complete FIT games are replay candidates')
        rows.append(dict(source=source, source_game=index, source_episode=game['episode'],
            source_start=offset, source_end=end, terminal_code=1 if game['status'] == 'WON' else -1,
            eligible_steps=game['steps']-(game['status'] == 'WON')))
        offset = end
    require(offset == dataset['fit_step_end'], 'original source complete-game FIT steps remain unchanged')
    return rows


def choose_source_games(rows, quota):
    intervals = deque([(0, len(rows))]); remaining = quota; selected = []
    while intervals and remaining:
        first, end = intervals.popleft()
        if first == end:
            continue
        middle = (first+end)//2
        intervals.extend(((first, middle), (middle+1, end)))
        row = rows[middle]; count = min(remaining, row['eligible_steps'])
        if count:
            partial = None if count == row['eligible_steps'] else [((2*i+1)*row['eligible_steps'])//(2*count) for i in range(count)]
            selected.append(dict(row, selected_count=count, selected_local_steps=partial)); remaining -= count
    require(remaining == 0, 'observed FIT candidate pool supplies the exact frozen source quota')
    return sorted(selected, key=lambda row:row['source_game'])


def expected_plans(old, current):
    pools = {OLD:source_inventory(old, OLD), CURRENT:source_inventory(current, CURRENT)}
    available = {source:sum(row['eligible_steps'] for row in rows) for source, rows in pools.items()}
    budget = available[CURRENT]; quotas = {OLD:budget//2, CURRENT:budget-budget//2}
    require(budget >= 2 and available[OLD] >= quotas[OLD], 'real retained pools support the matched all-current and half-old replay budgets')
    new_records = [dict(row, selected_count=row['eligible_steps'], selected_local_steps=None,
        fit_start=row['source_start'], fit_end=row['source_end']) for row in pools[CURRENT]]
    selected = {source:choose_source_games(pools[source], quota) for source, quota in quotas.items()}
    mixed = []; offset = 0
    for index in range(max(len(rows) for rows in selected.values())):
        for source in (OLD, CURRENT):
            if index < len(selected[source]):
                row = dict(selected[source][index]); end = offset+row['source_end']-row['source_start']
                mixed.append(dict(row, fit_start=offset, fit_end=end)); offset = end
    plans = {
        'NEW_ONLY':dict(budget_nonwinning_afterstates=budget, quotas={OLD:0, CURRENT:budget},
            candidate_game_count=current['fit_game_count'], fitted_full_steps=current['fit_step_end'], games=new_records),
        'MIXED_REPLAY':dict(budget_nonwinning_afterstates=budget, quotas=quotas,
            candidate_game_count=len(mixed), fitted_full_steps=offset, games=mixed)}
    return plans, available


def sample_origin(plan, sample):
    index = sample['episode']; require(0 <= index < len(plan['games']), 'fit sample identifies an actual selected complete source game')
    game = plan['games'][index]; local = sample['step']-game['fit_start']
    selected = range(game['eligible_steps']) if game['selected_local_steps'] is None else game['selected_local_steps']
    require(local in selected, 'fitted example is one of the exact eligible selected source steps')
    return game, local


def check_factual_sample(sample, plan, life, score_ledgers):
    game, local = sample_origin(plan, sample)
    scores = score_ledgers[life, game['source'], game['source_game']]
    target = sum(scores[local+1:])/2048.; label = float(game['terminal_code'] == 1)
    probability = sample['risk_probability']
    require(sample['reward_target'] == target and sample['risk_target'] == label,
        'selected sample suffix includes every unselected future reward from its original full natural game')
    require(0. <= probability <= 1. and close(sample['risk_error'], label-probability)
        and close(sample['reward_error'], target-sample['reward_prediction'])
        and close(sample['combined_prediction'], sample['reward_prediction']+8.*(probability-.5)),
        'replay component predictions residuals and full utility combination retain their frozen definition')


def read_target_game_scores(document, old, current, lives):
    """Read score ledgers only from already audited worlds; no physics or RNG replay."""
    needed = {}
    for life in lives:
        for arm in LEARNERS:
            plan = life['replay']['plans'][arm]
            for name in ('first_sample', 'last_sample'):
                game, local = sample_origin(plan, life['arms'][arm]['fit'][name])
                key = (life['lifecycle'], game['source'], game['source_game'])
                needed[key] = []
    rows_read = {OLD:0, CURRENT:0}; score_values = {OLD:0, CURRENT:0}
    for source_name, input_document in ((OLD, old), (CURRENT, current)):
        for parent in input_document['parent_receipts']:
            ids = parent['lifecycle_ids']
            wanted = {key:values for key, values in needed.items() if key[1] == source_name and key[0] in ids}
            if not wanted:
                continue
            episode_to_game = {}
            for life in ids:
                dataset = old['by_lifecycle'][life]['stages']['A1']['dataset'] if source_name == OLD else current['by_lifecycle'][life]['datasets']['CURRENT_DATA']
                episode_to_game.update({(life, game['episode']):index for index, game in enumerate(dataset['games'])
                    if (life, source_name, index) in wanted})
            with gzip.open(parent['trace_file'], 'rt') as source:
                for line in source:
                    marker = '"phase":"A1"' if source_name == OLD else '"arm":"CURRENT_DATA"'
                    if marker not in line:
                        continue
                    row = json.loads(line); rows_read[source_name] += 1
                    if row['kind'] != 'TRAIN':
                        continue
                    action = 0
                    for spawn in row['raw_spawns']:
                        if spawn['kind'] == 'POST_ACTION':
                            game = episode_to_game.get((row['lifecycle'], spawn['episode']))
                            if game is not None:
                                wanted[row['lifecycle'], source_name, game].append(row['scores'][action]); score_values[source_name] += 1
                            action += 1
            for key, scores in wanted.items():
                life, _, index = key
                dataset = old['by_lifecycle'][life]['stages']['A1']['dataset'] if source_name == OLD else current['by_lifecycle'][life]['datasets']['CURRENT_DATA']
                game = dataset['games'][index]
                require(len(scores) == game['steps'] and sum(scores) == game['score'],
                    'selected target source game retains its full original score sequence and natural terminal label')
    return needed, dict(score_ledger_rows_read=rows_read, selected_target_game_score_values=score_values,
        independent_physics_rows_replayed=0)


def check_fit(fit, plan, life, score_ledgers):
    games = plan['games']; count = plan['budget_nonwinning_afterstates']; full_steps = plan['fitted_full_steps']
    n = len(games); wins = sum(game['terminal_code'] == 1 for game in games)
    require(fit['method'] == 'LOCAL_RISK' and fit['alpha'] == .0025 and fit['frozen_game_start_targets']
        and fit['fitted_games'] == fit['candidate_fitted_games'] == fit['selected_games'] == plan['candidate_game_count'] == n
        and fit['fitted_steps'] == full_steps and fit['trained_afterstates']
        == fit['reward_trained_afterstates'] == fit['risk_trained_afterstates'] == count,
        'both reward/risk replay heads process the exact matched selected-afterstate budget within full source games')
    targets = dict(terminal_game_labels=n, risk_label_assignments=count,
        reward_suffix_target_assignments=full_steps, reward_suffix_additions=full_steps,
        goal_checks=full_steps, skipped_winning_afterstates=wins)
    require(Counter(fit['target_counts']) == Counter(targets), 'replay labels use full original future rewards and natural terminal outcomes')
    selection = dict(fit_afterstates_checked=full_steps, winning_afterstates_skipped=wins,
        nonwinning_selection_reads=full_steps-wins, unselected_nonwinning_afterstates=full_steps-wins-count,
        selected_nonwinning_afterstates=count, games_with_selected_samples=n)
    require(Counter(fit['selection_counts']) == Counter(selection), 'native mask visits distinguish full-game targets from selected supervised states')
    check_representation(fit['representation_counts'], 'LOCAL_RISK', count)
    work, norm = Counter(fit['learning_counts']), Counter(fit['normalization_counts'])
    writes, products = norm['game_unique_addresses'], norm['reward_gradient_products']
    require(n <= writes <= 32*count and count <= products <= 32*count, 'actual nonempty selected game and sample address inventories')
    expected = dict(td_updates=count, value_predictions=count, table_lookups=64*count, table_updates=2*writes,
        table_update_occurrences=32*count, reward_predictions=count, risk_predictions=count,
        reward_table_lookups=32*count, risk_table_lookups=32*count, reward_table_updates=writes, risk_parameter_updates=writes)
    require(work == Counter(expected), 'actual reward and risk replay parameter commits remain counted separately')
    known = dict(games_processed=n, feature_extractions=count, feature_occurrences=32*count,
        feature_digit_reads=192*count, feature_address_multiply_adds=192*count, sort_calls=n+count, sort_items=64*count,
        denominator_occurrence_visits=32*count, reward_gradient_accumulations=products,
        risk_gradient_products=products, risk_gradient_accumulations=products, global_denominator_accumulations=0,
        normalization_divisions=2*writes, parameter_update_multiplications=2*writes,
        game_parameter_commits=n, reward_game_commits=n, risk_game_commits=n,
        reward_parameter_writes=writes, risk_parameter_writes=writes, global_zero_denominators=0,
        address_denominator_searches=products)
    require(all(norm[key] == value for key, value in known.items()), 'same per-game occurrence normalization on actual selected reward/risk samples')
    for name, index in (('first_sample', 0), ('last_sample', n-1)):
        sample = fit[name]; game, local = sample_origin(plan, sample)
        selected = game['selected_local_steps']
        expected_local = (0 if name == 'first_sample' else game['eligible_steps']-1) if selected is None else \
            selected[0 if name == 'first_sample' else -1]
        require(sample['episode'] == index and local == expected_local, 'native examples are the actual first and last selected chronological updates')
        check_factual_sample(sample, plan, life, score_ledgers)
    return count


def original_fit_identity(fit):
    return {key:value for key, value in scientific_receipt(fit).items()
        if key not in ('candidate_fitted_games', 'selected_games', 'selection_counts')}


def check_inputs_and_plans(life, previous, current):
    require(life['lifecycle'] == previous['lifecycle'] == current['lifecycle']
        and life['parent'] == previous['parent'] == current['parent']
        and life['inputs'] == {OLD:previous['stages']['A1']['dataset'], CURRENT:current['datasets']['CURRENT_DATA']},
        'same audited original A1 and V306 current-policy factual inventories')
    require(life['evaluation_belief'] == previous['evaluation_beliefs']['A'] == current['evaluation_belief'],
        'replay retains original observed A1 planning belief without new source or heldout updates')
    check_belief(life['evaluation_belief'], previous['stages']['A1']['dataset'])
    plans, available = expected_plans(life['inputs'][OLD], life['inputs'][CURRENT]); replay = life['replay']
    require(replay['budget'] == available[CURRENT] and replay['available'] == available,
        'NEW_ONLY and replay both process exactly all available current FIT nonwinning states')
    require(replay['plans'] == plans, 'full-game midpoint breadth-first selection and exact quantile boundary masks preserve all source-game-step identities')
    offset = plans['MIXED_REPLAY']['fitted_full_steps']
    expected = dict(candidate_fit_games=sum(data['fit_game_count'] for data in life['inputs'].values()),
        candidate_fit_afterstates=sum(data['fit_step_end'] for data in life['inputs'].values()),
        selected_training_afterstates_per_arm=replay['budget'], copied_replay_afterstate_cells=16*offset,
        copied_replay_reward_values=offset, copied_replay_game_boundaries=plans['MIXED_REPLAY']['candidate_game_count'],
        selection_mask_bytes=4*(life['inputs'][CURRENT]['fit_step_end']+offset))
    require(replay['selection_counts'] == expected, 'actual candidate scans full replay copies and FIT-only mask allocations remain paid')
    return plans


def check_initialization(life, previous):
    initial = previous['stages']['A1']['arms']['LOCAL_RISK']
    equal_tree(scientific_receipt(life['initial_fit']), scientific_receipt(initial['fit']),
        'replayed initial full A1 reward/risk fit reproduces all V303 numerical samples and work')
    require(set(life['arms']) == set(ARMS) and life['initial_head_setup'] == life['arms']['A1_FROZEN']['head_setup'],
        'all replay arms exist and original A1 carrier/reference share one physical head allocation')
    for arm in ARMS:
        setup = life['arms'][arm]['head_setup']; check_new_head(setup)
        counts = setup['setup_counts']; size = counts['source_parameters_copied']
        if arm in LEARNERS:
            require(counts['a1_parameters_copied'] == 2*size and counts['a1_weight_bytes_copied'] == 16*size,
                'both replay learners copy identical complete A1 reward and risk parameters')
        else:
            require(counts.get('a1_parameters_copied', 0) == counts.get('a1_weight_bytes_copied', 0) == 0,
                'SOURCE and original A1 reference do not charge a second initialization copy')
    return initial['head_updates_after']


def check_lifecycle(life, previous, current, score_ledgers):
    plans = life['replay']['plans']; initial_updates = check_initialization(life, previous)
    endpoints = {}; processed = Counter(); cutoffs = 0
    for arm in ARMS:
        value = life['arms'][arm]; before = 0 if arm == 'SOURCE' else initial_updates; fit = value['fit']
        if arm in LEARNERS:
            samples = check_fit(fit, plans[arm], life['lifecycle'], score_ledgers)
            if arm == 'NEW_ONLY':
                equal_tree(original_fit_identity(fit), scientific_receipt(current['arms']['CURRENT_DATA']['fit']),
                    'all-current masked fit exactly reproduces the unchanged V306 CURRENT_DATA numerical control')
        else:
            require(fit['method'] == 'NONE' and fit['trained_afterstates'] == 0
                and not fit['learning_counts'] and not fit['target_counts'], 'SOURCE and A1 references do not receive replay updates')
            samples = 0
        require(value['head_updates_before'] == before and value['head_updates_after'] == before+samples,
            'both replay learners retain the same initial A1 history and add exactly the common supervised budget')
        endpoints[arm] = check_evaluation(value['evaluation'], life['lifecycle'], life['evaluation_belief'])
        processed[arm] = samples; cutoffs += endpoints[arm]['cutoffs']
    return dict(lifecycle=life['lifecycle'], parent=life['parent'], arms=endpoints), processed, cutoffs


def eligible_samples(dataset):
    return sum(game['steps']-(game['status'] == 'WON') for game in dataset['games'][:dataset['fit_game_count']])


def check_evaluation(value, life, belief):
    games, counts = value['game_summaries'], value['counts']
    require(value['estimated_p_four'] == belief['estimated_p_four'] and value['static_evaluation_valid'],
        'all replay policies evaluate with the unchanged observed A1 belief and frozen parameters')
    require(len(games) == 32 and [game['seed'] for game in games] == [307900000000+life*1000000+i for i in range(32)],
        'all four replay policies use the same 32 fresh paired evaluation seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'complete replay evaluation horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and max(game['final_board']) < 11, 'no hidden premature cutoff or terminal goal')
            bonus = 0.
        else:
            terminal(game['final_board'], game['status']); bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'replay whole-game utility includes natural terminal score and bonus')
    steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games)
    expected = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=64,
        raw_tile_productions=steps+64, environment_random_draws=2*(steps+64), ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+32, ground_status_internal_swipe_calls=4*(steps+32-wins),
        ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(counts['environment']) == Counter(expected), 'all new replay evaluation initial and terminal raw tiles are paid')
    planning_counts(counts['planning'], steps)
    check_representation(value['representation_counts'], 'LOCAL_RISK', counts['planning'].get('value_predictions', 0))
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games), wins=wins,
        losses=sum(game['status'] == 'LOST' for game in games), cutoffs=sum(game['status'] == 'CUTOFF' for game in games),
        cutoff_episodes=[i for i, game in enumerate(games) if game['status'] == 'CUTOFF'], steps=steps)


def check_contrast(saved, values):
    require(len(values) == 64 and close(saved['mean'], mean(values)), 'signed equal-life paired replay means')
    equal_tree(saved['lifecycle_deltas'], {str(i):value for i, value in enumerate(values)}, 'all adverse replay lives remain retained')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'], {str(parent):mean(group) for parent, group in enumerate(groups)}, 'four frozen-parent paired replay means')
    low, high = saved['ci95']
    require(saved['interval_scope'] == INTERVAL_SCOPE
        and mean(min(group) for group in groups)-1e-10 <= low <= high <= mean(max(group) for group in groups)+1e-10,
        'replay interval remains conditional on retained source A1 and current-policy histories')
    require(saved['improved_equal_worse'] == [sum(v > 0. for v in values), sum(v == 0. for v in values), sum(v < 0. for v in values)]
        and saved['adverse_lifecycles'] == [i for i, value in enumerate(values) if value < 0.], 'negative replay effects are preserved')


def check_support(summary, cutoffs):
    complete = cutoffs == 0; supported = complete and summary['paired_contrasts'][PRIMARY]['ci95'][0] > 0.
    low, high = summary['paired_contrasts']['MIXED_REPLAY_minus_A1_FROZEN']['ci95']
    retention = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else 'SUPPORTED_NONDECREASE' if low >= 0.
        else 'SUPPORTED_LOSS' if high < 0. else 'UNRESOLVED')
    gains = {arm:complete and summary['paired_contrasts'][arm+'_minus_SOURCE']['ci95'][0] > 0.
        for arm in ('A1_FROZEN', 'NEW_ONLY', 'MIXED_REPLAY')}
    require(summary['complete_game_endpoints'] == complete and summary['primary_replay_gain_supported'] == supported
        and summary['primary_replay_gain_status'] == ('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        'replay advantage uses its own positive primary interval and complete endpoints')
    require(summary['replay_retention_status'] == retention and summary['replay_no_degradation_supported']
        == (retention == 'SUPPORTED_NONDECREASE'), 'advantage over new-only experience does not imply A1 retention')
    require(summary['source_reference_gain_supported'] == gains, 'SOURCE gains remain separate from replay and retention claims')


def check_result_summary(summary, records, cutoffs):
    equal_tree(summary['by_lifecycle'], records, 'all four fresh same-seed replay game endpoints')
    require(summary['primary_contrast'] == PRIMARY and summary['bootstrap_draws'] == 20000 and summary['bootstrap_seed'] == 30700001
        and summary['estimator'] == 'EQUAL_A_EVALUATION_GAMES_THEN_LIFECYCLES', 'frozen supervised-budget replay primary and estimator')
    for arm in ARMS:
        values = [row['arms'][arm] for row in records]
        expected = dict(mean_game_utility=mean(value['mean_game_utility'] for value in values),
            **{key:sum(value[key] for value in values) for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')})
        equal_tree(summary['arms'][arm], expected, 'equal evaluation-game then lifecycle replay utility '+arm)
    require(set(summary['paired_contrasts']) == {left+'_minus_'+right for left, right in PAIRS}, 'all frozen replay SOURCE and A1 comparisons')
    for left, right in PAIRS:
        check_contrast(summary['paired_contrasts'][left+'_minus_'+right],
            [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility'] for row in records])
    check_support(summary, cutoffs)


def check_training_budget(account, old, current):
    require(account['new_training_environment_observations'] == account['new_training_acquisitions'] == 0,
        'retained old/current replay acquires no new training environment data')
    inherited = old['accounting']['inherited_costs_per_arm']['SOURCE']
    a1_raw = sum(life['stages']['A1']['acquisition']['warmup']['raw_tiles']
        +life['stages']['A1']['acquisition']['training']['raw_tiles'] for life in old['by_lifecycle'])
    current_raw = current['accounting']['new_training_raw_tiles_by_actor']['CURRENT_DATA']
    base = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+a1_raw
    expected = {arm:base+(current_raw if arm in LEARNERS else 0) for arm in ARMS}
    require(account['inherited_a1_raw_tiles'] == a1_raw and account['inherited_current_raw_tiles'] == current_raw
        and account['inherited_costs_per_arm'] == dict.fromkeys(ARMS, inherited),
        'replay pays full original A1 facts and retained CURRENT_DATA without importing SOURCE_DATA costs')
    require(account['economic_training_raw_tiles_per_arm'] == expected and not account['historical_total_compute_closed'],
        'only replay learners pay the retained current cohort and historical unavailable CPU stays explicit')
    return expected


def check_accounting(document, old, current, old_audit, current_audit):
    account = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    economic = check_training_budget(account, old, current)
    budget = sum(life['replay']['budget'] for life in lives); initial = [life['initial_fit'] for life in lives]
    require(account['matched_supervised_state_budget_per_updating_arm'] == budget
        and account['new_processed_training_samples'] == dict(SOURCE=0, A1_FROZEN=0, NEW_ONLY=budget, MIXED_REPLAY=budget),
        'all-current and half-old replay match actual fitted nonwinning states exactly')
    require(account['initial_replayed_training_samples'] == sum(fit['trained_afterstates'] for fit in initial)
        and account['initial_refit_counts'] == sum_counts(fit['learning_counts'] for fit in initial)
        and close(account['initial_refit_cpu_seconds'], sum(fit['cpu_seconds'] for fit in initial)),
        'actual A1 refit computation is paid without duplicating old acquisition')
    require(account['selection_counts'] == sum_counts(life['replay']['selection_counts'] for life in lives)
        and close(account['selection_cpu_seconds'], sum(life['replay']['selection_cpu_seconds'] for life in lives)),
        'all actual source scans full-game replay copies masks and selection CPU remain paid')
    require(account['new_evaluation_games'] == 8192, 'all four fresh paired replay evaluation arms count their actual games')
    fields = (('fit_counts', 'learning_counts'), ('fit_target_counts', 'target_counts'),
        ('fit_normalization_counts', 'normalization_counts'), ('fit_representation_counts', 'representation_counts'),
        ('fit_selection_counts', 'selection_counts'), ('fit_setup_counts', 'setup_counts'))
    for arm in ARMS:
        values = [life['arms'][arm] for life in lives]; fits = [value['fit'] for value in values]
        setups = [value['head_setup'] for value in values]; evaluations = [value['evaluation'] for value in values]
        for field, key in fields:
            require(account[field][arm] == sum_counts(nonpeak(fit.get(key, {})) for fit in fits), 'actual '+arm+' '+field)
        require(close(account['fit_cpu_seconds'][arm], sum(fit['cpu_seconds'] for fit in fits))
            and account['private_head_weight_bytes_created'][arm] == sum(setup['private_weight_bytes'] for setup in setups)
            and account['head_setup_counts'][arm] == sum_counts(setup['setup_counts'] for setup in setups)
            and close(account['head_setup_cpu_seconds'][arm], sum(setup['setup_cpu_seconds'] for setup in setups)),
            'each actual private replay head allocation A1 copy and masked fit CPU is counted once')
        require(close(account['evaluation_cpu_seconds_per_arm'][arm], sum(value['cpu_seconds'] for value in evaluations))
            and account['evaluation_representation_counts'][arm] == sum_counts(value['representation_counts'] for value in evaluations),
            'all actual new static reward/risk replay evaluation work remains paid')
        for kind in ('environment', 'planning'):
            require(account['evaluation_counts_per_arm'][arm][kind] == sum_counts(value['counts'][kind] for value in evaluations),
                'all actual new replay '+kind+' evaluation costs')
    require([parent['parent'] for parent in parents] == list(range(4)), 'four original SOURCE parent loads')
    for parent in parents:
        require(parent['lifecycle_ids'] == list(range(parent['parent'], 64, 4))
            and parent['source_setup']['checkpoint_loads'] == 1 and parent['source_setup']['new_leaf_updates'] == 0
            and all(parent['reconstruction'][source]['stages'] == 16 for source in (OLD, CURRENT)),
            'each frozen source reconstructs exactly sixteen old A1 and retained current factual lives')
    require(sum(parent['reconstruction'][OLD]['canonical_rows_read'] for parent in parents) == old_audit['canonical_rows']
        and sum(parent['reconstruction'][CURRENT]['canonical_rows_read'] for parent in parents) == current_audit['canonical_rows'],
        'actual retained input scans retain their original canonical row inventories')
    for source in (OLD, CURRENT):
        require(account['reconstruction_counts'][source] == sum_counts(parent['reconstruction'][source]['counts'] for parent in parents)
            and close(account['reconstruction_cpu_seconds'][source], sum(parent['reconstruction'][source]['cpu_seconds'] for parent in parents)),
            'actual execution input reconstruction '+source+' costs')
    for field in ('worker_cpu_seconds', 'compiler_cpu_seconds'):
        key = 'cpu_seconds' if field == 'worker_cpu_seconds' else field
        require(close(account[field], sum(parent[key] for parent in parents)), 'actual '+field+' aggregate')
    return economic


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(document['schema'] == 'acfqp.experience_replay.v307' and document['status'] == 'EXPERIMENT_COMPLETE',
        'complete supervised-budget replay terminal document')
    equal_tree(settings, json_file(directory/'configuration.json'), 'unchanged pre-run V307 configuration')
    expected = dict(lifecycles=list(range(64)), parents=4, arms=list(ARMS), retained_actor=CURRENT, true_p_four=.1,
        alpha=.0025, query=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.),
        representation='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_RISK',
        initialization='IDENTICAL_RETAINED_V303_A1_REWARD_AND_RISK',
        training_budget='ALL_CURRENT_FIT_NONWINNING_AFTERSTATES_PER_LIFECYCLE',
        mixed_quotas='FLOOR_HALF_OLD_A1_AND_REMAINING_CURRENT',
        game_selection='FIT_INDEX_MIDPOINT_BREADTH_FIRST_FULL_GAMES_THEN_ONE_QUANTILE_MASK_PER_SOURCE',
        game_order='CHRONOLOGICAL_WITHIN_SOURCE_THEN_OLD_NEW_ALTERNATING_OLD_FIRST',
        targets='ORIGINAL_COMPLETE_NATURAL_GAME_SUFFIX_AND_WIN_LABEL',
        fit_scope='ORIGINAL_80_PERCENT_COMPLETE_GAME_PREFIX_NO_HELDOUT_OR_TAIL',
        planning_probability='FIXED_ORIGINAL_A1_OBSERVED_BELIEF', seed_evaluation=307900000000,
        evaluation_games=32, max_steps=8192, bootstrap_draws=20000, bootstrap_seed=30700001,
        primary=PRIMARY, retention='MIXED_REPLAY_minus_A1_FROZEN_CI_LOWER_NONNEGATIVE',
        interval_scope=INTERVAL_SCOPE, new_training_environment_observations=0, new_evaluation_games=8192,
        stop_rule='NO_MIXING_ALPHA_BUDGET_OR_CHECKPOINT_TUNING_ON_THE_RETAINED_COHORTS')
    for key, value in expected.items():
        require(settings[key] == value, 'registered exact-budget replay V307 '+key)
    old = json_file(settings['a1_summary']); current = json_file(settings['current_summary'])
    old_audit = json_file(Path(settings['a1_summary']).with_name('audit.json'))
    current_audit = json_file(Path(settings['current_summary']).with_name('audit.json'))
    require(old['schema'] == 'acfqp.continual.v303' and current['schema'] == 'acfqp.policy_data.v306'
        and old_audit['status'] == current_audit['status'] == 'PASS'
        and old_audit['independent_valid'] and current_audit['independent_valid'],
        'settled original A1 and complete new current-policy world audits')
    require(current['settings']['source_summary'] == settings['a1_summary']
        and document['source_provenance'] == old['source_provenance'] == current['source_provenance'],
        'same original sources initial A1 histories and V306 current factual parents')
    lives = document['by_lifecycle']
    require([life['lifecycle'] for life in lives] == list(range(64)) and all(life['parent'] == life['lifecycle']%4 for life in lives),
        'all 64 matched retained replay lifecycles under four original parents')
    for life, previous, current_life in zip(lives, old['by_lifecycle'], current['by_lifecycle']):
        check_inputs_and_plans(life, previous, current_life)
    ledgers, ledger_receipt = read_target_game_scores(document, old, current, lives)
    records = []; processed = Counter(); cutoffs = 0
    for life, previous, current_life in zip(lives, old['by_lifecycle'], current['by_lifecycle']):
        record, samples, ncutoffs = check_lifecycle(life, previous, current_life, ledgers)
        records.append(record); processed.update(samples); cutoffs += ncutoffs
    check_result_summary(document['summary'], records, cutoffs)
    economic = check_accounting(document, old, current, old_audit, current_audit)
    return dict(status='PASS', independent_valid=True, lifecycles=64, fixed_source_parents=4,
        new_training_environment_observations=0, new_evaluation_games=8192, distinct_evaluation_seed_conditions=2048,
        evaluation_cutoffs=cutoffs, new_processed_training_samples=dict(processed),
        matched_supervised_state_budget_per_updating_arm=document['accounting']['matched_supervised_state_budget_per_updating_arm'],
        economic_training_raw_tiles_per_arm=economic,
        actual_new_parameter_writes={arm:document['accounting']['fit_counts'][arm].get('table_updates', 0) for arm in ARMS},
        primary_replay_gain_supported=document['summary']['primary_replay_gain_supported'],
        replay_retention_status=document['summary']['replay_retention_status'],
        replay_no_degradation_supported=document['summary']['replay_no_degradation_supported'],
        source_reference_gain_supported=document['summary']['source_reference_gain_supported'],
        primary_utility=document['summary']['paired_contrasts'][PRIMARY], historical_total_compute_closed=False,
        source_score_ledger_check=ledger_receipt,
        method='Independent original FIT inventory and source quotas, midpoint full-game breadth-first selection '
            'and exact boundary quantiles, selected source-game-step identities, original full score suffix targets, '
            'matching actual supervised samples, unchanged V306 new-only numerical fit, initial A1 copies and '
            'histories, fresh whole-game endpoints and actual costs.',
        limitations='Original A1 and V306 world integrity is inherited; only selected target game score ledgers '
            'are reread without physics replay. No weight refit or bootstrap recomputation; saved intervals are '
            'checked for scope and feasible range. Equal supervised states do not equalize full-game/address '
            'commits or computation. Replay changes experience composition and game ordering together on retained '
            'cohorts, not an independent confirmation or new B retention test. Historical V303 CPU remains unavailable.', errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    directory = parser.parse_args().output
    try:
        result = audit(directory)
    except ValueError as error:
        result = dict(status='FAIL', independent_valid=False, errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(not result['independent_valid'])


if __name__ == '__main__':
    main()
