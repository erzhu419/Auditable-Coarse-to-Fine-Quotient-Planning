#!/usr/bin/env python3
"""Independent V313 sparse-head linkage and literal frozen-policy tape audit."""
import argparse
from collections import Counter, deque, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import math
import gzip
import random
from statistics import mean

import numpy as np

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_fresh_source_v312 import ACTIONS, PATTERNS
from verify_policy_data_v306 import swipe, pooled_memory, board_status
from verify_natural_online_value_v286 import planning_counts, Memory
from verify_split_risk_v301 import check_representation
from verify_fresh_confirmation_v312 import (check_linear_representation, check_source_target_compute,
    check_detection_route, check_fresh_source_document)
from verify_context_continual_v305 import observed_statistics
from verify_continual_v303 import check_belief, check_stage_split
from verify_stable_b_v298 import learned

TASKS = ('A', 'B')
PROBABILITIES = {'A': .1, 'B': .5}
INITIAL_RAW = 131072
POST_RAW = 65536
CHUNK_RAW = 256
PROBE_ACTIONS = 8
STAGES = ('A0', 'B0')
RAW = INITIAL_RAW
DETECTOR_CAP = 4096
ARMS = ('SOURCE', 'FIRST_LOCAL', 'FIRST_LINEAR', 'FIXED_LOCAL', 'CLOSED_LOCAL', 'CLOSED_LINEAR')
UPDATING_ARMS = ARMS[3:]
DIRECT_ARMS = ('FIRST_LOCAL', 'FIRST_LINEAR', 'CLOSED_LOCAL', 'CLOSED_LINEAR')
PAIRS = (('CLOSED_LOCAL', 'FIRST_LOCAL'), ('CLOSED_LOCAL', 'FIXED_LOCAL'), ('CLOSED_LOCAL', 'CLOSED_LINEAR'),
    ('CLOSED_LOCAL', 'SOURCE'), ('CLOSED_LINEAR', 'FIRST_LINEAR'), ('CLOSED_LINEAR', 'SOURCE'))
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def stage_context(row):
    require(row['phase'] in STAGES and row['true_p_four'] == PROBABILITIES[row['phase'][0]],
        'new initial A0/B0 world metadata follows the frozen two-task probabilities')


def warmup_seed(life, stage, game):
    return 313100000000+STAGES.index(stage)*100000+life*1000000+game


def training_seed(life, stage):
    return 313200000000+STAGES.index(stage)*100000+life*10000000


def post_seed(life, task, round_index):
    return 313500000000+life*10000000+TASKS.index(task)*1000000+round_index*100000


def evaluation_seed(life, task, episode):
    return 313900000000+life*1000000+TASKS.index(task)*100000+episode


def physical_status(board, radix=11):
    if max(board) >= radix:
        return 'WON'
    if 0 in board or any(board[4*r+c] == board[4*r+c+1] for r in range(4) for c in range(3)) \
            or any(board[4*r+c] == board[4*(r+1)+c] for r in range(3) for c in range(4)):
        return 'ACTIVE'
    return 'LOST'


class TileRandom:
    """Literal mt19937_64 and the existing upper-53-bit raw-tile uniforms."""
    def __init__(self, seed):
        self.words = [int(seed)]
        for index in range(1, 312):
            before = self.words[-1]
            self.words.append((6364136223846793005*(before^(before >> 62))+index)&((1 << 64)-1))
        self.index = 312

    def random(self):
        if self.index == 312:
            for index in range(312):
                merged = (self.words[index]&0xffffffff80000000)|(self.words[(index+1)%312]&0x7fffffff)
                self.words[index] = self.words[(index+156)%312]^(merged >> 1) \
                    ^(0xb5026f5aa96619e9 if merged&1 else 0)
            self.index = 0
        value = self.words[self.index]; self.index += 1
        value ^= (value >> 29)&0x5555555555555555
        value ^= (value << 17)&0x71d67fffeda60000
        value ^= (value << 37)&0xfff7eee000000000
        value ^= value >> 43
        return (value >> 11)*2.**-53


def seeded_place(board, spawn, rng, probability):
    empty = [index for index, value in enumerate(board) if not value]
    require(empty, 'actual raw spawn requires an empty physical cell')
    expected = (empty[int(rng.random()*len(empty))], 1 if rng.random() < 1.-probability else 2)
    require((spawn['cell'], spawn['rank']) == expected,
        'new continuous seed determines every initial and post-action cell/rank draw')
    board[spawn['cell']] = spawn['rank']


def read_source_weights(path):
    with np.load(path, allow_pickle=False) as data:
        metadata = json.loads(str(data['metadata']))
        require(metadata['schema'] == 'controlled_predictive_ntuple_td_v120'
            and metadata['radix'] == 11, 'V313 starts at the actual fresh V312 SOURCE value checkpoint')
        size = 4*11**6
        weights = np.zeros(size, dtype=np.float64)
        weights[data['indices']] = data['values']
    return weights


class HeadVersions:
    """Reassemble one actual private head from SOURCE/default and absolute sparse writes."""
    def __init__(self, source, source_checkpoint, identity, kind):
        require(kind in ('LOCAL_RISK', 'LINEAR_WIN2'), 'V313 active two-table head kind')
        self.identity, self.kind = dict(identity), kind
        self.source_checkpoint = str(source_checkpoint)
        self.reward = np.asarray(source, dtype=np.float64).reshape(-1).copy()
        self.default_terminal = 0. if kind == 'LOCAL_RISK' else 1./64.
        self.terminal = np.full_like(self.reward, self.default_terminal)
        self.version, self.file = -1, None
        self.receipts = []

    def apply(self, receipt):
        initial_arm = 'FIRST_LOCAL' if self.kind == 'LOCAL_RISK' else 'FIRST_LINEAR'
        expected_arm = initial_arm if receipt['version'] == 0 else self.identity['arm']
        require(receipt['schema'] == 'acfqp.head_version.v313' and receipt['head_kind'] == self.kind
            and all(receipt[key] == value for key, value in self.identity.items() if key != 'arm')
            and receipt['arm'] == expected_arm
            and receipt['version'] == self.version+1 and receipt['base_file'] == self.file
            and receipt['source_checkpoint'] == self.source_checkpoint
            and receipt['default_terminal'] == self.default_terminal,
            'actual head versions retain their own arm/context/SOURCE and sequential previous-weight base')
        path = Path(receipt['file'])
        require(path.stat().st_size == receipt['saved_bytes'], 'every actual sparse head receipt retains its physical saved bytes')
        with np.load(path, allow_pickle=False) as data:
            require(set(data.files) == {'reward_indices', 'reward_values', 'terminal_indices', 'terminal_values', 'metadata_json'},
                'actual head versions contain exactly both sparse tables and their ownership metadata')
            metadata_keys = ('schema', 'head_kind', 'lifecycle', 'parent', 'context_id', 'arm', 'version',
                'updates', 'file', 'base_file', 'source_checkpoint', 'default_terminal', 'parameter_count',
                'reward_indices_count', 'terminal_indices_count')
            equal_tree(json.loads(str(data['metadata_json'])), {key: receipt[key] for key in metadata_keys},
                'actual sparse head file ownership metadata')
            for name, weights in (('reward', self.reward), ('terminal', self.terminal)):
                indices, values = data[name+'_indices'], data[name+'_values']
                require(indices.dtype == np.int64 and values.dtype == np.float64 and indices.ndim == values.ndim == 1
                    and len(indices) == len(values) == receipt[name+'_indices_count']
                    and np.all((0 <= indices)&(indices < weights.size))
                    and np.all(indices[1:] > indices[:-1]) and np.all(np.isfinite(values)),
                    'head sparse writes are the actual distinct sorted table addresses and values')
                require(np.all(weights[indices] != values), 'each sparse head write changes its declared previous actual parameter')
                weights[indices] = values
        require(receipt['scan_parameters'] == self.reward.size+self.terminal.size,
            'both complete physical parameter tables are scanned once per version receipt')
        copied = 0 if receipt['version'] == 0 else self.reward.size+self.terminal.size
        require(receipt['parameter_count'] == self.reward.size and receipt['copy_parameters'] == copied
            and receipt['copy_bytes'] == 8*copied
            and receipt['changed_parameters'] == receipt['reward_indices_count']+receipt['terminal_indices_count'],
            'actual comparison snapshot copies and sparse changed-weight inventory are charged once')
        self.version, self.file = receipt['version'], str(path)
        self.receipts.append(deepcopy(receipt))

    @property
    def changed_parameters(self):
        row = self.receipts[-1]
        return row['reward_indices_count']+row['terminal_indices_count']


