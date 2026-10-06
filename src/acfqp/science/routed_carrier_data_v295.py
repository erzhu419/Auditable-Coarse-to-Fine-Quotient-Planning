"""Causal observed-module routes on the unchanged V293 carrier game inventory."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from time import process_time

import numpy as np

from . import conditional_carrier_data_v294 as retained

PHASES = retained.PHASES


class _Replay(retained._Replay):
    def __init__(self, expected):
        super().__init__(expected)
        self.module_ids = []
        self.initial_active_module_id = None
        self.warmup_modules = None
        self.routing_timeline = {phase:[] for phase in PHASES}
        self.routing_counts = Counter()

    def train(self, row):
        if self.warmup_modules is None:
            self.warmup_modules = deepcopy(self.memory.modules)
            self.initial_active_module_id = self.memory.module_id
        if not self.in_game:
            self.module_ids = []
        self.module_ids.extend(row['module_id_before'] for spawn in row['raw_spawns']
                               if spawn['kind']=='POST_ACTION')
        before = {phase:len(games) for phase,games in self.games.items()}
        super().train(row)
        self.processing['routed_action_assignments'] += len(row['actions'])
        for event in row['memory_events']:
            self.routing_counts[event['kind']] += 1
            if event['kind'] in ('created', 'reactivated'):
                raw = event['obs_index']-self.warmup.warmup_raw
                phase = PHASES[(raw-1)//retained.RAW_PER_PHASE]
                self.routing_timeline[phase].append(dict(raw_index=raw, kind=event['kind'],
                    previous_module_id=event['previous_module_id'], module_id=event['module_id']))
                self.processing['routing_event_records'] += 1
        pure_phase = None
        for phase,games in self.games.items():
            if len(games)!=before[phase]:
                game,anchors = games[-1]
                if len(self.module_ids)!=len(game['rewards']):
                    raise ValueError('Observed modules must align with every retained factual action')
                game['module_ids'] = np.asarray(self.module_ids, dtype=np.int64)
                for anchor in anchors:
                    anchor['module_id'] = self.module_ids[anchor['step']]
                pure_phase = phase
        if row['completed_games']:
            completion = row['completed_games'][0]
            raw = completion['end_raw']
            phase = PHASES[(raw-1)//retained.RAW_PER_PHASE]
            reason = 'CUTOFF' if completion['status']=='CUTOFF' else 'MIXED_PHASE' if pure_phase is None else None
            self.routing_timeline[phase].append(dict(kind='GAME_COMPLETE', raw_index=raw,
                metadata=dict(completion, phase=pure_phase) if pure_phase is not None else deepcopy(completion),
                pure_phase=pure_phase, exclusion_reason=reason, fit=False))
            self.processing['game_complete_route_records'] += 1

    def finish(self):
        result = super().finish()
        started = process_time()
        fit_episodes = {phase:{game['metadata']['episode'] for game in value['fit_games']}
                        for phase,value in result['phases'].items()}
        for phase,timeline in self.routing_timeline.items():
            for item in timeline:
                if item['kind']=='GAME_COMPLETE':
                    item['fit'] = item['pure_phase'] is not None and item['metadata']['episode'] in fit_episodes[phase]
        result.update(initial_active_module_id=self.initial_active_module_id,
            warmup_modules=self.warmup_modules, warmup_module_ids=[module['id'] for module in self.warmup_modules],
            routing_timeline=self.routing_timeline)
        result['costs'].update(routing_event_inventory=dict(self.routing_counts),
            retained_route_records=sum(len(value) for value in self.routing_timeline.values()),
            routed_retained_actions=sum(len(game['module_ids']) for value in result['phases'].values()
                for split in ('fit_games','heldout_games') for game in value[split]),
            routing_scope='All actual carrier observations, including initial spawns, heldout, mixed games and unfinished tail. '
                'Only natural pure-phase fit-prefix GAME_COMPLETE records carry fit=True.')
        result['costs']['processing_cpu_seconds'] += process_time()-started
        return result


def load_parent(trace_path, expected_lives):
    """Read once; raw_index counts consumed carrier tiles (first spawn is 1).

    Same-index routing is retained before GAME_COMPLETE, because the terminal
    spawn was observed before a complete factual game became available to fit.
    """
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
