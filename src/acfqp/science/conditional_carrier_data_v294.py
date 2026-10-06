"""Reconstruct V293 carrier facts and causal whole-game V294 partitions."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from time import process_time

import numpy as np

from acfqp.domains import standard_2048 as ground
from .online_episode_stream_v292 import _GameBuffer
from .retained_actor_data_v287 import _Replay as _WarmupReplay, _memory_state

PHASES = ('A', 'B', 'A_prime')
RAW_PER_PHASE = 65536


class _Replay:
    def __init__(self, expected):
        self.expected = expected
        self.warmup = _WarmupReplay(expected)
        self.memory = self.warmup.memory
        state = expected['carrier']['phases']['A']['training']['before_stream']
        self.buffer = _GameBuffer(state, ground.GOAL_RANK, True)
        self.p_values, self.spawns, self.initial_board = [], [], [0]*16
        self.initial_count, self.in_game = 0, False
        self.games = {phase:[] for phase in PHASES}
        self.exclusions, self.snapshots, self.chunks = [], {}, 0
        self.acquired = {kind:Counter() for kind in ('environment', 'planning', 'learning')}
        self.processing = Counter()
        self.cpu_seconds = 0.

    def train(self, row):
        p = self.memory.predict()
        if p!=row['model_p_four'] or self.memory.module_id!=row['module_id_before']:
            raise ValueError('Carrier p must use only the preceding observed raw prefix')
        if not row['actor_weights_readonly'] or row['leaf_updates_before']!=row['leaf_updates_after']:
            raise ValueError('Retained SOURCE carrier must remain frozen')
        events = []
        for spawn in row['raw_spawns']:
            if spawn['kind']=='INITIAL':
                if not self.in_game:
                    self.initial_board, self.initial_count = [0]*16, 0
                    self.p_values, self.spawns, self.in_game = [], [], True
                self.initial_board[spawn['cell']] = spawn['rank']
                self.initial_count += 1
            else:
                self.p_values.append(p)
                self.spawns.append((spawn['cell'], spawn['rank']))
            event = self.memory.observe(spawn['rank'])
            if event is not None:
                events.append(event)
        if events!=row['memory_events']:
            raise ValueError('Carrier memory events must follow its actual raw ranks')
        terminal = self.buffer.ingest(row)
        for kind in self.acquired:
            self.acquired[kind].update(row['counts'][kind])
        self.chunks += 1
        if terminal is not None:
            completion, data = terminal
            phase = next((name for i,name in enumerate(PHASES)
                if completion['start_raw']>=i*RAW_PER_PHASE
                and completion['end_raw']<=(i+1)*RAW_PER_PHASE), None)
            reason = 'CUTOFF' if completion['status']=='CUTOFF' else 'MIXED_PHASE' if phase is None else None
            if reason is not None:
                self.exclusions.append(dict(completion, reason=reason,
                    raw_tiles=completion['end_raw']-completion['start_raw']))
            else:
                if (data is None or self.initial_count!=2 or len(self.p_values)!=completion['steps']
                        or len(self.spawns)!=completion['steps']):
                    raise ValueError('Pure natural game must retain each afterstate and its before-action p')
                data = dict(afterstates=data['afterstates'], rewards=data['rewards'],
                    model_p_four=np.asarray(self.p_values, dtype=np.float64),
                    terminal_code=1 if completion['status']=='WON' else -1,
                    metadata=dict(completion, phase=phase))
                candidates = []
                for slot,q in enumerate((.25, .5, .75)):
                    step = int((completion['steps']-1)*q)
                    board = list(self.initial_board) if step==0 else data['afterstates'][step-1].tolist()
                    if step:
                        cell,rank = self.spawns[step-1]
                        board[cell] = rank
                    candidates.append(dict(anchor_id=f"L{self.expected['lifecycle']:02d}-{phase}-Q{slot}",
                        lifecycle=self.expected['lifecycle'], parent=self.expected['parent'],
                        phase=phase, phase_index=PHASES.index(phase), anchor_index=slot,
                        episode=completion['episode'], step=step, board_before_action=board,
                        model_p_four=self.p_values[step]))
                self.games[phase].append((data, candidates))
                self.processing['retained_pure_game_steps'] += completion['steps']
            self.in_game = False
        raw = self.buffer.state['raw_tiles']
        if raw and raw%RAW_PER_PHASE==0:
            phase = PHASES[raw//RAW_PER_PHASE-1]
            expected = self.expected['carrier']['phases'][phase]['snapshot']
            if (self.buffer.state!=expected['stream'] or _memory_state(self.memory)!=expected['memory']
                    or self.memory.predict()!=expected['estimated_p_four']):
                raise ValueError('Carrier checkpoint must reproduce its observed prefix')
            self.snapshots[phase] = deepcopy(expected)

    def finish(self):
        started = process_time()
        original = self.expected['carrier']
        if (self.warmup.warmup_raw!=self.expected['warmup']['raw_tiles']
                or self.buffer.state!=original['final_stream'] or len(self.snapshots)!=3
                or self.buffer.state['raw_tiles']!=3*RAW_PER_PHASE):
            raise ValueError('V294 requires the complete retained warmup and carrier acquisition')
        if any(dict(value)!=original['training_counts'][kind] for kind,value in self.acquired.items()):
            raise ValueError('Carrier acquisition work must match its original receipt')
        phases = {}
        for phase in PHASES:
            records = self.games[phase]
            n_fit = 4*len(records)//5
            if not 0<n_fit<len(records):
                raise ValueError('Every phase requires a chronological fit prefix and natural heldout games')
            phases[phase] = dict(fit_games=[game for game,_ in records[:n_fit]],
                heldout_games=[game for game,_ in records[n_fit:]], anchors=records[n_fit][1],
                snapshot=self.snapshots[phase], checkpoint_p_four=self.snapshots[phase]['estimated_p_four'])
        tail = self.buffer.unfinished()
        self.processing.update(self.warmup.processing)
        self.processing.update(self.buffer.counts)
        result = dict(lifecycle=self.expected['lifecycle'], parent=self.expected['parent'], phases=phases,
            final_memory=self.memory.to_payload(), carrier_snapshots=self.snapshots,
            costs=dict(reused_carrier_raw_tiles=self.buffer.state['raw_tiles'],
                carrier_acquisition_counts={kind:dict(value) for kind,value in self.acquired.items()},
                warmup_raw_tiles=self.warmup.warmup_raw,
                warmup_environment_counts=self.expected['warmup']['environment_counts'],
                warmup_direct_counts=self.expected['warmup']['direct_counts'],
                warmup_memory_counts=self.expected['warmup']['memory_counts'],
                excluded_games=self.exclusions, excluded_tail=tail,
                fit_games=sum(len(value['fit_games']) for value in phases.values()),
                heldout_games=sum(len(value['heldout_games']) for value in phases.values()),
                fit_steps=sum(len(game['rewards']) for value in phases.values() for game in value['fit_games']),
                heldout_steps=sum(len(game['rewards']) for value in phases.values() for game in value['heldout_games']),
                reconstructed_chunks=self.chunks, processing_counts=dict(self.processing),
                processing_memory_counts=dict(self.memory.counts),
                processing_cpu_seconds=self.cpu_seconds, new_environment_raw_tiles=0,
                input_scope='V293 shared warmup and SOURCE carrier; validation, deployment and science labels excluded.'))
        result['costs']['processing_cpu_seconds'] += process_time()-started
        return result


def load_parent(trace_path, expected_lives):
    """Read a parent gzip once; include only warmup and actual carrier facts."""
    started = process_time()
    replays = {life:_Replay(expected) for life,expected in expected_lives.items()}
    with gzip.open(trace_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row_started = process_time()
            row = json.loads(line)
            if row['lifecycle'] not in replays:
                continue
            replay = replays[row['lifecycle']]
            replay.processing['trace_rows_read'] += 1
            if row['kind']=='WARMUP':
                replay.warmup.warmup(row)
            elif row['kind']=='CARRIER_TRAIN':
                replay.train(row)
            replay.cpu_seconds += process_time()-row_started
    overhead = process_time()-started-sum(replay.cpu_seconds for replay in replays.values())
    for replay in replays.values():
        replay.cpu_seconds += overhead/len(replays)
    return {life:replay.finish() for life,replay in replays.items()}
