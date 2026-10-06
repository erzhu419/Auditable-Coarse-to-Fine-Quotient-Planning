#!/usr/bin/env python3
"""Compact V287 audit using retained score receipts, without world/weight replay."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_natural_online_value_v286 import (
    check_contrast, close, equal_counts, planning_counts, require, terminal,
)

ARMS = ('FROZEN', 'SHADOW_TD', 'EPISODIC_MC')
METRICS = ('bias', 'mse', 'mae')
PAIRS = (('EPISODIC_MC','FROZEN'), ('SHADOW_TD','FROZEN'), ('EPISODIC_MC','SHADOW_TD'))


def future_targets(scores, status):
    suffix = 4. if status == 'WON' else -4.
    targets = []
    for score in reversed(scores):
        targets.append(suffix)
        suffix += score/2048.
    targets.reverse()
    return targets[:-1] if status == 'WON' else targets


def check_fit(fit, games, method):
    steps, wins = sum(g['steps'] for g in games), sum(g['status'] == 'WON' for g in games)
    updates, losses = steps-wins, len(games)-wins
    c, t = Counter(fit['learning_counts']), Counter(fit['target_counts'])
    require(fit['method'] == method and fit['fitted_games'] == len(games) and fit['fitted_steps'] == steps
        and fit['trained_afterstates'] == c['td_updates'] == updates, 'same chronological fit afterstate inventory')
    predictions = updates if method == 'MC' else updates+updates-len(games)
    require(c['value_predictions'] == predictions and c['table_lookups'] == 32*predictions
        and c['table_update_occurrences'] == 32*updates and c['table_updates'] <= 32*updates, 'fit physical work')
    expected = dict(goal_checks=steps if method == 'MC' else 2*steps-len(games),
        skipped_winning_afterstates=wins, raw_target_subtractions=updates)
    if method == 'MC':
        expected.update(suffix_games=len(games),suffix_target_assignments=steps,suffix_reward_additions=steps)
        require(t['target_buffer_doubles_peak'] >= max(g['steps'] for g in games), 'MC suffix buffer cost')
    else:
        expected.update(analytic_next_tails=wins, terminal_target_assignments=losses,
            td_next_reward_additions=steps-len(games), prediction_shift_additions=2*(updates-len(games)))
    equal_counts({k:v for k,v in t.items() if k != 'target_buffer_doubles_peak'},expected,'fit target construction counts')
    for example in (fit['first_update'],fit['last_update']):
        require(close(example['raw_target']-example['raw_prediction_before_update'],example['error']), 'TD example prediction/error identity')
    return updates


def check_holdout(heldout, games, score_rows, fit_steps):
    metrics = heldout['game_metrics']
    require(len(metrics) == len(games), 'heldout episode inventory')
    cursor, samples, wins = fit_steps, 0, 0
    for saved, game, scores in zip(metrics,games,score_rows):
        actual = future_targets(scores,game['status'])
        require((saved['episode'],saved['start'],saved['end'],saved['count'])
            == (game['episode'],cursor,cursor+game['steps'],len(actual)), 'heldout chronological afterstate inventory')
        require(close(saved['mean_factual_future_utility'],mean(actual)), 'heldout factual suffix includes current reward or wrong terminal bonus')
        require(close(saved['bias'],saved['mean_prediction']-saved['mean_factual_future_utility']), 'heldout signed bias')
        require(saved['mse']+1e-10 >= saved['bias']**2 and saved['mae']+1e-10 >= abs(saved['bias'])
            and saved['mse']+1e-10 >= saved['mae']**2, 'heldout error moment consistency')
        cursor += game['steps']; samples += len(actual); wins += game['status'] == 'WON'
    for metric in METRICS:
        require(close(heldout['metrics'][metric],mean(g[metric] for g in metrics)), 'heldout episode weighting')
    p, t = Counter(heldout['prediction_counts']), Counter(heldout['target_counts'])
    equal_counts(p,dict(value_predictions=samples,table_lookups=32*samples),'heldout static prediction costs/no training')
    expected = dict(goal_checks=sum(g['steps'] for g in games),suffix_games=len(games),
        suffix_target_assignments=sum(g['steps'] for g in games), suffix_reward_additions=sum(g['steps'] for g in games),
        prediction_shift_additions=2*samples,skipped_winning_afterstates=wins)
    equal_counts({k:v for k,v in t.items() if k != 'target_buffer_doubles_peak'},expected,'heldout target costs')
    require(t['target_buffer_doubles_peak'] >= max(g['steps'] for g in games),'heldout suffix buffer cost')
    return dict(games=len(games),samples=samples,**{k:mean(g[k] for g in metrics) for k in METRICS})


def evaluation(games, life, counts):
    require(len(games) == 16 and [g['seed'] for g in games] == [287500000000+life*1000000+i for i in range(16)], 'fresh paired V287 evaluation seeds')
    for g in games:
        terminal(g['final_board'],g['status'])
        require(1 <= g['steps'] <= 8192 and g['utility'] == g['score']/2048.+(4. if g['status'] == 'WON' else -4.), 'new full-game utility')
    steps,wins = sum(g['steps'] for g in games),sum(g['status'] == 'WON' for g in games)
    equal_counts(counts['environment'],dict(sampled_transitions=steps,post_action_spawns=steps,
        initial_spawns=32,raw_tile_productions=steps+32,environment_random_draws=2*(steps+32),
        ground_explicit_swipe_calls=steps,ground_state_status_calls=steps+16,
        ground_status_internal_swipe_calls=4*(steps+16-wins),ground_swipe_calls=steps+4*(steps+16-wins)), 'new evaluation environment cost')
    planning_counts(counts['planning'],steps)
    return dict(games=16,mean_game_utility=mean(g['utility'] for g in games),wins=wins,
        losses=16-wins,cutoffs=0,steps=steps)


def pooled(rows):
    return dict(mean_game_utility=mean(r['mean_game_utility'] for r in rows),
        **{k:sum(r[k] for r in rows) for k in ('games','wins','losses','cutoffs','steps')})


def read_retained(original, datasets):
    """Read already audited canonical A score/events; no swipes or Beta rescoring."""
    result = {}
    for parent in original['parent_receipts']:
        ids = parent['lifecycle_ids']
        game_scores = {life:defaultdict(list) for life in ids}
        games = {life:[] for life in ids}
        fit_states = {life:deepcopy(next(l for l in original['by_lifecycle'] if l['lifecycle'] == life)['warmup']['final_memory']) for life in ids}
        # The input is the retained V286 compact canonical serialization.
        with gzip.open(parent['trace_file'],'rt') as stream:
            for line in stream:
                if '"arm":"FROZEN","phase":"A"' not in line[:200]:
                    continue
                row = json.loads(line)
                if row['kind'] != 'TRAIN':
                    continue
                life = row['lifecycle']; dataset = datasets[life]
                scores = iter(row['scores'])
                state = fit_states[life]
                for offset,spawn in enumerate(row['raw_spawns']):
                    if spawn['kind'] == 'POST_ACTION':
                        game_scores[life][spawn['episode']].append(next(scores))
                    if row['start']['raw_tiles']+offset >= dataset['fit_end_raw']:
                        continue
                    state['observations_seen'] += 1
                    state['pending']['n'] += 1
                    state['pending']['fours'] += spawn['rank'] == 2
                    if state['pending']['n'] == 64:
                        event = next(e for e in row['memory_events'] if e['obs_index'] == state['observations_seen'])
                        require(event['block_fours'] == state['pending']['fours'], 'retained fit-prefix event count')
                        if event['kind'] == 'created':
                            state['modules'].append(dict(id=event['module_id'],alpha=1,beta=1,visits=0))
                        state['active_module_id'] = event['module_id']
                        m = state['modules'][event['module_id']]
                        m['alpha'] += event['block_fours']; m['beta'] += 64-event['block_fours']; m['visits'] += 1
                        state['pending'] = dict(n=0,fours=0)
                games[life].extend(row['completed_games'])
        for life in ids:
            require(all(len(game_scores[life][g['episode']]) == g['steps'] and sum(game_scores[life][g['episode']]) == g['score'] for g in games[life]), 'canonical retained factual score inventory')
            result[life] = dict(games=games[life],scores=[game_scores[life][g['episode']] for g in games[life]],fit_memory=fit_states[life])
        print(json.dumps(dict(event='retained_parent_receipts_checked',parent=parent['parent'])),flush=True)
    return result


def audit(directory):
    directory = Path(directory)
    d = json.loads((directory/'summary.json').read_text())
    frozen = json.loads((directory/'configuration.json').read_text())
    require(d['settings'] == frozen and frozen['alpha'] == .0025 and frozen['fit_fraction'] == .8
        and frozen['arms'] == list(ARMS), 'registered methods, alpha or split changed')
    original = json.loads(Path(frozen['source_summary']).read_text())
    require(json.loads(Path(frozen['source_summary']).with_name('audit.json').read_text())['independent_valid'], 'retained source audit')
    require(d['source_provenance'] == original['source_provenance'], 'source data changed')
    lives = d['by_lifecycle']
    require([l['lifecycle'] for l in lives] == list(range(16)) and all(l['parent'] == l['lifecycle']%4 for l in lives), 'complete fixed-source cohort')
    datasets = {l['lifecycle']:l['dataset'] for l in lives}
    retained = read_retained(original,datasets)
    records = []
    fit_samples = heldout_samples = excluded_raw = 0
    for l in lives:
        life,ds = l['lifecycle'],l['dataset']
        canonical = retained[life]
        games = canonical['games']; n = 4*len(games)//5
        require(ds['fit_game_count'] == n and n > 0 and n < len(games), 'fit split must be first floor80% complete games')
        require(ds['games'] == [dict(g,split='FIT' if i<n else 'HELDOUT') for i,g in enumerate(games)], 'heldout/tail/source-game selection changed')
        fit_steps,all_steps = sum(g['steps'] for g in games[:n]),sum(g['steps'] for g in games)
        fit_raw,complete_raw = games[n-1]['end_raw'],games[-1]['end_raw']
        require(ds['fit_step_end'] == fit_steps and ds['fit_end_raw'] == fit_raw, 'fit temporal boundary')
        costs = ds['costs']; old = original['by_lifecycle'][life]
        expected = dict(full_A_raw_tiles=131072,fit_raw_tiles=fit_raw,heldout_raw_tiles=complete_raw-fit_raw,
            fit_steps=fit_steps,heldout_steps=all_steps-fit_steps,
            excluded_tail_games=int(complete_raw<131072),excluded_tail_raw_tiles=131072-complete_raw,
            excluded_tail_steps=old['arms']['FROZEN']['phases']['A']['training']['after_stream']['post_action_spawns']-all_steps)
        require(all(costs[k] == v for k,v in expected.items()), 'excluded tail or full acquired budget omitted')
        require(costs['full_A_acquisition_counts'] == old['arms']['FROZEN']['phases']['A']['training']['counts'], 'retained A processing/acquisition conflated')
        for key in ('warmup_raw_tiles','warmup_environment_counts','warmup_direct_counts','warmup_memory_counts'):
            source_key = key.removeprefix('warmup_')
            require(costs[key] == old['warmup'][source_key], 'shared warmup inheritance')
        learned = {k:ds['fit_memory'][k] for k in ('observations_seen','active_module_id','modules','pending')}
        require(learned == canonical['fit_memory'], 'fit belief incorporates heldout observations')
        require(l['evaluation_snapshot']['memory']['observations_seen'] == learned['observations_seen'], 'snapshot prefix observations')
        for key in ('active_module_id','modules','pending'):
            require(l['evaluation_snapshot']['memory'][key] == learned[key], 'snapshot memory changed during fitting/evaluation')
        m = learned['modules'][learned['active_module_id']]
        require(l['evaluation_snapshot']['estimated_p_four'] == m['alpha']/(m['alpha']+m['beta']), 'same static fit-prefix belief')
        arms = {}
        for arm in ARMS:
            a = l['arms'][arm]
            if arm == 'FROZEN':
                require(a['new_value_updates'] == 0 and not a['fit']['learning_counts'] and not a['fit']['target_counts']
                    and a['head_setup']['source_weights_shared'] and a['head_setup']['private_weight_bytes'] == 0, 'frozen source was fitted/copied')
            else:
                method = 'TD' if arm == 'SHADOW_TD' else 'MC'
                updates = check_fit(a['fit'],games[:n],method)
                require(a['new_value_updates'] == updates, 'heldout/evaluation feedback credited as fitting')
                setup = a['head_setup']
                require(not setup['source_weights_shared'] and setup['private_weight_bytes'] == setup['setup_counts']['source_weight_bytes_copied'], 'same source initialization/copy cost')
                for example in (a['fit']['first_update'],a['fit']['last_update']):
                    source_query = d['source_provenance']['parents'][l['parent']]['source_query']
                    fs,gs = source_query['failure_penalty'],source_query['goal_bonus']
                    offset = fs-4.+(8.-fs-gs)*.5
                    require(close(example['raw_target'],example['target']-offset), 'query offset applied incorrectly')
                first,last = a['fit']['first_update'],a['fit']['last_update']
                last_targets = future_targets(canonical['scores'][n-1],games[n-1]['status'])
                require(first['episode'] == 0 and first['step'] == 0 and last['episode'] == n-1
                    and last['step'] == fit_steps-(2 if games[n-1]['status'] == 'WON' else 1), 'chronological first/last updates')
                require(close(last['target'],last_targets[-1]), 'last fitted terminal target')
                if method == 'MC':
                    require(close(first['target'],future_targets(canonical['scores'][0],games[0]['status'])[0]), 'MC first target contains current reward')
            heldout = check_holdout(a['heldout'],games[n:],canonical['scores'][n:],fit_steps)
            arms[arm] = dict(evaluation(a['game_summaries'],life,a['evaluation_counts']),heldout=heldout)
        records.append(dict(lifecycle=life,parent=life%4,arms=arms))
        fit_samples += sum(g['steps']-(g['status'] == 'WON') for g in games[:n])
        heldout_samples += arms['FROZEN']['heldout']['samples']; excluded_raw += costs['excluded_tail_raw_tiles']
    summary = d['summary']
    require(summary['by_lifecycle'] == records,'equal eval-game/episode/life means differ')
    for arm in ARMS:
        values = [r['arms'][arm] for r in records]
        held = [r['heldout'] for r in values]
        expected = dict(pooled(values),heldout=dict(games=sum(r['games'] for r in held),samples=sum(r['samples'] for r in held),
            **{k:mean(r[k] for r in held) for k in METRICS}))
        require(summary['arms'][arm] == expected,'pooled evaluation or episode-equal heldout means')
    for left,right in PAIRS:
        name = left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],[r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records])
        for metric in METRICS:
            vals = [r['arms'][left]['heldout'][metric]-r['arms'][right]['heldout'][metric] for r in records]
            saved = summary['heldout_contrasts'][name][metric]
            require(saved['mean'] == mean(vals) and saved['lifecycle_deltas'] == {str(i):v for i,v in enumerate(vals)},'heldout signed lifecycle deltas')
            require(saved['positive_equal_negative'] == [sum(v>0 for v in vals),sum(v==0 for v in vals),sum(v<0 for v in vals)],'heldout signed negatives')
            groups = [vals[p::4] for p in range(4)]
            require(saved['parent_mean_deltas'] == {str(p):mean(g) for p,g in enumerate(groups)}
                and saved['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS', 'heldout parent scope')
            low,high = saved['ci95']
            require(mean(min(g) for g in groups) <= low <= high <= mean(max(g) for g in groups), 'heldout interval bounds')
    require(summary['bootstrap_draws'] == frozen['bootstrap_draws'] == 20000 and summary['bootstrap_seed'] == frozen['bootstrap_seed'] == 28700001
        and summary['primary_contrast'] == 'EPISODIC_MC_minus_FROZEN' and summary['complete_game_endpoints'], 'registered endpoint/uncertainty')
    a = d['accounting']; inherited = a['inherited_costs_per_arm']['FROZEN']
    old_inherited = original['accounting']['inherited_costs_per_arm']['FROZEN']
    for key in inherited:
        if key.startswith('retained_actor_'):
            continue
        require(inherited[key] == old_inherited[key],'historical source cost changed')
    retained_counts = {k:dict(sum((Counter(old['arms']['FROZEN']['phases']['A']['training']['counts'][k])
        for old in original['by_lifecycle']),Counter())) for k in ('environment','planning','learning')}
    require(a['retained_physical_A_counts'] == inherited['retained_actor_A_counts'] == retained_counts
        and a['retained_physical_A_raw_tiles'] == inherited['retained_actor_A_raw_tiles'] == 2097152, 'whole retained A physical acquisition')
    economic = sum(inherited[k] for k in ('source_training_raw_tiles','dynamics_raw_tiles','warmup_raw_tiles','retained_actor_A_raw_tiles'))
    require(a['new_training_environment_observations'] == 0 and a['shared_warmup_raw_tiles'] == old_inherited['warmup_raw_tiles'], 'new observations or repeated shared warmup')
    for arm in ARMS:
        require(a['inherited_costs_per_arm'][arm] == inherited and a['economic_training_raw_tiles_per_arm'][arm] == economic,'same arm economic ledger')
        require(a['new_value_updates'][arm] == (0 if arm == 'FROZEN' else fit_samples),'aggregate fitted updates')
        for key,section,field in (('fit_counts','fit','learning_counts'),('heldout_prediction_counts','heldout','prediction_counts')):
            equal_counts(a[key][arm],sum((Counter(l['arms'][arm][section][field]) for l in lives),Counter()),'aggregate '+key)
        for section in ('fit','heldout'):
            counters = [Counter(l['arms'][arm][section]['target_counts']) for l in lives]
            equal_counts(a[section+'_target_counts'][arm],sum((Counter({k:v for k,v in c.items() if k != 'target_buffer_doubles_peak'}) for c in counters),Counter()),'aggregate target operation costs')
            require(a[section+'_target_buffer_doubles_peak'][arm] == max(c['target_buffer_doubles_peak'] for c in counters),'buffer peaks incorrectly added')
        require(a['private_head_weight_bytes_created'][arm] == sum(l['arms'][arm]['head_setup']['private_weight_bytes'] for l in lives),'weight allocation cost')
    for kind in ('environment','planning'):
        equal_counts(a['evaluation_counts'][kind],sum((Counter(l['arms'][arm]['evaluation_counts'][kind]) for l in lives for arm in ARMS),Counter()),'new evaluation cost aggregate')
    require(a['reconstruction_costs_by_lifecycle'] == {str(l['lifecycle']):l['dataset']['costs'] for l in lives},'reconstruction cost omitted')
    for key in ('cpu_seconds','compiler_cpu_seconds'):
        require(close(a['worker_cpu_seconds' if key == 'cpu_seconds' else key],sum(p[key] for p in d['parent_receipts'])),'new CPU aggregate')
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,new_training_environment_observations=0,
        evaluation_games=768,evaluation_cutoffs=0,fitted_afterstates_per_trainable_arm=fit_samples,heldout_afterstates_per_arm=heldout_samples,
        excluded_tail_raw_tiles_billed=excluded_raw,economic_training_raw_tiles_per_arm=economic,
        contrasts={name:{k:value[k] for k in ('mean','ci95','improved_equal_worse','adverse_lifecycles')} for name,value in summary['paired_contrasts'].items()},
        method='Canonical retained score/terminal/fit-prefix metadata, factual MC suffixes, fit/heldout/eval inventories, signed means and costs. No world or weight replay; existing 20000-draw CI not recomputed.',
        limitations='Heldout MSE/MAE moment consistency and aggregate weighting checked; per-afterstate predictions and TD bootstrap weight values not reexecuted. Conditional on four existing sources, not a causal comparison with V286 actor feedback.',errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    directory = parser.parse_args().input
    try:
        result = audit(directory)
    except ValueError as error:
        result = dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))
    raise SystemExit(not result['independent_valid'])


if __name__ == '__main__':
    main()