def component_value(board, reward, terminal, kind, radix=11):
    addresses = np.zeros(32, dtype=np.int64)
    cells = np.asarray(board, dtype=np.int64)
    for digit in range(6):
        addresses = radix*addresses+cells[PATTERNS[:, digit]]
    addresses += (np.arange(32)//8)*radix**6
    r = sum(float(reward[index]) for index in addresses)
    t = sum(float(terminal[index]) for index in addresses)
    if kind == 'LOCAL_RISK':
        t = 1./(1.+math.exp(-t)) if t >= 0. else math.exp(t)/(1.+math.exp(t))
    require(kind in ('LOCAL_RISK', 'LINEAR_WIN2'), 'actual LOCAL or active unclipped LINEAR head')
    return r+8.*(t-.5)


def literal_choose(board, reward, terminal, kind, probability, depth='H2', radix=11):
    """Independent swipe/expectation/terminal traversal over the reconstructed actual weights."""
    require(depth in ('DIRECT', 'H2'), 'same learned head executes DIRECT or full H2')
    if max(board) >= radix:
        return dict(action=None, value=4., action_values={})

    def direct(position):
        choices = {}
        for action in ACTIONS:
            after, score = swipe(position, action)
            if after != list(position):
                tail = 4. if max(after) >= radix else component_value(after, reward, terminal, kind, radix)
                choices[action] = dict(afterstate=after, score=score, tail_value=tail, value=score/2048.+tail)
        return choices

    choices = direct(board)
    if depth == 'H2':
        for row in choices.values():
            after = row['afterstate']
            if max(after) >= radix:
                continue
            empty = [index for index, value in enumerate(after) if not value]; expectation = 0.
            for index in empty:
                for rank in (1, 2):
                    spawned = list(after); spawned[index] = rank
                    inner = direct(spawned)
                    tail = max(value['value'] for value in inner.values()) if inner else -4.
                    expectation += ((1.-probability if rank == 1 else probability)/len(empty))*tail
            row['tail_value'] = expectation; row['value'] = row['score']/2048.+expectation
    if not choices:
        return dict(action=None, value=-4., action_values={})
    selected = max(choices, key=lambda action: choices[action]['value'])
    return dict(action=selected, **choices[selected], action_values=choices)


def check_actor_link(row, expected):
    require(all(row[key] == value for key, value in expected.items()),
        'whole collection batch uses the actual declared own context and frozen head version')
    require(not row['counts']['learning'] and not row['bank_update_counts'] and not row['td_examples'],
        'batch actor is frozen until all physical collection chunks finish')


class BatchWorld:
    """One new continuous post-initial stream, with all labels and fixed action probes."""
    def __init__(self, seed, raw_budget, probability, expected_identity, kind, radix=11):
        self.seed, self.raw_budget, self.probability = seed, raw_budget, probability
        self.expected_identity, self.kind, self.radix = dict(expected_identity), kind, radix
        self.rng = TileRandom(seed)
        self.state = self.before = None
        self.games, self.scores, self.ends, self.game_memories = [], [], [], []
        self.current_scores = []
        self.first_probes, self.last_probes = [], deque(maxlen=PROBE_ACTIONS)
        self.actions = self.chunks = self.fours = 0
        self.counts = {key: Counter() for key in ('environment', 'planning', 'learning')}
        self.representation = Counter()
        self.processing = Counter(); self.snapshot = None

    def train(self, row):
        check_actor_link(row, self.expected_identity)
        start, raw = row['start'], row['raw_spawns']
        require(start['stream_seed'] == self.seed and raw
            and len(raw) == min(CHUNK_RAW, self.raw_budget-start['raw_tiles']),
            'each fresh continuous batch pays exactly its raw chunk boundary')
        if self.state is None:
            require(start['raw_tiles'] == start['post_action_spawns'] == start['random_draw_position'] == 0
                and start['status'] == 'NOT_STARTED' and start['board'] == [0]*16
                and start['initial_count'] == 0 and start['pending_afterstate'] is start['pending_bank_id'] is None,
                'every post-initial batch starts a new physical stream')
            self.state = deepcopy(start); self.before = deepcopy(start)
        require(self.state == start, 'all actual raw chunks preserve batch state continuity')
        state = self.state; completed = []; action_index = starts = initializations = posts = wins = losses = cutoffs = 0
        for raw_index, spawn in enumerate(raw):
            if spawn['kind'] == 'INITIAL':
                if state['status'] != 'INITIALIZING':
                    require(state['status'] in ('NOT_STARTED', 'WON', 'LOST', 'CUTOFF'), 'initial raw spawn cannot reset an active game')
                    state.update(board=[0]*16, episode=state['episode']+1, step=0, return_score=0,
                        status='INITIALIZING', initial_count=0, game_start_raw=state['raw_tiles'],
                        pending_afterstate=None, pending_bank_id=None)
                    self.current_scores = []; starts += 1
                require(state['initial_count'] < 2, 'natural new game has exactly two paid initial tiles')
                state['initial_count'] += 1; initializations += state['initial_count'] == 2
            else:
                require(spawn['kind'] == 'POST_ACTION' and state['status'] == 'ACTIVE', 'every actual action begins on an active physical board')
                action, score = row['actions'][action_index], row['scores'][action_index]
                before = list(state['board']); after, actual_score = swipe(before, action)
                record = row['action_records'][action_index]
                require(after != before and score == actual_score and record['episode'] == state['episode']
                    and record['step'] == state['step'] and record['raw_index'] == raw_index,
                    'actual action records preserve independent legal swipe score and physical step identity')
                probe = dict(index=self.actions, board=before, action=action, score=score, value=record['h2_value'],
                    episode=state['episode'], step=state['step'], raw_index=state['raw_tiles'])
                if len(self.first_probes) < PROBE_ACTIONS:
                    self.first_probes.append(probe)
                self.last_probes.append(probe); self.actions += 1
                state['board'] = after; state['step'] += 1; state['return_score'] += score
                state['post_action_spawns'] += 1; self.current_scores.append(score)
                state['pending_afterstate'] = None if max(after) >= self.radix else list(after)
                state['pending_bank_id'] = None if max(after) >= self.radix else 0
                action_index += 1; posts += 1
            require(spawn['episode'] == state['episode'], 'raw rank belongs to its actual natural game')
            seeded_place(state['board'], spawn, self.rng, self.probability)
            self.fours += spawn['rank'] == 2
            state['raw_tiles'] += 1; state['random_draw_position'] += 2
            if state['initial_count'] == 2:
                state['status'] = physical_status(state['board'], self.radix)
                if state['status'] == 'ACTIVE' and state['step'] == 8192:
                    state['status'] = 'CUTOFF'
            if state['status'] in ('WON', 'LOST', 'CUTOFF'):
                state.update(pending_afterstate=None, pending_bank_id=None)
                game = dict(episode=state['episode'], stream_seed=self.seed, start_raw=state['game_start_raw'],
                    end_raw=state['raw_tiles'], steps=state['step'], score=state['return_score'], status=state['status'])
                completed.append(game); self.games.append(game); self.scores.append(self.current_scores)
                self.ends.append(state['post_action_spawns'])
                self.game_memories.append(pooled_memory(state['raw_tiles'], self.fours))
                wins += state['status'] == 'WON'; losses += state['status'] == 'LOST'; cutoffs += state['status'] == 'CUTOFF'
        require(action_index == len(row['actions']) == len(row['scores']) == len(row['action_records'])
            and completed == row['completed_games'] and state == row['end'],
            'every new whole-game label and paid tail ends at its literal physical raw boundary')
        expected = dict(sampled_transitions=posts, post_action_spawns=posts, initial_spawns=len(raw)-posts,
            raw_tile_productions=len(raw), environment_random_draws=2*len(raw), ground_explicit_swipe_calls=posts,
            ground_state_status_calls=posts+initializations, ground_status_internal_swipe_calls=4*(posts+initializations-wins),
            ground_swipe_calls=posts+4*(posts+initializations-wins), episodes_started=starts,
            episodes_completed=wins+losses+cutoffs, won_games=wins, lost_games=losses, cutoff_games=cutoffs)
        require(Counter(row['counts']['environment']) == Counter(expected), 'new collection costs include every initial winning and tail tile')
        planning_counts(row['counts']['planning'], posts)
        predictions = row['counts']['planning'].get('value_predictions', 0)
        if self.kind == 'LOCAL_RISK':
            check_representation(row['representation_counts'], self.kind, predictions)
        else:
            check_linear_representation(row['representation_counts'], predictions)
        for key in self.counts:
            self.counts[key].update(row['counts'][key])
        boundary = int(state['status'] not in ('NOT_STARTED', 'INITIALIZING'))
        internal = 4*(initializations+losses+int(boundary and state['status'] != 'WON'))
        self.processing.update(ground_explicit_swipe_calls=posts, ground_swipe_calls=posts+internal,
            ground_state_status_calls=initializations+wins+losses+boundary, ground_status_internal_swipe_calls=internal)
        self.representation.update(row['representation_counts']); self.chunks += 1

    def checkpoint(self, row):
        require(all(row[key] == value for key, value in self.expected_identity.items())
            and self.snapshot is None and self.state['raw_tiles'] == self.raw_budget,
            'one actual frozen-policy snapshot follows its complete paid batch')
        require(row['snapshot'] == dict(stream=self.state, memory=pooled_memory(self.raw_budget, self.fours)),
            'batch snapshot preserves all independently reconstructed initial winning and tail ranks')
        expected = dict(raw_tiles=self.raw_budget, before_stream=self.before, after_stream=self.state,
            chunks=self.chunks, counts={key: dict(value) for key, value in self.counts.items()},
            representation_counts=dict(self.representation))
        equal_tree(row['training'], expected, 'actual batch snapshot physical and planning counts')
        require(Counter(row['reconstruction']['counts']) == self.processing
            and row['reconstruction']['memory_counts'] == pooled_memory(self.raw_budget, self.fours)['counts']
            and row['reconstruction']['chunks'] == self.chunks,
            'new batch reconstruction and all-raw observational processing are paid')
        self.snapshot = deepcopy(row)

    def check_probes(self, head, saved_probes):
        require(self.state is not None and self.state['raw_tiles'] == self.raw_budget,
            'predeclared policy probes are checked only after the entire paid batch closes')
        probes = {row['index']: row for row in self.first_probes+list(self.last_probes)}
        saved = {}
        for name, expected in (('first', self.first_probes), ('last', list(self.last_probes))):
            require(len(saved_probes[name]) == len(expected), 'all fixed first-eight and last-eight probes are retained')
            for observed, actual in zip(saved_probes[name], expected):
                require(observed['episode'] == actual['episode'] and observed['step'] == actual['step']
                    and observed['raw_index'] == actual['raw_index'] and observed['preboard'] == actual['board']
                    and observed['chosen_action'] == actual['action'] and observed['h2_value'] == actual['value'],
                    'saved action probes are the predeclared actual tape boundaries rather than selected example boards')
                saved[actual['index']] = observed
        for probe in probes.values():
            chosen = literal_choose(probe['board'], head.reward, head.terminal, head.kind,
                self.expected_identity['model_p_four'], radix=self.radix)
            require(chosen['action'] == probe['action'] and chosen['score'] == probe['score']
                and close(chosen['value'], probe['value']),
                'predeclared first/last actual actions and full H2 values use reconstructed frozen actor weights')
            equal_tree(saved[probe['index']]['action_values'],
                {action: value['value'] for action, value in chosen['action_values'].items()},
                'all literal candidate H2 values use the saved actual actor head')
        return len(probes)


def prefix_selection(games, fit_game_count, quota):
    """Select only chronological nonwinning states; retain complete original game suffixes."""
    eligible = sum(game['steps']-(game['status'] == 'WON') for game in games[:fit_game_count])
    require(0 < quota <= eligible and all(game['status'] in ('WON', 'LOST') for game in games),
        'common quota uses only factual natural complete-game FIT afterstates')
    mask, selected = [], 0
    fit_steps = sum(row['steps'] for row in games[:fit_game_count])
    for game in games:
        for step in range(game['steps']):
            take = len(mask) < fit_steps \
                and not (game['status'] == 'WON' and step == game['steps']-1) and selected < quota
            mask.append(take); selected += take
    return dict(eligible_samples=eligible, selected_samples=selected,
        last_selected_step=max(index for index, take in enumerate(mask) if take), selection_mask=mask,
        candidate_fit_steps=fit_steps, selection_rule='CHRONOLOGICAL_NONWINNING_FIT_PREFIX_FULL_FACTUAL_SUFFIXES')


def check_batch_dataset(dataset, world):
    require(world.snapshot is not None, 'new natural-game training facts require their closed batch snapshot')
    n = 4*len(world.games)//5
    require(0 < n < len(world.games) and dataset['fit_game_count'] == n
        and dataset['games'] == [dict(game, split='FIT' if index < n else 'HELDOUT') for index, game in enumerate(world.games)]
        and all(game['status'] in ('WON', 'LOST') for game in world.games),
        'all new natural complete games receive chronological 80/20 FIT and HELDOUT labels')
    fit_raw, complete_raw = world.games[n-1]['end_raw'], world.games[-1]['end_raw']
    fit_steps, complete_steps = world.ends[n-1], world.ends[-1]
    require(dataset['fit_step_end'] == fit_steps and dataset['fit_end_raw'] == fit_raw
        and dataset['fit_memory'] == world.game_memories[n-1]
        and dataset['actor_memory_A_end'] == pooled_memory(world.raw_budget, world.fours),
        'batch FIT probability excludes HELDOUT and tail while all paid observational ranks remain recorded')
    expected = dict(full_batch_raw_tiles=world.raw_budget, full_batch_acquisition_counts=world.snapshot['training']['counts'],
        fit_raw_tiles=fit_raw, heldout_raw_tiles=complete_raw-fit_raw, fit_steps=fit_steps,
        heldout_steps=complete_steps-fit_steps, excluded_tail_games=int(complete_raw < world.raw_budget),
        excluded_tail_steps=world.actions-complete_steps, excluded_tail_raw_tiles=world.raw_budget-complete_raw,
        warmup_raw_tiles=0, warmup_environment_counts={}, warmup_direct_counts={}, warmup_memory_counts={},
        processing_counts=dict(world.processing), processing_memory_counts=pooled_memory(world.raw_budget, world.fours)['counts'],
        reconstructed_chunks=world.chunks, processing_cpu_seconds=world.snapshot['reconstruction']['cpu_seconds'])
    equal_tree(dataset['costs'], expected, 'all paid complete-game FIT HELDOUT tail and reconstruction batch costs')
    return n


def check_masked_fit(fit, games, scores, fit_game_count, quota, selection):
    expected = prefix_selection(games, fit_game_count, quota)
    require(all(selection[key] == value for key, value in expected.items() if key != 'selection_mask'),
        'equal quota masks select the chronological eligible prefix without changing complete factual suffixes')
    mask = expected['selection_mask']; fit_games = games[:fit_game_count]
    fit_steps = expected['candidate_fit_steps']; wins = sum(game['status'] == 'WON' for game in fit_games)
    selected_games, first, last, offset = 0, None, None, 0
    for index, game in enumerate(fit_games):
        selected = [step for step in range(game['steps']) if mask[offset+step]]
        if selected:
            selected_games += 1
            if first is None:
                first = (index, selected[0], offset+selected[0])
            last = (index, selected[-1], offset+selected[-1])
        offset += game['steps']
    kind = fit['method']; terminal_name = 'risk' if kind == 'LOCAL_RISK' else 'win'
    require(kind in ('LOCAL_RISK', 'LINEAR_WIN2') and fit['alpha'] == .0025 and fit['frozen_game_start_targets']
        and fit['fitted_games'] == fit['candidate_fitted_games'] == fit_game_count
        and fit['fitted_steps'] == fit_steps and fit['selected_games'] == selected_games
        and fit['trained_afterstates'] == fit['reward_trained_afterstates'] == fit[terminal_name+'_trained_afterstates'] == quota,
        'all consolidations retain game-start residuals and exactly the common selected-state quota')
    expected_selection = dict(fit_afterstates_checked=fit_steps, winning_afterstates_skipped=wins,
        nonwinning_selection_reads=fit_steps-wins, unselected_nonwinning_afterstates=fit_steps-wins-quota,
        selected_nonwinning_afterstates=quota, games_with_selected_samples=selected_games)
    require(Counter(fit['selection_counts']) == Counter(expected_selection), 'actual masks check every FIT state and update selected natural samples only')
    targets = dict(terminal_game_labels=fit_game_count, reward_suffix_target_assignments=fit_steps,
        reward_suffix_additions=fit_steps, goal_checks=fit_steps, skipped_winning_afterstates=wins,
        **{terminal_name+'_label_assignments': quota})
    require(Counter(fit['target_counts']) == Counter(targets), 'full natural game reward suffixes and true WIN labels survive partial-game selection')
    norm = fit['normalization_counts']; writes, products = norm['game_unique_addresses'], norm['reward_gradient_products']
    require(selected_games <= writes <= 32*quota and quota <= products <= 32*quota,
        'selected-state commits use their actual nonempty parameter-address inventories')
    work = dict(td_updates=quota, value_predictions=quota, table_lookups=64*quota, table_updates=2*writes,
        table_update_occurrences=32*quota, reward_predictions=quota, reward_table_lookups=32*quota,
        reward_table_updates=writes, **{terminal_name+'_predictions': quota, terminal_name+'_table_lookups': 32*quota,
        terminal_name+'_parameter_updates': writes})
    require(Counter(fit['learning_counts']) == Counter(work), 'both actual reward and terminal tables read and write the same selected sample inventory')
    common = dict(games_processed=fit_game_count, feature_extractions=quota, feature_occurrences=32*quota,
        feature_digit_reads=192*quota, feature_address_multiply_adds=192*quota, sort_calls=fit_game_count+quota,
        sort_items=64*quota, denominator_occurrence_visits=32*quota, reward_gradient_accumulations=products,
        normalization_divisions=2*writes, parameter_update_multiplications=2*writes,
        game_parameter_commits=selected_games, reward_game_commits=selected_games, reward_parameter_writes=writes,
        address_denominator_searches=products, **{terminal_name+'_gradient_products': products,
        terminal_name+'_gradient_accumulations': products, terminal_name+'_game_commits': selected_games,
        terminal_name+'_parameter_writes': writes})
    require(all(norm[key] == value for key, value in common.items()), 'actual game-start address multiplicities normalize both heads before each game commit')
    if kind == 'LOCAL_RISK':
        check_representation(fit['representation_counts'], kind, quota)
    else:
        check_linear_representation(fit['representation_counts'], quota)
    for name, location in (('first_sample', first), ('last_sample', last)):
        game_index, step, global_step = location; sample = fit[name]
        label = float(games[game_index]['status'] == 'WON')
        target = sum(scores[game_index][step+1:])/2048.
        prediction = sample['risk_probability'] if kind == 'LOCAL_RISK' else sample['win_prediction']
        require(sample['episode'] == game_index and sample['step'] == global_step
            and sample['reward_target'] == target and sample[terminal_name+'_target'] == label
            and close(sample['reward_error'], target-sample['reward_prediction'])
            and close(sample[terminal_name+'_error'], label-prediction)
            and close(sample['combined_prediction'], sample['reward_prediction']+8.*(prediction-.5)),
            'first and last selected examples retain their complete factual future rewards and actual WIN residuals')
        if kind == 'LOCAL_RISK':
            require(0 <= prediction <= 1, 'LOCAL terminal prediction remains its sigmoid WIN probability')
    return quota


def check_same_evaluation_head(direct, h2):
    require(direct['head_version'] == h2['head_version']
        and direct['estimated_p_four'] == h2['estimated_p_four'],
        'DIRECT and H2 execute precisely the same learned head version and immutable bank belief')


def require_source_audit(directory):
    source = json_file(Path(directory)/'audit.json')
    receipt = json_file(Path(directory)/'audit_execution.json')
    require(source['status'] == 'PASS' and source['independent_valid'] and receipt['exit_code'] == 0,
        'V313 readiness requires the completed independent fresh V312 SOURCE audit')
    return source


class InitialWorld:
    """Literal new-world reconstruction; no planner, training or bootstrap calls."""
    def __init__(self, life, stage):
        self.life, self.stage = life, stage
        self.memory = Memory(); self.state = self.before = None
        self.first_afterstate = None; self.rng = None
        self.warm_games = []; self.warm_events = []; self.warm_environment = Counter(); self.warm_direct = Counter()
        self.processing = Counter(); self.train_counts = {kind:Counter() for kind in ('environment', 'planning', 'learning')}
        self.games = []; self.scores = defaultdict(list); self.game_memories = {}
        self.training_events = []; self.training_rows = 0
        self.detection = self.snapshot = self.training = None
        self.looks = []; self.look_module_counts = []; self.last_look_games = 0
        self.initial_raw = self.initial_games = self.confirmation_raw = self.confirmation_games = 0

    def context(self, row):
        require(row['lifecycle'] == self.life and row['parent'] == self.life%4 and row['phase'] == self.stage,
            'new world lifecycle source-parent and stage membership')
        if row['kind'] != 'DETECTOR_LOOK':
            stage_context(row)
        else:
            require('true_p_four' not in row, 'provisional detector evidence contains no true world probability')

    def warmup(self, row):
        self.context(row)
        require(self.detection is None, 'all detector observations precede its final decision and training')
        extra = row['kind'] == 'CONFIRMATION'
        if extra:
            require(self.looks and self.looks[-1]['decision'] == 'PENDING_CONFIRMATION'
                and not self.looks[-1]['at_cap'] and self.memory.obs < DETECTOR_CAP
                and len(self.warm_games) == self.last_look_games,
                'only a genuinely ambiguous uncapped look starts exactly one additional complete detector game')
        else:
            require(row['kind'] == 'WARMUP' and not self.looks and self.memory.obs < 256,
                'initial detector warmup stops at the first complete game after 256 raw observations')
        game = row['summary']; raw = row['raw_spawns']; board = [0]*16; actions = 0
        rng = random.Random(game['seed'])
        require(game['seed'] == warmup_seed(self.life, self.stage, len(self.warm_games))
            and len(raw) == game['steps']+2 and [spawn['kind'] for spawn in raw[:2]] == ['INITIAL', 'INITIAL']
            and all(spawn['kind'] == 'POST_ACTION' for spawn in raw[2:]), 'fresh complete SOURCE detector game and all initial/post-action tiles')
        for index, spawn in enumerate(raw):
            if index >= 2:
                require(board_status(board) == 'ACTIVE', 'detector cannot continue after a natural terminal board')
                after, score = swipe(board, row['actions'][actions])
                require(after != board and score == row['scores'][actions], 'detector actual legal swipe and independent merge score')
                board = after; actions += 1
            seeded_place(board, spawn, rng, PROBABILITIES[self.stage[0]])
        require(actions == len(row['actions']) == len(row['scores']) == game['steps']
            and sum(row['scores']) == game['score'] and board == row['final_board']
            and board_status(board) == game['status'] and game['status'] in ('WON', 'LOST')
            and game['utility'] == game['score']/2048.+(4. if game['status'] == 'WON' else -4.),
            'detector full factual score sequence and natural terminal outcome')
        steps, won = game['steps'], game['status'] == 'WON'
        environment = dict(initial_spawns=2, sampled_transitions=steps, environment_random_draws=2*(steps+2),
            ground_explicit_swipe_calls=steps, ground_state_status_calls=steps+1,
            ground_status_internal_swipe_calls=4*(steps+1-won), ground_swipe_calls=steps+4*(steps+1-won))
        require(Counter(row['counts']['environment']) == Counter(environment), 'all detector environment work and initial tiles are paid')
        direct = Counter(row['counts']['direct'])
        require(direct['choose_calls'] == direct['inner_choose_calls'] == steps
            and direct['inner_learned_swipe_calls'] == 4*steps
            and direct['inner_line_table_lookups'] == 4*direct['inner_learned_swipe_calls']
            and direct['inner_table_lookups'] == 32*direct['inner_value_predictions']
            and direct['td_updates'] == direct['inner_td_updates'] == 0, 'detector uses frozen SOURCE DIRECT and receives no learning updates')
        events = self.memory.consume(spawn['rank'] for spawn in raw)
        require(row['memory_events'] == events, 'every initial and confirmation rank produces its literal observed memory event')
        self.warm_events.extend(events)
        self.warm_games.append(game); self.warm_environment.update(environment); self.warm_direct.update(direct)
        if extra:
            self.confirmation_raw += len(raw); self.confirmation_games += 1
        else:
            self.initial_raw += len(raw); self.initial_games += 1
        internal = 4*(not won)
        self.processing.update(ground_explicit_swipe_calls=steps, ground_swipe_calls=steps+internal,
            ground_state_status_calls=1, ground_status_internal_swipe_calls=internal, warmup_records=1)

    def look(self, row):
        self.context(row)
        require(self.detection is None and self.state is None and self.memory.obs >= 256
            and row['look_index'] == len(self.looks)
            and (not self.looks or len(self.warm_games) == self.last_look_games+1),
            'one detector look follows the initial minimum or exactly one new complete confirmation game')
        statistics = observed_statistics(self.memory.learned())
        require(row['statistics'] == statistics and row['detector_raw_tiles'] == self.memory.obs
            and row['at_cap'] == (self.memory.obs >= DETECTOR_CAP),
            'each detector look includes every paid initial and confirmation rank including natural overshoot')
        require(row['prototype_committed'] is False, 'provisional detector looks never commit a bank prototype')
        self.looks.append(row); self.look_module_counts.append(len(self.memory.modules))
        self.last_look_games = len(self.warm_games)

    def detect(self, row):
        self.context(row)
        require(self.detection is None and self.state is None and self.looks
            and len(self.warm_games) == self.last_look_games
            and (self.looks[-1]['decision'] != 'PENDING_CONFIRMATION' or self.looks[-1]['at_cap']),
            'one final detector snapshot follows resolved evidence or capped ambiguity before any training acquisition')
        belief = row['detector_belief']; memory = belief['memory']
        require(memory['method'] == 'LIBRARY' and learned(memory) == self.memory.learned()
            and belief['estimated_p_four'] == self.memory.probability(), 'blind detector belief contains only its observed completed detector games')
        self.detection = row; self.warm_raw = self.memory.obs; self.warm_final = self.memory.learned()
        self.warm_counts = self.memory.counts.copy()
        self.warm_counts['predict_calls'] = 1

    def train(self, row):
        self.context(row)
        require(self.detection is not None and self.detection['route']['created'] and self.snapshot is None,
            'only a newly created observed context acquires a model cohort')
        start = row['start']; raw = row['raw_spawns']; memory = self.memory
        require(row['arm'] == 'FROZEN' and row['active_bank_id'] == 0 and row['module_id_before'] == memory.active
            and row['model_p_four'] == memory.probability(), 'new cohort uses original SOURCE and preceding observed online LIBRARY probability')
        require(start['stream_seed'] == training_seed(self.life, self.stage)
            and len(raw) == min(RAW-start['raw_tiles'], 64-memory.n) and raw,
            'fresh continuous SOURCE stream stops at each observed block and exact paid raw boundary')
        if self.state is None:
            require(start['raw_tiles'] == start['post_action_spawns'] == start['random_draw_position'] == 0
                and start['status'] == 'NOT_STARTED' and start['initial_count'] == 0
                and start['board'] == [0]*16 and start['pending_afterstate'] is start['pending_bank_id'] is None,
                'created context acquires a new empty stream without old training facts')
            self.state = deepcopy(start); self.before = deepcopy(start)
            self.rng = TileRandom(start['stream_seed'])
        require(start == self.state, 'new cohort continuity across factual chunks')
        state = self.state; action = starts = init_done = posts = wins = losses = 0; completed = []; events = []
        for spawn in raw:
            if spawn['kind'] == 'INITIAL':
                if state['status'] != 'INITIALIZING':
                    require(state['status'] in ('NOT_STARTED', 'WON', 'LOST'), 'initial tile cannot restart an active or censored game')
                    state.update(board=[0]*16, episode=state['episode']+1, step=0, return_score=0,
                        status='INITIALIZING', initial_count=0, game_start_raw=state['raw_tiles'], pending_afterstate=None, pending_bank_id=None)
                    starts += 1
                require(state['initial_count'] < 2, 'new game has exactly two initialization tiles')
                state['initial_count'] += 1; init_done += state['initial_count'] == 2
            else:
                require(spawn['kind'] == 'POST_ACTION' and state['status'] == 'ACTIVE' and state['initial_count'] == 2,
                    'new action follows an active two-tile initialization')
                after, score = swipe(state['board'], row['actions'][action])
                require(after != state['board'] and score == row['scores'][action], 'actual new cohort legal swipe and independent merge score')
                state['board'] = after; self.scores[state['episode']].append(score); action += 1; posts += 1
                if self.first_afterstate is None:
                    self.first_afterstate = list(after)
                state['step'] += 1; state['return_score'] += score; state['post_action_spawns'] += 1
                state['pending_afterstate'] = list(after); state['pending_bank_id'] = 0
            require(spawn['episode'] == state['episode'], 'every new raw tile belongs to its actual continuous game')
            seeded_place(state['board'], spawn, self.rng, PROBABILITIES[self.stage[0]]); state['raw_tiles'] += 1; state['random_draw_position'] += 2
            events.extend(memory.consume([spawn['rank']]))
            if state['initial_count'] == 2:
                state['status'] = board_status(state['board'])
            if state['status'] in ('WON', 'LOST'):
                state.update(pending_afterstate=None, pending_bank_id=None)
                game = dict(episode=state['episode'], stream_seed=state['stream_seed'], start_raw=state['game_start_raw'],
                    end_raw=state['raw_tiles'], steps=state['step'], score=state['return_score'], status=state['status'])
                completed.append(game); self.games.append(game); self.game_memories[game['episode']] = memory.learned()
                wins += state['status'] == 'WON'; losses += state['status'] == 'LOST'
        require(action == len(row['actions']) == len(row['scores']) and completed == row['completed_games']
            and state == row['end'] and events == row['memory_events'],
            'new cohort end boards pending states all natural terminals and observed memory events')
        environment = dict(sampled_transitions=posts, post_action_spawns=posts, initial_spawns=len(raw)-posts,
            raw_tile_productions=len(raw), environment_random_draws=2*len(raw), ground_explicit_swipe_calls=posts,
            ground_state_status_calls=posts+init_done, ground_status_internal_swipe_calls=4*(posts+init_done-wins),
            ground_swipe_calls=posts+4*(posts+init_done-wins), episodes_started=starts,
            episodes_completed=wins+losses, won_games=wins, lost_games=losses)
        require(Counter(row['counts']['environment']) == Counter(environment), 'actual new acquisition includes all initial winning and tail raw tiles')
        planning_counts(row['counts']['planning'], posts)
        require(not row['counts']['learning'] and not row['bank_update_counts'] and not row['td_examples'], 'SOURCE acquisition does not fit a learned bank')
        boundary = int(state['status'] not in ('NOT_STARTED', 'INITIALIZING'))
        internal = 4*(init_done+losses+int(boundary and state['status'] != 'WON'))
        self.processing.update(ground_explicit_swipe_calls=posts, ground_swipe_calls=posts+internal,
            ground_state_status_calls=init_done+wins+losses+boundary, ground_status_internal_swipe_calls=internal)
        for kind in self.train_counts:
            self.train_counts[kind].update(row['counts'][kind])
        self.training_events.extend(events); self.training_rows += 1

    def checkpoint(self, row):
        self.context(row)
        require(self.detection is not None and self.detection['route']['created'] and self.snapshot is None
            and self.state is not None and self.state['raw_tiles'] == RAW and row['arm'] == 'FROZEN',
            'one model snapshot follows a created context and its exact raw acquisition boundary')
        snapshot, training = row['snapshot'], row['training']
        require(snapshot['stream'] == self.state and snapshot['memory'] == self.memory.learned()
            and snapshot['estimated_p_four'] == self.memory.probability() and snapshot['active_bank_id'] == 0
            and snapshot['new_value_updates'] == 0, 'new model snapshot contains the complete observed SOURCE stream without value updates')
        require(training['raw_tiles'] == RAW and training['chunks'] == self.training_rows
            and training['before_stream'] == self.before and training['after_stream'] == self.state
            and training['memory_event_count'] == len(self.training_events)
            and all(Counter(training['counts'][kind]) == self.train_counts[kind] for kind in self.train_counts),
            'model acquisition ledger counts all actual new blocks environment and planning')
        require(Counter({key:value for key,value in training['memory_counts'].items() if key != 'predict_calls'})
            == self.memory.counts-self.warm_counts and training['memory_counts']['predict_calls'] == self.training_rows+1,
            'actor online probability is predicted once per actual chunk and once at its final boundary')
        self.snapshot, self.training = snapshot, training


def expected_configuration(source_summary):
    return dict(schema='acfqp.closed_loop_freeze.v313',
        protocol=str(Path(__file__).resolve().parents[1]/'specs/CLOSED_LOOP_V313.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(16)),
        parents=4, workers=4, arms=list(ARMS), tasks=list(TASKS), true_probabilities=PROBABILITIES,
        rounds=[1, 2], initial_raw_per_task=INITIAL_RAW, round_raw_per_collector=POST_RAW,
        fit_fraction=.8, alpha=.0025, query=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.), max_steps=8192,
        initial_contexts='V309_CONFIRMED_NEW_BANKS_DISTINCT_PRECONDITION',
        initial_heads='NEW_TARGET_FACTS_FIRST_LOCAL_AND_FIRST_LINEAR_FROM_V312_SOURCE',
        context_updates='SUPPLIED_KNOWN_TASK_BANK_FROM_ITS_INITIAL_OBSERVED_ROUTE',
        planning_probability='IMMUTABLE_ACTUAL_BANK_FIRST_FIT_BELIEF',
        collectors=dict(FIXED_LOCAL='FIRST_LOCAL_VERSION_0', CLOSED_LOCAL='PREVIOUS_OWN_LOCAL_VERSION',
            CLOSED_LINEAR='PREVIOUS_OWN_LINEAR_VERSION'),
        shared_cohort='ROUND_1_LOCAL_IDENTICAL_FIRST_ACTOR_SHARED_PHYSICALLY_CHARGED_PER_ARM',
        quota='MINIMUM_ELIGIBLE_NONWINNING_80_PERCENT_FIT_STATES_PER_TASK_ROUND',
        selection='CHRONOLOGICAL_ELIGIBLE_PREFIX_MASK_FULL_FACTUAL_SUFFIXES_NO_OLD_LABEL_REPLAY',
        head_history='SOURCE_RELATIVE_SPARSE_V0_AND_ACTUAL_CHANGED_ADDRESS_V1_V2',
        action_probes='FIRST_EIGHT_AND_LAST_EIGHT_ACTIONS_EACH_NEW_BATCH',
        seed_initial_warmup=313100000000, seed_initial_training=313200000000,
        seed_collection=313500000000, collection_life_stride=10000000, collection_task_stride=1000000,
        collection_round_stride=100000, seed_evaluation=313900000000, evaluation_games_per_cell=32,
        bootstrap_draws=20000, bootstrap_seed=31300001, primary='CLOSED_LOCAL_minus_FIRST_LOCAL_FINAL_AB',
        feedback='CLOSED_LOCAL_minus_FIXED_LOCAL_FINAL_AB', retention='FINAL_LOCAL_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        planning_control='SAME_FIRST_AND_FINAL_LOCAL_LINEAR_HEAD_DIRECT_VS_H2',
        expected_post_raw_physical=16*2*5*POST_RAW, expected_evaluation_games=16*2*32*13,
        evidence_scope='DEVELOPMENT_16_NEW_TARGET_LIVES_CONDITIONAL_ON_FOUR_FROZEN_V312_VALUE_PARENTS_SHARED_DYNAMICS',
        stop_rule='NO_SEED_ALPHA_QUOTA_OR_CHECKPOINT_TUNING_RETAIN_CUTOFFS_AND_LOSS')


def expected_actor(life, task, round_index, collector):
    row = life['initial'][task]
    if collector in ('SHARED_LOCAL', 'FIXED_LOCAL'):
        return row['head_versions']['FIRST_LOCAL']
    first = 'FIRST_LINEAR' if collector == 'CLOSED_LINEAR' else 'FIRST_LOCAL'
    return row['head_versions'][first] if round_index == 1 else life['rounds']['1'][task]['arms'][collector]['head_version']


def read_canonical(document):
    lives = {row['lifecycle']: row for row in document['by_lifecycle']}
    initial = {(life, stage): InitialWorld(life, stage) for life in range(16) for stage in STAGES}
    batches = {}; rows_read = 0; initial_heads = set(); consolidated = set()
    for parent in document['parent_receipts']:
        parent_id = parent['parent']; path = Path(parent['trace_file'])
        require(path.stat().st_size == parent['trace_bytes'], 'new canonical tapes retain their actual compressed byte inventory')
        parent_rows = 0
        with gzip.open(path, 'rt') as stream:
            for line in stream:
                row = json.loads(line); life_id = row['lifecycle']; life = lives[life_id]
                require(life_id%4 == row['parent'] == parent_id, 'all actual raw histories belong to their frozen fresh SOURCE parent')
                rows_read += 1; parent_rows += 1
                if row['kind'] == 'INITIAL_HEADS':
                    key = life_id, row['task']
                    require(key not in initial_heads and initial[life_id, row['task']+'0'].snapshot is not None
                        and row['head_versions'] == life['initial'][row['task']]['head_versions'],
                        'initial sparse head history follows exactly its new completed SOURCE cohort')
                    initial_heads.add(key); continue
                if row['kind'] == 'CONSOLIDATED_HEAD':
                    task, round_index, arm = row['task'], row['round_index'], row['arm']
                    key = life_id, task, round_index, arm
                    batch = life['rounds'][str(round_index)][task]; value = batch['arms'][arm]
                    collector = 'SHARED_LOCAL' if round_index == 1 and arm != 'CLOSED_LINEAR' else arm
                    require(key not in consolidated and all(batches[life_id, task, round_index, name].snapshot is not None
                        for name in batch['collectors']) and row['quota'] == batch['quota']
                        and row['selection'] == batch['collectors'][collector]['selection']
                        and row['head_version'] == value['head_version'] and row['fit'] == value['fit'],
                        'all new collection closes before its sole actual own-data consolidation and sparse version write')
                    consolidated.add(key); continue
                phase = row['phase']
                if phase in STAGES:
                    world = initial[life_id, phase]
                    if phase == 'B0':
                        require((life_id, 'A') in initial_heads, 'B initial detection follows completed A adaptation')
                    method = {'WARMUP': world.warmup, 'CONFIRMATION': world.warmup, 'DETECTOR_LOOK': world.look,
                        'DETECTION_SNAPSHOT': world.detect, 'TRAIN': world.train, 'ACQUISITION_SNAPSHOT': world.checkpoint}.get(row['kind'])
                else:
                    task = row['task']; round_index = int(phase[-1]); collector = row['arm']
                    batch = life['rounds'][str(round_index)][task]
                    require(phase == f'{task}_R{round_index}' and collector in batch['collectors']
                        and (life_id, 'B') in initial_heads, 'registered fresh known-context post-initial batch identity')
                    key = life_id, task, round_index, collector
                    if key not in batches:
                        actor = expected_actor(life, task, round_index, collector)
                        identity = dict(lifecycle=life_id, parent=parent_id, arm=collector, batch_id=phase, phase=phase,
                            true_p_four=PROBABILITIES[task], model_p_four=life['initial'][task]['planning_belief']['estimated_p_four'],
                            task=task, actor_head_updates=actor['updates'], collector_policy_kind=actor['head_kind'],
                            actor_version=actor, stream_seed=post_seed(life_id, task, round_index))
                        batches[key] = BatchWorld(identity['stream_seed'], POST_RAW, PROBABILITIES[task], identity, actor['head_kind'])
                    world = batches[key]
                    method = {'TRAIN': world.train, 'ACQUISITION_SNAPSHOT': world.checkpoint}.get(row['kind'])
                require(method is not None, 'canonical history contains only declared fresh physical or head-version events')
                method(row)
        require(parent_rows == parent['canonical_rows'], 'each actual parent canonical row count closes exactly')
    require(len(initial_heads) == 32 and len(consolidated) == 16*2*2*3 and len(batches) == 16*2*5
        and all(world.snapshot is not None for world in initial.values())
        and all(world.snapshot is not None for world in batches.values()),
        'all sixteen complete initial and five-collector per-task histories are new and present')
    return initial, batches, rows_read


def check_initial_acquisition(row, world):
    acquisition, warm = row['acquisition'], row['acquisition']['warmup']
    require(row['context_route'] == world.detection['route'] and row['context_route']['created']
        and row['context_id'] == row['context_route']['context_id'], 'first adaptation belongs to its actually observed newly created context')
    require(warm['game_summaries'] == world.warm_games and warm['raw_tiles'] == world.warm_raw
        and warm['memory_events'] == world.warm_events and warm['final_memory'] == world.warm_final
        and warm['initial_raw_tiles'] == world.initial_raw and warm['confirmation_raw_tiles'] == world.confirmation_raw
        and warm['initial_game_count'] == world.initial_games and warm['confirmation_games'] == world.confirmation_games
        and warm['detector_looks'] == len(world.looks), 'all paid initial and additional complete detector games are retained')
    require(Counter(warm['environment_counts']) == world.warm_environment and Counter(warm['direct_counts']) == world.warm_direct
        and Counter(warm['memory_counts']) == world.warm_counts, 'initial detector physical DIRECT and observed-memory work is paid')
    require(acquisition['new_value_updates'] == acquisition['new_evaluation_games'] == 0 and acquisition['physical_acquisitions'] == 1
        and acquisition['training'] == world.training and acquisition['snapshot'] == world.snapshot,
        'new first cohort uses unchanged SOURCE and its exact paid acquisition boundary')
    reconstruction = acquisition['reconstruction']; expected_memory = Counter(world.memory.counts)
    expected_memory['predict_calls'] = world.training_rows+2
    require(Counter(reconstruction['counts']) == world.processing and reconstruction['chunks'] == world.training_rows
        and Counter(reconstruction['memory_counts']) == expected_memory, 'initial observed-data reconstruction is inventoried once')
    dataset = row['dataset']
    n = check_stage_split(dataset, world.games, world.scores, world.game_memories, world.warm_raw, world.training, world.stage)
    check_belief(row['planning_belief'], dataset)
    require(learned(dataset['actor_memory_'+world.stage+'_end']) == world.memory.learned(), 'initial all-raw memory retains the paid tail')
    for key in ('environment_counts', 'direct_counts', 'memory_counts'):
        require(dataset['costs']['warmup_'+key] == warm[key], 'initial detector work enters new factual acquisition costs')
    require(dataset['costs']['processing_counts'] == reconstruction['counts']
        and dataset['costs']['processing_memory_counts'] == reconstruction['memory_counts']
        and dataset['costs']['reconstructed_chunks'] == reconstruction['chunks']
        and dataset['costs']['processing_cpu_seconds'] == reconstruction['cpu_seconds'], 'initial FIT reconstruction retains its actual measured work')
    return n


def check_initial_fit(fit, world, n, source):
    games = world.games[:n]; steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games)
    samples = steps-wins; terminal_name = 'risk' if fit['method'] == 'LOCAL_RISK' else 'win'
    require(fit['method'] in ('LOCAL_RISK', 'LINEAR_WIN2') and fit['alpha'] == .0025 and fit['frozen_game_start_targets']
        and fit['fitted_games'] == n and fit['fitted_steps'] == steps
        and fit['trained_afterstates'] == fit['reward_trained_afterstates'] == fit[terminal_name+'_trained_afterstates'] == samples,
        'both first heads fit identical complete factual nonwinning samples from original SOURCE')
    norm = fit['normalization_counts']; writes, products = norm['game_unique_addresses'], norm['reward_gradient_products']
    require(n <= writes <= 32*samples and samples <= products <= 32*samples, 'first heads retain actual game-local parameter-address work')
    work = dict(td_updates=samples, value_predictions=samples, table_lookups=64*samples, table_updates=2*writes,
        table_update_occurrences=32*samples, reward_predictions=samples, reward_table_lookups=32*samples,
        reward_table_updates=writes, **{terminal_name+'_predictions': samples, terminal_name+'_table_lookups': 32*samples,
        terminal_name+'_parameter_updates': writes})
    targets = dict(terminal_game_labels=n, reward_suffix_target_assignments=steps, reward_suffix_additions=steps,
        goal_checks=steps, skipped_winning_afterstates=wins, **{terminal_name+'_label_assignments': samples})
    require(Counter(fit['learning_counts']) == Counter(work) and Counter(fit['target_counts']) == Counter(targets),
        'first adaptation pays both active tables and complete factual reward/WIN labels')
    common = dict(games_processed=n, feature_extractions=samples, feature_occurrences=32*samples,
        feature_digit_reads=192*samples, feature_address_multiply_adds=192*samples, sort_calls=n+samples,
        sort_items=64*samples, denominator_occurrence_visits=32*samples, reward_gradient_accumulations=products,
        normalization_divisions=2*writes, parameter_update_multiplications=2*writes,
        game_parameter_commits=n, reward_game_commits=n, reward_parameter_writes=writes,
        address_denominator_searches=products, **{terminal_name+'_gradient_products': products,
        terminal_name+'_gradient_accumulations': products, terminal_name+'_game_commits': n, terminal_name+'_parameter_writes': writes})
    require(all(norm[key] == value for key, value in common.items()), 'first adaptation retains game-start address-multiplicity normalization')
    if fit['method'] == 'LOCAL_RISK':
        check_representation(fit['representation_counts'], fit['method'], samples)
    else:
        check_linear_representation(fit['representation_counts'], samples)
    for name, episode, step in (('first_sample', 0, 0), ('last_sample', n-1, steps-1-(games[-1]['status'] == 'WON'))):
        sample = fit[name]; local_step = step-sum(game['steps'] for game in games[:episode])
        target = sum(world.scores[games[episode]['episode']][local_step+1:])/2048.; label = float(games[episode]['status'] == 'WON')
        prediction = sample['risk_probability'] if terminal_name == 'risk' else sample['win_prediction']
        require(sample['episode'] == episode and sample['step'] == step and sample['reward_target'] == target
            and sample[terminal_name+'_target'] == label and close(sample['reward_error'], target-sample['reward_prediction'])
            and close(sample[terminal_name+'_error'], label-prediction)
            and close(sample['combined_prediction'], sample['reward_prediction']+8.*(prediction-.5)),
            'first adaptation examples preserve literal complete-game reward suffixes and true WIN residuals')
    neutral = np.zeros_like(source)
    require(fit['first_sample']['risk_probability' if terminal_name == 'risk' else 'win_prediction'] == .5
        and close(fit['first_sample']['reward_prediction'], component_value(world.first_afterstate, source, neutral, 'LOCAL_RISK')),
        'first real FIT example reads original fresh SOURCE reward and neutral terminal prediction')
    return samples


