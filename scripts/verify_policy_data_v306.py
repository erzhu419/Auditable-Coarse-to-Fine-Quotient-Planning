#!/usr/bin/env python3
"""Independent full-physics audit of the two new fixed-policy acquisition streams."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_continual_v303 import check_belief
from verify_context_continual_v305 import check_new_head
from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_history_control_v304 import scientific_receipt
from verify_natural_online_value_v286 import planning_counts, terminal
from verify_split_risk_v301 import check_representation, check_split_counts, check_split_heldout, nonpeak

ARMS = ('SOURCE', 'A1_FROZEN', 'SOURCE_DATA', 'CURRENT_DATA')
DATA_ARMS = ('SOURCE_DATA', 'CURRENT_DATA')
RAW = 131072
CHUNK_RAW = 256
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_RETAINED_V303_A1_HISTORIES'
PRIMARY = 'CURRENT_DATA_minus_SOURCE_DATA'
PAIRS = (('CURRENT_DATA', 'SOURCE_DATA'), ('CURRENT_DATA', 'A1_FROZEN'),
    ('SOURCE_DATA', 'A1_FROZEN'), ('CURRENT_DATA', 'SOURCE'), ('SOURCE_DATA', 'SOURCE'), ('A1_FROZEN', 'SOURCE'))


def swipe(board, action):
    """Literal independent 2048 row compression and one-merge-per-tile rule."""
    require(action in ('LEFT', 'RIGHT', 'UP', 'DOWN'), 'actual standard-world action')
    after = list(board); score = 0
    for line in range(4):
        indices = ([4*line+i for i in range(4)] if action == 'LEFT' else
            [4*line+i for i in range(3, -1, -1)] if action == 'RIGHT' else
            [4*i+line for i in range(4)] if action == 'UP' else
            [4*i+line for i in range(3, -1, -1)])
        values = [board[i] for i in indices if board[i]]; moved = []; i = 0
        while i < len(values):
            if i+1 < len(values) and values[i] == values[i+1]:
                rank = values[i]+1; moved.append(rank); score += 1 << rank; i += 2
            else:
                moved.append(values[i]); i += 1
        for index, rank in zip(indices, moved+[0]*(4-len(moved))):
            after[index] = rank
    return after, score


def board_status(board):
    if max(board) >= 11:
        return 'WON'
    if 0 in board or any(board[4*r+c] == board[4*r+c+1] for r in range(4) for c in range(3)) \
            or any(board[4*r+c] == board[4*(r+1)+c] for r in range(3) for c in range(4)):
        return 'ACTIVE'
    return 'LOST'


def pooled_memory(observations, fours):
    return dict(schema='acfqp.regime_memory.v115', method='POOLED', warmup_observations=256,
        block_size=64, recent_window=256, observations_seen=observations, warmup_complete=observations >= 256,
        active_module_id=0, modules=[dict(id=0, alpha=1+fours, beta=1+observations-fours, visits=int(observations >= 256))],
        pending=dict(n=0, fours=0), recent_ranks=[], stored_observation_counts=dict(statistics=observations, pending=0, raw=0),
        counts=dict(observations_received=observations, beta_updates=observations, predict_calls=0,
            routing_blocks=0, candidate_predictive_scores=0, module_creations=0, module_reactivations=0))


class PhysicalStream:
    """Rebuild one continuous actor stream; keep game moments, not raw histories."""
    def __init__(self, life, arm, belief, initial_updates):
        self.life, self.arm, self.belief, self.initial_updates = life, arm, belief, initial_updates
        self.state = self.before = None; self.games = []; self.moments = []; self.ends = []; self.fours = 0
        self.ranks = bytearray()
        self.game_first_score = self.game_last_score = self.game_weighted_score = 0
        self.counts = {key:Counter() for key in ('environment', 'planning', 'learning')}
        self.representation = Counter(); self.processing = Counter(); self.chunks = 0; self.snapshot = None

    def check_context(self, row):
        require(row['lifecycle'] == self.life and row['arm'] == self.arm and row['phase'] == 'A'
            and row['true_p_four'] == .1 and row['model_p_four'] == self.belief['estimated_p_four']
            and row['actor_head_updates'] == self.initial_updates,
            'new fixed-policy actor uses the original A1 observed belief and unchanged parameter history')

    def train(self, row):
        self.check_context(row); start, end = row['start'], row['end']; raw = row['raw_spawns']
        require(self.snapshot is None, 'fixed-policy acquisition continued after its raw boundary')
        require(start['stream_seed'] == 306200000000+self.life*10000000
            and len(raw) == min(CHUNK_RAW, RAW-start['raw_tiles']) and raw,
            'both actor arms retain the same continuous seed and exact paid raw chunk boundary')
        if self.state is None:
            require(start['raw_tiles'] == start['post_action_spawns'] == start['random_draw_position'] == 0
                and start['status'] == 'NOT_STARTED' and start['initial_count'] == 0
                and start['board'] == [0]*16 and start['pending_afterstate'] is start['pending_bank_id'] is None,
                'new actor begins a fresh empty continuous stream with both initial tiles unpaid')
            self.state = deepcopy(start)
            self.before = deepcopy(start)
        require(self.state == start, 'new canonical stream continuity across fixed raw chunks')
        state = self.state; action_index = 0; completed = []; starts = init_done = wins = losses = posts = 0
        for spawn in raw:
            require(spawn['rank'] in (1, 2) and 0 <= spawn['cell'] < 16, 'new raw spawn rank and cell')
            if spawn['kind'] == 'INITIAL':
                if state['status'] != 'INITIALIZING':
                    require(state['status'] in ('NOT_STARTED', 'WON', 'LOST'),
                        'new initialization cannot reset an active or censored game')
                    state.update(board=[0]*16, episode=state['episode']+1, step=0, return_score=0,
                        status='INITIALIZING', initial_count=0, game_start_raw=state['raw_tiles'],
                        pending_afterstate=None, pending_bank_id=None)
                    self.game_first_score = self.game_last_score = self.game_weighted_score = 0; starts += 1
                require(state['initial_count'] < 2, 'new game has exactly two initial raw tiles')
                state['initial_count'] += 1
                if state['initial_count'] == 2:
                    init_done += 1
            else:
                require(spawn['kind'] == 'POST_ACTION' and state['status'] == 'ACTIVE' and state['initial_count'] == 2
                    and action_index < len(row['actions']), 'new action follows an active two-tile initialization')
                after, score = swipe(state['board'], row['actions'][action_index])
                require(after != state['board'] and score == row['scores'][action_index],
                    'new actual swipe is legal and has its independent merge score')
                state['board'] = after; action_index += 1; posts += 1
                if state['step'] == 0:
                    self.game_first_score = score
                self.game_last_score = score; self.game_weighted_score += state['step']*score
                state['step'] += 1; state['return_score'] += score; state['post_action_spawns'] += 1
                state['pending_afterstate'] = list(after); state['pending_bank_id'] = 0
            require(spawn['episode'] == state['episode'] and state['board'][spawn['cell']] == 0,
                'new spawn occupies an empty cell in its actual continuous game')
            state['board'][spawn['cell']] = spawn['rank']; self.fours += spawn['rank'] == 2
            self.ranks.append(spawn['rank'])
            state['raw_tiles'] += 1; state['random_draw_position'] += 2
            if state['initial_count'] == 2:
                state['status'] = board_status(state['board'])
            if state['status'] in ('WON', 'LOST'):
                state.update(pending_afterstate=None, pending_bank_id=None)
                game = dict(episode=state['episode'], stream_seed=state['stream_seed'],
                    start_raw=state['game_start_raw'], end_raw=state['raw_tiles'], steps=state['step'],
                    score=state['return_score'], status=state['status'])
                completed.append(game); self.games.append(game); self.ends.append(state['post_action_spawns'])
                samples = state['step']-(state['status'] == 'WON')
                require(samples > 0, 'complete new game includes a nonwinning afterstate')
                self.moments.append(dict(first_score=self.game_first_score, last_score=self.game_last_score,
                    weighted_score=self.game_weighted_score, mean_factual_future_utility=(4. if state['status'] == 'WON' else -4.)
                    +self.game_weighted_score/(2048.*samples), memory=pooled_memory(state['raw_tiles'], self.fours)))
                wins += state['status'] == 'WON'; losses += state['status'] == 'LOST'
        require(action_index == len(row['actions']) == len(row['scores']) and completed == row['completed_games']
            and state == end, 'new canonical end board pending state and complete score/terminal receipts')
        expected = dict(sampled_transitions=posts, post_action_spawns=posts, initial_spawns=len(raw)-posts,
            raw_tile_productions=len(raw), environment_random_draws=2*len(raw), ground_explicit_swipe_calls=posts,
            ground_state_status_calls=posts+init_done, ground_status_internal_swipe_calls=4*(posts+init_done-wins),
            ground_swipe_calls=posts+4*(posts+init_done-wins), episodes_started=starts,
            episodes_completed=wins+losses, won_games=wins, lost_games=losses)
        require(Counter(row['counts']['environment']) == Counter(expected), 'new actual acquisition includes initial and winning spawns')
        planning_counts(row['counts']['planning'], posts)
        require(not row['counts']['learning'] and not row['bank_update_counts'] and not row['td_examples'],
            'both complete reward/risk acquisition actors remain frozen without training')
        check_representation(row['representation_counts'], 'LOCAL_RISK', row['counts']['planning'].get('value_predictions', 0))
        for key in self.counts:
            self.counts[key].update(row['counts'][key])
        boundary = int(state['status'] not in ('NOT_STARTED', 'INITIALIZING'))
        processing_internal = 4*(init_done+losses+int(boundary and state['status'] != 'WON'))
        self.processing.update(ground_explicit_swipe_calls=posts, ground_swipe_calls=posts+processing_internal,
            ground_state_status_calls=init_done+wins+losses+boundary,
            ground_status_internal_swipe_calls=processing_internal)
        self.representation.update(row['representation_counts']); self.chunks += 1

    def checkpoint(self, row):
        self.check_context(row)
        require(self.snapshot is None and self.state is not None and self.state['raw_tiles'] == RAW,
            'new fixed-policy snapshot occurs exactly once at its paid raw boundary')
        require(row['snapshot']['stream'] == self.state
            and row['snapshot']['memory'] == pooled_memory(RAW, self.fours),
            'snapshot preserves full independent physical stream and all-raw observational POOLED statistics')
        training = row['training']
        require(training['raw_tiles'] == RAW and training['chunks'] == self.chunks
            and training['before_stream'] == self.before and training['after_stream'] == self.state
            and all(Counter(training['counts'][key]) == self.counts[key] for key in self.counts)
            and Counter(training['representation_counts']) == self.representation,
            'new snapshot records actual whole-actor physical planning and reward/risk work')
        reconstruction = row['reconstruction']
        require(Counter(reconstruction['counts']) == self.processing
            and reconstruction['memory_counts'] == pooled_memory(RAW, self.fours)['counts']
            and reconstruction['chunks'] == self.chunks,
            'all actual reconstruction swipes status calls and POOLED updates remain paid')
        self.snapshot = row


def check_dataset(dataset, stream):
    require(stream.snapshot is not None, 'new acquired factual stream has its closed raw snapshot')
    games = stream.games; n = 4*len(games)//5
    require(0 < n < len(games) and dataset['fit_game_count'] == n
        and dataset['games'] == [dict(game, split='FIT' if i < n else 'HELDOUT') for i, game in enumerate(games)],
        'new 80/20 split uses all complete chronological games without selecting labels')
    fit_steps = stream.ends[n-1]; complete_steps = stream.ends[-1]
    fit_raw, complete_raw = games[n-1]['end_raw'], games[-1]['end_raw']
    require(dataset['fit_step_end'] == fit_steps and dataset['fit_end_raw'] == fit_raw
        and dataset['fit_memory'] == stream.moments[n-1]['memory'],
        'new FIT boundary and observational tracker exclude heldout and unfinished tail')
    require(dataset['actor_memory_A_end'] == pooled_memory(RAW, stream.fours), 'new observational tracker includes all paid initial and tail ranks')
    expected = dict(full_A_raw_tiles=RAW, fit_raw_tiles=fit_raw, heldout_raw_tiles=complete_raw-fit_raw,
        fit_steps=fit_steps, heldout_steps=complete_steps-fit_steps,
        excluded_tail_games=int(complete_raw < RAW), excluded_tail_raw_tiles=RAW-complete_raw,
        excluded_tail_steps=stream.state['post_action_spawns']-complete_steps, warmup_raw_tiles=0,
        reconstructed_chunks=stream.chunks, warmup_environment_counts={}, warmup_direct_counts={}, warmup_memory_counts={})
    require(all(dataset['costs'][key] == value for key, value in expected.items())
        and dataset['costs']['full_A_acquisition_counts'] == stream.snapshot['training']['counts'],
        'new acquisition has no repeated warmup and pays all initial tiles and unfinished tails')
    require(Counter(dataset['costs']['processing_counts']) == stream.processing
        and dataset['costs']['processing_memory_counts'] == pooled_memory(RAW, stream.fours)['counts']
        and dataset['costs']['processing_cpu_seconds'] == stream.snapshot['reconstruction']['cpu_seconds'],
        'new dataset retains its actual independent physical and observational reconstruction work')
    return n


def check_new_fit(fit, dataset, stream):
    n = dataset['fit_game_count']; games = stream.games[:n]
    steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games); samples = steps-wins
    require(fit['method'] == 'LOCAL_RISK' and fit['alpha'] == .0025 and fit['frozen_game_start_targets']
        and fit['fitted_games'] == n and fit['fitted_steps'] == dataset['fit_step_end'] == steps
        and fit['trained_afterstates'] == fit['reward_trained_afterstates'] == fit['risk_trained_afterstates'] == samples,
        'both new LOCAL heads retain the unchanged method and complete-game nonwinning FIT samples')
    check_split_counts(fit, 'LOCAL_RISK', n, steps, wins, samples)
    work, norm = Counter(fit['learning_counts']), Counter(fit['normalization_counts'])
    writes = norm['game_unique_addresses']; products = norm['reward_gradient_products']
    require(n <= writes <= 32*samples and samples <= products <= 32*samples,
        'new normalization work falls within actual nonempty game and sample address inventories')
    expected = dict(td_updates=samples, value_predictions=samples, table_lookups=64*samples,
        table_updates=2*writes, table_update_occurrences=32*samples, reward_predictions=samples,
        risk_predictions=samples, reward_table_lookups=32*samples, risk_table_lookups=32*samples,
        reward_table_updates=writes, risk_parameter_updates=writes)
    require(work == Counter(expected), 'new complete reward/risk training counts each actual parameter commit')
    known = dict(games_processed=n, feature_extractions=samples, feature_occurrences=32*samples,
        feature_digit_reads=192*samples, feature_address_multiply_adds=192*samples, sort_calls=n+samples,
        sort_items=64*samples, denominator_occurrence_visits=32*samples,
        reward_gradient_accumulations=products, risk_gradient_products=products, risk_gradient_accumulations=products,
        global_denominator_accumulations=0, normalization_divisions=2*writes, parameter_update_multiplications=2*writes,
        game_parameter_commits=n, reward_game_commits=n, risk_game_commits=n,
        reward_parameter_writes=writes, risk_parameter_writes=writes, global_zero_denominators=0,
        address_denominator_searches=products)
    require(all(norm[key] == value for key, value in known.items()), 'new game-start occurrence normalization work remains unchanged')
    for key, index in (('first_sample', 0), ('last_sample', n-1)):
        sample, game, moments = fit[key], games[index], stream.moments[index]
        expected_step = 0 if index == 0 else dataset['fit_step_end']-1-(game['status'] == 'WON')
        reward_target = (game['score']-moments['first_score'])/2048. if index == 0 else \
            moments['last_score']/2048. if game['status'] == 'WON' else 0.
        y, p = float(game['status'] == 'WON'), sample['risk_probability']
        require(sample['episode'] == index and sample['step'] == expected_step
            and sample['reward_target'] == reward_target and sample['risk_target'] == y,
            'new first and last factual targets exclude current reward and terminal bonus')
        require(0. <= p <= 1. and close(sample['risk_error'], y-p)
            and close(sample['reward_error'], reward_target-sample['reward_prediction'])
            and close(sample['combined_prediction'], sample['reward_prediction']+8.*(p-.5)),
            'new frozen game-start component predictions and residuals retain their numerical definition')
    return samples


def read_canonical(document, previous):
    lives = {life['lifecycle']:life for life in document['by_lifecycle']}
    old_lives = {life['lifecycle']:life for life in previous['by_lifecycle']}
    streams = {}; rows_read = 0
    require([parent['parent'] for parent in document['parent_receipts']] == list(range(4)), 'four frozen SOURCE parents')
    for parent in document['parent_receipts']:
        ids = list(range(parent['parent'], 64, 4))
        require(parent['lifecycle_ids'] == ids, 'all sixteen paired actor lives belong to their original SOURCE parent')
        path = Path(parent['trace_file'])
        require(path.stat().st_size == parent['trace_bytes'], 'closed new actor canonical trace size')
        for life in ids:
            for arm in DATA_ARMS:
                updates = 0 if arm == 'SOURCE_DATA' else old_lives[life]['stages']['A1']['arms']['LOCAL_RISK']['head_updates_after']
                streams[life, arm] = PhysicalStream(life, arm, lives[life]['evaluation_belief'], updates)
        with gzip.open(path, 'rt') as source:
            for line in source:
                row = json.loads(line); rows_read += 1; key = (row['lifecycle'], row['arm'])
                require(key in streams and row['lifecycle'] in ids and row['parent'] == parent['parent'],
                    'new canonical actor life and SOURCE parent membership')
                if row['kind'] == 'TRAIN':
                    streams[key].train(row)
                else:
                    require(row['kind'] == 'ACQUISITION_SNAPSHOT', 'only fixed-policy training and its closed raw snapshot are canonical')
                    streams[key].checkpoint(row)
    require(set(streams) == {(life, arm) for life in range(64) for arm in DATA_ARMS}
        and all(stream.snapshot is not None for stream in streams.values()), 'all 128 new actor histories are naturally closed at their raw budgets')
    return streams, rows_read


def check_evaluation(value, life, belief):
    games = value['game_summaries']; counts = value['counts']
    require(value['estimated_p_four'] == belief['estimated_p_four'] and value['static_evaluation_valid'],
        'new A evaluation keeps original observed A1 belief and static parameters')
    require(len(games) == 32 and [game['seed'] for game in games] == [306900000000+life*1000000+i for i in range(32)],
        'all four policies use the same 32 genuinely new A evaluation seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'new complete-game evaluation horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and max(game['final_board']) < 11, 'evaluation cutoff cannot hide a terminal goal or short game')
            bonus = 0.
        else:
            terminal(game['final_board'], game['status']); bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'new full-game utility retains score and natural terminal bonus')
    steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games)
    expected = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=64,
        raw_tile_productions=steps+64, environment_random_draws=2*(steps+64), ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+32, ground_status_internal_swipe_calls=4*(steps+32-wins),
        ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(counts['environment']) == Counter(expected), 'all new evaluation initial and terminal raw tiles are counted')
    planning_counts(counts['planning'], steps)
    check_representation(value['representation_counts'], 'LOCAL_RISK', counts['planning'].get('value_predictions', 0))
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games), wins=wins,
        losses=sum(game['status'] == 'LOST' for game in games), cutoffs=sum(game['status'] == 'CUTOFF' for game in games),
        cutoff_episodes=[i for i, game in enumerate(games) if game['status'] == 'CUTOFF'], steps=steps)


def check_initialization(life, previous):
    initial = previous['stages']['A1']['arms']['LOCAL_RISK']
    require(life['lifecycle'] == previous['lifecycle'] and life['parent'] == previous['parent']
        and life['evaluation_belief'] == previous['evaluation_beliefs']['A'],
        'all four policies inherit the same retained A1 parent and original observed belief')
    check_belief(life['evaluation_belief'], previous['stages']['A1']['dataset'])
    equal_tree(scientific_receipt(life['initial_fit']), scientific_receipt(initial['fit']),
        'full initial reward/risk fit reproduces V303 A1 numerical samples and all normalization work')
    require(set(life['arms']) == set(ARMS) and set(life['datasets']) == set(life['acquisitions']) == set(DATA_ARMS),
        'four frozen policy arms and two genuinely new actor data inventories')
    require(life['initial_head_setup'] == life['arms']['A1_FROZEN']['head_setup'],
        'initial A1 carrier and frozen reference share one physical head allocation')
    for arm in ARMS:
        setup = life['arms'][arm]['head_setup']; check_new_head(setup)
        counts = setup['setup_counts']; size = counts['source_parameters_copied']
        if arm in DATA_ARMS:
            require(counts['a1_parameters_copied'] == 2*size and counts['a1_weight_bytes_copied'] == 16*size,
                'both learners copy the same complete A1 reward and risk parameters')
        else:
            require(counts.get('a1_parameters_copied', 0) == counts.get('a1_weight_bytes_copied', 0) == 0,
                'SOURCE and original A1 carrier have no duplicated learner-copy work')
    return initial['head_updates_after']


def check_lifecycle(life, previous, streams):
    initial_updates = check_initialization(life, previous)
    for arm in DATA_ARMS:
        stream = streams[life['lifecycle'], arm]; check_dataset(life['datasets'][arm], stream)
        acquisition = life['acquisitions'][arm]
        require(acquisition['warmup'] == dict(raw_tiles=0, environment_counts={}, direct_counts={}, memory_counts={})
            and acquisition['new_actor_updates'] == 0,
            'fixed-policy actors add no new warmup and receive no learning update during data acquisition')
        for key in ('training', 'snapshot', 'reconstruction'):
            require(acquisition[key] == stream.snapshot[key], 'new actual acquisition matches its closed canonical '+key)
    require(streams[life['lifecycle'], 'SOURCE_DATA'].ranks == streams[life['lifecycle'], 'CURRENT_DATA'].ranks,
        'paired continuous raw seeds produce the same rank draws even when policy boards and spawn cells differ')
    endpoints = {}; cutoffs = 0; new_samples = Counter()
    for arm in ARMS:
        value = life['arms'][arm]; fit = value['fit']; before = 0 if arm == 'SOURCE' else initial_updates
        if arm in DATA_ARMS:
            samples = check_new_fit(fit, life['datasets'][arm], streams[life['lifecycle'], arm])
        else:
            require(fit['method'] == 'NONE' and fit['trained_afterstates'] == 0
                and not fit['learning_counts'] and not fit['target_counts'], 'SOURCE and A1 references are not fitted again')
            samples = 0
        require(value['head_updates_before'] == before and value['head_updates_after'] == before+samples,
            'each learner continues its identical A1 history exactly once on its own new complete games')
        endpoints[arm] = check_evaluation(value['evaluation'], life['lifecycle'], life['evaluation_belief'])
        new_samples[arm] = samples; cutoffs += endpoints[arm]['cutoffs']
    return dict(lifecycle=life['lifecycle'], parent=life['parent'], arms=endpoints), new_samples, cutoffs


def check_contrast(saved, values):
    require(len(values) == 64 and close(saved['mean'], mean(values)), 'signed equal-life paired policy-data means')
    equal_tree(saved['lifecycle_deltas'], {str(i):value for i, value in enumerate(values)}, 'all adverse actor-data lives remain retained')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'], {str(parent):mean(group) for parent, group in enumerate(groups)}, 'four frozen-parent paired actor-data means')
    low, high = saved['ci95']
    require(saved['interval_scope'] == INTERVAL_SCOPE
        and mean(min(group) for group in groups)-1e-10 <= low <= high <= mean(max(group) for group in groups)+1e-10,
        'actor-data interval remains conditional on four original parents and retained A1 histories')
    require(saved['improved_equal_worse'] == [sum(v > 0. for v in values), sum(v == 0. for v in values), sum(v < 0. for v in values)]
        and saved['adverse_lifecycles'] == [i for i, value in enumerate(values) if value < 0.], 'negative actor-data effects are preserved')


def check_support(summary, cutoffs):
    complete = cutoffs == 0
    supported = complete and summary['paired_contrasts'][PRIMARY]['ci95'][0] > 0.
    low, high = summary['paired_contrasts']['CURRENT_DATA_minus_A1_FROZEN']['ci95']
    retention = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else 'SUPPORTED_NONDECREASE' if low >= 0.
        else 'SUPPORTED_LOSS' if high < 0. else 'UNRESOLVED')
    gains = {arm:complete and summary['paired_contrasts'][arm+'_minus_SOURCE']['ci95'][0] > 0.
        for arm in ('A1_FROZEN', 'SOURCE_DATA', 'CURRENT_DATA')}
    require(summary['complete_game_endpoints'] == complete and summary['primary_policy_data_gain_supported'] == supported,
        'current-policy data advantage requires positive primary interval and complete endpoints')
    require(summary['primary_policy_data_gain_status'] == ('SUPPORTED_' if supported else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        'primary support remains conditional on fixed original sources and A1 histories')
    require(summary['current_policy_retention_status'] == retention and summary['current_policy_no_degradation_supported']
        == (retention == 'SUPPORTED_NONDECREASE'), 'advantage over source-policy data does not imply retention of A1 capability')
    require(summary['source_reference_gain_supported'] == gains, 'gains over original SOURCE remain separate from actor-data and retention claims')


def check_result_summary(summary, records, cutoffs):
    equal_tree(summary['by_lifecycle'], records, 'all four new same-seed A policy endpoints')
    require(summary['primary_contrast'] == PRIMARY and summary['bootstrap_draws'] == 20000 and summary['bootstrap_seed'] == 30600001,
        'fixed actor-data primary and conditional bootstrap')
    require(summary['estimator'] == 'EQUAL_A_EVALUATION_GAMES_THEN_LIFECYCLES'
        and summary['heldout_estimator'] == 'EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES_SEPARATELY_BY_DATASET',
        'new complete A game utility and dataset-specific prediction estimators stay frozen')
    for arm in ARMS:
        values = [row['arms'][arm] for row in records]
        expected = dict(mean_game_utility=mean(value['mean_game_utility'] for value in values),
            **{key:sum(value[key] for value in values) for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')})
        equal_tree(summary['arms'][arm], expected, 'equal evaluation game then lifecycle utility '+arm)
    require(set(summary['paired_contrasts']) == {left+'_minus_'+right for left, right in PAIRS}, 'all data-policy SOURCE and A1 contrasts')
    for left, right in PAIRS:
        check_contrast(summary['paired_contrasts'][left+'_minus_'+right],
            [row['arms'][left]['mean_game_utility']-row['arms'][right]['mean_game_utility'] for row in records])
    require(not summary.get('heldout_by_dataset', {}), 'the frozen actor-data experiment does not invent unsupplied prediction diagnostics')
    check_support(summary, cutoffs)


def check_training_budget(account, old):
    inherited = old['accounting']['inherited_costs_per_arm']['SOURCE']
    raw = sum(life['stages']['A1']['acquisition']['warmup']['raw_tiles']
        +life['stages']['A1']['acquisition']['training']['raw_tiles'] for life in old['by_lifecycle'])
    base = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+raw
    new_raw = dict.fromkeys(DATA_ARMS, 64*RAW)
    expected = {arm:base+new_raw.get(arm, 0) for arm in ARMS}
    require(account['inherited_a1_raw_tiles'] == raw and account['inherited_costs_per_arm'] == dict.fromkeys(ARMS, inherited),
        'all references and learners pay the same original SOURCE dynamics and complete retained A1 observations')
    require(account['new_training_raw_tiles_by_actor'] == new_raw
        and account['new_training_environment_observations'] == 64*2*RAW and account['physical_acquisitions'] == 128,
        'two physically distinct actor cohorts each pay exactly 131072 raw including all initial and tail tiles')
    require(account['economic_training_raw_tiles_per_arm'] == expected and not account['historical_total_compute_closed'],
        'only updating learners pay their own new cohort and unavailable original historical CPU remains explicit')
    return expected


def check_accounting(document, old, old_audit, canonical_rows):
    account = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    economic = check_training_budget(account, old)
    acquisitions = [life['acquisitions'][arm] for life in lives for arm in DATA_ARMS]
    initial = [life['initial_fit'] for life in lives]
    require(account['new_evaluation_games'] == 8192
        and account['initial_replayed_training_samples'] == sum(value['trained_afterstates'] for value in initial)
        and account['initial_refit_counts'] == sum_counts(value['learning_counts'] for value in initial)
        and close(account['initial_refit_cpu_seconds'], sum(value['cpu_seconds'] for value in initial)),
        'actual A1 refitting and all genuinely new evaluation games are paid once')
    fields = (('new_training_environment_counts', 'training', 'counts', 'environment'),
        ('new_acquisition_planning_counts', 'training', 'counts', 'planning'))
    for field, section, key, kind in fields:
        require(account[field] == sum_counts(value[section][key][kind] for value in acquisitions), 'actual '+field)
    require(account['new_acquisition_representation_counts'] == sum_counts(value['training']['representation_counts'] for value in acquisitions)
        and account['new_acquisition_setup_counts'] == sum_counts(value['native_setup_counts'] for value in acquisitions)
        and close(account['new_acquisition_cpu_seconds'], sum(value['cpu_seconds'] for value in acquisitions)),
        'actual full reward/risk actor representation native setup and acquisition CPU')
    require(account['new_reconstruction_counts'] == sum_counts(value['reconstruction']['counts'] for value in acquisitions)
        and account['new_reconstruction_memory_counts'] == sum_counts(value['reconstruction']['memory_counts'] for value in acquisitions)
        and close(account['new_reconstruction_cpu_seconds'], sum(value['reconstruction']['cpu_seconds'] for value in acquisitions)),
        'all actual new physical reconstruction and observational POOLED work is paid')
    require(account['excluded_tail_raw_tiles_by_actor'] == {arm:sum(life['datasets'][arm]['costs']['excluded_tail_raw_tiles'] for life in lives)
        for arm in DATA_ARMS}, 'both unfinished actor tails remain paid despite exclusion from labels')
    work_fields = (('fit_counts', 'learning_counts'), ('fit_target_counts', 'target_counts'),
        ('fit_normalization_counts', 'normalization_counts'), ('fit_representation_counts', 'representation_counts'), ('fit_setup_counts', 'setup_counts'))
    for arm in ARMS:
        values = [life['arms'][arm] for life in lives]; fits = [value['fit'] for value in values]
        evaluations = [value['evaluation'] for value in values]; setups = [value['head_setup'] for value in values]
        require(account['new_processed_training_samples'][arm] == sum(fit['trained_afterstates'] for fit in fits)
            and account['final_cumulative_updates'][arm] == sum(value['head_updates_after'] for value in values),
            'new actor-specific fitted samples and inherited plus new cumulative histories remain separate')
        for field, key in work_fields:
            rows = [fit.get(key, {}) for fit in fits]
            require(account[field][arm] == sum_counts(nonpeak(row) for row in rows), 'actual '+arm+' '+field)
            peaks = {name:max(row.get(name, 0) for row in rows)
                for name in {name for row in rows for name in row if name.endswith('_peak')}}
            require(account[field+'_buffer_peaks'][arm] == peaks, 'actual '+arm+' '+field+' buffer peaks')
        require(account['private_head_weight_bytes_created'][arm] == sum(value['private_weight_bytes'] for value in setups)
            and account['head_setup_counts'][arm] == sum_counts(value['setup_counts'] for value in setups)
            and close(account['head_setup_cpu_seconds'][arm], sum(value['setup_cpu_seconds'] for value in setups)),
            'four actual heads and extra A1 reward/risk copies count each allocation exactly once')
        require(close(account['fit_cpu_seconds'][arm], sum(value['cpu_seconds'] for value in fits))
            and close(account['evaluation_cpu_seconds_per_arm'][arm], sum(value['cpu_seconds'] for value in evaluations))
            and account['evaluation_representation_counts'][arm] == sum_counts(value['representation_counts'] for value in evaluations),
            'actual new fit and full reward/risk evaluation representation and CPU work')
        for kind in ('environment', 'planning'):
            require(account['evaluation_counts_per_arm'][arm][kind] == sum_counts(value['counts'][kind] for value in evaluations),
                'actual new per-arm '+kind+' evaluation work')
    for kind in ('environment', 'planning'):
        require(account['evaluation_counts'][kind] == sum_counts(account['evaluation_counts_per_arm'][arm][kind] for arm in ARMS),
            'all four new evaluation '+kind+' costs')
    require(canonical_rows == 128*(RAW//CHUNK_RAW+1)
        and account['canonical_trace_bytes'] == sum(parent['trace_bytes'] for parent in parents), 'all 65664 new canonical actor records are retained')
    for parent in parents:
        reconstruction = parent['initial_reconstruction']
        require(parent['source_setup']['checkpoint_loads'] == 1 and parent['source_setup']['new_leaf_updates'] == 0
            and reconstruction['stages'] == 16, 'original SOURCE is loaded once and exactly sixteen old A1 stages are reconstructed')
    require(sum(parent['initial_reconstruction']['canonical_rows_read'] for parent in parents) == old_audit['canonical_rows']
        and account['initial_reconstruction_counts'] == sum_counts(parent['initial_reconstruction']['counts'] for parent in parents)
        and close(account['initial_reconstruction_cpu_seconds'], sum(parent['initial_reconstruction']['cpu_seconds'] for parent in parents)),
        'actual old A1 input reconstruction work is paid without rereading it in this audit')
    for field in ('worker_cpu_seconds', 'compiler_cpu_seconds'):
        key = 'cpu_seconds' if field == 'worker_cpu_seconds' else field
        require(close(account[field], sum(parent[key] for parent in parents)), 'actual new '+field+' aggregate')
    return economic


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(document['schema'] == 'acfqp.policy_data.v306' and document['status'] == 'EXPERIMENT_COMPLETE',
        'complete new actor-data terminal document')
    equal_tree(settings, json_file(directory/'configuration.json'), 'unchanged pre-run V306 configuration')
    expected = dict(lifecycles=list(range(64)), parents=4, arms=list(ARMS), actors=list(DATA_ARMS), retained_stage='A1',
        true_p_four=.1, raw_budget_per_actor=RAW, chunk_raw=CHUNK_RAW, fit_fraction=.8, alpha=.0025,
        query=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.),
        representation='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_RISK',
        actor_policy='FULL_SPLIT_H2_WITH_FROZEN_REWARD_AND_RISK',
        actor_initializations=dict(SOURCE_DATA='ORIGINAL_SOURCE_ZERO_RISK', CURRENT_DATA='FROZEN_RETAINED_A1'),
        learner_initialization='IDENTICAL_RETAINED_A1_REWARD_AND_RISK_COPIES',
        planning_probability='FIXED_ORIGINAL_A1_OBSERVED_BELIEF_FOR_BOTH_ACTORS_AND_ALL_EVALUATIONS',
        observations='TWO_NEW_A_COHORTS_FROM_PAIRED_CONTINUOUS_RAW_RNG_STREAMS',
        seed_training=306200000000, seed_evaluation=306900000000, evaluation_games=32, max_steps=8192,
        bootstrap_draws=20000, bootstrap_seed=30600001, primary=PRIMARY,
        retention='CURRENT_DATA_minus_A1_FROZEN_CI_LOWER_NONNEGATIVE', interval_scope=INTERVAL_SCOPE,
        new_training_raw_tiles=64*2*RAW, new_evaluation_games=8192,
        stop_rule='NO_ACTOR_INITIALIZATION_ALPHA_OR_SEED_TUNING_ON_THESE_NEW_COHORTS')
    for key, value in expected.items():
        require(settings[key] == value, 'registered fixed-policy actor-data V306 '+key)
    old = json_file(settings['source_summary']); old_audit = json_file(Path(settings['source_summary']).with_name('audit.json'))
    require(old['schema'] == 'acfqp.continual.v303' and old_audit['status'] == 'PASS' and old_audit['independent_valid'],
        'settled original A1 complete canonical worlds and numerical source controls')
    require(document['source_provenance'] == old['source_provenance'], 'unchanged original SOURCE parents and learned deterministic dynamics')
    lives = document['by_lifecycle']
    require([life['lifecycle'] for life in lives] == list(range(64)) and all(life['parent'] == life['lifecycle']%4 for life in lives),
        'all 64 new matched actor-data lifecycles retain their fixed original parents')
    streams, canonical_rows = read_canonical(document, old)
    records = []; processed = Counter(); cutoffs = 0
    for life, previous in zip(lives, old['by_lifecycle']):
        record, samples, ncutoffs = check_lifecycle(life, previous, streams)
        records.append(record); processed.update(samples); cutoffs += ncutoffs
    check_result_summary(document['summary'], records, cutoffs)
    economic = check_accounting(document, old, old_audit, canonical_rows)
    return dict(status='PASS', independent_valid=True, lifecycles=64, fixed_source_parents=4,
        new_actor_histories=128, canonical_rows=canonical_rows, new_training_environment_observations=64*2*RAW,
        new_evaluation_games=8192, distinct_evaluation_seed_conditions=2048, evaluation_cutoffs=cutoffs,
        new_processed_training_samples=dict(processed), economic_training_raw_tiles_per_arm=economic,
        actual_new_parameter_writes={arm:document['accounting']['fit_counts'][arm].get('table_updates', 0) for arm in ARMS},
        primary_policy_data_gain_supported=document['summary']['primary_policy_data_gain_supported'],
        current_policy_retention_status=document['summary']['current_policy_retention_status'],
        current_policy_no_degradation_supported=document['summary']['current_policy_no_degradation_supported'],
        source_reference_gain_supported=document['summary']['source_reference_gain_supported'],
        primary_utility=document['summary']['paired_contrasts'][PRIMARY], historical_total_compute_closed=False,
        method='Independent compression/merge and legal-spawn replay of every new raw record, full game and prefix/tail labels, '
            'fixed observed A1 belief and actor histories, paired continuous rank draws, independent POOLED statistics, '
            'factual suffix targets and normalization identities, new terminal-game means and actual physical/compute costs.',
        limitations='Original retained A1 world integrity is inherited without rereading its tapes. No parameter refit, '
            'per-action policy recomputation, raw RNG regeneration or new bootstrap draws; saved intervals are checked '
            'for scope and feasible range. Actor-data policies change trajectories and factual labels together. '
            'Initial A1 histories and sources remain fixed; B retention is not evaluated and full independent method '
            'confirmation is not established. Historical interrupted V303 CPU remains unavailable.', errors=[])


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
