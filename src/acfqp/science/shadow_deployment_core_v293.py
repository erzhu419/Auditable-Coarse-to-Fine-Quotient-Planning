"""Shared source-carrier learning, paid validation and continuous deployment."""
from collections import Counter
from math import sqrt
import resource
from statistics import mean, stdev
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory, BLOCK
from .natural_model_revision_v281 import MAX_STEPS, delta
from .natural_online_value_v286 import compact_training, memory_state
from .native_episode_consolidation_v290 import fit_consolidated
from .native_value_stream_v286 import NativeValueStream
from .online_episode_stream_v292 import _GameBuffer, _accumulate, _fit_sample, _evaluate

ARMS = ('FROZEN_H2', 'UNCONDITIONAL_H2', 'VALIDATED_H2')
PHASES = (('A', .1), ('B', .5), ('A_prime', .1))
CARRIER_RAW_PER_PHASE = 65536
ONLINE_RAW_PER_PHASE = 262144
VALIDATION_PAIRS = 8
EVALUATION_GAMES = 32
T_CRITICAL_7 = 2.364624251


def carrier_seed(life):
    return 293200010000+life*10000000


def validation_seed(life, phase, pair):
    return 293600010000+life*1000000+phase*100000+pair


def deployment_seed(life, arm_index):
    return 293400010000+life*10000000+arm_index*1000000


def evaluation_seed(life, phase, episode):
    return 293900010000+life*1000000+phase*100000+episode


def select_submission(pairs):
    """The selector receives only eight paired observed returns and statuses."""
    if len(pairs) != VALIDATION_PAIRS:
        raise ValueError('Submission requires all eight complete validation pairs')
    differences = [pair['candidate']['utility']-pair['incumbent']['utility'] for pair in pairs]
    average, std = mean(differences), stdev(differences)
    se = std/sqrt(len(differences))
    lower = average-T_CRITICAL_7*se
    cutoff_pairs = [i for i, pair in enumerate(pairs)
        if any(pair[side]['status'] == 'CUTOFF' for side in ('incumbent', 'candidate'))]
    return dict(pairs=len(pairs), pair_deltas=differences, mean_delta=average,
        sample_std=std, standard_error=se, lower95=lower, t_critical=T_CRITICAL_7,
        no_cutoffs=not cutoff_pairs, cutoff_pairs=cutoff_pairs,
        accept=not cutoff_pairs and lower > 0.)


def _utility(game, leaf):
    bonus = (leaf.target_query['goal_bonus'] if game['status'] == 'WON' else
             -leaf.target_query['failure_penalty'] if game['status'] == 'LOST' else 0.)
    return game['score']/2048.+bonus


def _realized(receipt, leaf):
    return sum(receipt['scores'])/2048.+sum(
        leaf.target_query['goal_bonus'] if game['status'] == 'WON' else
        -leaf.target_query['failure_penalty'] if game['status'] == 'LOST' else 0.
        for game in receipt['completed_games'])


def _unfinished(state):
    active = state['status'] in ('ACTIVE', 'INITIALIZING')
    return dict(episode=state['episode'] if active else None,
        raw_tiles=state['raw_tiles']-state['game_start_raw'] if active else 0,
        steps=state['step'] if active else 0, score=state['return_score'] if active else 0,
        status=state['status'])


def _head_copy(template, origin, runtime, purpose, submission_id, copies, emit, life):
    started, cpu_started = perf_counter(), process_time()
    copied = QueryTD(template.parent, 'PRIOR', runtime)
    np.copyto(copied.weights, origin.weights)
    copied.freeze()
    setup = dict(purpose=purpose, submission_id=submission_id,
        setup_counts=dict(copied.setup_counts, snapshot_parameters_copied=copied.weights.size,
            snapshot_weight_bytes_copied=copied.weights.nbytes),
        setup_seconds=copied.setup_seconds, seconds=perf_counter()-started,
        cpu_seconds=process_time()-cpu_started, private_weight_bytes=copied.weights.nbytes,
        copied_from_value_updates=origin.updates)
    copies.append(setup)
    emit(dict(kind='HEAD_COPY', lifecycle=life, **setup))
    return copied, setup


