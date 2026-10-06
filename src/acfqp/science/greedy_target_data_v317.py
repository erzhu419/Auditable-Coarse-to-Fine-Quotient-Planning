"""Retain factual post-spawn boards inside the same fixed-actor replay loop."""
from collections import Counter, deque
from copy import deepcopy
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .retained_actor_data_v287 import _place, _swipe
from .natural_online_value_v286 import compact_training
from .native_policy_stream_v313 import NativePolicyStream

RAW_BUDGET = 131072
CHUNK_RAW = 256


class FixedPolicyData:
    def __init__(self,life,parent):
        self.life,self.parent=life,parent
        self.memory=SpawnMemory('POOLED')
        self.state=None; self.postspawn_boards=[]; self.afterstates=[]; self.scores=[]; self.ends=[]; self.codes=[]
        self.games=[]; self.memories=[]; self.chunks=0; self.processing=Counter(); self.cpu_seconds=0.

    def consume(self,row):
        started=process_time()
        if self.state is None: self.state=dict(row['start'])
        if self.state!=row['start'] or row['bank_update_counts'] or row['td_examples'] or row['counts']['learning']:
            raise ValueError('Frozen actor stream changed state or received learning updates')
        state=self.state; board=tuple(state['board']); action_index=complete_index=0
        for spawn in row['raw_spawns']:
            if spawn['kind']=='INITIAL':
                if state['status']!='INITIALIZING':
                    if state['status'] not in ('NOT_STARTED','WON','LOST'): raise ValueError('Initial tile reset an active game')
                    state.update(episode=state['episode']+1,step=0,return_score=0,status='INITIALIZING',
                        initial_count=0,game_start_raw=state['raw_tiles'],pending_afterstate=None,pending_bank_id=None)
                    board=(0,)*16
                if state['initial_count']>=2: raise ValueError('More than two initial tiles')
                board=_place(board,spawn); state['initial_count']+=1
                if state['initial_count']==2: state['status']=_status(board,self.processing)
            elif spawn['kind']=='POST_ACTION':
                if state['status']!='ACTIVE': raise ValueError('Actual action outside an active game')
                score=row['scores'][action_index]
                after=_swipe(board,row['actions'][action_index],score,self.processing); action_index+=1
                self.afterstates.append(after); self.scores.append(score)
                board=_place(after,spawn); self.postspawn_boards.append(board)
                self.processing['observed_postspawn_boards']+=1
                self.processing['observed_postspawn_cells']+=16
                state['step']+=1; state['return_score']+=score; state['post_action_spawns']+=1
                won=max(after)>=11
                state['pending_afterstate']=None if won else list(after); state['pending_bank_id']=None if won else 0
                candidate=row['completed_games'][complete_index] if complete_index<len(row['completed_games']) else None
                if won or (candidate is not None and candidate['episode']==state['episode'] and candidate['steps']==state['step']):
                    if candidate is not None and candidate['status']=='CUTOFF': raise ValueError('Natural terminal labels exclude retained actor cutoffs')
                    state['status']=_status(board,self.processing)
                    if state['status'] not in ('WON','LOST'): raise ValueError('Completed game is not physically terminal')
            else: raise ValueError('Unknown raw-spawn kind')
            if spawn['episode']!=state['episode']: raise ValueError('Raw tile episode does not continue the actual stream')
            state['raw_tiles']+=1; state['random_draw_position']+=2; self.memory.observe(spawn['rank'])
            if state['status'] in ('WON','LOST'):
                state['pending_afterstate']=state['pending_bank_id']=None
                actual=dict(episode=state['episode'],stream_seed=state['stream_seed'],start_raw=state['game_start_raw'],
                    end_raw=state['raw_tiles'],steps=state['step'],score=state['return_score'],status=state['status'])
                if actual!=row['completed_games'][complete_index]: raise ValueError('Completed factual game receipt changed')
                self.games.append(actual);self.ends.append(len(self.afterstates));self.codes.append(1 if actual['status']=='WON' else -1)
                self.memories.append(self.memory.to_payload());complete_index+=1
        state['board']=list(board)
        if state['status'] not in ('NOT_STARTED','INITIALIZING') and _status(board,self.processing)!=state['status']:
            raise ValueError('Raw chunk does not end in its reported physical state')
        if action_index!=len(row['actions']) or action_index!=len(row['scores']) or complete_index!=len(row['completed_games']) or state!=row['end']:
            raise ValueError('Actual action, score, completion or stream boundary changed')
        self.chunks+=1;self.cpu_seconds+=process_time()-started

    def finish(self,training):
        started=process_time();n=4*len(self.games)//5
        if not 0<n<len(self.games): raise ValueError('Factual data requires FIT and HELDOUT complete games')
        if self.state!=training['after_stream'] or self.state['raw_tiles']!=training['raw_tiles']:
            raise ValueError('Frozen-policy factual observation budget is incomplete')
        total,fit=self.ends[-1],self.ends[n-1];fit_raw=self.games[n-1]['end_raw'];complete_raw=self.games[-1]['end_raw']
        postspawn=np.asarray(self.postspawn_boards[:total],dtype=np.int32).reshape(-1,16)
        costs=dict(full_A_raw_tiles=training['raw_tiles'],full_A_acquisition_counts=training['counts'],
            warmup_raw_tiles=0,warmup_environment_counts={},warmup_direct_counts={},warmup_memory_counts={},
            fit_raw_tiles=fit_raw,heldout_raw_tiles=complete_raw-fit_raw,fit_steps=fit,heldout_steps=total-fit,
            excluded_tail_games=int(complete_raw<training['raw_tiles']),excluded_tail_steps=len(self.afterstates)-total,
            excluded_tail_raw_tiles=training['raw_tiles']-complete_raw,processing_counts=dict(self.processing),
            processing_memory_counts=dict(self.memory.counts),reconstructed_chunks=self.chunks,
            postspawn_board_array_bytes=int(postspawn.nbytes))
        result=dict(lifecycle=self.life,parent=self.parent,
            afterstates=np.asarray(self.afterstates[:total],dtype=np.int32).reshape(-1,16),
            postspawn_boards=postspawn,
            rewards=np.asarray(self.scores[:total],dtype=np.float64)/2048.,ends=np.asarray(self.ends,dtype=np.int64),
            terminal_codes=np.asarray(self.codes,dtype=np.int32),games=[dict(g,split='FIT' if i<n else 'HELDOUT') for i,g in enumerate(self.games)],
            fit_game_count=n,fit_step_end=fit,fit_end_raw=fit_raw,fit_memory=self.memories[n-1],
            actor_memory_A_end=self.memory.to_payload(),costs=costs)
        self.cpu_seconds+=process_time()-started;costs['processing_cpu_seconds']=self.cpu_seconds
        return result