def check_evaluation(value, life, task, belief, version, planner):
    require(value['estimated_p_four'] == belief['estimated_p_four'] and value['head_version'] == version
        and value['planner'] == planner and value['static_evaluation_valid'],
        'new whole-game evaluation executes its exact actual head and immutable bank planning belief')
    games = value['game_summaries']; require(len(games) == 32
        and [game['seed'] for game in games] == [evaluation_seed(life, task, i) for i in range(32)], 'all new H2/DIRECT endpoints use their paired V313 task seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'every new whole-game endpoint retains its actual horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and physical_status(game['final_board']) == 'ACTIVE', 'no early artificial evaluation cutoff')
            bonus = 0.
        else:
            require(physical_status(game['final_board']) == game['status'] and game['status'] in ('WON', 'LOST'), 'evaluation terminal labels match physical final boards')
            bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'paired utility retains the original natural terminal bonus')
    steps, wins = sum(game['steps'] for game in games), sum(game['status'] == 'WON' for game in games)
    expected = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=64, raw_tile_productions=steps+64,
        environment_random_draws=2*(steps+64), ground_explicit_swipe_calls=steps, ground_state_status_calls=steps+32,
        ground_status_internal_swipe_calls=4*(steps+32-wins), ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(value['counts']['environment']) == Counter(expected), 'all new evaluation initial winning and final spawns remain paid')
    planning_counts(value['counts']['planning'], steps, depth=1 if planner == 'DIRECT' else 2)
    if version is not None:
        predictions = value['counts']['planning'].get('value_predictions', 0)
        if version['head_kind'] == 'LOCAL_RISK':
            check_representation(value['representation_counts'], version['head_kind'], predictions)
        else:
            check_linear_representation(value['representation_counts'], predictions)
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games), wins=wins,
        losses=sum(game['status'] == 'LOST' for game in games), cutoffs=sum(game['status'] == 'CUTOFF' for game in games),
        cutoff_episodes=[i for i, game in enumerate(games) if game['status'] == 'CUTOFF'], steps=steps)


