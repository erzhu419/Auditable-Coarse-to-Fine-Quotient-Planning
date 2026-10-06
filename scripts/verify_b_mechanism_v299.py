"""Independent arithmetic checks for the frozen V298 B replay; no new world."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from math import ceil
from math import isclose, isfinite
from pathlib import Path
from statistics import mean
from time import process_time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(left, right):
    return isfinite(float(left)) and isfinite(float(right)) and isclose(
        float(left), float(right), rel_tol=1e-10, abs_tol=1e-9)


def check_episode_identity(ordinal, status, samples, canonical_game):
    """The replay cannot relabel a donor outcome or change sample membership."""
    require(ordinal >= 0 and status == canonical_game['status']
        and status in ('WON', 'LOST'), 'retained natural donor outcome')
    require(samples == canonical_game['steps'] - (status == 'WON'),
        'same complete-game nonwinning training samples')


def check_mc_target(raw_scores, status, local_step, target):
    """Afterstate MC labels exclude the reward of the action just taken."""
    require(status in ('WON', 'LOST') and 0 <= local_step < len(raw_scores),
        'retained natural MC target membership')
    expected = (4. if status == 'WON' else -4.) + sum(
        raw_scores[local_step+1:]) / 2048.
    require(close(target, expected), 'original factual MC suffix target')
    return expected


def check_loss_descent(before_mse, after_mse):
    """The emitted local game residual loss must actually decrease."""
    require(isfinite(before_mse) and isfinite(after_mse)
        and before_mse >= 0 and after_mse >= 0, 'finite local residual loss')
    require(after_mse <= before_mse or close(after_mse, before_mse),
        'game mean MC update increased its own factual residual loss')


def check_panel_delta(before, after, saved_delta):
    require(len(before) == len(after) == len(saved_delta),
        'fixed panel prediction/delta inventory')
    require(all(close(delta, right-left)
        for left, right, delta in zip(before, after, saved_delta)),
        'game donor prediction delta arithmetic')


def check_telescoping(source, final, donor_deltas):
    """Sum donor effects from both statuses without omitting negative changes."""
    require(len(source) == len(final), 'fixed panel initial/final inventory')
    totals = {'WON': [0.]*len(source), 'LOST': [0.]*len(source)}
    for status, values in donor_deltas:
        require(status in totals and len(values) == len(source),
            'complete signed donor status/panel inventory')
        for index, value in enumerate(values):
            require(isfinite(value), 'finite signed donor effect')
            totals[status][index] += value
    require(all(close(right-left, totals['WON'][index]+totals['LOST'][index])
        for index, (left, right) in enumerate(zip(source, final))),
        'all-game signed WON/LOST prediction closure')
    return totals


def check_margin(values, selected, saved_margin):
    """Action order uses the root's legal values and its documented tie order."""
    require(values and selected in values, 'legal root action inventory')
    best = min(values, key=lambda action: (-values[action], action))
    require(selected == best, 'root argmax and lexical tie order')
    if len(values) == 1:
        require(saved_margin is None, 'one-action root has no runner-up margin')
    else:
        second = max(value for action, value in values.items() if action != best)
        require(close(saved_margin, values[best]-second), 'legal root runner-up margin')


def check_loss_delta_closure(targets, source, final, donor_deltas,
                             saved_loss_change):
    """The donor split must explain the final factual panel SSE change."""
    require(len(targets) == len(source) == len(final), 'fixed factual loss panel')
    check_telescoping(source, final, donor_deltas)
    change = sum((right-target)**2-(left-target)**2
        for target, left, right in zip(targets, source, final))
    require(close(change, saved_loss_change), 'factual panel loss change arithmetic')
    return change


def check_zero_new_world(new_raw, new_games, old_raw, retained_raw):
    require(new_raw == new_games == 0, 'offline diagnostic generated a new world')
    require(old_raw == retained_raw, 'retained B acquisition cost omitted or repaid')