def acquire_policy_data(leaf, life, parent, arm, model_p_four, environment_p_four,
                        seed, batch_id, emit, runtime, raw_budget=RAW_BUDGET,
                        *, actor_version, task):
    """Keep the actual actor and model law fixed for this paid raw-tile batch."""
    started, cpu_started = perf_counter(), process_time()
    updates = leaf.updates
    engine = NativePolicyStream(leaf, seed, runtime, max_steps=8192)
    data = FixedPolicyData(life, parent)
    first_probes, last_probes = [], deque(maxlen=8)
    tags = dict(lifecycle=life, parent=parent, arm=arm, batch_id=batch_id,
        phase=batch_id, true_p_four=environment_p_four, model_p_four=model_p_four,
        task=task, actor_head_updates=updates, collector_policy_kind=leaf.kind,
        actor_version=deepcopy(actor_version), stream_seed=int(seed))
    try:
        before = engine.state()
        while engine.state()['raw_tiles'] < raw_budget:
            receipt = engine.advance(model_p_four, environment_p_four,
                min(CHUNK_RAW, raw_budget-engine.state()['raw_tiles']))
            for action, record in zip(receipt['actions'], receipt['action_records']):
                probe = dict(episode=record['episode'], step=record['step'],
                    raw_index=receipt['start']['raw_tiles']+record['raw_index'],
                    preboard=record['preboard'], chosen_action=action,
                    h2_value=record['h2_value'], action_values=record['action_values'])
                if len(first_probes) < 8:
                    first_probes.append(probe)
                last_probes.append(probe)
            row = dict(kind='TRAIN', **tags, **compact_training(receipt),
                action_records=[{key:value for key,value in record.items()
                    if key not in ('preboard', 'action_values')} for record in receipt['action_records']],
                representation_counts=receipt['representation_counts'],
                seconds=receipt['seconds'], cpu_seconds=receipt['cpu_seconds'])
            emit(row)
            data.consume(row)
        if leaf.updates != updates:
            raise ValueError('V317 frozen policy actor was fitted during acquisition')
        training = dict(raw_tiles=raw_budget, before_stream=before,
            after_stream=engine.state(), chunks=data.chunks,
            counts={key:dict(value) for key, value in engine.counts.items()},
            representation_counts=dict(engine.representation_counts))
        dataset = data.finish(training)
        costs = dataset['costs']
        costs['full_batch_raw_tiles'] = costs.pop('full_A_raw_tiles')
        costs['full_batch_acquisition_counts'] = costs.pop('full_A_acquisition_counts')
        dataset['batch_id'] = batch_id
        snapshot = dict(stream=engine.state(), memory=data.memory.to_payload())
        reconstruction = dict(counts=dict(data.processing), memory_counts=dict(data.memory.counts),
            cpu_seconds=data.cpu_seconds, chunks=data.chunks)
        emit(dict(kind='ACQUISITION_SNAPSHOT', **tags, snapshot=snapshot,
            training=training, reconstruction=reconstruction,
            policy_probes=dict(first=first_probes, last=list(last_probes))))
        return dict(dataset=dataset, acquisition=dict(batch_id=batch_id,
            actor_version=deepcopy(actor_version), collector_policy_kind=leaf.kind,
            actor_head_updates_before=updates, actor_head_updates_after=leaf.updates,
            policy_probes=dict(first=first_probes, last=list(last_probes)),
            warmup=dict(raw_tiles=0, environment_counts={}, direct_counts={}, memory_counts={}),
            training=training, snapshot=snapshot, reconstruction=reconstruction,
            native_setup_counts=dict(engine.setup_counts), native_setup_seconds=engine.setup_seconds,
            native_setup_cpu_seconds=engine.setup_cpu_seconds,
            compiler_cpu_seconds=engine.compiler_cpu_seconds,
            seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started,
            new_actor_updates=0))
    finally:
        engine.close()
