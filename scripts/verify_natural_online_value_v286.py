#!/usr/bin/env python3
"""Independent streaming receipt audit; no environment, planner or training calls."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import json
from math import isclose, lgamma, log
from pathlib import Path
from statistics import mean

ARMS = ('FROZEN', 'ORDINARY_TD', 'PERSISTENT_TD')
PHASES = ('A', 'B', 'A_prime')
RAW, GAMES = 131072, 16


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equal_counts(a, b, message):
    require(Counter(a) == Counter(b), message)


def close(a, b):
    return isclose(a, b, rel_tol=1e-11, abs_tol=1e-12)


def terminal(board, status):
    require(len(board) == 16, 'terminal board size')
    if status == 'WON':
        require(max(board) >= 11, 'WON lacks goal tile')
    else:
        require(status == 'LOST' and max(board) < 11 and 0 not in board
            and all(board[4*r+c] != board[4*r+c+1] for r in range(4) for c in range(3))
            and all(board[4*r+c] != board[4*(r+1)+c] for r in range(3) for c in range(4)),
            'LOST retains legal move/goal or unexpected cutoff')


def utility(game):
    require(game['status'] in ('WON', 'LOST'), 'nonterminal full-game receipt')
    return game['score']/2048. + (4. if game['status'] == 'WON' else -4.)


class Memory:
    """Literal V115 Beta/block rule on the new all-raw input definition."""
    def __init__(self):
        self.obs = self.active = self.n = self.fours = 0
        self.modules = [dict(id=0, alpha=1, beta=1, visits=0)]
        self.counts = Counter()

    def learned(self):
        return dict(observations_seen=self.obs, active_module_id=self.active,
            modules=deepcopy(self.modules), pending=dict(n=self.n, fours=self.fours))

    def probability(self):
        module = self.modules[self.active]
        return module['alpha']/(module['alpha']+module['beta'])

    @staticmethod
    def predictive(alpha, beta, n, fours):
        def lb(a, b):
            return lgamma(a)+lgamma(b)-lgamma(a+b)
        return lb(alpha+fours, beta+n-fours)-lb(alpha, beta)

    def consume(self, ranks):
        events = []
        for rank in ranks:
            require(rank in (1, 2), 'unobserved tile rank')
            self.obs += 1
            self.counts['observations_received'] += 1
            if self.obs <= 256:
                m = self.modules[0]
                m['alpha'] += rank == 2
                m['beta'] += rank == 1
                self.counts['beta_updates'] += 1
                if self.obs == 256:
                    m['visits'] = 1
                    events.append(dict(obs_index=256, kind='initialized', module_id=0,
                        previous_module_id=0, block_n=256, block_fours=m['alpha']-1,
                        modules_before=1, modules_after=1, existing_log_scores=[], new_log_score=None))
                continue
            self.n += 1
            self.fours += rank == 2
            if self.n != 64:
                continue
            previous, before = self.active, len(self.modules)
            scores = [dict(module_id=m['id'], log_score=self.predictive(m['alpha'], m['beta'], 64, self.fours))
                      for m in self.modules]
            best = max(scores, key=lambda row: (row['log_score'], -row['module_id']))
            new_score = self.predictive(1, 1, 64, self.fours)-log(64)
            self.counts['routing_blocks'] += 1
            self.counts['candidate_predictive_scores'] += before+1
            if new_score > best['log_score']:
                self.active = before
                self.modules.append(dict(id=before, alpha=1, beta=1, visits=0))
                self.counts['module_creations'] += 1
                kind = 'created'
            else:
                self.active = best['module_id']
                kind = 'reactivated' if self.active != previous else 'updated'
                self.counts['module_reactivations'] += kind == 'reactivated'
            m = self.modules[self.active]
            m['alpha'] += self.fours
            m['beta'] += 64-self.fours
            m['visits'] += 1
            self.counts['beta_updates'] += 64
            events.append(dict(obs_index=self.obs, kind=kind, module_id=self.active,
                previous_module_id=previous, block_n=64, block_fours=self.fours,
                modules_before=before, modules_after=len(self.modules),
                existing_log_scores=scores, new_log_score=new_score))
            self.n = self.fours = 0
        return events


def planning_counts(counts, decisions, depth=2):
    c = Counter(counts)
    require(c['choose_calls'] == decisions, 'extra or missing action selection at chunk boundary')
    if depth == 2:
        require(c['root_swipe_calls'] == 4*decisions and c['second_ply_swipe_calls'] == 4*c['leaf_choose_calls'], 'H2 swipe work')
        require(c['learned_swipe_calls'] == c['root_swipe_calls']+c['second_ply_swipe_calls'], 'H2 total swipes')
        require(c['leaf_choose_calls'] == c['generated_spawn_outcomes'] == c['expanded_postspawn_states'], 'H2 successors')
        require(c['spawn_rank1_outcomes'] == c['spawn_rank2_outcomes'] and
                c['generated_spawn_outcomes'] == c['spawn_rank1_outcomes']+c['spawn_rank2_outcomes'], 'H2 rank branches')
        require(c['expectimax_probability_products'] == c['expectimax_probability_sums'] == c['generated_spawn_outcomes'], 'H2 probability work')
    else:
        require(c['root_swipe_calls'] == c['learned_swipe_calls'] == 4*decisions
            and c['leaf_choose_calls'] == c['second_ply_swipe_calls'] == c['generated_spawn_outcomes'] == 0,
            'DIRECT work contains H2 successors or incorrect root work')
    require(c['line_table_lookups'] == 4*c['learned_swipe_calls'] and
            c['table_lookups'] == 32*c['value_predictions'], 'lookup work')


def check_chunk(row, phase_left, memory):
    """Check raw/action/game ledger and saved-bank credits without board replay."""
    start, end = row['start'], row['end']
    raw = row['raw_spawns']
    n = len(raw)
    require(n == min(phase_left, 64-memory.n) and n > 0, 'raw budget crosses memory block or phase')
    require(row['module_id_before'] == memory.active and row['model_p_four'] == memory.probability(), 'decision used uncommitted memory')
    bank = memory.active if row['arm'] == 'PERSISTENT_TD' else 0
    require(row['active_bank_id'] == bank, 'current bank differs from blind route')
    require(end['raw_tiles'] == start['raw_tiles']+n and
            end['random_draw_position'] == 2*end['raw_tiles'], 'raw/RNG budget omits initial tiles')
    completions = {g['episode']: g for g in row['completed_games']}
    require(len(completions) == len(row['completed_games']), 'duplicate completed game')
    episode, step, score = start['episode'], start['step'], start['return_score']
    initial, game_start, status = start['initial_count'], start['game_start_raw'], start['status']
    pending = start['pending_bank_id']
    credits, update_ids = Counter(), []
    actions = iter(zip(row['actions'], row['scores']))
    starts = init_done = posts = wins = losses = censored = 0
    for i, spawn in enumerate(raw):
        require(spawn['rank'] in (1, 2) and 0 <= spawn['cell'] < 16, 'raw spawn fields')
        if spawn['episode'] != episode:
            require(spawn['episode'] == episode+1 and status != 'ACTIVE', 'game restarted before terminal')
            episode += 1
            step = score = initial = 0
            game_start, status, pending = start['raw_tiles']+i, 'INITIALIZING', None
            starts += 1
        absolute = start['raw_tiles']+i
        if spawn['kind'] == 'INITIAL':
            require(initial < 2 and status == 'INITIALIZING' and pending is None, 'initial tile follows action/pending')
            initial += 1
            if initial == 2:
                status = 'ACTIVE'
                init_done += 1
            continue
        require(spawn['kind'] == 'POST_ACTION' and initial == 2 and status == 'ACTIVE', 'action before second initial tile')
        action, reward = next(actions)
        require(action in ('DOWN', 'LEFT', 'RIGHT', 'UP') and reward >= 0 and reward % 4 == 0, 'actual action/score ledger')
        if pending is not None and row['arm'] != 'FROZEN':
            credits[str(pending)] += 1
            update_ids.append(dict(raw_tiles_before_update=absolute, episode=episode, step=step,
                bank_id=pending, kind='PREVIOUS_PENDING'))
        pending = bank
        step += 1
        score += reward
        posts += 1
        if episode in completions and completions[episode]['end_raw'] == absolute+1:
            game = completions.pop(episode)
            require(game['stream_seed'] == start['stream_seed'] and 'seed' not in game, 'synthetic per-game seed or changed RNG')
            require((game['start_raw'], game['steps'], game['score']) == (game_start, step, score), 'completed game score/steps differ from actual actions')
            status = game['status']
            require(status in ('WON', 'LOST'), 'training game cutoff/nonterminal')
            wins += status == 'WON'
            losses += status == 'LOST'
            if status == 'LOST' and row['arm'] != 'FROZEN':
                credits[str(bank)] += 1
                update_ids.append(dict(raw_tiles_before_update=absolute+1, episode=episode,
                    step=step-1, bank_id=bank, kind='TERMINAL_LOSS'))
            pending = None
    require(next(actions, None) is None and len(row['actions']) == len(row['scores']) == posts and not completions, 'action/completion inventory')
    require((end['episode'], end['step'], end['return_score'], end['initial_count'], end['game_start_raw'], end['status'], end['pending_bank_id'])
            == (episode, step, score, initial, game_start, status, pending), 'paused stream or pending bank differs')
    require(end['post_action_spawns'] == start['post_action_spawns']+posts, 'post-action cumulative count')
    if status in ('WON', 'LOST'):
        terminal(end['board'], status)
    expected_env = dict(sampled_transitions=posts, post_action_spawns=posts,
        initial_spawns=n-posts, raw_tile_productions=n, environment_random_draws=2*n,
        ground_explicit_swipe_calls=posts, ground_state_status_calls=posts+init_done,
        ground_status_internal_swipe_calls=4*(posts+init_done-wins),
        ground_swipe_calls=posts+4*(posts+init_done-wins), episodes_started=starts,
        episodes_completed=wins+losses, won_games=wins, lost_games=losses)
    equal_counts(row['counts']['environment'], expected_env, 'actual environment ledger')
    planning_counts(row['counts']['planning'], posts)
    equal_counts(row['bank_update_counts'], credits, 'TD credited to wrong bank or repeated/missing update')
    learning = Counter(row['counts']['learning'])
    require(learning['td_updates'] == sum(credits.values()) and learning['table_update_occurrences'] == 32*sum(credits.values())
            and learning['table_lookups'] == 32*learning['value_predictions'], 'TD work counts')
    require(learning['table_updates'] <= learning['table_update_occurrences'], 'unique table writes exceed occurrences')
    if row['arm'] == 'FROZEN':
        require(not learning and not row['td_examples'], 'frozen leaf was updated or unused SARSA calculated')
    else:
        require(sum(credits.values()) == posts-wins+int(start['pending_bank_id'] is not None)-int(pending is not None)-censored,
                'afterstate TD inventory')
        expected_examples = [] if not update_ids else [update_ids[0], update_ids[-1]]
        require(len(row['td_examples']) == len(expected_examples), 'first/last TD receipts missing')
        for example, identity in zip(row['td_examples'], expected_examples):
            require(all(example[k] == v for k, v in identity.items()), 'first/last TD causal identity')
            if example['kind'] == 'TERMINAL_LOSS':
                require(example['target'] == -4., 'LOSS target differs')
    return credits


def check_games(games, life, phase, counts, depth=2):
    require(len(games) == 16, 'checkpoint game budget')
    seeds = [286500000000+life*1000000+phase*100000+i for i in range(16)]
    require([g['seed'] for g in games] == seeds, 'fresh paired evaluation seeds')
    for game in games:
        terminal(game['final_board'], game['status'])
        require(1 <= game['steps'] <= 8192 and game['utility'] == utility(game), 'complete utility includes score and terminal bonus')
    posts, wins = sum(g['steps'] for g in games), sum(g['status'] == 'WON' for g in games)
    expected = dict(sampled_transitions=posts, post_action_spawns=posts, initial_spawns=32,
        raw_tile_productions=posts+32, environment_random_draws=2*(posts+32),
        ground_explicit_swipe_calls=posts, ground_state_status_calls=posts+16,
        ground_status_internal_swipe_calls=4*(posts+16-wins), ground_swipe_calls=posts+4*(posts+16-wins))
    equal_counts(counts['environment'], expected, 'evaluation physical costs')
    planning_counts(counts['planning'], posts, depth)
    return dict(games=16, mean_game_utility=mean(g['utility'] for g in games), wins=wins,
        losses=16-wins, cutoffs=0, steps=posts)


def pooled(rows):
    return dict(mean_game_utility=mean(r['mean_game_utility'] for r in rows),
        **{k: sum(r[k] for r in rows) for k in ('games', 'wins', 'losses', 'cutoffs', 'steps')})


def check_contrast(saved, values):
    require(saved['lifecycle_deltas'] == {str(i): v for i, v in enumerate(values)} and saved['mean'] == mean(values), 'signed equal-life deltas/mean')
    require(saved['improved_equal_worse'] == [sum(v > 0 for v in values), sum(v == 0 for v in values), sum(v < 0 for v in values)]
            and saved['adverse_lifecycles'] == [i for i, v in enumerate(values) if v < 0], 'adverse lives filtered')
    groups = [values[p::4] for p in range(4)]
    require(saved['parent_mean_deltas'] == {str(p): mean(v) for p, v in enumerate(groups)}
            and saved['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS', 'fixed-parent bootstrap inputs/scope')
    low, high = saved['ci95']
    require(mean(min(g) for g in groups) <= low <= high <= mean(max(g) for g in groups), 'CI outside possible parent resamples')


def audit(directory):
    directory = Path(directory)
    d = json.loads((directory/'summary.json').read_text())
    frozen = json.loads((directory/'configuration.json').read_text())
    settings, accounting = d['settings'], d['accounting']
    for key in ('arms', 'lifecycles', 'parents', 'raw_tiles_per_phase', 'evaluation_games', 'alpha', 'max_steps',
                'seed_training', 'seed_warmup', 'seed_evaluation', 'memory_input', 'evaluation'):
        require(settings[key] == frozen[key], 'configuration changed: '+key)
    require(settings['arms'] == list(ARMS) and settings['lifecycles'] == list(range(16)) and settings['raw_tiles_per_phase'] == RAW
            and settings['evaluation_games'] == GAMES and settings['seed_evaluation'] == 286500000000, 'registered cohort/budget')
    require(d['summary']['bootstrap_seed'] == frozen['bootstrap_seed'] == 28600001 and
            d['summary']['bootstrap_draws'] == frozen['bootstrap_draws'] == 20000, 'registered bootstrap changed')
    lives = {l['lifecycle']: l for l in d['by_lifecycle']}
    require(set(lives) == set(range(16)) and len(d['by_lifecycle']) == 16, 'complete sixteen-life cohort')
    train_totals, eval_totals = {k: Counter() for k in ('environment','planning','learning')}, {k: Counter() for k in ('environment','planning')}
    warm_env, warm_direct, warm_mem = Counter(), Counter(), Counter()
    warm_raw = warm_games = examples = train_rows = 0
    states, phase_counts, bank_counts, rank_prefixes, memories, events_n = {}, {}, defaultdict(Counter), {}, {}, Counter()
    phase_memory_before, phase_chunks = {}, Counter()
    evaluations, directs, warm_started = set(), set(), set()
    rebuilt = {}
    require([p['parent'] for p in d['parent_receipts']] == list(range(4)), 'four source parent receipts')
    for parent in d['parent_receipts']:
        p = parent['parent']
        require(parent['lifecycle_ids'] == list(range(p,16,4)) and parent['setup']['checkpoint_loads'] == 1
                and parent['setup']['new_leaf_updates'] == 0, 'source physical loading or new-leaf provenance')
        path = Path(parent['trace_file'])
        require(path.stat().st_size == parent['trace_bytes'], 'retained trace size')
        with gzip.open(path,'rt') as stream:
            for line in stream:
                r = json.loads(line)
                life = r['lifecycle']
                require(life in parent['lifecycle_ids'] and lives[life]['parent'] == p, 'trace lifecycle/source parent')
                if r['kind'] == 'WARMUP':
                    if life not in warm_started:
                        memories[life,'warm'] = Memory()
                        warm_started.add(life)
                    m = memories[life,'warm']
                    game = r['summary']
                    require(game['seed'] == 286100000000+life*1000000+warm_games_for_life(lives[life], game['seed']), 'warmup seed')
                    require(game in lives[life]['warmup']['game_summaries'] and utility(game) == game['utility'], 'warmup complete-game receipt')
                    terminal(r['final_board'], game['status'])
                    require(len(r['actions']) == len(r['scores']) == game['steps'] and sum(r['scores']) == game['score'], 'warmup actions/score')
                    require(len(r['raw_spawns']) == game['steps']+2 and [s['kind'] for s in r['raw_spawns'][:2]] == ['INITIAL','INITIAL'], 'warmup all initial observations')
                    m.consume(s['rank'] for s in r['raw_spawns'])
                    warm_raw += len(r['raw_spawns']); warm_games += 1
                    continue
                if r['kind'] == 'TRAIN':
                    arm, phase = r['arm'], r['phase']
                    key, pk = (life,arm), (life,arm,phase)
                    require(arm in ARMS and phase in PHASES, 'unexpected arm/phase')
                    if key not in states:
                        m = memories[life,'warm']
                        require(m.learned() == lives[life]['warmup']['final_memory'], 'independent warmup memory')
                        memories[key] = deepcopy(m)
                        states[key] = r['start']
                        rank_prefixes[key] = bytearray()
                    require(r['start'] == states[key], 'training continuity broken after chunk/evaluation')
                    require(r['start']['stream_seed'] == 286200000000+life*10000000, 'continuous training seed')
                    index = PHASES.index(phase)
                    phase_end = (index+1)*RAW
                    require(index*RAW <= r['start']['raw_tiles'] < phase_end, 'training phase switched at wrong raw index')
                    if pk not in phase_counts:
                        phase_counts[pk] = {kind: Counter() for kind in train_totals}
                        phase_memory_before[pk] = memories[key].counts.copy()
                        require(r['start'] == lives[life]['arms'][arm]['phases'][phase]['training']['before_stream'], 'phase start snapshot')
                    m = memories[key]
                    credits = check_chunk(r, phase_end-r['start']['raw_tiles'], m)
                    examples += len(r['td_examples'])
                    bank_counts[key].update(credits)
                    expected_events = m.consume(s['rank'] for s in r['raw_spawns'])
                    require(r['memory_events'] == expected_events, 'independent Beta route event differs')
                    rank_prefixes[key].extend(s['rank'] for s in r['raw_spawns'])
                    events_n[pk] += len(expected_events)
                    for kind in train_totals:
                        train_totals[kind].update(r['counts'][kind])
                        phase_counts[pk][kind].update(r['counts'][kind])
                    states[key] = r['end']
                    train_rows += 1
                    phase_chunks[pk] += 1
                    for example in r['td_examples']:
                        source_query = d['source_provenance']['parents'][p]['source_query']
                        fs, gs = source_query['failure_penalty'], source_query['goal_bonus']
                        offset = (fs-4.)+((8.)-(fs+gs))*.5
                        require(close(example['raw_target'], example['target']-offset), 'query TD offset applied incorrectly')
                    continue
                require(r['kind'] in ('EVALUATION','DIRECT_FINAL'), 'unknown trace row')
                arm = r.get('arm','PERSISTENT_TD')
                phase = r.get('phase','A_prime')
                key, pk = (life,arm), (life,arm,phase)
                snapshot = lives[life]['arms'][arm]['phases'][phase]['snapshot']
                require(r['snapshot'] == snapshot and snapshot['stream'] == states[key]
                        and snapshot['memory'] == memories[key].learned(), 'evaluation used changed training/memory snapshot')
                require(snapshot['estimated_p_four'] == memories[key].probability(), 'snapshot belief differs')
                require(len(rank_prefixes[key]) == (PHASES.index(phase)+1)*RAW, 'snapshot observed unequal budget')
                if r['kind'] == 'EVALUATION':
                    require(pk not in evaluations, 'duplicate checkpoint evaluation')
                    evaluations.add(pk)
                    saved = lives[life]['arms'][arm]['phases'][phase]
                    require(r['game_summaries'] == saved['game_summaries'] and r['counts'] == saved['evaluation_counts'], 'evaluation receipt/summary differs')
                    equal_counts(phase_counts[pk]['environment'],saved['training']['counts']['environment'],'phase execution counts')
                    for kind in ('planning','learning'):
                        equal_counts(phase_counts[pk][kind],saved['training']['counts'][kind],'phase '+kind+' costs')
                    require(events_n[pk] == saved['training']['memory_event_count'] and states[key] == saved['training']['after_stream'], 'phase route count/final pause')
                    memory_work = memories[key].counts-phase_memory_before[pk]
                    memory_work['predict_calls'] = phase_chunks[pk]+1
                    equal_counts(memory_work,saved['training']['memory_counts'],'phase memory/router costs')
                    require(phase_chunks[pk] == saved['training']['chunks'],'phase chunk inventory')
                    gs = check_games(r['game_summaries'],life,PHASES.index(phase),r['counts'])
                    rebuilt[pk] = gs
                else:
                    require(life not in directs, 'duplicate final DIRECT')
                    directs.add(life)
                    require(r['game_summaries'] == lives[life]['direct_final']['game_summaries'] and r['counts'] == lives[life]['direct_final']['counts'], 'DIRECT receipt')
                    rebuilt[life,'DIRECT'] = check_games(r['game_summaries'],life,2,r['counts'],depth=1)
                for kind in eval_totals:
                    eval_totals[kind].update(r['counts'][kind])
        print(json.dumps(dict(event='independent_parent_audited',parent=p)),flush=True)
    require(len(evaluations) == 16*3*3 and directs == set(range(16)), 'complete checkpoint evaluations')
    rows = []
    for life in range(16):
        l = lives[life]
        warm_env.update(l['warmup']['environment_counts']); warm_direct.update(l['warmup']['direct_counts']); warm_mem.update(l['warmup']['memory_counts'])
        arms = {}
        for arm in ARMS:
            key = life,arm
            a = l['arms'][arm]
            require(len(rank_prefixes[key]) == 3*RAW and rank_prefixes[key] == rank_prefixes[life,'FROZEN'], 'arm raw rank prefixes differ')
            require(memories[key].learned() == a['final_memory'] == l['arms']['FROZEN']['final_memory'], 'arm blind memory differs')
            require(states[key] == a['final_stream'], 'evaluation altered final stream')
            for phase in PHASES:
                require(memories[life,arm].obs == l['warmup']['raw_tiles']+3*RAW, 'final raw observation memory count')
                saved = a['phases'][phase]
                require(saved['training']['raw_tiles'] == RAW, 'phase raw budget')
                require(saved['snapshot']['memory'] == l['arms']['FROZEN']['phases'][phase]['snapshot']['memory'], 'same-prefix routed memories differ')
            for kind in train_totals:
                equal_counts(a['training_counts'][kind],sum((phase_counts[life,arm,ph][kind] for ph in PHASES),Counter()),'arm aggregate '+kind)
            updates = sum(bank_counts[key].values())
            require(updates == a['new_value_updates'] == sum(s['updates'] for s in a['phases']['A_prime']['snapshot']['banks'].values()), 'bank update totals')
            if arm != 'FROZEN':
                equal_counts({i:b['td_updates'] for i,b in a['bank_counts'].items()},bank_counts[key],'bank credit aggregate')
                for field in ('td_updates','value_predictions','table_lookups','table_updates','table_update_occurrences'):
                    require(sum(b.get('inner_'+field,0) for b in a['bank_counts'].values()) == a['training_counts']['learning'].get(field,0), 'bank inner work aggregate')
            else:
                require(updates == 0 and a['private_weight_bytes'] == 0, 'frozen private/updated tables')
            setups = a['bank_setups']
            require(len({s['bank_id'] for s in setups}) == len(setups), 'bank recreated instead of retained')
            require(a['private_weight_bytes'] == (sum(s['weight_bytes'] for s in setups) if arm != 'FROZEN' else 0), 'private table storage')
            for setup in setups:
                if arm != 'FROZEN':
                    require(not setup['source_weights_shared'] and setup['setup_counts']['source_weight_bytes_copied'] == setup['weight_bytes']
                        and setup['setup_counts']['source_parameters_copied']*8 == setup['weight_bytes'], 'new-bank source copying costs')
                else:
                    require(setup['source_weights_shared'] and not setup['setup_counts'],'frozen source shared-table cost')
            phases = {ph:rebuilt[life,arm,ph] for ph in PHASES}
            arms[arm] = dict(pooled(list(phases.values())),phases=phases,
                mean_lifecycle_utility=mean(r['mean_game_utility'] for r in phases.values()))
        rows.append(dict(lifecycle=life,parent=life%4,arms=arms,direct_final=rebuilt[life,'DIRECT']))
    summary = d['summary']
    require(summary['by_lifecycle'] == rows, 'independent equal-game/phase/life statistics')
    for arm in ARMS:
        expected = dict(pooled([r['arms'][arm] for r in rows]),
            mean_lifecycle_utility=mean(r['arms'][arm]['mean_lifecycle_utility'] for r in rows),
            phases={ph:pooled([r['arms'][arm]['phases'][ph] for r in rows]) for ph in PHASES})
        require(summary['arms'][arm] == expected,'arm summary means or terminal counts')
    for left,right in (('PERSISTENT_TD','ORDINARY_TD'),('PERSISTENT_TD','FROZEN'),('ORDINARY_TD','FROZEN')):
        saved = summary['paired_contrasts'][left+'_minus_'+right]
        check_contrast(saved,[r['arms'][left]['mean_lifecycle_utility']-r['arms'][right]['mean_lifecycle_utility'] for r in rows])
        for ph in PHASES:
            check_contrast(saved['phases'][ph],[r['arms'][left]['phases'][ph]['mean_game_utility']-r['arms'][right]['phases'][ph]['mean_game_utility'] for r in rows])
    check_contrast(summary['planner_contribution'],[r['arms']['PERSISTENT_TD']['phases']['A_prime']['mean_game_utility']-r['direct_final']['mean_game_utility'] for r in rows])
    require(summary['direct_final'] == pooled([r['direct_final'] for r in rows]) and summary['complete_game_endpoints'], 'DIRECT pooled results')
    for kind in train_totals:
        equal_counts(accounting['training_counts'][kind],train_totals[kind],'global training '+kind)
    for kind in eval_totals:
        equal_counts(accounting['evaluation_counts'][kind],eval_totals[kind],'global evaluation '+kind)
    require(accounting['training_raw_tiles'] == train_totals['environment']['raw_tile_productions'] == 18874368
        and accounting['training_raw_tiles_per_arm'] == 6291456, 'global matched raw budget')
    require(accounting['physical_warmup_raw_tiles'] == warm_raw == sum(l['warmup']['raw_tiles'] for l in lives.values())
        and accounting['physical_warmup_games'] == warm_games, 'physical warmup counted repeatedly')
    equal_counts(accounting['physical_warmup_environment_counts'],warm_env,'shared warmup physical costs')
    source = d['source_provenance']
    inherited = accounting['inherited_costs_per_arm']['FROZEN']
    source_env = sum((Counter(s['inherited_training_costs']['environment_counts']) for s in source['parents']),Counter())
    equal_counts(inherited['source_training_environment_counts'],source_env,'source acquisition inherited costs')
    equal_counts(inherited['warmup_environment_counts'],warm_env,'economic warmup environment')
    equal_counts(inherited['warmup_direct_counts'],warm_direct,'economic warmup direct')
    equal_counts(inherited['warmup_memory_counts'],warm_mem,'economic warmup memory')
    require(inherited['source_training_raw_tiles'] == source_env['sampled_transitions']+source_env['initial_spawns']
        and inherited['warmup_raw_tiles'] == warm_raw and inherited['dynamics_costs'] == source['inherited_dynamics_costs'], 'all-raw inherited ledger')
    dynamics_env = source['inherited_dynamics_costs']['source_environment']
    require(inherited['dynamics_raw_tiles'] == dynamics_env['sampled_transitions']+dynamics_env['initial_spawns'], 'source dynamics initial tiles')
    economic = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm_raw+6291456
    for arm in ARMS:
        require(accounting['inherited_costs_per_arm'][arm] == inherited and accounting['economic_training_raw_tiles_per_arm'][arm] == economic, 'arm economic costs differ or omitted')
        require(accounting['new_value_updates'][arm] == sum(sum(bank_counts[life,arm].values()) for life in range(16)), 'new TD update ledger')
    for field in ('cpu_seconds','compiler_cpu_seconds'):
        global_name = 'worker_cpu_seconds' if field == 'cpu_seconds' else field
        require(close(accounting[global_name],sum(p[field] for p in d['parent_receipts'])),'worker CPU duplicated or omitted')
    require(accounting['trace_bytes'] == sum(p['trace_bytes'] for p in d['parent_receipts']), 'trace storage costs')
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,
        training_raw_tiles=18874368,new_training_raw_tiles_per_arm=6291456,economic_training_raw_tiles_per_arm=economic,
        raw_rank_and_blind_memory_equal=True,training_chunks=train_rows,td_receipt_examples=examples,
        new_value_updates=accounting['new_value_updates'],evaluation_games=2560,evaluation_cutoffs=0,
        training_completed_games=train_totals['environment']['episodes_completed'],training_cutoffs=0,
        trace_bytes=accounting['trace_bytes'],signed_contrasts={k:{f:v[f] for f in ('mean','ci95','improved_equal_worse','adverse_lifecycles')}
            for k,v in summary['paired_contrasts'].items()},
        bootstrap_scope='All signed phase/lifecycle deltas and fixed-parent inputs checked. Registered 20000-draw intervals not recomputed.',
        limitations='Training action/score/status and bank-credit inventories checked without replaying intermediate boards or TD weights. All evaluation terminal boards checked. Conditional on four existing sources; no optimal-value claim.',errors=[])


def warm_games_for_life(life,seed):
    return next(i for i,g in enumerate(life['warmup']['game_summaries']) if g['seed'] == seed)


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
