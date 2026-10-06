"""Fixed factual B labels and exact cumulative update diagnostics; no inference."""
from math import fsum
from statistics import mean

import numpy as np

ARMS = ('SOURCE', 'MEAN')
SPLITS = ('FIT', 'HELDOUT')
METRICS = ('bias', 'mse', 'mae', 'mean_prediction', 'mean_factual_future_utility')
OUTCOMES = ('WON', 'LOST')


def _positions(n):
    m = min(4, n)
    return [0] if m == 1 else [k*(n-1)//(m-1) for k in range(m)]


def select_indices(dataset, split, goal_rank=11):
    """Four temporal game positions, then four nonwinning steps per game.

    Selection never reads reward, target or eventual terminal outcome. Returned
    indices address the complete original dataset, including the heldout suffix.
    """
    if split not in SPLITS:
        raise ValueError('V299 panels use FIT or HELDOUT complete games')
    ends = np.asarray(dataset['ends'], dtype=np.int64)
    boards = np.asarray(dataset['afterstates'], dtype=np.int32)
    fit = int(dataset['fit_game_count'])
    games = list(range(fit)) if split == 'FIT' else list(range(fit, len(ends)))
    selected = []
    for ordinal in _positions(len(games)):
        game = games[ordinal]
        start, end = int(ends[game-1]) if game else 0, int(ends[game])
        candidates = np.flatnonzero(np.max(boards[start:end], axis=1)<goal_rank)+start
        selected.extend(int(candidates[position]) for position in _positions(len(candidates)))
    return selected


def _game_metrics(rows):
    if not rows:
        return dict(games=0, samples=0, metrics=None)
    return dict(games=len(rows), samples=sum(int(row['count']) for row in rows),
        metrics={key:mean(float(row[key]) for row in rows) for key in METRICS})


def _full_metrics(life):
    grouped = {}
    for split in SPLITS:
        arms, terminal = {}, {}
        for arm in ARMS:
            rows = [row for row in life['final_full'][arm]['game_metrics'] if row['split']==split]
            arms[arm] = _game_metrics(rows)
            terminal[arm] = {status:_game_metrics([row for row in rows if row['status']==status])
                             for status in OUTCOMES}
        grouped[split] = dict(arms=arms, terminal=terminal,
            MEAN_minus_SOURCE={key:arms['MEAN']['metrics'][key]-arms['SOURCE']['metrics'][key]
                               for key in METRICS})
    return grouped


def _panel_deltas(life):
    n = len(life['panel'])
    by_status = {status:[fsum(float(update['delta_predictions'][j])
                    for update in life['updates'] if update['status']==status)
                for j in range(n)] for status in OUTCOMES}
    initial, final = life['snapshots'][0]['predictions'], life['snapshots'][-1]['predictions']
    current = [float(value) for value in initial]
    loss_by_status = {status:[0.]*n for status in OUTCOMES}
    for update in life['updates']:
        for j,delta in enumerate(update['delta_predictions']):
            delta = float(delta)
            error = current[j]-float(life['panel'][j]['target'])
            loss_by_status[update['status']][j] += 2.*error*delta+delta*delta
            current[j] += delta
    observed = [float(final[j])-float(initial[j]) for j in range(n)]
    total = [fsum(by_status[status][j] for status in OUTCOMES) for j in range(n)]
    residual = [observed[j]-total[j] for j in range(n)]
    closed = all(abs(r)<=1e-10*max(1.,abs(o),abs(t))
                 for r,o,t in zip(residual,observed,total))
    observed_loss = [(float(final[j])-float(life['panel'][j]['target']))**2
                     -(float(initial[j])-float(life['panel'][j]['target']))**2 for j in range(n)]
    total_loss = [fsum(loss_by_status[status][j] for status in OUTCOMES) for j in range(n)]
    loss_residual = [observed_loss[j]-total_loss[j] for j in range(n)]
    loss_closed = all(abs(r)<=1e-10*max(1.,abs(o),abs(t))
                     for r,o,t in zip(loss_residual,observed_loss,total_loss))
    panel = [dict(row, source_prediction=float(initial[j]), mean_prediction=float(final[j]),
        observed_prediction_delta=observed[j],
        donor_prediction_deltas={status:by_status[status][j] for status in OUTCOMES},
        accumulated_prediction_delta=total[j], closure_residual=residual[j],
        observed_factual_mse_delta=observed_loss[j],
        donor_factual_mse_deltas={status:loss_by_status[status][j] for status in OUTCOMES},
        factual_loss_closure_residual=loss_residual[j])
        for j,row in enumerate(life['panel'])]
    return dict(panel=panel, closed=closed, loss_closed=loss_closed,
        max_absolute_closure_residual=max(abs(r) for r in residual),
        max_absolute_loss_closure_residual=max(abs(r) for r in loss_residual),
        by_recipient_split={split:dict(
            observed_prediction_delta=mean(row['observed_prediction_delta'] for row in panel if row['split']==split),
            donor_prediction_deltas={status:mean(row['donor_prediction_deltas'][status]
                for row in panel if row['split']==split) for status in OUTCOMES},
            observed_factual_mse_delta=mean(row['observed_factual_mse_delta'] for row in panel if row['split']==split),
            donor_factual_mse_deltas={status:mean(row['donor_factual_mse_deltas'][status]
                for row in panel if row['split']==split) for status in OUTCOMES}) for split in SPLITS})


def _local_metrics(life):
    rows = life['updates']
    increases = [int(row['game']) for row in rows
        if float(row['local_mse_after'])-float(row['local_mse_before'])
        >1e-10*max(1.,abs(float(row['local_mse_before'])),abs(float(row['local_mse_after'])))]
    return dict(games=len(rows), samples=sum(int(row['local_samples']) for row in rows),
        mean_game_mse_before=mean(float(row['local_mse_before']) for row in rows),
        mean_game_mse_after=mean(float(row['local_mse_after']) for row in rows),
        mean_game_mse_delta=mean(float(row['local_mse_after'])-float(row['local_mse_before']) for row in rows),
        increasing_games=increases, all_game_mse_nonincreasing=not increases,
        by_donor_terminal={status:dict(games=sum(row['status']==status for row in rows),
            samples=sum(int(row['local_samples']) for row in rows if row['status']==status))
            for status in OUTCOMES})


def _aggregate_full(rows):
    result = {}
    for split in SPLITS:
        arms = {arm:dict(games=sum(row['final_full'][split]['arms'][arm]['games'] for row in rows),
            samples=sum(row['final_full'][split]['arms'][arm]['samples'] for row in rows),
            metrics={key:mean(row['final_full'][split]['arms'][arm]['metrics'][key] for row in rows)
                     for key in METRICS}) for arm in ARMS}
        terminal = {}
        for status in OUTCOMES:
            present = [row for row in rows if row['final_full'][split]['terminal']['SOURCE'][status]['games']]
            terminal[status] = dict(lifecycles_with_games=[row['lifecycle'] for row in present],
                arms={arm:dict(games=sum(row['final_full'][split]['terminal'][arm][status]['games'] for row in present),
                    samples=sum(row['final_full'][split]['terminal'][arm][status]['samples'] for row in present),
                    metrics={key:mean(row['final_full'][split]['terminal'][arm][status]['metrics'][key]
                                     for row in present) for key in METRICS} if present else None)
                    for arm in ARMS})
            terminal[status]['MEAN_minus_SOURCE'] = {
                key:mean(row['final_full'][split]['terminal']['MEAN'][status]['metrics'][key]
                         -row['final_full'][split]['terminal']['SOURCE'][status]['metrics'][key]
                         for row in present) for key in METRICS} if present else None
        result[split] = dict(arms=arms, terminal=terminal,
            MEAN_minus_SOURCE={key:mean(row['final_full'][split]['MEAN_minus_SOURCE'][key] for row in rows)
                               for key in METRICS},
            mse_increased_lifecycles=[row['lifecycle'] for row in rows
                if row['final_full'][split]['MEAN_minus_SOURCE']['mse']>0.])
    return result


def summarize(lives):
    """Preserve all life signs; game-then-life means describe frozen facts only."""
    rows = [dict(lifecycle=int(life['lifecycle']), parent=int(life['parent']),
        final_full=_full_metrics(life), local_update=_local_metrics(life),
        panel_prediction_deltas=_panel_deltas(life))
        for life in sorted(lives,key=lambda row:row['lifecycle'])]
    return dict(schema='acfqp.b_mechanism_analysis.v299', lifecycles=len(rows),
        by_lifecycle=rows, final_full=_aggregate_full(rows),
        local_update=dict(games=sum(row['local_update']['games'] for row in rows),
            samples=sum(row['local_update']['samples'] for row in rows),
            mean_game_mse_delta=mean(row['local_update']['mean_game_mse_delta'] for row in rows),
            all_game_mse_nonincreasing=all(row['local_update']['all_game_mse_nonincreasing'] for row in rows),
            increasing_games=[dict(lifecycle=row['lifecycle'],game=game) for row in rows
                              for game in row['local_update']['increasing_games']]),
        panel_prediction_delta_closed=all(row['panel_prediction_deltas']['closed'] for row in rows),
        panel_factual_loss_delta_closed=all(row['panel_prediction_deltas']['loss_closed'] for row in rows),
        panel_prediction_deltas={split:dict(
            observed_prediction_delta=mean(row['panel_prediction_deltas']['by_recipient_split'][split]
                                           ['observed_prediction_delta'] for row in rows),
            donor_prediction_deltas={status:mean(row['panel_prediction_deltas']['by_recipient_split'][split]
                ['donor_prediction_deltas'][status] for row in rows) for status in OUTCOMES},
            observed_factual_mse_delta=mean(row['panel_prediction_deltas']['by_recipient_split'][split]
                                           ['observed_factual_mse_delta'] for row in rows),
            donor_factual_mse_deltas={status:mean(row['panel_prediction_deltas']['by_recipient_split'][split]
                ['donor_factual_mse_deltas'][status] for row in rows) for status in OUTCOMES}) for split in SPLITS},
        evidence_scope='Descriptive fixed factual SOURCE B suffix labels; games then lifecycles equally weighted. '
            'Terminal strata use eventual observed outcomes only for diagnosis. No new bootstrap, world '
            'execution, independent policy gain, conditional noise or counterfactual action values are inferred.')