def check_head_setups(life, size):
    total = 0
    for task in TASKS:
        require(set(life['head_setups'][task]) == set(ARMS[1:]), 'each bank owns both first heads and all three private learner branches')
        for arm, setup in life['head_setups'][task].items():
            counts = setup['setup_counts']; terminal_name = 'half_win' if arm in ('FIRST_LINEAR', 'CLOSED_LINEAR') else 'zero_risk'
            require(counts['source_parameters_copied'] == size and counts['source_weight_bytes_copied'] == 8*size
                and counts['allocated_weight_parameters'] == 2*size and counts['allocated_weight_bytes'] == 16*size
                and counts['initialized_'+terminal_name+'_parameters'] == size and setup['private_weight_bytes'] == 16*size,
                'each actual two-table learner allocation retains the same fresh SOURCE/default initialization work')
            if arm in UPDATING_ARMS:
                require(counts['first_parameters_copied'] == 2*size and counts['first_weight_bytes_copied'] == 16*size,
                    'private branches copy both actual first-adapted arrays once')
            total += setup['private_weight_bytes']
    require(life['private_head_weight_bytes'] == total, 'the five private two-table heads in both actual banks are counted once')


def check_lifecycle(life, initial_worlds, batch_worlds, source, source_checkpoint):
    life_id, parent = life['lifecycle'], life['parent']; prototypes = []; cells = {}; direct = {}
    latest = {}; probe_count = 0; unchanged = []
    contexts = {task: life['initial'][task]['context_id'] for task in TASKS}
    require(life['initial_context_precondition_met'] == (len(set(contexts.values())) == 2),
        'known-context consolidation requires distinct actually confirmed initial task banks')
    check_head_setups(life, source.size)
    for task in TASKS:
        first = life['initial'][task]; world = initial_worlds[life_id, task+'0']
        context, created = check_detection_route(first['context_route'], world.detection['detector_belief'], prototypes, world.looks)
        require(created and context == contexts[task], 'every new initial head follows its independently confirmed observed bank')
        n = check_initial_acquisition(first, world)
        for arm in ('FIRST_LOCAL', 'FIRST_LINEAR'):
            check_initial_fit(first['first_fits'][arm], world, n, source)
            require(first['head_versions'][arm]['updates'] == first['first_fits'][arm]['trained_afterstates'],
                'first actual sparse head update count matches exactly its own complete FIT samples')
            require(first['head_versions'][arm]['source_checkpoint'] == source_checkpoint,
                'every actual first head starts at its own audited fresh V312 SOURCE parent checkpoint')
        local_norm, linear_norm = (first['first_fits'][arm]['normalization_counts'] for arm in ('FIRST_LOCAL', 'FIRST_LINEAR'))
        require(local_norm['game_unique_addresses'] == linear_norm['game_unique_addresses']
            and local_norm['reward_gradient_products'] == linear_norm['reward_gradient_products'],
            'identical first LOCAL and LINEAR factual states have the same address multiplicities and parameter inventory')
        belief = first['planning_belief']; values = {}
        for arm in ARMS[:3]:
            version = None if arm == 'SOURCE' else first['head_versions'][arm]
            values[arm] = check_evaluation(first['evaluations'][arm]['H2'], life_id, task, belief, version, 'H2')
        cells['FIRST_'+task] = dict(task=task, checkpoint='FIRST', estimated_p_four=belief['estimated_p_four'], arms=values)
        latest[task] = {arm: first['head_versions']['FIRST_LINEAR' if arm == 'CLOSED_LINEAR' else 'FIRST_LOCAL'] for arm in UPDATING_ARMS}
    for round_index in (1, 2):
        for task in TASKS:
            batch = life['rounds'][str(round_index)][task]; first = life['initial'][task]
            other = 'B' if task == 'A' else 'A'; expected_collectors = ('SHARED_LOCAL', 'CLOSED_LINEAR') if round_index == 1 else UPDATING_ARMS
            require(set(batch['collectors']) == set(expected_collectors), 'only actual declared shared or separate collector cohorts are present')
            require(batch['inactive_head_versions_before'] == batch['inactive_head_versions_after'] == latest[other],
                'the other known-context bank retains all its actual head history throughout collection and consolidation')
            eligible = []
            for collector, receipt in batch['collectors'].items():
                world = batch_worlds[life_id, task, round_index, collector]
                n = check_batch_dataset(receipt['dataset'], world)
                actor = expected_actor(life, task, round_index, collector); acquisition = receipt['acquisition']
                require(receipt['actor_version'] == acquisition['actor_version'] == actor
                    and acquisition['actor_head_updates_before'] == acquisition['actor_head_updates_after'] == actor['updates']
                    and acquisition['new_actor_updates'] == 0 and acquisition['training'] == world.snapshot['training']
                    and acquisition['snapshot'] == world.snapshot['snapshot'] and acquisition['reconstruction'] == world.snapshot['reconstruction']
                    and acquisition['policy_probes'] == world.snapshot['policy_probes'],
                    'actual frozen collector receipt matches its complete canonical batch and recorded policy probes')
                eligible.append(sum(game['steps']-(game['status'] == 'WON') for game in world.games[:n]))
            require(batch['quota'] == min(eligible) and batch['quota'] > 0,
                'the common training quota is exactly the minimum natural nonwinning FIT sample count across actual collectors')
            values = dict(cells['FIRST_'+task]['arms'])
            for arm, item in batch['arms'].items():
                require(arm in UPDATING_ARMS, 'only the three declared private branches receive scheduled fits')
                collector = 'SHARED_LOCAL' if round_index == 1 and arm != 'CLOSED_LINEAR' else arm
                receipt = batch['collectors'][collector]; world = batch_worlds[life_id, task, round_index, collector]
                n = receipt['dataset']['fit_game_count']
                check_masked_fit(item['fit'], world.games, world.scores, n, batch['quota'], receipt['selection'])
                version = item['head_version']
                require(item['updates_before'] == latest[task][arm]['updates'] and item['updates_after'] == version['updates']
                    == item['updates_before']+batch['quota'] and version['version'] == round_index
                    and version['base_file'] == latest[task][arm]['file'], 'each consolidation continues its own previous actual private learner state once')
                latest[task][arm] = version
                values[arm] = check_evaluation(item['evaluations']['H2'], life_id, task, first['planning_belief'], version, 'H2')
                if round_index == 1 and arm in ('CLOSED_LOCAL', 'CLOSED_LINEAR') and version['changed_parameters'] == 0:
                    unchanged.append(dict(lifecycle=life_id, task=task, arm=arm, version=1, changed_parameters=0))
            require(set(batch['arms']) == set(UPDATING_ARMS), 'all three updating branches fit their own full scheduled quota')
            if round_index == 1:
                require(batch['arms']['FIXED_LOCAL']['fit'] == batch['arms']['CLOSED_LOCAL']['fit']
                    or all(batch['arms']['FIXED_LOCAL']['fit'][key] == batch['arms']['CLOSED_LOCAL']['fit'][key]
                        for key in ('first_sample', 'last_sample', 'learning_counts', 'normalization_counts', 'representation_counts', 'target_counts')),
                    'physically shared first LOCAL facts and identical private initial arrays produce identical first fits')
                with np.load(batch['arms']['FIXED_LOCAL']['head_version']['file'], allow_pickle=False) as fixed, \
                        np.load(batch['arms']['CLOSED_LOCAL']['head_version']['file'], allow_pickle=False) as closed:
                    require(all(np.array_equal(fixed[name], closed[name]) for name in
                        ('reward_indices', 'reward_values', 'terminal_indices', 'terminal_values')),
                        'identical shared first LOCAL data and private fits retain exactly identical actual changed parameters')
            cells[f'ROUND{round_index}_{task}'] = dict(task=task, checkpoint=f'ROUND{round_index}',
                estimated_p_four=first['planning_belief']['estimated_p_four'], quota=batch['quota'], arms=values)
    for task in TASKS:
        first = life['initial'][task]; context = contexts[task]
        for arm in ARMS[1:]:
            kind = 'LINEAR_WIN2' if arm in ('FIRST_LINEAR', 'CLOSED_LINEAR') else 'LOCAL_RISK'
            initial_arm = 'FIRST_LINEAR' if kind == 'LINEAR_WIN2' else 'FIRST_LOCAL'
            head = HeadVersions(source, first['head_versions'][initial_arm]['source_checkpoint'],
                dict(lifecycle=life_id, parent=parent, context_id=context, arm=arm), kind)
            head.apply(first['head_versions'][initial_arm])
            if arm in ('FIRST_LOCAL', 'FIRST_LINEAR'):
                for round_index in (1, 2):
                    collector = 'SHARED_LOCAL' if round_index == 1 else 'FIXED_LOCAL'
                    if arm == 'FIRST_LOCAL':
                        world = batch_worlds[life_id, task, round_index, collector]
                        probe_count += world.check_probes(head, world.snapshot['policy_probes'])
                final_version = first['head_versions'][arm]
            else:
                for round_index in (1, 2):
                    if arm in ('CLOSED_LOCAL', 'CLOSED_LINEAR'):
                        collector = 'SHARED_LOCAL' if round_index == 1 and arm == 'CLOSED_LOCAL' else arm
                        world = batch_worlds[life_id, task, round_index, collector]
                        if collector != 'SHARED_LOCAL':
                            probe_count += world.check_probes(head, world.snapshot['policy_probes'])
                    head.apply(life['rounds'][str(round_index)][task]['arms'][arm]['head_version'])
                final_version = life['rounds']['2'][task]['arms'][arm]['head_version']
            require(life['final_head_versions'][task][arm] == final_version, 'final first/fixed/closed head inventory preserves each actual version lineage')
        direct[task] = {}
        for arm in DIRECT_ARMS:
            version = first['head_versions'][arm] if arm in ('FIRST_LOCAL', 'FIRST_LINEAR') else latest[task][arm]
            h2 = first['evaluations'][arm]['H2'] if arm in ('FIRST_LOCAL', 'FIRST_LINEAR') else life['rounds']['2'][task]['arms'][arm]['evaluations']['H2']
            check_same_evaluation_head(life['final_direct'][task][arm], h2)
            direct[task][arm] = check_evaluation(life['final_direct'][task][arm], life_id, task, first['planning_belief'], version, 'DIRECT')
    return dict(lifecycle=life_id, parent=parent, cells=cells, direct=direct), probe_count, unchanged


