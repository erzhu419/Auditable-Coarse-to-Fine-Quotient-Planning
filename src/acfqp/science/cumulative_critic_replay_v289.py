"""Chronological V287 MC replay with fixed direct-value anchor snapshots."""
from collections import Counter
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ALPHA
from .native_retained_critic_v287 import fit_retained


def assemble_anchor_panel(dataset, indices, goal=4., failure=4.):
    """Select factual after-current-action MC targets from complete games.

    Complete WON games end at the first winning afterstate. That last step is
    analytic and cannot be selected as a trainable direct-value anchor.
    """
    started, cpu_started = perf_counter(), process_time()
    ends = np.asarray(dataset['ends'], dtype=np.int64)
    indices = np.asarray(indices, dtype=np.int64)
    episodes = np.searchsorted(ends, indices, side='right')
    rows, counts = {}, Counter()
    for episode in np.unique(episodes):
        episode = int(episode)
        start = int(ends[episode - 1]) if episode else 0
        end = int(ends[episode])
        selected = indices[episodes == episode]
        winning = int(dataset['terminal_codes'][episode]) == 1
        if winning and end - 1 in selected:
            raise ValueError('winning afterstates are analytic, not direct-value anchors')
        suffix = float(goal if winning else -failure)
        targets = np.empty(end - start, dtype=np.float64)
        for step in range(end - 1, start - 1, -1):
            targets[step - start] = suffix
            suffix += float(dataset['rewards'][step])
        counts.update(suffix_games=1, suffix_target_assignments=end-start,
                      suffix_reward_additions=end-start)
        counts['target_buffer_doubles_peak'] = max(counts['target_buffer_doubles_peak'], end-start)
        for step in selected:
            step = int(step)
            rows[step] = dict(episode=episode, step=step,
                afterstate=np.asarray(dataset['afterstates'][step], dtype=np.int32).tolist(),
                target=float(targets[step-start]))
    counts['selected_anchors'] = len(indices)
    return dict(rows=[rows[int(step)] for step in indices], counts=dict(counts),
                seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)


def replay_cumulative(leaf, dataset, anchor_indices, build_dir, on_snapshot=None):
    """Fit each original complete game once, preserving every MC update.

    Snapshot prediction is the query-converted direct afterstate leaf. The
    callback reads the current leaf after each snapshot; its planner costs are
    measured separately from fitting and anchor scoring.
    """
    started, cpu_started = perf_counter(), process_time()
    afterstates = np.asarray(dataset['afterstates'], dtype=np.int32)
    rewards = np.asarray(dataset['rewards'], dtype=np.float64)
    ends = np.asarray(dataset['ends'], dtype=np.int64)
    terminal_codes = np.asarray(dataset['terminal_codes'], dtype=np.int32)
    anchor_indices = np.asarray(anchor_indices, dtype=np.int64)
    n_fit = int(dataset['fit_game_count'])
    fit_end = int(dataset['fit_step_end'])
    if (int(ends[n_fit-1]) if n_fit else 0) != fit_end:
        raise ValueError('the fit boundary must end the frozen prefix of complete games')
    learning, targets, setup, scoring = Counter(), Counter(), Counter(), Counter()
    snapshots, first_update, last_update = [], None, None
    initial_updates = leaf.updates
    fit_seconds = fit_cpu_seconds = anchor_seconds = anchor_cpu_seconds = 0.
    callback_seconds = callback_cpu_seconds = 0.
    callback_calls = 0

    def snapshot(completed, steps):
        nonlocal anchor_seconds, anchor_cpu_seconds, callback_seconds, callback_cpu_seconds, callback_calls
        wall, cpu = perf_counter(), process_time()
        before = leaf.model.counts.copy()
        predictions = [float(leaf.model.value(afterstates[index])
                             + leaf.failure_shift + leaf.success_shift)
                       for index in anchor_indices]
        leaf._charge(before)
        n = len(anchor_indices)
        leaf.counts.update(anchor_snapshots=1, anchor_predictions=n,
                           prediction_shift_additions=2*n)
        scoring.update(snapshots=1, value_predictions=n, table_lookups=32*n,
                       prediction_shift_additions=2*n)
        snapshots.append(dict(completed_fit_games=completed,
            cumulative_updates=learning['td_updates'], cumulative_fit_steps=steps,
            predictions=predictions))
        anchor_seconds += perf_counter()-wall
        anchor_cpu_seconds += process_time()-cpu
        if on_snapshot is not None:
            wall, cpu = perf_counter(), process_time()
            on_snapshot(completed, leaf)
            callback_seconds += perf_counter()-wall
            callback_cpu_seconds += process_time()-cpu
            callback_calls += 1

    snapshot(0, 0)
    start = 0
    for game in range(n_fit):
        end = int(ends[game])
        piece = dict(afterstates=afterstates[start:end], rewards=rewards[start:end],
            ends=np.asarray([end-start], dtype=np.int64),
            terminal_codes=terminal_codes[game:game+1], fit_game_count=1,
            fit_step_end=end-start)
        receipt = fit_retained(leaf, piece, 'MC', build_dir, alpha=ALPHA)
        learning.update(receipt['learning_counts'])
        for key, value in receipt['target_counts'].items():
            if key == 'target_buffer_doubles_peak':
                targets[key] = max(targets[key], value)
            else:
                targets[key] += value
        setup.update(receipt['setup_counts'])
        fit_seconds += receipt['seconds']
        fit_cpu_seconds += receipt['cpu_seconds']
        if receipt['first_update'] is not None:
            if first_update is None:
                first_update = dict(receipt['first_update'], episode=game,
                                    step=start+receipt['first_update']['step'])
            last_update = dict(receipt['last_update'], episode=game,
                               step=start+receipt['last_update']['step'])
        snapshot(game+1, end)
        start = end
    return dict(method='MC', alpha=ALPHA, snapshots=snapshots, fitted_games=n_fit,
        fitted_steps=fit_end, trained_afterstates=learning['td_updates'],
        initial_updates=initial_updates, learning_counts=dict(learning),
        target_counts=dict(targets), setup_counts=dict(setup),
        anchor_scoring_counts=dict(scoring), first_update=first_update, last_update=last_update,
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started,
        fit_seconds=fit_seconds, fit_cpu_seconds=fit_cpu_seconds,
        anchor_seconds=anchor_seconds, anchor_cpu_seconds=anchor_cpu_seconds,
        callback_seconds=callback_seconds, callback_cpu_seconds=callback_cpu_seconds,
        callback_calls=callback_calls)
