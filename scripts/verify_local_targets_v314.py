#!/usr/bin/env python3
"""Independent V314 physical fixed-actor and every saved sampled-SARSA target audit."""
import argparse
from collections import Counter, deque, defaultdict
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path
import random
from statistics import mean
import numpy as np

from verify_closed_loop_v313 import (ACTIONS, PATTERNS, TileRandom, seeded_place,
    swipe, physical_status, HeadVersions, literal_choose, component_value,
    check_actor_link, check_batch_dataset, check_initial_acquisition, check_initial_fit,
    check_contrast, require_source_audit, read_source_weights,
    close, equal_tree, json_file, require, sum_counts, pooled_memory, board_status,
    planning_counts, Memory, check_representation, check_detection_route,
    check_fresh_source_document, observed_statistics, learned)

TASKS = ('A', 'B')
STAGES = ('A0', 'B0')
PROBABILITIES = {'A': .1, 'B': .5}
ARMS = ('SOURCE', 'FIRST_LOCAL', 'MC_LOCAL', 'TD_LOCAL')
UPDATING_ARMS = ('MC_LOCAL', 'TD_LOCAL')
PAIRS = (('TD_LOCAL', 'FIRST_LOCAL'), ('TD_LOCAL', 'MC_LOCAL'),
    ('TD_LOCAL', 'SOURCE'), ('MC_LOCAL', 'FIRST_LOCAL'),
    ('MC_LOCAL', 'SOURCE'), ('FIRST_LOCAL', 'SOURCE'))
INITIAL_RAW = RAW = 131072
POST_RAW = 65536
DETECTOR_CAP = 4096
CHUNK_RAW = 256
PROBE_ACTIONS = 8
LIVES = 16
ROUND_RAW = POST_RAW
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
MAX_STEPS = 8192
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def stage_context(row):
    require(row['phase'] in STAGES and row['true_p_four'] == PROBABILITIES[row['phase'][0]],
        'new initial A0/B0 world metadata follows the frozen two-task probabilities')


def warmup_seed(life, stage, game):
    return 314100000000+STAGES.index(stage)*100000+life*1000000+game


def training_seed(life, stage):
    return 314200000000+STAGES.index(stage)*100000+life*10000000


def post_seed(life, task, round_index):
    return 314500000000+life*10000000+TASKS.index(task)*1000000+round_index*100000


def evaluation_seed(life, task, episode):
    return 314900000000+life*1000000+TASKS.index(task)*100000+episode


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


class FactualWorld:
    """One new continuous post-initial stream, with all labels and fixed action probes."""
    def __init__(self, seed, raw_budget, probability, expected_identity, kind, radix=11):
        self.seed, self.raw_budget, self.probability = seed, raw_budget, probability
        self.expected_identity, self.kind, self.radix = dict(expected_identity), kind, radix
        self.rng = TileRandom(seed)
        self.state = self.before = None
        self.games, self.scores, self.ends, self.game_memories = [], [], [], []
        self.current_scores = []
        self.afterstate_chunks = []
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
        chunk_afterstates = []
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
                chunk_afterstates.append(list(after))
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
        self.afterstate_chunks.append(np.asarray(chunk_afterstates, dtype=np.int32).reshape(-1, 16))

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


