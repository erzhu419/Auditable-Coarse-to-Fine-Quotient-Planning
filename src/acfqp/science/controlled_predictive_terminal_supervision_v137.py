"""Matched one-pass TD and terminal supervision on retained teacher episodes."""
from collections import Counter
from time import perf_counter

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_paired_ntuple_v130 import _delta

SCHEMA = 'acfqp.terminal_supervision.v137'
UPDATE_FIELDS = ('pre_raw_reward', 'pre_reward', 'pre_success', 'target_reward',
    'target_success', 'raw_reward_target', 'reward_error', 'success_error')


def reconstruct_episode(row):
    """Read recorded outcomes without drawing a spawn or choosing an action."""
    if (row['status'] not in ('WON', 'LOST') or row['start_step'] != 0
            or row['pending_before'] is not None or row['pending_after'] is not None):
        raise ValueError('V137 requires a complete terminal episode with no pending boundary')
    n = len(row['actions'])
    if n == 0 or row['end_step'] != n or any(len(row[key]) != n for key in
            ('scores', 'spawned_cells', 'spawned_ranks')):
        raise ValueError('retained episode transition columns differ in length')
    board, afterstates = tuple(row['start_board']), []
    if 'initial_spawns' in row:
        initial = [0]*16
        for spawn in row['initial_spawns']:
            if initial[spawn['cell']] or spawn['rank'] not in (1, 2):
                raise ValueError('retained initial spawn disagrees with its board')
            initial[spawn['cell']] = spawn['rank']
        if len(row['initial_spawns']) != 2 or initial != list(board):
            raise ValueError('retained initial board mismatch')
    work = Counter(replay_swipes=0, replayed_transitions=0, replayed_spawn_events=0,
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0)
    for step, (action, score, cell, rank) in enumerate(zip(row['actions'], row['scores'],
            row['spawned_cells'], row['spawned_ranks'])):
        afterstate, actual_score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
        work['replay_swipes'] += 1
        if not changed or actual_score != score:
            raise ValueError(f'retained action or score mismatch at step {step}')
        if afterstate[cell] != 0 or rank not in (1, 2):
            raise ValueError(f'retained spawn mismatch at step {step}')
        if max(afterstate) >= ground.GOAL_RANK and step != n-1:
            raise ValueError('retained episode continues after its goal')
        afterstates.append(afterstate)
        spawned = list(afterstate); spawned[cell] = rank
        board = tuple(spawned)
        work.update(replayed_transitions=1, replayed_spawn_events=1)
    if list(board) != row['end_board'] or sum(row['scores']) != row['return_score']:
        raise ValueError('retained end board or return score mismatch')
    status_work = Counter()
    actual_status = _status(board, status_work)
    work.update({f'replay_{key}': value for key, value in status_work.items()})
    if actual_status != row['status']:
        raise ValueError('retained terminal status mismatch')
    return afterstates, dict(work)


def _compare_source(predictions, updates, source):
    source_updates = source['joint_updates'][1:]
    if source['terminal_update'] is not None:
        source_updates = source_updates+[source['terminal_update']]
    if (len(source['next_components']) != len(predictions)
            or len(source_updates) != len(updates) or source['joint_updates'][0] is not None):
        raise ValueError('retained TD prediction or update alignment mismatch')
    result = dict(prediction_values_compared=0, prediction_values_matched=0,
        update_values_compared=0, update_values_matched=0, mismatches=0)
    for kind, actual_rows, expected_rows, fields in (
            ('prediction', predictions, source['next_components'], ('reward', 'success')),
            ('update', updates, source_updates, UPDATE_FIELDS)):
        for step, (actual, expected) in enumerate(zip(actual_rows, expected_rows)):
            for index, field in enumerate(fields):
                value = actual[index] if kind == 'prediction' else actual[field]
                result[f'{kind}_values_compared'] += 1
                if value == expected[field]:
                    result[f'{kind}_values_matched'] += 1
                else:
                    result['mismatches'] += 1
                    result.setdefault('first_mismatch', dict(kind=kind, step=step,
                        field=field, actual=value, expected=expected[field]))
    return result


def replay_episode(model, source_row, method):
    """Fit eligible afterstates once, in the original chronological order.

    TD predicts the following chosen afterstate before changing the preceding
    one. TERMINAL instead uses its recorded reward suffix and final outcome.
    Both call the unchanged V136 joint updater with its fixed step size.
    """
    if method not in ('TD', 'TERMINAL'):
        raise ValueError('V137 method must be TD or TERMINAL')
    started, before, updates_before = perf_counter(), model.counts.copy(), model.updates
    afterstates, replay_counts = reconstruct_episode(source_row)
    n, won = len(afterstates), source_row['status'] == 'WON'
    eligible = n-int(won)
    if any(max(board) >= model.radix for board in afterstates[:eligible]):
        raise ValueError('eligible afterstate reaches the learner goal')
    predictions, updates = [], []

    def fit(afterstate, reward, success):
        result = model.update(afterstate, reward, success)
        updates.append({field: result[field] for field in UPDATE_FIELDS})

    if method == 'TD':
        for step, afterstate in enumerate(afterstates):
            prediction = model.value(afterstate)
            predictions.append([prediction['reward'], prediction['success']])
            if step:
                fit(afterstates[step-1], source_row['scores'][step]/2048.+prediction['reward'],
                    prediction['success'])
        if not won:
            fit(afterstates[-1], 0., 0.)
        target_counts = dict(reward_target_additions=n-1,
            terminal_boundary_targets=int(not won), eligible_targets=eligible)
        comparison = _compare_source(predictions, updates, source_row)
    else:
        suffixes, total = [0]*n, 0
        for step in range(n-1, -1, -1):
            suffixes[step] = total
            total += source_row['scores'][step]
        for step in range(eligible):
            fit(afterstates[step], suffixes[step]/2048., float(won))
        target_counts = dict(suffix_score_additions=n, terminal_labels=eligible,
            eligible_targets=eligible)
        comparison = None
    if model.updates-updates_before != eligible:
        raise ValueError('replay did not update each eligible afterstate exactly once')
    return dict(method=method, episode=source_row['episode'], seed=source_row['seed'],
        status=source_row['status'], steps=n, eligible_updates=eligible,
        updates_before=updates_before, updates_after=model.updates,
        model_counts=_delta(model.counts, before), replay_counts=replay_counts,
        target_counts=target_counts, predictions=predictions, updates=updates,
        td_source_comparison=comparison, seconds=perf_counter()-started)
