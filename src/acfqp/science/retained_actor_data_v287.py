"""In-memory reconstruction of retained frozen-actor single-task experience."""
from collections import Counter
import gzip
import json
from time import process_time

import numpy as np

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_memory_v115 import SpawnMemory


def _memory_state(memory):
    payload = memory.to_payload()
    return {key: payload[key] for key in ('observations_seen', 'active_module_id', 'modules', 'pending')}


def _place(board, spawn):
    cell, rank = spawn['cell'], spawn['rank']
    if board[cell] != 0 or rank not in (1, 2):
        raise ValueError('retained spawn must occupy one empty cell with rank one or two')
    placed = list(board)
    placed[cell] = rank
    return tuple(placed)


def _swipe(board, action, expected_score, counts):
    after, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
    counts.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
    if not changed or score != expected_score:
        raise ValueError('retained action legality or score differs from the standard swipe')
    return after


class _Replay:
    def __init__(self, expected, phase='A'):
        self.expected = expected
        self.phase = phase
        self.memory = SpawnMemory('LIBRARY')
        self.state = None
        self.afterstates, self.scores, self.ends, self.codes, self.games = [], [], [], [], []
        self.game_memories = []
        self.warmup_raw = self.chunks = 0
        self.processing = Counter()
        self.acquired = {kind: Counter() for kind in ('environment', 'planning', 'learning')}
        self.cpu_seconds = 0.
        self.snapshot_seen = False

    def warmup(self, row):
        board, action_index = (0,)*16, 0
        initial = 0
        for spawn in row['raw_spawns']:
            if spawn['kind'] == 'INITIAL':
                if action_index or initial >= 2:
                    raise ValueError('warmup initial tiles are missing or misplaced')
                initial += 1
            else:
                if initial != 2:
                    raise ValueError('warmup action precedes its two initial tiles')
                board = _swipe(board, row['actions'][action_index], row['scores'][action_index], self.processing)
                action_index += 1
            board = _place(board, spawn)
            self.memory.observe(spawn['rank'])
        summary = row['summary']
        if (initial != 2 or action_index != len(row['actions']) or action_index != len(row['scores'])
                or action_index != summary['steps'] or sum(row['scores']) != summary['score']
                or list(board) != row['final_board'] or _status(board, self.processing) != summary['status']):
            raise ValueError('warmup sequence differs from its complete retained game')
        self.warmup_raw += len(row['raw_spawns'])
        self.processing['warmup_records'] += 1

    def train(self, row):
        if self.state is None:
            self.state = dict(self.expected['arms']['FROZEN']['phases'][self.phase]['training']['before_stream'])
        if self.state != row['start']:
            raise ValueError('A chunk start does not continue the preceding retained stream')
        if (self.memory.module_id != row['module_id_before']
                or self.memory.predict() != row['model_p_four'] or row['active_bank_id'] != 0):
            raise ValueError('A chunk uses a different observed-prefix actor memory')
        state = self.state
        board, action_index, completed_index, events = tuple(state['board']), 0, 0, []
        completions = row['completed_games']
        for spawn in row['raw_spawns']:
            if spawn['kind'] == 'INITIAL':
                if state['status'] != 'INITIALIZING':
                    if state['status'] not in ('NOT_STARTED', 'WON', 'LOST'):
                        raise ValueError('initial tile cannot reset an active A game')
                    state.update(episode=state['episode']+1, step=0, return_score=0,
                        status='INITIALIZING', initial_count=0, game_start_raw=state['raw_tiles'],
                        pending_afterstate=None, pending_bank_id=None)
                    board = (0,)*16
                if state['initial_count'] >= 2:
                    raise ValueError('retained game has more than two initial tiles')
                board = _place(board, spawn)
                state['initial_count'] += 1
                if state['initial_count'] == 2:
                    state['status'] = _status(board, self.processing)
            elif spawn['kind'] == 'POST_ACTION':
                if state['status'] != 'ACTIVE' or state['initial_count'] != 2:
                    raise ValueError('retained action does not follow an active two-tile initialization')
                if action_index >= len(row['actions']) or action_index >= len(row['scores']):
                    raise ValueError('post-action spawn has no retained action and score')
                score = row['scores'][action_index]
                after = _swipe(board, row['actions'][action_index], score, self.processing)
                self.afterstates.append(after)
                self.scores.append(score)
                action_index += 1
                board = _place(after, spawn)
                state['step'] += 1
                state['return_score'] += score
                state['post_action_spawns'] += 1
                winning = max(after) >= ground.GOAL_RANK
                state['pending_afterstate'] = None if winning else list(after)
                state['pending_bank_id'] = None if winning else 0
                candidate = completions[completed_index] if completed_index < len(completions) else None
                terminal = winning or (candidate is not None and candidate['episode'] == state['episode']
                    and candidate['steps'] == state['step'])
                state['status'] = _status(board, self.processing) if terminal else 'ACTIVE'
                if terminal and state['status'] not in ('WON', 'LOST'):
                    raise ValueError('retained completed A game is not a true terminal game')
            else:
                raise ValueError('retained raw tile has an unknown initial/post-action kind')
            if spawn['episode'] != state['episode']:
                raise ValueError('retained raw tile belongs to a different game')
            state['raw_tiles'] += 1
            state['random_draw_position'] += 2
            event = self.memory.observe(spawn['rank'])
            if event is not None:
                events.append(event)
            if state['status'] in ('WON', 'LOST'):
                state['pending_afterstate'] = state['pending_bank_id'] = None
                actual = dict(episode=state['episode'], stream_seed=state['stream_seed'],
                    start_raw=state['game_start_raw'], end_raw=state['raw_tiles'],
                    steps=state['step'], score=state['return_score'], status=state['status'])
                if completed_index >= len(completions) or actual != completions[completed_index]:
                    raise ValueError('completed A game differs from its retained terminal receipt')
                self.games.append(actual)
                self.ends.append(len(self.afterstates))
                self.codes.append(1 if state['status'] == 'WON' else -1)
                self.game_memories.append(self.memory.to_payload())
                completed_index += 1
        state['board'] = list(board)
        if state['status'] not in ('NOT_STARTED', 'INITIALIZING'):
            if _status(board, self.processing) != state['status']:
                raise ValueError('A chunk terminal status differs from its actual board')
        if (action_index != len(row['actions']) or action_index != len(row['scores'])
                or completed_index != len(completions) or state != row['end']):
            raise ValueError('A chunk end board, score, steps or episode accounting differs')
        if events != row['memory_events']:
            raise ValueError('A chunk memory events differ from the actual raw-rank prefix')
        for kind in self.acquired:
            self.acquired[kind].update(row['counts'][kind])
        self.chunks += 1

    def checkpoint(self, row):
        snapshot = row['snapshot']
        if (self.state != snapshot['stream'] or _memory_state(self.memory) != snapshot['memory']
                or self.memory.predict() != snapshot['estimated_p_four']):
            raise ValueError('A checkpoint does not reproduce the retained actor prefix')
        self.snapshot_seen = True

    def finish(self):
        phase = self.expected['arms']['FROZEN']['phases'][self.phase]
        training, snapshot = phase['training'], phase['snapshot']
        if (not self.snapshot_seen or self.state != training['after_stream']
                or self.state != snapshot['stream'] or self.warmup_raw != self.expected['warmup']['raw_tiles']
                or self.state['raw_tiles'] != training['raw_tiles']):
            raise ValueError('retained single-A observation or snapshot accounting is incomplete')
        if any(dict(counts) != training['counts'][kind] for kind, counts in self.acquired.items()):
            raise ValueError('retained single-A acquired work differs from its source receipt')
        fit_games = 4*len(self.games)//5
        if fit_games == 0 or fit_games == len(self.games):
            raise ValueError('single-A dataset requires both chronological fit and heldout complete games')
        total_steps, fit_steps = self.ends[-1], self.ends[fit_games-1]
        fit_raw, complete_raw = self.games[fit_games-1]['end_raw'], self.games[-1]['end_raw']
        games = [dict(game, split='FIT' if i < fit_games else 'HELDOUT')
                 for i, game in enumerate(self.games)]
        tail_steps = len(self.afterstates)-total_steps
        tail_raw = self.state['raw_tiles']-complete_raw
        costs = dict(warmup_raw_tiles=self.warmup_raw,
            warmup_environment_counts=self.expected['warmup']['environment_counts'],
            warmup_direct_counts=self.expected['warmup']['direct_counts'],
            warmup_memory_counts=self.expected['warmup']['memory_counts'],
            fit_raw_tiles=fit_raw, heldout_raw_tiles=complete_raw-fit_raw,
            fit_steps=fit_steps, heldout_steps=total_steps-fit_steps,
            excluded_tail_games=int(tail_raw > 0), excluded_tail_steps=tail_steps,
            excluded_tail_raw_tiles=tail_raw, processing_counts=dict(self.processing),
            processing_memory_counts=dict(self.memory.counts),
            processing_cpu_seconds=self.cpu_seconds, reconstructed_chunks=self.chunks)
        costs[f'full_{self.phase}_raw_tiles'] = self.state['raw_tiles']
        costs[f'full_{self.phase}_acquisition_counts'] = {
            kind: dict(counts) for kind, counts in self.acquired.items()}
        return dict(lifecycle=self.expected['lifecycle'], parent=self.expected['parent'],
            afterstates=np.asarray(self.afterstates[:total_steps], dtype=np.int32).reshape(-1, 16),
            rewards=np.asarray(self.scores[:total_steps], dtype=np.float64)/2048.,
            ends=np.asarray(self.ends, dtype=np.int64),
            terminal_codes=np.asarray(self.codes, dtype=np.int32), games=games,
            fit_game_count=fit_games, fit_step_end=fit_steps, fit_end_raw=fit_raw,
            fit_memory=self.game_memories[fit_games-1], costs=costs,
            **{f'actor_memory_{self.phase}_end': self.memory.to_payload()})


def load_retained_parent(trace_path, life_ids, expected_lives):
    """Read one V286 parent trace, excluding B/other arms from reconstruction.

    expected_lives maps each requested lifecycle ID to its V286 by_lifecycle
    receipt. Arrays contain every action of complete single-A games, including
    analytic winning afterstates; ends are exclusive cumulative action offsets.
    """
    replays = {life: _Replay(expected_lives[life]) for life in life_ids}
    with gzip.open(trace_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            life = row['lifecycle']
            if life not in replays:
                continue
            replay = replays[life]
            started = process_time()
            if row['kind'] == 'WARMUP':
                replay.warmup(row)
            elif row.get('arm') == 'FROZEN' and row.get('phase') == 'A':
                if row['kind'] == 'TRAIN':
                    replay.train(row)
                elif row['kind'] == 'EVALUATION':
                    replay.checkpoint(row)
            replay.cpu_seconds += process_time()-started
    return {life: replay.finish() for life, replay in replays.items()}