def _validation_game(template, head, p, env_p, seed, runtime, emit, life, arm, phase,
                     pair_index, branch, submission_id):
    started, cpu_started = perf_counter(), process_time()
    engine = NativeValueStream(template, seed, runtime, max_steps=MAX_STEPS)
    try:
        game = None
        while game is None:
            state, updates = engine.state(), head.updates
            receipt = engine.advance(head, 0, head if state['pending_bank_id'] is not None else None,
                p, env_p, tile_budget=BLOCK, max_postaction=BLOCK, depth=2, stop_on_game_end=True)
            emit(dict(kind='VALIDATION_TRAIN', lifecycle=life, arm=arm, phase=phase,
                pair_index=pair_index, branch=branch, seed=seed, submission_id=submission_id,
                model_p_four=p, actor_weights_readonly=not head.weights.flags.writeable,
                leaf_updates_before=updates, leaf_updates_after=head.updates,
                **compact_training(receipt)))
            if receipt['updates'] or head.updates != updates or head.weights.flags.writeable:
                raise ValueError('Validation must not update a value head')
            completed = receipt['completed_games']
            if len(completed) > 1:
                raise ValueError('Validation must pause at its first complete game')
            if completed:
                game = dict(completed[0], seed=seed, utility=_utility(completed[0], head),
                            raw_tiles=engine.state()['raw_tiles'])
        result = dict(game_summary=game, counts={kind: dict(value) for kind, value in engine.counts.items()},
            native_setup_counts=dict(engine.setup_counts), native_setup_seconds=engine.setup_seconds,
            seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)
        emit(dict(kind='VALIDATION_GAME', lifecycle=life, arm=arm, phase=phase,
            pair_index=pair_index, branch=branch, submission_id=submission_id,
            model_p_four=p, **result))
        return result
    finally:
        engine.close()


def _sum_counts(rows, key):
    return {kind: dict(sum((Counter(row[key][kind]) for row in rows), Counter()))
            for kind in ('environment', 'planning', 'learning')}