def expected_configuration(source_summary):
    return dict(schema='acfqp.local_target_freeze.v314',
        protocol=str(Path(__file__).resolve().parents[1]/'specs/LOCAL_TARGETS_V314.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(LIVES)),
        parents=4, workers=4, arms=list(ARMS), tasks=list(TASKS), true_probabilities=PROBABILITIES,
        rounds=[1,2], initial_raw_per_task=INITIAL_RAW, round_raw_per_collector=ROUND_RAW,
        fit_fraction=.8, alpha=.0025, query=QUERY, max_steps=MAX_STEPS,
        initial_contexts='V309_CONFIRMED_NEW_BANKS_DISTINCT_PRECONDITION',
        context_updates='SUPPLIED_KNOWN_TASK_BANK_FROM_INITIAL_OBSERVED_ROUTE',
        planning_probability='IMMUTABLE_ACTUAL_BANK_FIRST_FIT_BELIEF',
        collector='FROZEN_FIRST_LOCAL_VERSION_0_ALL_ROUNDS_SHARED_PHYSICALLY',
        quota='ALL_NONWINNING_COMPLETE_FIT_STATES_SHARED_BETWEEN_ARMS',
        mc_target='COMPLETE_FACTUAL_REWARD_SUFFIX_AND_TERMINAL_WIN_LABEL',
        td_target='ACTUAL_NEXT_ACTION_REWARD_AND_AFTERSTATE_BATCH_START_SARSA',
        bootstrap='BATCH_START_FROZEN_OWN_HEAD_V0_THEN_V1',
        update='UNCHANGED_GAME_START_CURRENT_RESIDUAL_AND_OCCURRENCE_NORMALIZATION',
        target_artifact='ALL_FIT_NATIVE_REWARD_WIN_KIND_TARGETS_WITH_ACTUAL_BOOTSTRAP_VERSION',
        head_history_format='acfqp.head_version.v313',
        action_probes='FIRST_EIGHT_AND_LAST_EIGHT_ACTIONS_EACH_NEW_BATCH',
        seed_initial_warmup=314100000000, seed_initial_training=314200000000,
        seed_collection=314500000000, collection_life_stride=10000000,
        collection_task_stride=1000000, collection_round_stride=100000,
        seed_evaluation=314900000000, evaluation_games_per_cell=32,
        bootstrap_draws=20000, bootstrap_seed=31400001,
        primary='TD_LOCAL_minus_FIRST_LOCAL_FINAL_AB',
        target_intervention='TD_LOCAL_minus_MC_LOCAL_FINAL_AB',
        retention='FINAL_TD_MINUS_OWN_FIRST_PER_TASK_CI_LOWER_NONNEGATIVE',
        expected_post_raw_physical=LIVES*2*2*ROUND_RAW,
        expected_evaluation_games=LIVES*2*32*6,
        evidence_scope='DEVELOPMENT_16_NEW_LIVES_CONDITIONAL_ON_FOUR_V312_PARENTS_SHARED_DYNAMICS',
        stop_rule='NO_SEED_ALPHA_TARGET_SNAPSHOT_BUDGET_OR_INTERVAL_TUNING_RETAIN_LOSS')


def check_evaluation(value, life, task, belief, version):
    planner = 'H2'
    require(value['estimated_p_four'] == belief['estimated_p_four'] and value['head_version'] == version
        and value['planner'] == planner and value['static_evaluation_valid'],
        'new whole-game evaluation executes its exact actual head and immutable bank planning belief')
    games = value['game_summaries']; require(len(games) == 32
        and [game['seed'] for game in games] == [evaluation_seed(life, task, i) for i in range(32)], 'all new H2/DIRECT endpoints use their paired V314 task seeds')
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


def feature_addresses(boards, radix=11):
    cells = np.asarray(boards, dtype=np.int32).reshape(-1, 16)
    addresses = np.zeros((len(cells), 32), dtype=np.int64)
    for digit in range(6):
        addresses = radix*addresses+cells[:, PATTERNS[:, digit]]
    return addresses+(np.arange(32)//8)*radix**6


def predict_components(boards, head, radix=11):
    """Literal occurrence order, bounded chunk arrays, and the existing stable sigmoid."""
    addresses = feature_addresses(boards, radix)
    reward, logit = np.zeros(len(addresses)), np.zeros(len(addresses))
    for occurrence in range(32):
        reward += head.reward[addresses[:, occurrence]]
        logit += head.terminal[addresses[:, occurrence]]
    probability = np.empty(len(logit)); positive = logit >= 0.
    probability[positive] = 1./(1.+np.exp(-logit[positive]))
    exp_negative = np.exp(logit[~positive])
    probability[~positive] = exp_negative/(1.+exp_negative)
    return reward, probability


def factual_targets(boards, rewards, games, fit_game_count, head, radix=11):
    """Targets use actual next action reward, never current reward or another game."""
    end = sum(game['steps'] for game in games[:fit_game_count])
    boards = np.asarray(boards, dtype=np.int32)[:end]
    rewards = np.asarray(rewards, dtype=np.float64)[:end]
    require(len(boards) == len(rewards) == end, 'every complete FIT step has its actual afterstate and reward')
    target_reward, target_win = np.zeros(end), np.zeros(end)
    kind = np.zeros(end, dtype=np.int32); offset = 0
    for game in games[:fit_game_count]:
        stop = offset+game['steps']; winning = np.max(boards[offset:stop], axis=1) >= radix
        require(game['status'] in ('WON', 'LOST') and stop > offset
            and (not np.any(winning) if game['status'] == 'LOST' else
                 winning[-1] and not np.any(winning[:-1])),
            'factual target successors retain exactly the natural game ending and untrained winning afterstate')
        active_stop = stop-1
        if active_stop > offset:
            successors = np.arange(offset, active_stop)
            kind[successors] = np.where(np.max(boards[successors+1], axis=1) >= radix, 2, 1)
            target_reward[successors] = rewards[successors+1]
            target_win[successors[kind[successors] == 2]] = 1.
        if game['status'] == 'LOST':
            kind[stop-1] = 3
        offset = stop
    bootstrap_indices = np.flatnonzero(kind == 1)
    for start in range(0, len(bootstrap_indices), 4096):
        indices = bootstrap_indices[start:start+4096]
        reward, probability = predict_components(boards[indices+1], head, radix)
        target_reward[indices] += reward; target_win[indices] = probability
    return target_reward, target_win, kind


def target_metadata(version, fit_games, fit_steps, radix=11):
    return dict(schema='acfqp.local_sampled_sarsa_targets.v314',
        bootstrap_mode='BATCH_START_FROZEN_OWN_HEAD', bootstrap_version=deepcopy(version),
        fitted_games=fit_games, fitted_steps=fit_steps, goal_rank=radix,
        target_kinds={'0':'UNUSED_WINNING_AFTERSTATE', '1':'SAMPLED_SUCCESSOR_BOOTSTRAP',
            '2':'ANALYTIC_NEXT_WIN', '3':'LAST_LOST'},
        target_rule='RECORDED_SUCCESSOR_AFTERSTATE_NEXT_REWARD_UNDISCOUNTED',
        target_array_bytes=fit_steps*20)


def check_td_targets(fit, boards, rewards, games, fit_game_count, head, version, radix=11):
    require(fit['method'] == 'TD_LOCAL' and fit['frozen_game_start_predictions']
        and fit['frozen_batch_start_bootstrap'] and fit['bootstrap_mode'] == 'BATCH_START_FROZEN_OWN_HEAD'
        and fit['bootstrap_version'] == version,
        'TD targets retain their own actual batch-start head, with unchanged game-start current predictions')
    expected = factual_targets(boards, rewards, games, fit_game_count, head, radix)
    steps, samples = len(expected[2]), np.count_nonzero(expected[2])
    artifact = fit['target_artifact']; path = Path(artifact['file'])
    require(path.stat().st_size == artifact['saved_bytes'], 'all saved native TD target bytes are charged')
    metadata = target_metadata(version, fit_game_count, steps, radix)
    equal_tree(artifact['metadata'], metadata, 'TD target ownership and full complete-FIT array metadata')
    with np.load(path, allow_pickle=False) as data:
        require(set(data.files) == {'targetreward', 'targetwin', 'targetkind', 'metadata_json'},
            'native TD target artifact contains its exact actual reward WIN kind arrays and metadata_json')
        equal_tree(json.loads(str(data['metadata_json'])), metadata, 'native TD target file records the actual own bootstrap version')
        for key, dtype, wanted in zip(('targetreward', 'targetwin', 'targetkind'),
                (np.float64, np.float64, np.int32), expected):
            saved = data[key]
            require(saved.dtype == dtype and saved.shape == (steps,), 'native target arrays cover every FIT step with their actual types')
            matched = np.array_equal(saved, wanted) if key == 'targetkind' else np.allclose(saved, wanted, rtol=1e-12, atol=1e-12)
            require(matched, 'every saved native '+key+' matches the independently reconstructed actual next consequence and own frozen head')
    counts = Counter(map(int, expected[2])); boot = counts[1]; next_reads = boot+counts[2]
    targets = dict(terminal_game_labels=fit_game_count, goal_checks=steps,
        skipped_winning_afterstates=counts[0], sampled_next_reward_reads=next_reads,
        reward_target_assignments=samples, win_target_assignments=samples,
        bootstrap_successor_targets=boot, analytic_next_win_targets=counts[2],
        terminal_lost_targets=counts[3], next_afterstate_goal_checks=next_reads, target_kind_reads=steps)
    require(Counter(fit['target_counts']) == Counter(targets), 'TD pays only real successor terminal and WIN assignments, with no phantom suffix work')
    bootstrap = dict(afterstate_predictions=boot, reward_table_lookups=32*boot, risk_table_lookups=32*boot,
        feature_extractions=boot, feature_occurrences=32*boot, feature_digit_reads=192*boot,
        feature_address_multiply_adds=192*boot, risk_sigmoid_evaluations=boot, local_risk_table_lookups=32*boot)
    require(Counter(fit['bootstrap_counts']) == Counter(bootstrap), 'frozen own-head bootstrap reads features and sigmoids are charged once')
    for name, step in (('first_sample', int(np.flatnonzero(expected[2])[0])),
                       ('last_sample', int(np.flatnonzero(expected[2])[-1]))):
        sample = fit[name]
        require(sample['step'] == step and close(sample['reward_target'], expected[0][step])
            and close(sample['risk_target'], expected[1][step]), 'actual TD first/last fit samples consume the saved native target arrays')
    first = fit['first_sample']; first_step = first['step']
    reward, probability = predict_components(np.asarray(boards)[first_step:first_step+1], head, radix)
    require(close(first['reward_prediction'], float(reward[0])) and close(first['risk_probability'], float(probability[0])),
        'the first TD current residual reads the same actual own head present at batch start')
    require(0 <= artifact['save_cpu_seconds'] <= fit['cpu_seconds']
        and 0 <= artifact['save_wall_seconds'] <= fit['seconds']
        and 0 <= fit['target_generation_cpu_seconds'] <= fit['cpu_seconds']
        and 0 <= fit['target_generation_wall_seconds'] <= fit['seconds'],
        'actual target generation and artifact saving remain contained in complete fit timing')
    return steps


def address_inventory(boards, games, fit_game_count, radix=11):
    writes = products = offset = commits = 0
    for game in games[:fit_game_count]:
        stop = offset+game['steps']; selected = np.asarray(boards)[offset:stop-(game['status'] == 'WON')]
        addresses = feature_addresses(selected, radix)
        if len(addresses):
            writes += len(np.unique(addresses)); commits += 1
            ordered = np.sort(addresses, axis=1)
            products += len(ordered)+np.count_nonzero(ordered[:, 1:] != ordered[:, :-1])
        offset = stop
    return writes, products, commits


def check_complete_fit(fit, boards, rewards, games, n, inventory, td_targets=None):
    steps = sum(game['steps'] for game in games[:n]); wins = sum(game['status'] == 'WON' for game in games[:n])
    samples = steps-wins; td = td_targets is not None
    require(fit['method'] == ('TD_LOCAL' if td else 'LOCAL_RISK') and fit['alpha'] == .0025
        and fit['fitted_games'] == n and fit['fitted_steps'] == steps
        and fit['trained_afterstates'] == fit['reward_trained_afterstates'] == fit['risk_trained_afterstates'] == samples
        and fit['frozen_game_start_predictions' if td else 'frozen_game_start_targets'],
        'MC and TD fit every actual nonwinning complete FIT state with the same alpha and game-start residual rule')
    writes, products, commits = inventory
    work = dict(td_updates=samples, value_predictions=samples, table_lookups=64*samples, table_updates=2*writes,
        table_update_occurrences=32*samples, reward_predictions=samples, risk_predictions=samples,
        reward_table_lookups=32*samples, risk_table_lookups=32*samples, reward_table_updates=writes, risk_parameter_updates=writes)
    require(Counter(fit['learning_counts']) == Counter(work), 'independent factual address inventories match both actual parameter-read and write ledgers')
    norm = dict(games_processed=n, feature_extractions=samples, feature_occurrences=32*samples,
        feature_digit_reads=192*samples, feature_address_multiply_adds=192*samples, sort_calls=n+samples,
        sort_items=64*samples, denominator_occurrence_visits=32*samples, game_unique_addresses=writes,
        reward_gradient_products=products, reward_gradient_accumulations=products,
        risk_gradient_products=products, risk_gradient_accumulations=products,
        normalization_divisions=2*writes, parameter_update_multiplications=2*writes,
        game_parameter_commits=commits, reward_game_commits=commits, risk_game_commits=commits,
        reward_parameter_writes=writes, risk_parameter_writes=writes, address_denominator_searches=products)
    require(all(fit['normalization_counts'][key] == value for key, value in norm.items()),
        'literal same-game occurrence multiplicities determine both learner normalizations and commits')
    check_representation(fit['representation_counts'], 'LOCAL_RISK', samples)
    if not td:
        targets = dict(terminal_game_labels=n, risk_label_assignments=samples,
            reward_suffix_target_assignments=steps, reward_suffix_additions=steps, goal_checks=steps, skipped_winning_afterstates=wins)
        require(Counter(fit['target_counts']) == Counter(targets), 'MC retains complete factual reward suffixes and hard natural WIN labels')
    for name, episode, step in (('first_sample', 0, 0), ('last_sample', n-1, steps-1-(games[n-1]['status'] == 'WON'))):
        sample = fit[name]; local = step-sum(game['steps'] for game in games[:episode])
        target = td_targets[0][step] if td else sum(rewards[step+1:sum(game['steps'] for game in games[:episode+1])])
        label = td_targets[1][step] if td else float(games[episode]['status'] == 'WON')
        require(sample['episode'] == episode and sample['step'] == step and close(sample['reward_target'], target)
            and close(sample['risk_target'], label) and 0 <= sample['risk_probability'] <= 1
            and close(sample['reward_error'], target-sample['reward_prediction'])
            and close(sample['risk_error'], label-sample['risk_probability'])
            and close(sample['combined_prediction'], sample['reward_prediction']+8.*(sample['risk_probability']-.5)),
            'first and last current residuals use their actual full-MC or factual one-step targets')
    return samples


def check_equal_fit_work(mc, td):
    for key in ('learning_counts', 'representation_counts'):
        equal_tree(td[key], mc[key], 'same factual states produce equal actual '+key)
    mc_norm = {key:value for key,value in mc['normalization_counts'].items() if key != 'native_buffer_bytes_peak'}
    td_norm = {key:value for key,value in td['normalization_counts'].items() if key != 'native_buffer_bytes_peak'}
    require(Counter(mc_norm) == Counter(td_norm), 'MC and TD retain identical factual address normalization and actual table writes')
def read_canonical(document):
    lives = {row['lifecycle']:row for row in document['by_lifecycle']}
    initial = {(life, stage):InitialWorld(life, stage) for life in range(16) for stage in STAGES}
    batches = {}; rows_read = 0; initial_heads = set(); consolidated = set()
    for parent in document['parent_receipts']:
        parent_id = parent['parent']; path = Path(parent['trace_file'])
        require(path.stat().st_size == parent['trace_bytes'], 'new canonical tapes retain their actual compressed byte inventory')
        parent_rows = 0
        with gzip.open(path, 'rt') as stream:
            for line in stream:
                row = json.loads(line); life_id = row['lifecycle']; life = lives[life_id]
                require(life_id%4 == row['parent'] == parent_id, 'new raw histories belong to their frozen fresh SOURCE parent')
                rows_read += 1; parent_rows += 1
                if row['kind'] == 'INITIAL_HEADS':
                    key = life_id, row['task']
                    require(key not in initial_heads and initial[life_id, row['task']+'0'].snapshot is not None
                        and row['head_versions'] == life['initial'][row['task']]['head_versions'],
                        'initial actual sparse head follows its completed new SOURCE cohort')
                    initial_heads.add(key); continue
                if row['kind'] == 'CONSOLIDATED_HEAD':
                    task, round_index, arm = row['task'], row['round_index'], row['arm']
                    key = life_id, task, round_index, arm
                    batch = life['rounds'][str(round_index)][task]; value = batch['arms'][arm]
                    require(key not in consolidated and batches[life_id, task, round_index].snapshot is not None
                        and row['quota'] == batch['quota'] and row['head_version'] == value['head_version']
                        and row['fit'] == value['fit'],
                        'sole actual private fit and sparse version follow the complete shared factual batch')
                    consolidated.add(key); continue
                phase = row['phase']
                if phase in STAGES:
                    world = initial[life_id, phase]
                    if phase == 'B0':
                        require((life_id, 'A') in initial_heads, 'B initial detection follows completed A adaptation')
                    method = {'WARMUP':world.warmup, 'CONFIRMATION':world.warmup, 'DETECTOR_LOOK':world.look,
                        'DETECTION_SNAPSHOT':world.detect, 'TRAIN':world.train, 'ACQUISITION_SNAPSHOT':world.checkpoint}.get(row['kind'])
                else:
                    task = row['task']; round_index = int(phase[-1]); collector = row['arm']
                    require(phase == f'{task}_R{round_index}' and round_index in (1, 2)
                        and collector == 'FIXED_FIRST' and (life_id, 'B') in initial_heads,
                        'only declared fresh fixed-FIRST known-context batches are collected')
                    key = life_id, task, round_index
                    if key not in batches:
                        actor = life['initial'][task]['head_versions']['FIRST_LOCAL']
                        identity = dict(lifecycle=life_id, parent=parent_id, arm=collector, batch_id=phase, phase=phase,
                            true_p_four=PROBABILITIES[task], model_p_four=life['initial'][task]['planning_belief']['estimated_p_four'],
                            task=task, actor_head_updates=actor['updates'], collector_policy_kind='LOCAL_RISK',
                            actor_version=actor, stream_seed=post_seed(life_id, task, round_index))
                        batches[key] = FactualWorld(identity['stream_seed'], POST_RAW, PROBABILITIES[task], identity, 'LOCAL_RISK')
                    world = batches[key]
                    method = {'TRAIN':world.train, 'ACQUISITION_SNAPSHOT':world.checkpoint}.get(row['kind'])
                require(method is not None, 'canonical history contains only declared fresh physical and actual version events')
                method(row)
        require(parent_rows == parent['canonical_rows'], 'each actual parent canonical row count closes exactly')
    require(len(initial_heads) == 32 and len(consolidated) == 128 and len(batches) == 64
        and all(world.snapshot is not None for world in initial.values())
        and all(world.snapshot is not None for world in batches.values()),
        'all sixteen initial and four shared post histories per life are new and complete')
    return initial, batches, rows_read


def check_head_setups(life, size):
    total = 0
    for task in TASKS:
        require(set(life['head_setups'][task]) == {'FIRST_LOCAL', 'MC_LOCAL', 'TD_LOCAL'},
            'each actual bank owns its fixed FIRST and two private LOCAL branches')
        for arm, setup in life['head_setups'][task].items():
            counts = setup['setup_counts']
            require(counts['source_parameters_copied'] == size and counts['source_weight_bytes_copied'] == 8*size
                and counts['allocated_weight_parameters'] == 2*size and counts['allocated_weight_bytes'] == 16*size
                and counts['initialized_zero_risk_parameters'] == size and setup['private_weight_bytes'] == 16*size,
                'every actual LOCAL allocation retains its real SOURCE reward copy and zero-logit initialization costs')
            if arm in UPDATING_ARMS:
                require(counts['first_parameters_copied'] == 2*size and counts['first_weight_bytes_copied'] == 16*size,
                    'MC and TD start from private copies of both actual FIRST-adapted tables')
            total += setup['private_weight_bytes']
    require(life['private_head_weight_bytes'] == total, 'both banks count all three actual two-table heads once')


def check_fixed_collector(receipt, world, actor):
    acquisition = receipt['acquisition']; n = check_batch_dataset(receipt['dataset'], world)
    require(receipt['actor_version'] == acquisition['actor_version'] == actor
        and acquisition['actor_head_updates_before'] == acquisition['actor_head_updates_after'] == actor['updates']
        and acquisition['new_actor_updates'] == 0 and acquisition['training'] == world.snapshot['training']
        and acquisition['snapshot'] == world.snapshot['snapshot'] and acquisition['reconstruction'] == world.snapshot['reconstruction']
        and acquisition['policy_probes'] == world.snapshot['policy_probes'],
        'every fixed FIRST collector remains at its own immutable actual v0 throughout complete physical acquisition')
    quota = sum(game['steps']-(game['status'] == 'WON') for game in world.games[:n])
    require(receipt['selection'] == dict(eligible_samples=quota, selected_samples=quota,
        selection_rule='ALL_NONWINNING_COMPLETE_FIT_STATES'),
        'shared facts fit all chronological nonwinning complete FIT states without cropping a successor or suffix')
    return n, quota


def check_lifecycle(life, initial_worlds, batch_worlds, source, source_checkpoint):
    life_id, parent = life['lifecycle'], life['parent']; prototypes = []; cells = {}; latest = {}
    contexts = {task:life['initial'][task]['context_id'] for task in TASKS}
    require(life['initial_context_precondition_met'] and len(set(contexts.values())) == 2,
        'known task updates address two actually confirmed distinct initial observed banks')
    check_head_setups(life, source.size)
    for task in TASKS:
        first = life['initial'][task]; world = initial_worlds[life_id, task+'0']
        context, created = check_detection_route(first['context_route'], world.detection['detector_belief'], prototypes, world.looks)
        require(created and context == contexts[task], 'initial FIRST head follows its independently confirmed observed bank')
        n = check_initial_acquisition(first, world)
        require(set(first['first_fits']) == set(first['head_versions']) == {'FIRST_LOCAL'}, 'initial cohort fits only FIRST_LOCAL')
        fit, version = first['first_fits']['FIRST_LOCAL'], first['head_versions']['FIRST_LOCAL']
        check_initial_fit(fit, world, n, source)
        require(version['updates'] == fit['trained_afterstates'] and version['source_checkpoint'] == source_checkpoint,
            'actual FIRST v0 begins at its audited fresh SOURCE and complete FIT update count')
        belief = first['planning_belief']
        values = {arm:check_evaluation(first['evaluations'][arm]['H2'], life_id, task, belief,
            None if arm == 'SOURCE' else version) for arm in ('SOURCE', 'FIRST_LOCAL')}
        cells['FIRST_'+task] = dict(task=task, checkpoint='FIRST', estimated_p_four=belief['estimated_p_four'], arms=values)
        latest[task] = {arm:version for arm in UPDATING_ARMS}
    for round_index in (1, 2):
        for task in TASKS:
            batch = life['rounds'][str(round_index)][task]; first = life['initial'][task]
            other = 'B' if task == 'A' else 'A'
            require(set(batch['collectors']) == {'FIXED_FIRST'} and set(batch['arms']) == set(UPDATING_ARMS),
                'one physically shared fixed-FIRST batch feeds exactly two private target arms')
            require(batch['inactive_head_versions_before'] == batch['inactive_head_versions_after'] == latest[other],
                'inactive bank actual head ancestry remains unchanged throughout the other task batch')
            world = batch_worlds[life_id, task, round_index]
            n, quota = check_fixed_collector(batch['collectors']['FIXED_FIRST'], world, first['head_versions']['FIRST_LOCAL'])
            require(batch['quota'] == quota and quota > 0, 'both arms receive the full actual nonwinning FIT inventory')
            values = dict(cells['FIRST_'+task]['arms'])
            for arm in UPDATING_ARMS:
                item = batch['arms'][arm]; version = item['head_version']
                require(item['updates_before'] == latest[task][arm]['updates'] and item['updates_after'] == version['updates']
                    and item['updates_after']-item['updates_before'] == quota and version['updates'] == latest[task][arm]['updates']+quota,
                    'both private learner histories advance exactly once for each shared nonwinning sample')
                values[arm] = check_evaluation(item['evaluations']['H2'], life_id, task, first['planning_belief'], version)
                latest[task][arm] = version
            cells[f'ROUND{round_index}_{task}'] = dict(task=task, checkpoint=f'ROUND{round_index}',
                estimated_p_four=first['planning_belief']['estimated_p_four'], quota=quota, arms=values)
            check_equal_fit_work(batch['arms']['MC_LOCAL']['fit'], batch['arms']['TD_LOCAL']['fit'])
    for task in TASKS:
        equal_tree(life['final_head_versions'][task], dict(FIRST_LOCAL=life['initial'][task]['head_versions']['FIRST_LOCAL'],
            **latest[task]), 'actual final pointers preserve fixed FIRST and both private own-v2 heads')
    probes = target_steps = 0
    # Reconstruct one lineage at a time. No dense checkpoints or fits are recreated.
    for task in TASKS:
        first = life['initial'][task]; v0 = first['head_versions']['FIRST_LOCAL']
        identity = dict(lifecycle=life_id, parent=parent, context_id=contexts[task], arm='FIRST_LOCAL')
        head = HeadVersions(source, source_checkpoint, identity, 'LOCAL_RISK'); head.apply(v0)
        factual = {}
        for round_index in (1, 2):
            batch = life['rounds'][str(round_index)][task]; world = batch_worlds[life_id, task, round_index]
            probes += world.check_probes(head, batch['collectors']['FIXED_FIRST']['acquisition']['policy_probes'])
            boards = np.concatenate(world.afterstate_chunks)
            rewards = np.asarray([score for scores in world.scores for score in scores]+(world.current_scores if world.state['status'] == 'ACTIVE' else []), dtype=np.float64)/2048.
            require(len(boards) == len(rewards) == world.actions, 'independent raw replay retains every current and next afterstate including paid tails')
            n = batch['collectors']['FIXED_FIRST']['dataset']['fit_game_count']
            factual[round_index] = (boards, rewards, world.games, n, address_inventory(boards, world.games, n))
        del head
        for arm in UPDATING_ARMS:
            head = HeadVersions(source, source_checkpoint, dict(identity, arm=arm), 'LOCAL_RISK'); head.apply(v0)
            previous = v0
            for round_index in (1, 2):
                item = life['rounds'][str(round_index)][task]['arms'][arm]; fit = item['fit']
                boards, rewards, games, n, inventory = factual[round_index]
                expected = None
                if arm == 'TD_LOCAL':
                    target_steps += check_td_targets(fit, boards, rewards, games, n, head, previous)
                    expected = factual_targets(boards, rewards, games, n, head)
                check_complete_fit(fit, boards, rewards, games, n, inventory, expected)
                head.apply(item['head_version']); previous = item['head_version']
            del head
    return dict(lifecycle=life_id, parent=parent, cells=cells), probes, target_steps


def aggregate(values):
    return dict(games=sum(value['games'] for value in values), wins=sum(value['wins'] for value in values),
        losses=sum(value['losses'] for value in values), cutoffs=sum(value['cutoffs'] for value in values),
        steps=sum(value['steps'] for value in values), mean_game_utility=mean(value['mean_game_utility'] for value in values))


def check_analysis(summary, records):
    equal_tree(summary['by_lifecycle'], records, 'all actual new immutable-bank whole-H2 endpoint cells')
    require(summary['bootstrap_draws'] == 20000 and summary['bootstrap_seed'] == 31400001
        and summary['interval_scope'] == INTERVAL_SCOPE and summary['primary_contrast'] == 'TD_LOCAL_minus_FIRST_LOCAL_FINAL_AB'
        and summary['estimator'] == 'EQUAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',
        'sole new V314 own-FIRST primary and frozen paired conditional interval contract')
    def utility(record, key, arm):
        return record['cells'][key]['arms'][arm]['mean_game_utility']
    for task in TASKS:
        key = 'FIRST_'+task
        check_contrast(summary['cells'][key]['paired_contrasts']['FIRST_LOCAL_minus_SOURCE'],
            [utility(row, key, 'FIRST_LOCAL')-utility(row, key, 'SOURCE') for row in records])
        equal_tree(summary['cells'][key]['arms'], {arm:aggregate([row['cells'][key]['arms'][arm] for row in records])
            for arm in ('SOURCE', 'FIRST_LOCAL')}, 'all initial physical endpoint arm aggregates')
    for round_index in (1, 2):
        for left, right in PAIRS:
            name = left+'_minus_'+right
            check_contrast(summary['round_ab_contrasts'][str(round_index)][name],
                [mean(utility(row, f'ROUND{round_index}_{task}', left)-utility(row, f'ROUND{round_index}_{task}', right)
                    for task in TASKS) for row in records])
            for task in TASKS:
                key = f'ROUND{round_index}_{task}'
                check_contrast(summary['cells'][key]['paired_contrasts'][name],
                    [utility(row, key, left)-utility(row, key, right) for row in records])
        for task in TASKS:
            key = f'ROUND{round_index}_{task}'
            equal_tree(summary['cells'][key]['arms'], {arm:aggregate([row['cells'][key]['arms'][arm] for row in records])
                for arm in ARMS}, 'all actual checkpoint whole-game endpoint aggregates')
            for arm in UPDATING_ARMS:
                check_contrast(summary['checkpoint_contrasts'][key][arm],
                    [utility(row, key, arm)-utility(row, key, 'FIRST_LOCAL') for row in records])
    equal_tree(summary['final_ab_contrasts'], summary['round_ab_contrasts']['2'], 'final endpoint is exactly the second frozen round')
    physical = {arm:[] for arm in ARMS}
    for row in records:
        for task in TASKS:
            for arm in ('SOURCE', 'FIRST_LOCAL'):
                physical[arm].append(row['cells']['FIRST_'+task]['arms'][arm])
            for round_index in (1, 2):
                for arm in UPDATING_ARMS:
                    physical[arm].append(row['cells'][f'ROUND{round_index}_{task}']['arms'][arm])
    equal_tree(summary['arms'], {arm:aggregate(values) for arm,values in physical.items()}, 'each physically executed whole evaluation game is counted once')
    complete = not any(value['cutoffs'] for values in physical.values() for value in values)
    require(summary['complete_game_endpoints'] == complete and not summary['training_cutoffs']
        and summary['initial_context_precondition_met'] and not summary['initial_precondition_failed_lifecycles'],
        'all scientific support retains the full cohort and actual natural terminal availability')
    def status(contrast, retention=False):
        if not complete:
            return 'INCOMPLETE_GAME_ENDPOINTS'
        low, high = contrast['ci95']
        return ('SUPPORTED_NONDECREASE' if retention else 'SUPPORTED_GAIN') if (low >= 0 if retention else low > 0) \
            else 'SUPPORTED_LOSS' if high < 0 else 'UNRESOLVED'
    final = summary['final_ab_contrasts']; primary_status = status(final['TD_LOCAL_minus_FIRST_LOCAL'])
    target_status = status(final['TD_LOCAL_minus_MC_LOCAL']); net_status = status(final['TD_LOCAL_minus_SOURCE'])
    mc_status = status(final['MC_LOCAL_minus_FIRST_LOCAL'])
    task_gain = {task:status(summary['checkpoint_contrasts']['ROUND2_'+task]['TD_LOCAL']) for task in TASKS}
    retention = {task:status(summary['checkpoint_contrasts']['ROUND2_'+task]['TD_LOCAL'], True) for task in TASKS}
    primary, target = primary_status == 'SUPPORTED_GAIN', target_status == 'SUPPORTED_GAIN'
    preserved = all(value == 'SUPPORTED_NONDECREASE' for value in retention.values())
    expected = dict(primary_self_improvement_supported=primary, primary_self_improvement_status=primary_status,
        target_intervention_supported=target, target_intervention_status=target_status,
        final_net_gain_supported=net_status == 'SUPPORTED_GAIN', final_net_gain_status=net_status,
        mc_self_improvement_supported=mc_status == 'SUPPORTED_GAIN', mc_self_improvement_status=mc_status,
        final_task_improvement_supported={task:value == 'SUPPORTED_GAIN' for task,value in task_gain.items()},
        final_task_improvement_status=task_gain, task_retention_status=retention, task_retention_supported=preserved,
        retained_improvement_supported=primary and preserved, target_mechanism_supported=primary and preserved and target,
        checkpoint_status={key:{arm:status(value, True) for arm,value in contrasts.items()}
            for key,contrasts in summary['checkpoint_contrasts'].items()})
    equal_tree({key:summary[key] for key in expected}, expected,
        'own-FIRST gain, separate target intervention, net SOURCE and literal per-task retention support')
    return expected
def check_compute_totals(account, source_compute):
    target_cpu = sum(account[key] for key in ('worker_cpu_seconds', 'compiler_cpu_seconds', 'coordinator_cpu_seconds'))
    require(close(account['new_target_cpu_seconds'], target_cpu)
        and close(account['economic_source_and_target_cpu_seconds'], target_cpu+source_compute['full_source_cpu_seconds']),
        'full audited SOURCE CPU is carried economically once while contained fit bootstrap copy/save CPU is not added again')


def check_accounting(document, inherited):
    account, lives, parents = document['accounting'], document['by_lifecycle'], document['parent_receipts']
    initial = [row for life in lives for row in life['initial'].values()]
    batches = [row['collectors']['FIXED_FIRST'] for life in lives for tasks in life['rounds'].values() for row in tasks.values()]
    updates = {arm:[row['arms'][arm] for life in lives for tasks in life['rounds'].values() for row in tasks.values()]
        for arm in UPDATING_ARMS}
    evaluations = [result['H2'] for row in initial for result in row['evaluations'].values()]
    evaluations += [value['evaluations']['H2'] for values in updates.values() for value in values]
    initial_raw = sum(row['acquisition']['warmup']['raw_tiles']+row['acquisition']['training']['raw_tiles'] for row in initial)
    post_raw = sum(row['acquisition']['training']['raw_tiles'] for row in batches)
    require(len(initial) == 32 and len(batches) == 64 and post_raw == 64*POST_RAW
        and all(row['acquisition']['training']['raw_tiles'] == INITIAL_RAW for row in initial),
        'every initial and physically shared post cohort retains its frozen actual paid raw budget')
    source_raw = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']
    versions = [row['head_versions']['FIRST_LOCAL'] for row in initial]
    versions += [value['head_version'] for values in updates.values() for value in values]
    targets = [value['fit']['target_artifact'] for value in updates['TD_LOCAL']]
    require(len(versions) == len({row['file'] for row in versions}) == 160
        and len(targets) == len({row['file'] for row in targets}) == 64,
        'only actual FIRST and private changed versions and each sole native TD target file are saved')
    expected = dict(inherited_source_costs=inherited, source_physical_training_repeated=False,
        initial_acquisitions=32, post_physical_acquisitions=64, initial_raw_tiles=initial_raw, post_raw_tiles=post_raw,
        new_training_raw_tiles=initial_raw+post_raw,
        economic_training_raw_tiles_per_arm={arm:source_raw+initial_raw+(post_raw if arm in UPDATING_ARMS else 0) for arm in ARMS},
        excluded_tail_raw_tiles=sum(row['dataset']['costs']['excluded_tail_raw_tiles'] for row in initial+batches),
        fit_states_per_updating_arm={arm:sum(value['fit']['trained_afterstates'] for value in values) for arm,values in updates.items()},
        fit_counts_per_updating_arm={arm:sum_counts(value['fit']['learning_counts'] for value in values) for arm,values in updates.items()},
        fit_cpu_seconds_per_updating_arm={arm:sum(value['fit']['cpu_seconds'] for value in values) for arm,values in updates.items()},
        bootstrap_counts=sum_counts(value['fit']['bootstrap_counts'] for value in updates['TD_LOCAL']),
        initial_fit_cpu_seconds=sum(row['first_fits']['FIRST_LOCAL']['cpu_seconds'] for row in initial),
        post_acquisition_cpu_seconds=sum(row['acquisition']['cpu_seconds'] for row in batches),
        new_evaluation_games=sum(len(value['game_summaries']) for value in evaluations),
        evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations),
        evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        version_files=len(versions), version_saved_bytes=sum(row['saved_bytes'] for row in versions),
        version_scanned_parameters=sum(row['scan_parameters'] for row in versions),
        version_copy_parameters=sum(row['copy_parameters'] for row in versions),
        version_save_cpu_seconds=sum(row['save_cpu_seconds'] for row in versions),
        version_copy_cpu_seconds=sum(row['copy_cpu_seconds'] for row in versions),
        target_files=len(targets), target_saved_bytes=sum(row['saved_bytes'] for row in targets),
        target_save_cpu_seconds=sum(row['save_cpu_seconds'] for row in targets),
        private_head_weight_bytes_peak=max(life['private_head_weight_bytes'] for life in lives),
        canonical_trace_bytes=sum(row['trace_bytes'] for row in parents),
        worker_cpu_seconds=sum(row['cpu_seconds'] for row in parents),
        compiler_cpu_seconds=sum(row['compiler_cpu_seconds'] for row in parents), new_compute_closed=True)
    equal_tree({key:account[key] for key in expected}, expected,
        'complete physical shared facts, economic per-arm facts, extra target reads/saves and measured compute closure')
    require(account['new_evaluation_games'] == 6144
        and account['fit_states_per_updating_arm']['MC_LOCAL'] == account['fit_states_per_updating_arm']['TD_LOCAL'],
        'all six H2 checkpoints are new physical games and both updating arms fit the same complete facts')
    check_compute_totals(account, inherited['fresh_source_compute'])
    source = {row['parent']:row for row in document['source_provenance']['parents']}
    require([row['parent'] for row in parents] == list(range(4)) and all(row['status'] == 'COMPLETE' and row['failure'] is None
        and row['paid_raw_tiles'] == sum(item['acquisition']['warmup']['raw_tiles']+item['acquisition']['training']['raw_tiles']
            for life in lives if life['parent'] == row['parent'] for item in life['initial'].values())+16*POST_RAW
        and row['source_setup']['checkpoint_loads'] == 1 and row['source_setup']['new_leaf_updates'] == 0
        and row['source_setup']['inherited_updates'] == source[row['parent']]['updates'] for row in parents),
        'each complete parent worker loads one audited SOURCE without repeated training and retains every raw tile')
    return expected


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    frozen = json_file(directory/'configuration.json')
    require(document['schema'] == 'acfqp.local_targets.v314' and document['status'] == 'EXPERIMENT_COMPLETE'
        and document['scientific_gate'] == 'NOT_A_FORMAL_GATE', 'complete new V314 development experiment terminal schema')
    equal_tree(frozen, expected_configuration(frozen['source_summary']), 'frozen V314 scientific and actual data contract')
    equal_tree(document['settings'], frozen, 'all completed V314 data uses its original frozen contract')
    source_path = Path(frozen['source_summary']); original = json_file(source_path)
    source_audit = require_source_audit(source_path.parent)
    inherited = check_fresh_source_document(original, document['source_provenance'])
    require([row['lifecycle'] for row in document['by_lifecycle']] == list(range(16))
        and all(row['parent'] == row['lifecycle']%4 for row in document['by_lifecycle']),
        'all sixteen new development lives remain under their four audited fixed parents')
    initial, batches, rows_read = read_canonical(document)
    source_rows = {row['parent']:row for row in original['source_provenance']['parents']}
    source_weights = {parent:read_source_weights(row['checkpoint']) for parent,row in source_rows.items()}
    records = []; probes = target_steps = 0
    for life in document['by_lifecycle']:
        record, checked, steps = check_lifecycle(life, initial, batches, source_weights[life['parent']], source_rows[life['parent']]['checkpoint'])
        records.append(record); probes += checked; target_steps += steps
    support = check_analysis(document['summary'], records)
    check_accounting(document, inherited)
    require(probes == 64*16, 'all predeclared first/last probes from every physical fixed-FIRST collector are checked once')
    return dict(status='PASS', independent_valid=True, lifecycles=16, fixed_source_parents=4,
        fresh_source_audit_status=source_audit['status'], fresh_source_provenance_checked=True,
        canonical_rows=rows_read, physical_initial_acquisitions=len(initial), physical_post_acquisitions=len(batches),
        literal_actor_action_probes=probes, reconstructed_head_versions=160,
        immutable_bank_beliefs_valid=True, fixed_first_collector_valid=True,
        every_native_td_target_checked=True, saved_td_fit_rows=target_steps,
        trained_td_targets=document['accounting']['fit_states_per_updating_arm']['TD_LOCAL'],
        identical_factual_states_and_writes_valid=True, new_evaluation_games=6144,
        new_training_raw_tiles=document['accounting']['new_training_raw_tiles'],
        new_target_cpu_seconds=document['accounting']['new_target_cpu_seconds'],
        economic_source_and_target_cpu_seconds=document['accounting']['economic_source_and_target_cpu_seconds'],
        primary_utility=document['summary']['final_ab_contrasts']['TD_LOCAL_minus_FIRST_LOCAL'], **support,
        method='One independent replay of every new initial and fixed-FIRST continuous raw tape with literal seeded cell/rank physics and complete natural labels. Actual sparse v0/v1/v2 lineage reconstruction, all declared first/last candidate H2 action probes, every native saved TD reward/WIN/kind target from its own frozen batch-start head and actual recorded successor, same factual address normalization and writes, paired own-FIRST/target-intervention/net-SOURCE/task-retention endpoints and complete actual cost closure.',
        limitations='Conditional development evidence under four already audited V312 SOURCE parents and inherited deterministic dynamics. Supplied task/round boundaries address observed initial banks. All raw physics and saved TD targets are checked; actor choices are recomputed at the predeclared first/last probes. Complete fits, evaluation actions and bootstrap draws are not rerun. One-step factual targets do not establish the counterfactual H2 optimal operator. Prior SOURCE audit is read without replay; historical dynamics CPU remains unknown.', errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.output)
    except (ValueError, KeyError, FileNotFoundError, IndexError) as error:
        result = dict(status='FAIL', independent_valid=False, errors=[str(error)])
    (args.output/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['independent_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