def expected_panel_indices(games, fit_game_count):
    """Uniform temporal positions from receipts alone, without reading labels."""
    def positions(n):
        m = min(4, n)
        return [0] if m == 1 else [k*(n-1)//(m-1) for k in range(m)]
    starts, offset = [], 0
    for game in games:
        starts.append(offset)
        offset += game['steps']
    selected = []
    for ordinals in (list(range(fit_game_count)),
                     list(range(fit_game_count, len(games)))):
        for position in positions(len(ordinals)):
            ordinal = ordinals[position]
            game = games[ordinal]
            n = game['steps']-(game['status'] == 'WON')
            selected.extend(starts[ordinal]+step for step in positions(n))
    return selected


def check_h2_decomposition(source, current, fixed):
    require(source and set(source) == set(current) == set(fixed),
        'same legal root actions across H2 readouts')
    effects = {}
    for action in source:
        require(all(isfinite(value) for value in
            (source[action], current[action], fixed[action])), 'finite legal H2 values')
        leaf = fixed[action]-source[action]
        remax = current[action]-fixed[action]
        require(remax >= 0 or close(current[action], fixed[action]),
            'reselected second action is below the frozen SOURCE second action')
        effects[action] = dict(leaf=leaf, remax=remax,
                              total=current[action]-source[action])
        require(close(effects[action]['total'], leaf+remax),
            'H2 value change decomposition')
    return effects


def read_scores(receipt):
    """Read only the original factual score sequences, not weights or worlds."""
    scores = {life:defaultdict(list) for life in receipt['lifecycle_ids']}
    rows = 0
    with gzip.open(receipt['trace_file'], 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            rows += 1
            require(row['phase'] == 'B' and row['true_p_four'] == .5,
                'retained input remains the original B task')
            if row['kind'] == 'TRAIN':
                action_scores = iter(row['scores'])
                for spawn in row['raw_spawns']:
                    if spawn['kind'] == 'POST_ACTION':
                        scores[row['lifecycle']][spawn['episode']].append(next(action_scores))
                require(next(action_scores, None) is None,
                    'factual retained action/score membership')
    return scores, rows


def check_full_score(result, games, score_sequences, original_heldout):
    rows = result['game_metrics']
    require(len(rows) == len(games), 'complete FIT and HELDOUT game inventory')
    start = 0
    for ordinal, (row, game) in enumerate(zip(rows, games)):
        count = game['steps']-(game['status'] == 'WON')
        require(row['episode'] == ordinal and row['start'] == start
            and row['end'] == start+game['steps'] and row['count'] == count
            and row['split'] == game['split'] and row['status'] == game['status'],
            'complete factual scoring boundaries')
        scores = score_sequences[game['episode']]
        require(len(scores) == game['steps'] and sum(scores) == game['score'],
            'original complete factual rewards')
        target = (4. if game['status'] == 'WON' else -4.) + sum(
            index*score for index, score in enumerate(scores))/(2048.*count)
        require(close(row['mean_factual_future_utility'], target),
            'full-game future suffix mean excludes the immediate reward')
        require(close(row['bias'], row['mean_prediction']-target),
            'full-game factual prediction bias arithmetic')
        start += game['steps']
    heldout = [{key:value for key,value in row.items() if key not in ('split','status')}
        for row in rows if row['split'] == 'HELDOUT']
    require(heldout == original_heldout, 'original V298 complete heldout reproduction')
    for metric in ('bias','mse','mae'):
        require(close(result['metrics'][metric], mean(row[metric] for row in rows)),
            'complete score game mean '+metric)


def check_life(life, old, score_sequences):
    games, fit = old['dataset']['games'], old['dataset']['fit_game_count']
    require(life['lifecycle'] == old['lifecycle'] and life['parent'] == old['parent'],
        'retained lifecycle/source identity')
    for key in ('games','fit_game_count','fit_step_end','fit_end_raw','fit_memory'):
        require(life['dataset'][key] == old['dataset'][key],
            'original B chronological dataset '+key)
    require(life['estimated_p_four'] == old['evaluation_snapshot']['estimated_p_four'],
        'unchanged fit-prefix observed H2 belief')
    panel = life['panel']
    require([row['step'] for row in panel] == expected_panel_indices(games, fit),
        'outcome-blind temporal panel roster')
    starts, offset = [], 0
    for game in games:
        starts.append(offset)
        offset += game['steps']
    for row in panel:
        ordinal = row['episode']
        game = games[ordinal]
        require(row['status'] == game['status'] and row['split'] == game['split']
            and starts[ordinal] <= row['step'] < starts[ordinal]+game['steps']
            and max(row['afterstate']) < 11, 'original nonwinning panel membership')
        check_mc_target(score_sequences[game['episode']], game['status'],
            row['step']-starts[ordinal], row['target'])
    require(len(life['snapshots']) == fit+1 and len(life['updates']) == fit,
        'zero prefix and every complete fitting game retained')
    initial = life['snapshots'][0]['predictions']
    before, donors, loss_change = initial, [], 0.
    learned = Counter()
    for ordinal, update in enumerate(life['updates']):
        require(update['game'] == ordinal, 'original chronological donor order')
        check_episode_identity(ordinal, update['status'], update['local_samples'], games[ordinal])
        check_loss_descent(update['local_mse_before'], update['local_mse_after'])
        after = update['predictions_after']
        check_panel_delta(before, after, update['delta_predictions'])
        donors.append((update['status'], update['delta_predictions']))
        loss_change += sum(2*(prediction-row['target'])*delta+delta*delta
            for row, prediction, delta in zip(panel, before, update['delta_predictions']))
        counts = update['learning_counts']
        require(counts['td_updates'] == counts['value_predictions'] == update['local_samples']
            and counts['table_lookups'] == counts['table_update_occurrences'] == 32*update['local_samples'],
            'per-game actual sample and feature work')
        learned.update(counts)
        before = after
    for ordinal, snapshot in enumerate(life['snapshots']):
        require(snapshot['completed_fit_games'] == ordinal
            and (ordinal == 0 or snapshot['predictions'] == life['updates'][ordinal-1]['predictions_after']),
            'complete chronological prediction snapshots')
        for split in ('FIT','HELDOUT'):
            errors = [prediction-row['target'] for row,prediction in zip(panel,snapshot['predictions'])
                if row['split'] == split]
            for metric, values in (('bias',errors),('mse',[v*v for v in errors]),
                                   ('mae',[abs(v) for v in errors])):
                require(close(snapshot['metrics'][split][metric], mean(values)),
                    'fixed panel snapshot arithmetic '+metric)
    check_loss_delta_closure([row['target'] for row in panel], initial, before,
        donors, loss_change)
    original = old['arms']['EPISODE_MEAN_MC']['fit']
    require(dict(learned) == life['replay']['learning_counts'] == original['learning_counts'],
        'original cumulative nonwinning fit work')
    for field in ('target_counts','consolidation_counts'):
        require(life['replay'][field] == {key:value for key,value in original[field].items()
            if not key.endswith('_peak')}, 'original nonpeak fit work '+field)
    require(all(life['replay'][key] == original[key] for key in ('first_sample','last_sample')),
        'original global first and last MC samples')
    predictions = len(panel)*(fit+1)+2*sum(row['local_samples'] for row in life['updates'])
    diagnostic = life['diagnostic_counts']
    require(diagnostic['prediction_terminal_checks'] == diagnostic['value_predictions'] == predictions
        and diagnostic['table_lookups'] == diagnostic['feature_occurrences'] == 32*predictions
        and diagnostic['query_shift_additions'] == 2*predictions,
        'actual direct panel and local-game prediction work')
    for arm, prior in (('SOURCE','FROZEN'),('MEAN','EPISODE_MEAN_MC')):
        check_full_score(life['final_full'][arm], games, score_sequences,
            old['arms'][prior]['heldout']['game_metrics'])
    nodes = sorted({ceil(fraction*fit) for fraction in (0.,.25,.5,.75,1.)})
    require([row['completed_fit_games'] for row in life['h2']] == nodes,
        'five frozen quartile H2 prefixes')
    for group in life['h2']:
        require([row['step'] for row in group['rows']] == [row['step'] for row in panel],
            'H2 uses the same fixed root panel')
        for row in group['rows']:
            actions = row['actions']
            source = {name:q['source_q'] for name,q in actions.items()}
            current = {name:q['current_q'] for name,q in actions.items()}
            fixed = {name:q['frozen_second_q'] for name,q in actions.items()}
            effects = check_h2_decomposition(source,current,fixed)
            for name,q in actions.items():
                require(close(q['fixed_leaf_delta'], effects[name]['leaf'])
                    and close(q['reselection_delta'], effects[name]['remax']),
                    'saved H2 leaf and remax effects')
            for key,values in (('source_actions',source),('current_actions',current),
                               ('frozen_second_actions',fixed)):
                require(row[key] == min(values,key=lambda action:(-values[action],action)),
                    'legal H2 recommendation and lexical tie order')
            if group['completed_fit_games'] == 0:
                require(all(close(source[name], current[name]) and close(source[name], fixed[name])
                    for name in source), 'zero-prefix unchanged SOURCE H2')
    require(life['h2_counts'] == dict(sum((Counter(group['counts']) for group in life['h2']),Counter())),
        'actual five-prefix H2 processing work')
    require(life['reproduction'] == dict(original_fit_nonpeak_counts_and_examples_exact=True,
        original_source_and_mean_full_heldout_exact=True), 'original fit and heldout closure claims')
    return len(panel), fit


def check_trace(receipt, lives):
    rows, events = 0, {life:dict(PANEL=[],GAME=[],H2=[]) for life in receipt['lifecycle_ids']}
    path = Path(receipt['trace_file'])
    require(path.stat().st_size == receipt['trace_bytes'], 'new retained diagnostic storage')
    with gzip.open(path,'rt') as stream:
        for line in stream:
            row = json.loads(line)
            rows += 1
            require(row['lifecycle'] in events and row['kind'] in events[row['lifecycle']],
                'canonical diagnostic event membership')
            events[row['lifecycle']][row['kind']].append(row)
    for lid, event in events.items():
        life = lives[lid]
        require(event['PANEL'] == [dict(kind='PANEL',lifecycle=lid,parent=life['parent'],
            panel=life['panel'],source_predictions=life['snapshots'][0]['predictions'],
            estimated_p_four=life['estimated_p_four'])], 'canonical immutable panel/source/belief')
        require(event['GAME'] == [dict(kind='GAME',lifecycle=lid,**update)
            for update in life['updates']], 'canonical all signed donor game updates')
        require(event['H2'] == [dict(kind='H2',lifecycle=lid,**group)
            for group in life['h2']], 'canonical fixed-prefix H2 readouts')
    return rows


def check_summary(d):
    lives, summary = d['by_lifecycle'], d['summary']
    require(summary['lifecycles'] == len(lives)
        and [row['lifecycle'] for row in summary['by_lifecycle']] == list(range(64)),
        'all signed diagnostic lifecycle summaries')
    total_games = sum(len(life['updates']) for life in lives)
    samples = sum(update['local_samples'] for life in lives for update in life['updates'])
    local = summary['local_update']
    require(local['games'] == total_games and local['samples'] == samples
        and local['all_game_mse_nonincreasing'] and not local['increasing_games'],
        'all local factual residual losses retained')
    delta = mean(mean(update['local_mse_after']-update['local_mse_before']
        for update in life['updates']) for life in lives)
    require(close(local['mean_game_mse_delta'], delta), 'game then life local loss mean')
    require(summary['panel_prediction_delta_closed'], 'all signed panel delta closures')
    donor_means = {split:{status:[] for status in ('WON','LOST')}
        for split in ('FIT','HELDOUT')}
    observed_means = {split:[] for split in ('FIT','HELDOUT')}
    for life, saved_life in zip(lives,summary['by_lifecycle']):
        initial, final = life['snapshots'][0]['predictions'],life['snapshots'][-1]['predictions']
        deltas = check_telescoping(initial,final,
            [(row['status'],row['delta_predictions']) for row in life['updates']])
        saved = saved_life['panel_prediction_deltas']
        require(saved['closed'] and len(saved['panel']) == len(life['panel']),
            'every factual recipient and signed donor retained in analysis')
        for index, row in enumerate(saved['panel']):
            require(all(row[key] == value for key,value in life['panel'][index].items())
                and close(row['source_prediction'],initial[index])
                and close(row['mean_prediction'],final[index])
                and close(row['observed_prediction_delta'],final[index]-initial[index])
                and all(close(row['donor_prediction_deltas'][status],deltas[status][index])
                    for status in ('WON','LOST')), 'signed factual panel attribution in summary')
        for split in ('FIT','HELDOUT'):
            ids = [index for index,row in enumerate(life['panel']) if row['split'] == split]
            observed_means[split].append(mean(final[index]-initial[index] for index in ids))
            for status in ('WON','LOST'):
                donor_means[split][status].append(mean(deltas[status][index] for index in ids))
    for split in ('FIT','HELDOUT'):
        saved = summary['panel_prediction_deltas'][split]
        require(close(saved['observed_prediction_delta'],mean(observed_means[split]))
            and all(close(saved['donor_prediction_deltas'][status],mean(donor_means[split][status]))
                for status in ('WON','LOST')), 'signed donor game then life panel means')
        means = {}
        for arm in ('SOURCE','MEAN'):
            groups = [[row for row in life['final_full'][arm]['game_metrics'] if row['split'] == split]
                for life in lives]
            saved = summary['final_full'][split]['arms'][arm]
            require(saved['games'] == sum(len(group) for group in groups)
                and saved['samples'] == sum(row['count'] for group in groups for row in group),
                'all full factual game/sample totals')
            means[arm] = {metric:mean(mean(row[metric] for row in group) for group in groups)
                for metric in ('bias','mse','mae','mean_prediction','mean_factual_future_utility')}
            require(all(close(saved['metrics'][key], value) for key,value in means[arm].items()),
                'full factual game then life metric means')
        require(all(close(summary['final_full'][split]['MEAN_minus_SOURCE'][key],
            means['MEAN'][key]-means['SOURCE'][key]) for key in means['SOURCE']),
            'full factual signed metric contrast')
        adverse = [life['lifecycle'] for life in lives if mean(row['mse'] for row in
            life['final_full']['MEAN']['game_metrics'] if row['split']==split) > mean(row['mse'] for row in
            life['final_full']['SOURCE']['game_metrics'] if row['split']==split)]
        require(summary['final_full'][split]['mse_increased_lifecycles'] == adverse,
            'adverse factual learning histories preserved')
    for node, fraction in enumerate((0.,.25,.5,.75,1.)):
        values = []
        for life in lives:
            rows = life['h2'][node]['rows']
            values.append(dict(disagreement=mean(r['source_actions']!=r['current_actions'] for r in rows),
                fixed_second_disagreement=mean(r['source_actions']!=r['frozen_second_actions'] for r in rows),
                reselection_changed_choice=mean(r['current_actions']!=r['frozen_second_actions'] for r in rows),
                reselection_premium=mean(mean(q['current_q']-q['frozen_second_q']
                    for q in r['actions'].values()) for r in rows)))
        require(all(close(d['h2_summary'][str(fraction)][key],mean(value[key] for value in values))
            for key in values[0]), 'frozen quartile H2 lifecycle means')


def audit(directory):
    started = process_time()
    directory = Path(directory)
    d = json.loads((directory/'summary.json').read_text())
    settings = json.loads((directory/'configuration.json').read_text())
    require(settings == d['settings'], 'frozen V299 configuration unchanged')
    require(d['schema'] == 'acfqp.b_mechanism.v299' and d['status'] == 'DIAGNOSTIC_COMPLETE'
        and d['scientific_gate'] == 'NOT_A_FORMAL_GATE', 'fixed-data diagnostic scope')
    expected = dict(schema='acfqp.b_mechanism_freeze.v299',lifecycles=list(range(64)),parents=4,
        method='EPISODE_MEAN_MC',alpha=.0025,phase='B',new_environment_observations=0,
        new_evaluation_games=0,selection='FOUR_TIME_GAMES_PER_SPLIT_AND_FOUR_NONWINNING_TIME_STEPS',
        fractions=[0.,.25,.5,.75,1.],belief='FIXED_V298_FIT_PREFIX')
    require(all(settings[key] == value for key,value in expected.items()), 'original frozen replay protocol')
    old = json.loads(Path(settings['source_summary']).read_text())
    require(old['schema'] == 'acfqp.stable_b.v298' and json.loads(
        Path(settings['source_summary']).with_name('audit.json').read_text())['independent_valid'],
        'previous audited V298 facts')
    require(d['source_provenance'] == old['source_provenance'], 'unchanged original SOURCE provenance')
    lives = {life['lifecycle']:life for life in d['by_lifecycle']}
    prior = {life['lifecycle']:life for life in old['by_lifecycle']}
    require([life['lifecycle'] for life in d['by_lifecycle']] == list(range(64))
        and all(life['parent'] == life['lifecycle']%4 for life in lives.values()),
        'complete frozen 64-life cohort')
    canonical_rows = diagnostic_rows = panels = fitting_games = 0
    for parent, receipt in enumerate(d['parent_receipts']):
        ids = list(range(parent,64,4))
        require(receipt['parent'] == parent and receipt['lifecycle_ids'] == ids,
            'four fixed sources and every retained life')
        scores, rows = read_scores(old['parent_receipts'][parent])
        canonical_rows += rows
        for lid in ids:
            n, games = check_life(lives[lid],prior[lid],scores[lid])
            panels += n
            fitting_games += games
        diagnostic_rows += check_trace(receipt,lives)
    check_summary(d)
    account = d['accounting']
    check_zero_new_world(account['new_environment_observations'],account['new_evaluation_games'],
        account['inherited_training_raw_tiles'],old['accounting']['new_training_environment_observations'])
    require(account['inherited_evaluation_counts'] == old['accounting']['evaluation_counts']
        and account['inherited_economic_training_raw_tiles'] ==
            old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN'],
        'previous environment and source economic costs inherited once')
    require(account['canonical_input_rows_read'] == canonical_rows,
        'actual retained input read work')
    for field, life_field in (('replay_learning_counts','replay'),
        ('diagnostic_prediction_counts','diagnostic_counts'),('h2_counts','h2_counts')):
        values = [life[life_field]['learning_counts'] if field=='replay_learning_counts'
            else life[life_field] for life in lives.values()]
        require(account[field] == dict(sum((Counter(value) for value in values),Counter())),
            'actual diagnostic aggregate work '+field)
    values_by_field = dict(
        replay_target_counts=[life['replay']['target_counts'] for life in lives.values()],
        replay_consolidation_counts=[life['replay']['consolidation_counts'] for life in lives.values()],
        native_setup_counts=[life['native_setup_counts'] for life in lives.values()],
        source_setup_counts=[receipt['source_setup']['setup_counts'] for receipt in d['parent_receipts']],
        private_head_setup_counts=[life['private_setup']['counts'] for life in lives.values()],
        host_label_counts=[{key:value for key,value in life['label_counts'].items() if key!='buffer_bytes'}
            for life in lives.values()],
        reconstruction_counts=[receipt['reconstruction']['reconstruction_counts'] for receipt in d['parent_receipts']],
        full_scoring_prediction_counts=[result['prediction_counts'] for life in lives.values()
            for result in life['final_full'].values()],
        full_scoring_target_counts=[{key:value for key,value in result['target_counts'].items()
            if not key.endswith('_peak')} for life in lives.values() for result in life['final_full'].values()],
        full_scoring_setup_counts=[result['setup_counts'] for life in lives.values()
            for result in life['final_full'].values()])
    for field, values in values_by_field.items():
        require(account[field] == dict(sum((Counter(value) for value in values),Counter())),
            'actual summed processing/setup work '+field)
    require(account['replay_buffer_peaks'] == {key:max(life['replay']['buffers'].get(key,0)
        for life in lives.values()) for key in {key for life in lives.values() for key in life['replay']['buffers']}},
        'actual replay buffer peaks use max rather than sums')
    require(account['host_label_buffer_bytes_peak'] == max(life['label_counts']['buffer_bytes'] for life in lives.values())
        and account['full_scoring_target_buffer_doubles_peak'] == max(
            result['target_counts'].get('target_buffer_doubles_peak',0) for life in lives.values()
                for result in life['final_full'].values()), 'actual label and full scoring buffer peaks')
    require(account['private_weight_bytes'] == sum(life['private_setup']['bytes'] for life in lives.values())
        and all(life['private_setup']['bytes'] == life['private_setup']['counts']['source_weight_bytes_copied']
            for life in lives.values()), 'actual private SOURCE copy bytes')
    for field in ('worker_cpu_seconds','compiler_cpu_seconds','canonical_trace_bytes'):
        key = 'cpu_seconds' if field=='worker_cpu_seconds' else 'trace_bytes' if field=='canonical_trace_bytes' else field
        require(close(account[field],sum(receipt[key] for receipt in d['parent_receipts'])),
            'actual process and retained storage cost '+field)
    return dict(status='PASS',independent_valid=True,lifecycles=64,panel_items=panels,
        fitting_games=fitting_games,canonical_input_rows=canonical_rows,diagnostic_rows=diagnostic_rows,
        original_fit_and_heldout_reproduced=True,new_environment_observations=0,new_evaluation_games=0,
        audit_cpu_seconds=process_time()-started,
        audit_scope='Frozen factual labels, all donor arithmetic and cumulative work, original heldout equality '
            'and legal H2 argmax/decomposition. No refitting, world execution or bootstrap.',errors=[])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',required=True,type=Path)
    args = parser.parse_args()
    result = audit(args.input)
    (args.input/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