def check_contrast(saved, values):
    require(len(values) == 16 and close(saved['mean'], mean(values)), 'all sixteen signed paired whole-lifecycle endpoint differences')
    equal_tree(saved['lifecycle_deltas'], {str(index): value for index, value in enumerate(values)}, 'all new lifecycle endpoint deltas')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'], {str(parent): mean(group) for parent, group in enumerate(groups)}, 'four realized four-life parent means')
    low, high = saved['ci95']
    require(saved['interval_scope'] == INTERVAL_SCOPE and mean(min(group) for group in groups)-1e-10 <= low <= high
        <= mean(max(group) for group in groups)+1e-10, 'intervals retain their frozen-parent conditional scope and feasible range')
    require(saved['improved_equal_worse'] == [sum(value > 0 for value in values), sum(value == 0 for value in values), sum(value < 0 for value in values)]
        and saved['adverse_lifecycles'] == [index for index, value in enumerate(values) if value < 0], 'all adverse new lifecycle results are retained')


def check_analysis(summary, records, unchanged):
    equal_tree(summary['by_lifecycle'], records, 'all actual new H2 and DIRECT whole-game endpoint cells')
    require(summary['bootstrap_draws'] == 20000 and summary['bootstrap_seed'] == 31300001
        and summary['interval_scope'] == INTERVAL_SCOPE and summary['primary_contrast'] == 'CLOSED_LOCAL_minus_FIRST_LOCAL_FINAL_AB',
        'new V313 primary and frozen paired bootstrap contract')
    def utility(record, round_index, task, arm):
        return record['cells'][f'ROUND{round_index}_{task}']['arms'][arm]['mean_game_utility']
    for round_index in (1, 2):
        for left, right in PAIRS:
            name = left+'_minus_'+right
            values = [mean(utility(row, round_index, task, left)-utility(row, round_index, task, right) for task in TASKS) for row in records]
            check_contrast(summary['round_ab_contrasts'][str(round_index)][name], values)
            for task in TASKS:
                check_contrast(summary['cells'][f'ROUND{round_index}_{task}']['paired_contrasts'][name],
                    [utility(row, round_index, task, left)-utility(row, round_index, task, right) for row in records])
        for task in TASKS:
            for arm in UPDATING_ARMS:
                first = 'FIRST_LINEAR' if arm == 'CLOSED_LINEAR' else 'FIRST_LOCAL'
                check_contrast(summary['checkpoint_contrasts'][f'ROUND{round_index}_{task}'][arm],
                    [utility(row, round_index, task, arm)-utility(row, round_index, task, first) for row in records])
    equal_tree(summary['final_ab_contrasts'], summary['round_ab_contrasts']['2'], 'final endpoints preserve the second scheduled round')
    for arm in DIRECT_ARMS:
        by_task = [[utility(row, 2, task, arm)-row['direct'][task][arm]['mean_game_utility'] for row in records] for task in TASKS]
        check_contrast(summary['planning_contributions'][arm]['final_ab'], [mean(values) for values in zip(*by_task)])
        for task, values in zip(TASKS, by_task):
            check_contrast(summary['planning_contributions'][arm]['by_task'][task], values)
    complete = not any(value['cutoffs'] for row in records for cell in row['cells'].values() for value in cell['arms'].values()) \
        and not any(value['cutoffs'] for row in records for task in row['direct'].values() for value in task.values())
    require(summary['complete_game_endpoints'] == complete and not summary['training_cutoffs']
        and summary['initial_context_precondition_met'] and not summary['initial_precondition_failed_lifecycles'],
        'all scientific support retains training and evaluation cutoffs and the actual initial bank precondition')
    def status(contrast, retention=False):
        if not complete:
            return 'INCOMPLETE_GAME_ENDPOINTS'
        low, high = contrast['ci95']
        return ('SUPPORTED_NONDECREASE' if retention else 'SUPPORTED_GAIN') if (low >= 0 if retention else low > 0) \
            else 'SUPPORTED_LOSS' if high < 0 else 'UNRESOLVED'
    final = summary['final_ab_contrasts']; primary_status = status(final['CLOSED_LOCAL_minus_FIRST_LOCAL'])
    feedback_status = status(final['CLOSED_LOCAL_minus_FIXED_LOCAL']); net_status = status(final['CLOSED_LOCAL_minus_SOURCE'])
    task_gain = {task: status(summary['cells']['ROUND2_'+task]['paired_contrasts']['CLOSED_LOCAL_minus_FIRST_LOCAL']) for task in TASKS}
    retention = {task: status(summary['checkpoint_contrasts']['ROUND2_'+task]['CLOSED_LOCAL'], True) for task in TASKS}
    supported_retention = all(value == 'SUPPORTED_NONDECREASE' for value in retention.values())
    primary, feedback = primary_status == 'SUPPORTED_GAIN', feedback_status == 'SUPPORTED_GAIN'
    expected = dict(primary_self_improvement_supported=primary, primary_self_improvement_status=primary_status,
        feedback_supported=feedback, feedback_status=feedback_status, final_net_gain_supported=net_status == 'SUPPORTED_GAIN',
        final_net_gain_status=net_status, final_task_improvement_supported={task: value == 'SUPPORTED_GAIN' for task, value in task_gain.items()},
        final_task_improvement_status=task_gain, task_retention_status=retention, task_retention_supported=supported_retention,
        retained_improvement_supported=primary and supported_retention,
        closed_loop_mechanism_supported=primary and supported_retention and feedback and not unchanged,
        actor_change_premise_met=not unchanged, actor_change_premise_status='HOLD_NO_ACTOR_CHANGE' if unchanged else 'MET',
        unchanged_round_two_actors=unchanged)
    equal_tree({key: summary[key] for key in expected}, expected, 'own-first improvement feedback actual actor change and literal task retention support')
    return expected


