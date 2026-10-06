"""Complete factual games collected by each frozen current policy batch."""
from collections import deque
from copy import deepcopy
from time import perf_counter, process_time

from .natural_online_value_v286 import compact_training
from .native_policy_stream_v313 import NativePolicyStream
from .policy_actor_data_v306 import FixedPolicyData

RAW_BUDGET = 131072
CHUNK_RAW = 256


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
            raise ValueError('V313 frozen policy actor was fitted during acquisition')
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