def run_lifecycle(template, warmed, life, emit, runtime):
    """Run all three fixed arms with one shared, submission-independent shadow."""
    if template.weights.flags.writeable:
        raise ValueError('The shared source actor must be frozen')
    started, cpu_started = perf_counter(), process_time()
    child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    memory = SpawnMemory.from_payload(warmed.to_payload())
    shadow = QueryTD(template.parent, 'PRIOR', runtime)
    shadow_setup = dict(setup_counts=dict(shadow.setup_counts), setup_seconds=shadow.setup_seconds,
                        private_weight_bytes=shadow.weights.nbytes)
    totals = dict(fitted_games=0, fitted_steps=0, trained_afterstates=0, learning_counts={},
                  target_counts={}, consolidation_counts={}, setup_counts={}, seconds=0., cpu_seconds=0.)
    carrier = NativeValueStream(template, carrier_seed(life), runtime, max_steps=MAX_STEPS)
    carrier_buffer = _GameBuffer(carrier.state(), template.radix, True)
    deployments = {}
    incumbents = {arm: template for arm in ARMS}
    incumbent_ids = dict.fromkeys(ARMS, 0)
    arms = {arm: dict(phases={}) for arm in ARMS}
    carrier_phases, copies, a_heads = {}, [], {}
    saved_A_p = None
    current_counts = {arm: {kind: Counter() for kind in ('environment', 'planning')} for arm in ARMS}
    retention_counts = {arm: {kind: Counter() for kind in ('environment', 'planning')} for arm in ARMS}
    a_head_counts = {arm: {kind: Counter() for kind in ('environment', 'planning')} for arm in ARMS}
    try:
        for index, arm in enumerate(ARMS):
            deployments[arm] = NativeValueStream(template, deployment_seed(life, index), runtime, max_steps=MAX_STEPS)
        for phase_index, (phase, env_p) in enumerate(PHASES):
            before_carrier = {kind: dict(value) for kind, value in carrier.counts.items()}
            before_memory, before_state = dict(memory.counts), carrier.state()
            before_fit = dict(totals['learning_counts'])
            before_cutoffs = carrier_buffer.cutoffs
            source_utility, chunks, memory_events = 0., 0, 0
            quota = (phase_index+1)*CARRIER_RAW_PER_PHASE
            while carrier.state()['raw_tiles'] < quota:
                state = carrier.state()
                remaining = min(quota-state['raw_tiles'], BLOCK-memory.pending_n)
                p, module = memory.predict(), memory.module_id
                source_updates = template.updates
                receipt = carrier.advance(template, 0,
                    template if state['pending_bank_id'] is not None else None, p, env_p,
                    tile_budget=remaining, max_postaction=BLOCK, depth=2, stop_on_game_end=True)
                events = []
                for spawn in receipt['raw_spawns']:
                    event = memory.observe(spawn['rank'])
                    if event is not None:
                        events.append(event)
                memory_events += len(events)
                source_utility += _realized(receipt, template)
                emit(dict(kind='CARRIER_TRAIN', lifecycle=life, phase=phase, model_p_four=p,
                    module_id_before=module, memory_events=events,
                    actor_weights_readonly=not template.weights.flags.writeable,
                    leaf_updates_before=source_updates, leaf_updates_after=template.updates,
                    **compact_training(receipt)))
                if receipt['updates'] or template.updates != source_updates:
                    raise ValueError('The shared carrier actor received a value update')
                terminal = carrier_buffer.ingest(receipt)
                chunks += 1
                if terminal is not None:
                    game, data = terminal
                    old_updates = shadow.updates
                    if data is not None:
                        fit = fit_consolidated(shadow, data, 'EPISODE_MEAN_MC', runtime, alpha=.0025)
                        for key in ('fitted_games', 'fitted_steps', 'trained_afterstates', 'seconds', 'cpu_seconds'):
                            totals[key] += fit[key]
                        for key in ('learning_counts', 'target_counts', 'consolidation_counts', 'setup_counts'):
                            _accumulate(totals[key], fit[key])
                        fit = dict(fit, first_sample=_fit_sample(fit['first_sample'], game),
                                   last_sample=_fit_sample(fit['last_sample'], game))
                    else:
                        fit = dict(method='SKIPPED_CUTOFF', trained_afterstates=0, learning_counts={},
                            target_counts={}, consolidation_counts={}, first_sample=None, last_sample=None)
                    emit(dict(kind='SHADOW_FIT', lifecycle=life, phase=phase, completion=game,
                        fitted=data is not None, old_value_updates=old_updates,
                        new_value_updates=shadow.updates, fit=fit))
                    del data
            p = memory.predict()
            carrier_training = dict(raw_tiles=CARRIER_RAW_PER_PHASE, chunks=chunks,
                before_stream=before_state, after_stream=carrier.state(),
                memory_counts=delta(memory.counts, before_memory), memory_event_count=memory_events,
                counts={kind: delta(value, before_carrier[kind]) for kind, value in carrier.counts.items()},
                shadow_learning_counts=delta(totals['learning_counts'], before_fit),
                cutoff_games=carrier_buffer.cutoffs-before_cutoffs)
            carrier_snapshot = dict(estimated_p_four=p, memory=memory_state(memory), stream=carrier.state(),
                shadow_value_updates=shadow.updates, unfinished_game=carrier_buffer.unfinished())
            carrier_phases[phase] = dict(training=carrier_training, snapshot=carrier_snapshot,
                realized_utility=source_utility, raw_tiles=CARRIER_RAW_PER_PHASE,
                cutoff_games=carrier_training['cutoff_games'])
            proposal_id = phase_index+1
            proposal, proposal_setup = _head_copy(template, shadow, runtime, 'CANDIDATE',
                                                 proposal_id, copies, emit, life)
            for arm in ARMS:
                incumbent, old_id = incumbents[arm], incumbent_ids[arm]
                validation, pair_rows = [], []
                candidate = template if arm == 'FROZEN_H2' else proposal
                candidate_id = 0 if arm == 'FROZEN_H2' else proposal_id
                for pair_index in range(VALIDATION_PAIRS):
                    seed = validation_seed(life, phase_index, pair_index)
                    pair = dict(pair_index=pair_index, seed=seed,
                                incumbent_submission_id=old_id, candidate_submission_id=candidate_id)
                    for branch, head, head_id in (('incumbent', incumbent, old_id),
                                                  ('candidate', candidate, candidate_id)):
                        result = _validation_game(template, head, p, env_p, seed, runtime, emit,
                            life, arm, phase, pair_index, branch, head_id)
                        validation.append(result)
                        pair[branch] = result['game_summary']
                    pair_rows.append(pair)
                gate = select_submission(pair_rows)
                accept = arm == 'UNCONDITIONAL_H2' or (arm == 'VALIDATED_H2' and gate['accept'])
                if accept:
                    incumbents[arm], incumbent_ids[arm] = proposal, proposal_id
                submission = dict(candidate_submission_id=candidate_id, previous_submission_id=old_id,
                    deployed_submission_id=incumbent_ids[arm], accepted=accept,
                    rule='ALWAYS' if arm == 'UNCONDITIONAL_H2' else
                         'PAIRED_T_LOWER95_POSITIVE_NO_CUTOFF' if arm == 'VALIDATED_H2' else 'FROZEN_SOURCE',
                    gate=gate, shadow_value_updates=shadow.updates)
                emit(dict(kind='SUBMISSION', lifecycle=life, arm=arm, phase=phase, **submission))
                validation_raw = sum(result['game_summary']['raw_tiles'] for result in validation)
                validation_summary = dict(pairs=pair_rows, game_summaries=[result['game_summary'] for result in validation],
                    raw_tiles=validation_raw, counts=_sum_counts(validation, 'counts'),
                    cutoff_games=sum(result['game_summary']['status'] == 'CUTOFF' for result in validation),
                    realized_utility=sum(result['game_summary']['utility'] for result in validation),
                    native_setup_counts=dict(sum((Counter(result['native_setup_counts']) for result in validation), Counter())),
                    native_setup_seconds=sum(result['native_setup_seconds'] for result in validation),
                    seconds=sum(result['seconds'] for result in validation),
                    cpu_seconds=sum(result['cpu_seconds'] for result in validation))
                remaining = ONLINE_RAW_PER_PHASE-CARRIER_RAW_PER_PHASE-validation_raw
                if remaining < 0:
                    raise ValueError('Complete paired validation exceeded the frozen online quota')
                engine, head = deployments[arm], incumbents[arm]
                before_deploy, deploy_start = {kind: dict(value) for kind, value in engine.counts.items()}, engine.state()
                deployment_goal, deployed_utility, completed = deploy_start['raw_tiles']+remaining, 0., []
                deploy_started, deploy_cpu = perf_counter(), process_time()
                while engine.state()['raw_tiles'] < deployment_goal:
                    state, updates = engine.state(), head.updates
                    receipt = engine.advance(head, 0, head if state['pending_bank_id'] is not None else None,
                        p, env_p, tile_budget=min(BLOCK, deployment_goal-state['raw_tiles']),
                        max_postaction=BLOCK, depth=2, stop_on_game_end=True)
                    emit(dict(kind='DEPLOYMENT_TRAIN', lifecycle=life, arm=arm, phase=phase,
                        submission_id=incumbent_ids[arm], model_p_four=p,
                        actor_weights_readonly=not head.weights.flags.writeable,
                        leaf_updates_before=updates, leaf_updates_after=head.updates,
                        **compact_training(receipt)))
                    if receipt['updates'] or head.updates != updates or head.weights.flags.writeable:
                        raise ValueError('Deployment must not train value heads')
                    deployed_utility += _realized(receipt, head)
                    for completion in receipt['completed_games']:
                        game = dict(completion, utility=_utility(completion, head))
                        completed.append(game)
                        emit(dict(kind='DEPLOYMENT_GAME', lifecycle=life, arm=arm, phase=phase,
                                  submission_id=incumbent_ids[arm], game_summary=game))
                deployment = dict(raw_tiles=remaining, realized_utility=deployed_utility,
                    cutoff_games=sum(game['status'] == 'CUTOFF' for game in completed),
                    completed_game_summaries=completed, before_stream=deploy_start, after_stream=engine.state(),
                    unfinished_game=_unfinished(engine.state()),
                    counts={kind: delta(value, before_deploy[kind]) for kind, value in engine.counts.items()},
                    seconds=perf_counter()-deploy_started, cpu_seconds=process_time()-deploy_cpu)
                science_seeds = [evaluation_seed(life, phase_index, episode) for episode in range(EVALUATION_GAMES)]
                evaluated = _evaluate(carrier, head, p, env_p, science_seeds, 2)
                for kind, value in evaluated['counts'].items():
                    current_counts[arm][kind].update(value)
                if phase_index == 0:
                    saved_A_p = p
                    retention = dict(evaluated, shared_with_current=True,
                        counts={kind: {} for kind in current_counts[arm]}, seconds=0., cpu_seconds=0.)
                    a_heads[arm], a_setup = _head_copy(template, head, runtime,
                        'RETAINED_A_'+arm, incumbent_ids[arm], copies, emit, life)
                    arms[arm]['retained_A_head_setup'] = a_setup
                else:
                    a_seeds = [evaluation_seed(life, 0, episode) for episode in range(EVALUATION_GAMES)]
                    retention = dict(_evaluate(carrier, head, saved_A_p, .1, a_seeds, 2), shared_with_current=False)
                    for kind, value in retention['counts'].items():
                        retention_counts[arm][kind].update(value)
                phase_result = dict(submission=submission, validation=validation_summary, deployment=deployment,
                    online_raw_tiles=CARRIER_RAW_PER_PHASE+validation_raw+remaining,
                    online_realized_utility=source_utility+validation_summary['realized_utility']+deployed_utility,
                    game_summaries=evaluated['game_summaries'],
                    snapshot=dict(estimated_p_four=p, carrier_memory=memory_state(memory),
                        deployed_submission_id=incumbent_ids[arm], carrier_stream=carrier.state(),
                        deployment_stream=engine.state(), candidate_shadow_value_updates=shadow.updates),
                    evaluation_counts=evaluated['counts'], evaluation_seconds=evaluated['seconds'],
                    evaluation_cpu_seconds=evaluated['cpu_seconds'], retention_probe=retention)
                if phase_index == 1:
                    phase_result['a_head_on_B'] = _evaluate(carrier, a_heads.pop(arm), p, env_p, science_seeds, 2)
                    for kind, value in phase_result['a_head_on_B']['counts'].items():
                        a_head_counts[arm][kind].update(value)
                arms[arm]['phases'][phase] = phase_result
                emit(dict(kind='CHECKPOINT', lifecycle=life, arm=arm, phase=phase, **phase_result))
        for arm in ARMS:
            arms[arm].update(final_stream=deployments[arm].state(),
                final_unfitted_game=_unfinished(deployments[arm].state()),
                deployment_counts={kind: dict(value) for kind, value in deployments[arm].counts.items()},
                deployment_native_setup_counts=dict(deployments[arm].setup_counts),
                deployment_native_setup_seconds=deployments[arm].setup_seconds,
                cutoff_games=sum(phase['deployment']['cutoff_games'] for phase in arms[arm]['phases'].values()),
                evaluation_counts={kind: dict(value) for kind, value in current_counts[arm].items()},
                retention_evaluation_counts={kind: dict(value) for kind, value in retention_counts[arm].items()},
                a_head_on_B_evaluation_counts={kind: dict(value) for kind, value in a_head_counts[arm].items()})
        child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        return dict(lifecycle=life, parent=life%4, carrier=dict(phases=carrier_phases,
            training_counts={kind: dict(value) for kind, value in carrier.counts.items()},
            final_memory=memory.to_payload(), final_stream=carrier.state(),
            final_unfitted_game=carrier_buffer.unfinished(), cutoff_games=carrier_buffer.cutoffs,
            reconstruction_counts=dict(carrier_buffer.counts), reconstruction_cpu_seconds=carrier_buffer.cpu_seconds,
            retained_afterstate_steps_peak=carrier_buffer.peak_steps,
            native_setup_counts=dict(carrier.setup_counts), native_setup_seconds=carrier.setup_seconds),
            shadow=dict(fit_totals=totals, new_value_updates=shadow.updates, head_setup=shadow_setup),
            arms=arms, head_copies=copies,
            costs=dict(cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
                compiler_cpu_seconds=child_after.ru_utime+child_after.ru_stime-child_before.ru_utime-child_before.ru_stime))
    finally:
        carrier.close()
        for engine in deployments.values():
            engine.close()