def check_accounting(document, inherited):
    account, lives, parents = document['accounting'], document['by_lifecycle'], document['parent_receipts']
    initial = [row for life in lives for row in life['initial'].values()]
    batches = [collector for life in lives for tasks in life['rounds'].values() for row in tasks.values() for collector in row['collectors'].values()]
    updates = {arm: [row['arms'][arm] for life in lives for tasks in life['rounds'].values() for row in tasks.values()] for arm in UPDATING_ARMS}
    evaluations = [result['H2'] for row in initial for result in row['evaluations'].values()]
    evaluations += [value['evaluations']['H2'] for values in updates.values() for value in values]
    evaluations += [result for life in lives for task in life['final_direct'].values() for result in task.values()]
    initial_raw = sum(row['acquisition']['warmup']['raw_tiles']+row['acquisition']['training']['raw_tiles'] for row in initial)
    post_raw = sum(row['acquisition']['training']['raw_tiles'] for row in batches)
    require(len(initial) == 32 and len(batches) == 160 and post_raw == 16*2*5*POST_RAW
        and all(row['acquisition']['training']['raw_tiles'] == INITIAL_RAW for row in initial),
        'all actual initial SOURCE cohorts and once-physical shared/separate post cohorts retain the frozen raw budgets')
    source_raw = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']
    versions = [version for row in initial for version in row['head_versions'].values()]
    versions += [value['head_version'] for values in updates.values() for value in values]
    require(len(versions) == len({row['file'] for row in versions}) == 256, 'only actual initial and changed private versions are saved without redundant dense head checkpoints')
    expected = dict(inherited_source_costs=inherited, source_physical_training_repeated=False,
        initial_acquisitions=32, post_physical_acquisitions=160, initial_raw_tiles=initial_raw, post_raw_tiles=post_raw,
        new_training_raw_tiles=initial_raw+post_raw,
        economic_training_raw_tiles_per_arm={arm: source_raw+initial_raw+(16*2*2*POST_RAW if arm in UPDATING_ARMS else 0) for arm in ARMS},
        excluded_tail_raw_tiles=sum(row['dataset']['costs']['excluded_tail_raw_tiles'] for row in initial+batches),
        fit_states_per_updating_arm={arm: sum(value['fit']['trained_afterstates'] for value in values) for arm, values in updates.items()},
        fit_counts_per_updating_arm={arm: sum_counts(value['fit']['learning_counts'] for value in values) for arm, values in updates.items()},
        fit_cpu_seconds_per_updating_arm={arm: sum(value['fit']['cpu_seconds'] for value in values) for arm, values in updates.items()},
        initial_fit_cpu_seconds=sum(fit['cpu_seconds'] for row in initial for fit in row['first_fits'].values()),
        post_acquisition_cpu_seconds=sum(row['acquisition']['cpu_seconds'] for row in batches),
        new_evaluation_games=sum(len(value['game_summaries']) for value in evaluations),
        evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations),
        evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        version_files=len(versions), version_saved_bytes=sum(row['saved_bytes'] for row in versions),
        version_scanned_parameters=sum(row['scan_parameters'] for row in versions),
        version_copy_parameters=sum(row['copy_parameters'] for row in versions),
        version_save_cpu_seconds=sum(row['save_cpu_seconds'] for row in versions),
        version_copy_cpu_seconds=sum(row['copy_cpu_seconds'] for row in versions),
        private_head_weight_bytes_peak=max(life['private_head_weight_bytes'] for life in lives),
        canonical_trace_bytes=sum(row['trace_bytes'] for row in parents),
        worker_cpu_seconds=sum(row['cpu_seconds'] for row in parents),
        compiler_cpu_seconds=sum(row['compiler_cpu_seconds'] for row in parents), new_compute_closed=True)
    equal_tree({key: account[key] for key in expected}, expected, 'actual new raw sampling scans copies saves labels evaluations and physical compute closure')
    require(account['new_evaluation_games'] == 13312, 'all thirteen H2/DIRECT cells per task life are physically new whole games')
    target_cpu = sum(account[key] for key in ('worker_cpu_seconds', 'compiler_cpu_seconds', 'coordinator_cpu_seconds'))
    require(close(account['new_target_cpu_seconds'], target_cpu)
        and close(account['economic_source_and_target_cpu_seconds'], target_cpu+inherited['fresh_source_compute']['full_source_cpu_seconds']),
        'complete reused SOURCE CPU is charged economically once while contained setup copy save times stay within actual worker CPU')
    source = {row['parent']: row for row in document['source_provenance']['parents']}
    require([row['parent'] for row in parents] == list(range(4)) and all(row['source_setup']['checkpoint_loads'] == 1
        and row['source_setup']['new_leaf_updates'] == 0 and row['source_setup']['inherited_updates'] == source[row['parent']]['updates'] for row in parents),
        'each audited V312 SOURCE checkpoint is physically loaded once without retraining or changed value history')
    return expected


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    frozen = json_file(directory/'configuration.json')
    require(document['schema'] == 'acfqp.closed_loop.v313' and document['status'] == 'EXPERIMENT_COMPLETE'
        and document['scientific_gate'] == 'NOT_A_FORMAL_GATE', 'complete new V313 development experiment terminal schema')
    equal_tree(frozen, expected_configuration(frozen['source_summary']), 'frozen V313 scientific and data contract')
    equal_tree(document['settings'], frozen, 'all completed V313 data uses its original frozen contract')
    source_path = Path(frozen['source_summary']); original = json_file(source_path)
    source_audit = require_source_audit(source_path.parent)
    inherited = check_fresh_source_document(original, document['source_provenance'])
    require([row['lifecycle'] for row in document['by_lifecycle']] == list(range(16))
        and all(row['parent'] == row['lifecycle']%4 for row in document['by_lifecycle']), 'all sixteen fresh development lives remain under their four fixed parents')
    initial, batches, rows_read = read_canonical(document)
    source_rows = {row['parent']: row for row in original['source_provenance']['parents']}
    source_weights = {parent: read_source_weights(row['checkpoint']) for parent, row in source_rows.items()}
    records, unchanged = [], []; probes = 0
    for life in document['by_lifecycle']:
        record, checked, no_change = check_lifecycle(life, initial, batches, source_weights[life['parent']], source_rows[life['parent']]['checkpoint'])
        records.append(record); probes += checked; unchanged.extend(no_change)
    support = check_analysis(document['summary'], records, unchanged)
    check_accounting(document, inherited)
    require(probes == 16*2*5*16, 'all predeclared first/last probes from every physical collector are checked exactly once')
    return dict(status='PASS', independent_valid=True, lifecycles=16, fixed_source_parents=4,
        fresh_source_audit_status=source_audit['status'], fresh_source_provenance_checked=True,
        canonical_rows=rows_read, physical_initial_acquisitions=len(initial), physical_post_acquisitions=len(batches),
        literal_actor_action_probes=probes, reconstructed_head_versions=256,
        immutable_bank_beliefs_valid=True, complete_factual_suffix_labels_checked=True,
        shared_first_local_cohort_checked=True, actual_equal_quota_checked=True,
        same_head_direct_h2_checked=True, new_evaluation_games=13312,
        new_training_raw_tiles=document['accounting']['new_training_raw_tiles'],
        new_target_cpu_seconds=document['accounting']['new_target_cpu_seconds'],
        economic_source_and_target_cpu_seconds=document['accounting']['economic_source_and_target_cpu_seconds'],
        primary_utility=document['summary']['final_ab_contrasts']['CLOSED_LOCAL_minus_FIRST_LOCAL'], **support,
        method='One independent replay of all new detector and continuous initial/post raw tapes, independently seeded cell/rank draws and complete natural physical game labels; sparse SOURCE-relative and actual changed-address head reconstruction; literal first/last all-action H2 values and frozen version lineage; complete factual reward suffixes and chronological equal-quota masks; same actual heads for H2/DIRECT; own-first, feedback, source and literal task-retention endpoint checks; actual scans/copies/saves and CPU closure.',
        limitations='Development evidence is conditional on four audited V312 SOURCE value parents and inherited deterministic dynamics. Known task/batch boundaries address the initially observed context banks. Only fixed first-eight/last-eight collector action probes are recomputed; all physical tapes are replayed. Complete experimental fits, evaluation actions and bootstrap draws are not recomputed. Actual address writes and CPU can differ despite equal supervised-state quotas. SOURCE and target compute are accounted economically once; historical dynamics CPU remains unknown.', errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.output)
    except (ValueError, KeyError, FileNotFoundError, IndexError) as error:
        result = dict(status='FAIL', independent_valid=False, errors=[str(error)])
    path = args.output/'audit.json'; path.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['independent_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

