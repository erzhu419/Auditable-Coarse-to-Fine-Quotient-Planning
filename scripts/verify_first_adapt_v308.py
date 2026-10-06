#!/usr/bin/env python3
"""Independent new-history first-adaptation and warmup-only context audit."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_continual_v303 import check_belief, check_contrast, check_local_fit, check_stage_split, endpoint
from verify_context_continual_v305 import check_new_head, observed_statistics, route_scores
from verify_cumulative_critic_v289 import close, equal_tree, json_file, require, sum_counts
from verify_episode_consolidation_v290 import check_normalized_fit
from verify_natural_online_value_v286 import Memory, planning_counts, terminal
from verify_policy_data_v306 import board_status, swipe
from verify_split_risk_v301 import check_representation, nonpeak
from verify_stable_b_v298 import learned

ARMS = ('SOURCE', 'CONTEXT_MC', 'CONTEXT_LOCAL')
LEARNERS = ARMS[1:]
STAGES = ('A1', 'B', 'A2')
CELLS = ('A1_A', 'B_A', 'B_B', 'A2_A', 'A2_B')
RAW = 131072
PRIMARY = 'CONTEXT_LOCAL_minus_CONTEXT_MC_FINAL_AB'
PAIRS = (('CONTEXT_LOCAL', 'SOURCE'), ('CONTEXT_MC', 'SOURCE'), ('CONTEXT_LOCAL', 'CONTEXT_MC'))
CHECKPOINTS = dict(A_after_B=('B_A', 'A1_A'), B_after_A2=('A2_B', 'B_B'),
    A_restore_after_A2=('A2_A', 'B_A'), A_final_vs_A1=('A2_A', 'A1_A'))
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def stage_context(row):
    require(row['phase'] in STAGES and row['true_p_four'] == (.5 if row['phase'] == 'B' else .1),
        'registered actual new A/B/A world metadata')


def warmup_seed(life, stage, game):
    return 308100000000+STAGES.index(stage)*100000+life*1000000+game


def training_seed(life, stage):
    return 308200000000+STAGES.index(stage)*100000+life*10000000


def evaluation_seed(life, task, episode):
    return 308900000000+(100000 if task == 'B' else 0)+life*1000000+episode


def place(board, spawn):
    require(spawn['rank'] in (1, 2) and 0 <= spawn['cell'] < 16 and board[spawn['cell']] == 0,
        'actual new spawn has rank one or two and occupies an empty cell')
    board[spawn['cell']] = spawn['rank']


class StageWorld:
    """Literal new-world reconstruction; no planner, training or bootstrap calls."""
    def __init__(self, life, stage):
        self.life, self.stage = life, stage
        self.memory = Memory(); self.state = self.before = None
        self.warm_games = []; self.warm_events = []; self.warm_environment = Counter(); self.warm_direct = Counter()
        self.processing = Counter(); self.train_counts = {kind:Counter() for kind in ('environment', 'planning', 'learning')}
        self.games = []; self.scores = defaultdict(list); self.game_memories = {}
        self.training_events = []; self.training_rows = 0
        self.detection = self.snapshot = self.training = None

    def context(self, row):
        require(row['lifecycle'] == self.life and row['parent'] == self.life%4 and row['phase'] == self.stage,
            'new world lifecycle source-parent and stage membership')
        stage_context(row)

    def warmup(self, row):
        self.context(row)
        require(self.detection is None and self.memory.obs < 256, 'paid detector warmup stops at the first complete game after 256 raw observations')
        game = row['summary']; raw = row['raw_spawns']; board = [0]*16; actions = 0
        require(game['seed'] == warmup_seed(self.life, self.stage, len(self.warm_games))
            and len(raw) == game['steps']+2 and [spawn['kind'] for spawn in raw[:2]] == ['INITIAL', 'INITIAL']
            and all(spawn['kind'] == 'POST_ACTION' for spawn in raw[2:]), 'fresh complete SOURCE detector game and all initial/post-action tiles')
        for index, spawn in enumerate(raw):
            if index >= 2:
                require(board_status(board) == 'ACTIVE', 'detector cannot continue after a natural terminal board')
                after, score = swipe(board, row['actions'][actions])
                require(after != board and score == row['scores'][actions], 'detector actual legal swipe and independent merge score')
                board = after; actions += 1
            place(board, spawn)
        require(actions == len(row['actions']) == len(row['scores']) == game['steps']
            and sum(row['scores']) == game['score'] and board == row['final_board']
            and board_status(board) == game['status'] and game['status'] in ('WON', 'LOST')
            and game['utility'] == game['score']/2048.+(4. if game['status'] == 'WON' else -4.),
            'detector full factual score sequence and natural terminal outcome')
        steps, won = game['steps'], game['status'] == 'WON'
        environment = dict(initial_spawns=2, sampled_transitions=steps, environment_random_draws=2*(steps+2),
            ground_explicit_swipe_calls=steps, ground_state_status_calls=steps+1,
            ground_status_internal_swipe_calls=4*(steps+1-won), ground_swipe_calls=steps+4*(steps+1-won))
        require(Counter(row['counts']['environment']) == Counter(environment), 'all detector environment work and initial tiles are paid')
        direct = Counter(row['counts']['direct'])
        require(direct['choose_calls'] == direct['inner_choose_calls'] == steps
            and direct['inner_learned_swipe_calls'] == 4*steps
            and direct['inner_line_table_lookups'] == 4*direct['inner_learned_swipe_calls']
            and direct['inner_table_lookups'] == 32*direct['inner_value_predictions']
            and direct['td_updates'] == direct['inner_td_updates'] == 0, 'detector uses frozen SOURCE DIRECT and receives no learning updates')
        self.warm_events.extend(self.memory.consume(spawn['rank'] for spawn in raw))
        self.warm_games.append(game); self.warm_environment.update(environment); self.warm_direct.update(direct)
        internal = 4*(not won)
        self.processing.update(ground_explicit_swipe_calls=steps, ground_swipe_calls=steps+internal,
            ground_state_status_calls=1, ground_status_internal_swipe_calls=internal, warmup_records=1)

    def detect(self, row):
        self.context(row)
        require(self.detection is None and self.state is None and self.memory.obs >= 256,
            'context is observed once from completed warmup before any training acquisition')
        belief = row['detector_belief']; memory = belief['memory']
        require(memory['method'] == 'LIBRARY' and learned(memory) == self.memory.learned()
            and belief['estimated_p_four'] == self.memory.probability(), 'blind detector belief contains only its observed completed warmup')
        self.detection = row; self.warm_raw = self.memory.obs; self.warm_final = self.memory.learned()
        self.warm_counts = self.memory.counts.copy()

    def train(self, row):
        self.context(row)
        require(self.detection is not None and self.detection['route']['created'] and self.snapshot is None,
            'only a newly created observed context acquires a model cohort')
        start = row['start']; raw = row['raw_spawns']; memory = self.memory
        require(row['arm'] == 'FROZEN' and row['active_bank_id'] == 0 and row['module_id_before'] == memory.active
            and row['model_p_four'] == memory.probability(), 'new cohort uses original SOURCE and preceding observed online LIBRARY probability')
        require(start['stream_seed'] == training_seed(self.life, self.stage)
            and len(raw) == min(RAW-start['raw_tiles'], 64-memory.n) and raw,
            'fresh continuous SOURCE stream stops at each observed block and exact paid raw boundary')
        if self.state is None:
            require(start['raw_tiles'] == start['post_action_spawns'] == start['random_draw_position'] == 0
                and start['status'] == 'NOT_STARTED' and start['initial_count'] == 0
                and start['board'] == [0]*16 and start['pending_afterstate'] is start['pending_bank_id'] is None,
                'created context acquires a new empty stream without old training facts')
            self.state = deepcopy(start); self.before = deepcopy(start)
        require(start == self.state, 'new cohort continuity across factual chunks')
        state = self.state; action = starts = init_done = posts = wins = losses = 0; completed = []; events = []
        for spawn in raw:
            if spawn['kind'] == 'INITIAL':
                if state['status'] != 'INITIALIZING':
                    require(state['status'] in ('NOT_STARTED', 'WON', 'LOST'), 'initial tile cannot restart an active or censored game')
                    state.update(board=[0]*16, episode=state['episode']+1, step=0, return_score=0,
                        status='INITIALIZING', initial_count=0, game_start_raw=state['raw_tiles'], pending_afterstate=None, pending_bank_id=None)
                    starts += 1
                require(state['initial_count'] < 2, 'new game has exactly two initialization tiles')
                state['initial_count'] += 1; init_done += state['initial_count'] == 2
            else:
                require(spawn['kind'] == 'POST_ACTION' and state['status'] == 'ACTIVE' and state['initial_count'] == 2,
                    'new action follows an active two-tile initialization')
                after, score = swipe(state['board'], row['actions'][action])
                require(after != state['board'] and score == row['scores'][action], 'actual new cohort legal swipe and independent merge score')
                state['board'] = after; self.scores[state['episode']].append(score); action += 1; posts += 1
                state['step'] += 1; state['return_score'] += score; state['post_action_spawns'] += 1
                state['pending_afterstate'] = list(after); state['pending_bank_id'] = 0
            require(spawn['episode'] == state['episode'], 'every new raw tile belongs to its actual continuous game')
            place(state['board'], spawn); state['raw_tiles'] += 1; state['random_draw_position'] += 2
            events.extend(memory.consume([spawn['rank']]))
            if state['initial_count'] == 2:
                state['status'] = board_status(state['board'])
            if state['status'] in ('WON', 'LOST'):
                state.update(pending_afterstate=None, pending_bank_id=None)
                game = dict(episode=state['episode'], stream_seed=state['stream_seed'], start_raw=state['game_start_raw'],
                    end_raw=state['raw_tiles'], steps=state['step'], score=state['return_score'], status=state['status'])
                completed.append(game); self.games.append(game); self.game_memories[game['episode']] = memory.learned()
                wins += state['status'] == 'WON'; losses += state['status'] == 'LOST'
        require(action == len(row['actions']) == len(row['scores']) and completed == row['completed_games']
            and state == row['end'] and events == row['memory_events'],
            'new cohort end boards pending states all natural terminals and observed memory events')
        environment = dict(sampled_transitions=posts, post_action_spawns=posts, initial_spawns=len(raw)-posts,
            raw_tile_productions=len(raw), environment_random_draws=2*len(raw), ground_explicit_swipe_calls=posts,
            ground_state_status_calls=posts+init_done, ground_status_internal_swipe_calls=4*(posts+init_done-wins),
            ground_swipe_calls=posts+4*(posts+init_done-wins), episodes_started=starts,
            episodes_completed=wins+losses, won_games=wins, lost_games=losses)
        require(Counter(row['counts']['environment']) == Counter(environment), 'actual new acquisition includes all initial winning and tail raw tiles')
        planning_counts(row['counts']['planning'], posts)
        require(not row['counts']['learning'] and not row['bank_update_counts'] and not row['td_examples'], 'SOURCE acquisition does not fit a learned bank')
        boundary = int(state['status'] not in ('NOT_STARTED', 'INITIALIZING'))
        internal = 4*(init_done+losses+int(boundary and state['status'] != 'WON'))
        self.processing.update(ground_explicit_swipe_calls=posts, ground_swipe_calls=posts+internal,
            ground_state_status_calls=init_done+wins+losses+boundary, ground_status_internal_swipe_calls=internal)
        for kind in self.train_counts:
            self.train_counts[kind].update(row['counts'][kind])
        self.training_events.extend(events); self.training_rows += 1

    def checkpoint(self, row):
        self.context(row)
        require(self.detection is not None and self.detection['route']['created'] and self.snapshot is None
            and self.state is not None and self.state['raw_tiles'] == RAW and row['arm'] == 'FROZEN',
            'one model snapshot follows a created context and its exact raw acquisition boundary')
        snapshot, training = row['snapshot'], row['training']
        require(snapshot['stream'] == self.state and snapshot['memory'] == self.memory.learned()
            and snapshot['estimated_p_four'] == self.memory.probability() and snapshot['active_bank_id'] == 0
            and snapshot['new_value_updates'] == 0, 'new model snapshot contains the complete observed SOURCE stream without value updates')
        require(training['raw_tiles'] == RAW and training['chunks'] == self.training_rows
            and training['before_stream'] == self.before and training['after_stream'] == self.state
            and training['memory_event_count'] == len(self.training_events)
            and all(Counter(training['counts'][kind]) == self.train_counts[kind] for kind in self.train_counts),
            'model acquisition ledger counts all actual new blocks environment and planning')
        require(Counter({key:value for key,value in training['memory_counts'].items() if key != 'predict_calls'})
            == self.memory.counts-self.warm_counts and training['memory_counts']['predict_calls'] == self.training_rows+1,
            'actor online probability is predicted once per actual chunk and once at its final boundary')
        self.snapshot, self.training = snapshot, training


def read_canonical(document):
    worlds = {}; rows_read = 0
    for parent in document['parent_receipts']:
        ids = list(range(parent['parent'], 64, 4))
        require(parent['lifecycle_ids'] == ids, 'all new lives retain their four frozen SOURCE parents')
        path = Path(parent['trace_file']); require(path.stat().st_size == parent['trace_bytes'], 'new canonical tape physical byte inventory')
        states = {(life, stage):StageWorld(life, stage) for life in ids for stage in STAGES}
        with gzip.open(path, 'rt') as stream:
            for line in stream:
                row = json.loads(line); rows_read += 1; key = row['lifecycle'], row['phase']
                require(key in states and row['parent'] == parent['parent'], 'actual new canonical parent and life membership')
                world = states[key]
                if row['phase'] != 'A1':
                    previous = states[key[0], STAGES[STAGES.index(key[1])-1]]
                    require(previous.detection is not None and (not previous.detection['route']['created'] or previous.snapshot is not None),
                        'a new stage starts only after the previous detector or created model acquisition closes')
                method = {'WARMUP':world.warmup, 'DETECTION_SNAPSHOT':world.detect,
                    'TRAIN':world.train, 'ACQUISITION_SNAPSHOT':world.checkpoint}.get(row['kind'])
                require(method is not None, 'canonical tape contains only actual detector and optional new cohort records')
                method(row)
        for key, world in states.items():
            require(world.detection is not None and bool(world.snapshot) == world.detection['route']['created'],
                'every stage has paid detection and exactly newly created contexts have closed model cohorts')
            worlds[key] = world
    require(set(worlds) == {(life, stage) for life in range(64) for stage in STAGES}, 'all 192 new stage detectors without inherited training facts')
    return worlds, rows_read


def check_detection_route(route, belief, prototypes):
    statistics = observed_statistics(belief['memory']); scores = route_scores(statistics, prototypes)
    equal_tree(route['statistics'], statistics, 'routing sees only the completed current warmup raw counts')
    equal_tree(route['scores'], scores, 'independent Beta(1,1) same-versus-disjoint context evidence before model acquisition')
    best = max(scores, key=lambda row:(row['log_bayes_factor'], -row['context_id'])) if scores else None
    created = best is None or best['log_bayes_factor'] < 0.
    context = len(prototypes) if created else best['context_id']
    require(route['context_id'] == context and route['created'] == created,
        'actual nonnegative best evidence reuses its context and negative evidence creates a paid new bank')
    before = None if created else dict(prototypes[context])
    require(route['prototype_before'] == before, 'context evidence uses its prior warmup prototype')
    after = dict(context_id=context, observations=statistics['observations'], fours=statistics['fours'], visits=1)
    if before is not None:
        after.update(observations=before['observations']+statistics['observations'],
            fours=before['fours']+statistics['fours'], visits=before['visits']+1)
    require(route['prototype_after'] == after, 'only the current paid warmup is committed to a prototype once')
    if created:
        prototypes.append(after)
    else:
        prototypes[context] = after
    return context, created


def check_probe_route(route, belief, prototypes):
    statistics = observed_statistics(belief['memory']); scores = route_scores(statistics, prototypes)
    equal_tree(route['statistics'], statistics, 'retention probe uses the first task detector warmup without new data')
    equal_tree(route['scores'], scores, 'retention probe scores all current prototypes without modifying them')
    best = max(scores, key=lambda row:(row['log_bayes_factor'], -row['context_id']))
    require(route['kind'] == 'READ_ONLY_FIRST_DETECTOR' and route['context_id'] == best['context_id'],
        'readonly retention selection preserves the independently calculated highest-evidence context')
    return best['context_id']


def check_acquisition(row, world):
    acquisition = row['acquisition']; warm = acquisition['warmup']; created = row['context_route']['created']
    require(row['detector_belief'] == world.detection['detector_belief'] and row['context_route'] == world.detection['route'],
        'receipt detector and routing evidence precede every actual training row')
    require(warm['game_summaries'] == world.warm_games and warm['raw_tiles'] == world.warm_raw
        and warm['memory_events'] == world.warm_events and warm['final_memory'] == world.warm_final,
        'all original SOURCE warmup games and observed ranks remain in the detector receipt')
    require(Counter(warm['environment_counts']) == world.warm_environment and Counter(warm['direct_counts']) == world.warm_direct
        and Counter(warm['memory_counts']) == world.warm_counts, 'paid detector environment DIRECT and observed memory work')
    require(acquisition['new_value_updates'] == acquisition['new_evaluation_games'] == 0
        and acquisition['physical_acquisitions'] == int(created), 'only actually created contexts acquire frozen SOURCE cohorts')
    reconstruction = acquisition['reconstruction']
    require(Counter(reconstruction['counts']) == world.processing and reconstruction['chunks'] == world.training_rows,
        'all actual warmup and optional cohort reconstruction work is counted')
    expected_memory = Counter(world.memory.counts); expected_memory['predict_calls'] = world.training_rows+2 if created else 1
    require(Counter(reconstruction['memory_counts']) == expected_memory, 'detector and optional chunk/snapshot reconstruction probabilities are counted once')
    if not created:
        require(row['dataset'] is row['fit_snapshot'] is acquisition['training'] is acquisition['snapshot'] is None
            and not acquisition['native_setup_counts'] and acquisition['native_setup_seconds'] == 0.
            and world.state is None, 'context reuse has no model cohort native actor allocation or fitting dataset')
        return 0
    dataset = row['dataset']
    require(acquisition['snapshot'] == world.snapshot and acquisition['training'] == world.training,
        'created context closes its exact new all-raw acquisition')
    n = check_stage_split(dataset, world.games, world.scores, world.game_memories, world.warm_raw, world.training, world.stage)
    require(learned(dataset['actor_memory_'+world.stage+'_end']) == world.memory.learned(), 'complete actor belief includes the paid unfinished acquisition tail')
    for kind in ('environment_counts', 'direct_counts', 'memory_counts'):
        require(dataset['costs']['warmup_'+kind] == warm[kind], 'warmup costs enter new model reconstruction')
    require(dataset['costs']['processing_counts'] == reconstruction['counts']
        and dataset['costs']['processing_memory_counts'] == reconstruction['memory_counts']
        and dataset['costs']['reconstructed_chunks'] == reconstruction['chunks']
        and dataset['costs']['processing_cpu_seconds'] == reconstruction['cpu_seconds'], 'model retains actual reconstruction costs and complete original facts')
    check_belief(row['fit_snapshot'], dataset)
    return n


def check_bank_setup(setup):
    require(set(setup) == set(LEARNERS), 'each actual new context has the same MC and LOCAL bank allocation structure')
    mc, local = setup['CONTEXT_MC'], setup['CONTEXT_LOCAL']; check_new_head(local)
    counts = mc['setup_counts']; size = counts['source_parameters_copied']
    require(not mc['source_weights_shared'] and counts['source_weight_bytes_copied'] == 8*size
        and counts['allocated_weight_parameters'] == size and counts['allocated_weight_bytes'] == mc['private_weight_bytes'] == 8*size
        and size == local['setup_counts']['source_parameters_copied'], 'scalar MC copies the same original SOURCE prior once per created bank')


def check_evaluation(value, life, task, belief, arm):
    games, counts = value['game_summaries'], value['counts']
    require(value['estimated_p_four'] == belief['estimated_p_four'] and value['static_evaluation_valid'],
        'all three algorithms retain the first observed task belief and static parameters')
    require(len(games) == 32 and [game['seed'] for game in games] == [evaluation_seed(life, task, i) for i in range(32)],
        'all checkpoint arms have fresh same-task paired V308 evaluation seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'actual whole-game evaluation horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and max(game['final_board']) < 11, 'evaluation cannot fabricate an early cutoff or hide a goal')
            bonus = 0.
        else:
            terminal(game['final_board'], game['status']); bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'new whole-game utility includes the original natural terminal bonus')
    steps, wins = sum(game['steps'] for game in games), sum(game['status'] == 'WON' for game in games)
    environment = dict(sampled_transitions=steps, post_action_spawns=steps, initial_spawns=64,
        raw_tile_productions=steps+64, environment_random_draws=2*(steps+64), ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+32, ground_status_internal_swipe_calls=4*(steps+32-wins),
        ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(counts['environment']) == Counter(environment), 'all new evaluation initial and terminal tile production is paid')
    planning_counts(counts['planning'], steps)
    if arm == 'CONTEXT_LOCAL':
        check_representation(value['representation_counts'], 'LOCAL_RISK', counts['planning'].get('value_predictions', 0))
    else:
        require(not value['representation_counts'] and not value['setup_counts'], 'SOURCE and matched scalar MC use no split-risk representation')
    return dict(games=32, mean_game_utility=mean(game['utility'] for game in games), wins=wins,
        losses=sum(game['status'] == 'LOST' for game in games), cutoffs=sum(game['status'] == 'CUTOFF' for game in games),
        cutoff_episodes=[i for i, game in enumerate(games) if game['status'] == 'CUTOFF'], steps=steps)


def check_router_counts(life):
    observations = [life['stages'][stage]['context_route'] for stage in STAGES]
    probes = [life['stages'][stage]['evaluation_routes'][task] for stage, task in (('B', 'A'), ('A2', 'B'))]
    routes = observations+probes
    modules = sum(len(life['stages'][stage]['detector_belief']['memory']['modules']) for stage in STAGES)
    modules += sum(len(life['task_detectors'][task]['memory']['modules']) for task in ('A', 'B'))
    candidates = sum(len(route['scores']) for route in routes)
    expected = dict(statistics_module_visits=modules, statistics_parameter_reads=2*modules,
        statistics_pending_reads=2*len(routes), statistics_extractions=len(routes),
        log_beta_evaluations=3*candidates, lgamma_evaluations=9*candidates,
        candidate_scores=candidates, score_comparisons=sum(max(0, len(route['scores'])-1) for route in routes),
        context_creations=len(life['context_bank']['banks']), observe_calls=3, prototype_commits=3, select_calls=2)
    require(Counter(life['context_bank']['counts']) == Counter(expected), 'all three detector commits and two readonly retention classifications are paid')


def check_lifecycle(life, worlds):
    require(set(life['stages']) == set(STAGES) and set(life['evaluation_beliefs']) == set(life['task_detectors']) == {'A', 'B'},
        'all three new stages and both first-encounter task beliefs remain present')
    prototypes = []; updates = {arm:[] for arm in LEARNERS}; first_beliefs = {}; detectors = {}; cells = {}; processed = Counter(); cutoffs = 0
    repeated = {}
    for stage in STAGES:
        row = life['stages'][stage]; task = 'B' if stage == 'B' else 'A'; world = worlds[life['lifecycle'], stage]
        context, created = check_detection_route(row['context_route'], row['detector_belief'], prototypes)
        if created:
            for arm in LEARNERS:
                updates[arm].append(0)
        n = check_acquisition(row, world)
        if task not in first_beliefs:
            first_beliefs[task] = row['fit_snapshot'] if created else row['detector_belief']; detectors[task] = row['detector_belief']
        require(row['context_updates_before'] == {arm:{str(i):value for i,value in enumerate(values)} for arm,values in updates.items()},
            'all matched bank update histories continue before the actual stage decision')
        tasks = ('A',) if stage == 'A1' else ('A', 'B')
        require(set(row['arms']) == set(ARMS) and set(row['evaluation_routes']) == set(tasks), 'same three algorithms and five actual checkpoint task cells')
        samples = sum(game['steps']-(game['status'] == 'WON') for game in world.games[:n]) if created else 0
        for evaluated_task in tasks:
            route = row['evaluation_routes'][evaluated_task]
            if evaluated_task == task:
                require(route == dict(kind='ACTUAL_STAGE_ROUTE', context_id=context), 'current-task utility uses the actual detector context including A2 misrouting or creation')
            else:
                check_probe_route(route, detectors[evaluated_task], prototypes)
            cells[stage+'_'+evaluated_task] = dict(arms={})
        for arm in ARMS:
            value = row['arms'][arm]; fit = value['fit']; count = samples if created and arm != 'SOURCE' else 0
            before = 0 if arm == 'SOURCE' else updates[arm][context]
            require(value['parameters_retained'] and value['processed_training_samples'] == fit['trained_afterstates'] == count
                and value['head_updates_before'] == before and value['head_updates_after'] == before+count,
                'only new contexts fit once and both matched learners process exactly the same factual states')
            if count:
                if arm == 'CONTEXT_MC':
                    check_normalized_fit(fit, world.games[:n], row['dataset'], world.scores, 'EPISODE_MEAN_MC')
                else:
                    check_local_fit(fit, row['arms']['CONTEXT_MC']['fit'], row['dataset'], 'A1')
            else:
                require(fit['method'] == 'NONE' and not fit['learning_counts'] and not fit['target_counts'], 'SOURCE and existing context banks receive no refit')
            if arm != 'SOURCE':
                updates[arm][context] += count
            processed[arm] += count
            require(set(value['evaluations']) == set(tasks), 'all algorithms retain all actual checkpoint evaluations')
            for evaluated_task in tasks:
                evaluation = value['evaluations'][evaluated_task]
                selected = row['evaluation_routes'][evaluated_task]['context_id']
                record = check_evaluation(evaluation, life['lifecycle'], evaluated_task, first_beliefs[evaluated_task], arm)
                cells[stage+'_'+evaluated_task]['arms'][arm] = record; cutoffs += record['cutoffs']
                identity = dict(game_summaries=evaluation['game_summaries'], counts=evaluation['counts'], representation_counts=evaluation['representation_counts'])
                key = (arm, evaluated_task, -1 if arm == 'SOURCE' else selected,
                    0 if arm == 'SOURCE' else updates[arm][selected])
                if key in repeated:
                    equal_tree(identity, repeated[key], 'an unchanged bank repeats exact paired fixed-belief terminal outcomes')
                repeated[key] = identity
        require(row['context_updates_after'] == {arm:{str(i):value for i,value in enumerate(values)} for arm,values in updates.items()},
            'inactive banks and existing selected banks retain all parameters without additional fits')
    require(life['evaluation_beliefs'] == first_beliefs and life['task_detectors'] == detectors,
        'first actual FIT or reused warmup task beliefs exclude subsequent tasks and heldout data')
    banks = life['context_bank']['banks']
    require(len(banks) == len(prototypes) and [bank['context_id'] for bank in banks] == list(range(len(prototypes))),
        'all actually created contexts remain retained without forcing a two-bank answer')
    private = Counter()
    for bank, prototype in zip(banks, prototypes):
        require({key:bank[key] for key in prototype} == prototype
            and bank['head_updates'] == {arm:updates[arm][bank['context_id']] for arm in LEARNERS}, 'final banks retain warmup-only prototypes and one matched first adaptation')
        check_bank_setup(bank['head_setup'])
        for arm in LEARNERS:
            private[arm] += bank['head_setup'][arm]['private_weight_bytes']
    require(life['context_bank']['private_weight_bytes_per_arm'] == dict(private), 'all actually retained scalar and dual-head bank capacity is paid')
    check_router_counts(life)
    return dict(lifecycle=life['lifecycle'], parent=life['parent'], cells=cells), processed, cutoffs


def check_support(summary, cutoffs):
    complete = cutoffs == 0
    primary = complete and summary['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95'][0] > 0.
    net = complete and summary['final_ab_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95'][0] > 0.
    tasks = {task:complete and summary['cells']['A2_'+task]['paired_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95'][0] > 0.
        for task in ('A', 'B')}
    retention = {}
    for name in ('A_after_B', 'B_after_A2', 'A_final_vs_A1'):
        lower, upper = summary['checkpoint_contrasts'][name]['CONTEXT_LOCAL']['ci95']
        retention[name] = ('INCOMPLETE_GAME_ENDPOINTS' if not complete else 'SUPPORTED_NONDECREASE' if lower >= 0.
            else 'SUPPORTED_LOSS' if upper < 0. else 'UNRESOLVED')
    preserved = all(value == 'SUPPORTED_NONDECREASE' for value in retention.values())
    require(summary['complete_game_endpoints'] == complete and summary['primary_local_over_mc_supported'] == primary
        and summary['primary_local_over_mc_status'] == ('SUPPORTED_' if primary else 'NOT_SUPPORTED_')+INTERVAL_SCOPE,
        'LOCAL contribution requires a positive matched-MC interval and complete game endpoints')
    require(summary['final_net_gain_supported'] == net and summary['final_task_gain_supported'] == tasks
        and summary['final_dual_task_gain_supported'] == all(tasks.values()), 'net average and individual final task gains remain separate')
    require(summary['retention_status'] == retention and summary['retention_supported'] == preserved
        and summary['retained_gain_supported'] == (primary and net and preserved),
        'retained gain requires matched-MC contribution net SOURCE gain and all three zero-margin retention comparisons')


def check_result_summary(summary, records, cutoffs):
    equal_tree(summary['by_lifecycle'], records, 'all new three-arm five-cell whole-game endpoints')
    require(summary['primary_contrast'] == PRIMARY and summary['bootstrap_draws'] == 20000 and summary['bootstrap_seed'] == 30800001
        and summary['estimator'] == 'EQUAL_FINAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES', 'frozen new-sequence final equal-task contribution primary')
    require(set(summary['cells']) == set(CELLS), 'all five actual detector and retention probe cells remain present')
    for cell in CELLS:
        value = summary['cells'][cell]; stage, task = cell.split('_')
        require(value['stage'] == stage and value['task'] == task, 'new checkpoint task identity')
        require(set(value['paired_contrasts']) == {a+'_minus_'+b for a,b in PAIRS}, 'matched MC and original SOURCE comparisons remain complete')
        for arm in ARMS:
            rows = [record['cells'][cell]['arms'][arm] for record in records]
            expected = dict(mean_game_utility=mean(row['mean_game_utility'] for row in rows),
                **{key:sum(row[key] for row in rows) for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')})
            equal_tree(value['arms'][arm], expected, 'equal whole-game then lifecycle task utility '+cell+' '+arm)
        for left, right in PAIRS:
            check_contrast(value['paired_contrasts'][left+'_minus_'+right],
                [a-b for a,b in zip(endpoint(records, cell, left), endpoint(records, cell, right))])
    require(set(summary['final_ab_contrasts']) == set(summary['current_task_sequence_contrasts']) == {a+'_minus_'+b for a,b in PAIRS},
        'all registered final and current-sequence contrasts remain separate')
    for left, right in PAIRS:
        differences = [{cell:record['cells'][cell]['arms'][left]['mean_game_utility']-record['cells'][cell]['arms'][right]['mean_game_utility'] for cell in CELLS}
            for record in records]
        check_contrast(summary['final_ab_contrasts'][left+'_minus_'+right], [(row['A2_A']+row['A2_B'])/2 for row in differences])
        check_contrast(summary['current_task_sequence_contrasts'][left+'_minus_'+right], [mean(row[cell] for cell in ('A1_A', 'B_B', 'A2_A')) for row in differences])
    require(set(summary['checkpoint_contrasts']) == set(CHECKPOINTS), 'all signed retention and restoration contrasts remain present')
    for name, (after, before) in CHECKPOINTS.items():
        require(set(summary['checkpoint_contrasts'][name]) == set(ARMS), 'all algorithm retention contrasts remain present')
        for arm in ARMS:
            check_contrast(summary['checkpoint_contrasts'][name][arm], [a-b for a,b in zip(endpoint(records, after, arm), endpoint(records, before, arm))])
    for arm in ARMS:
        rows = [record['cells'][cell]['arms'][arm] for record in records for cell in CELLS]
        expected = {key:sum(row[key] for row in rows) for key in ('games', 'wins', 'losses', 'cutoffs', 'steps')}
        expected['mean_final_ab_game_utility'] = mean(mean(record['cells'][cell]['arms'][arm]['mean_game_utility'] for cell in ('A2_A', 'A2_B')) for record in records)
        expected['mean_current_task_sequence_game_utility'] = mean(mean(record['cells'][cell]['arms'][arm]['mean_game_utility'] for cell in ('A1_A', 'B_B', 'A2_A')) for record in records)
        equal_tree(summary['arms'][arm], expected, 'complete algorithm utility and natural endpoint inventory '+arm)
    check_support(summary, cutoffs)


def check_training_budget(account, inherited, lives):
    rows = [life['stages'][stage] for life in lives for stage in STAGES]
    warm = sum(row['acquisition']['warmup']['raw_tiles'] for row in rows)
    created = [row for row in rows if row['context_route']['created']]
    actor = sum(row['acquisition']['training']['raw_tiles'] for row in created)
    require(account['old_target_training_raw_reused'] == 0 and account['physical_detection_stages'] == 192
        and account['physical_acquisitions'] == len(created) and account['new_training_environment_observations'] == warm+actor
        and account['new_warmup_raw_tiles'] == warm and account['new_actor_raw_tiles'] == actor == RAW*len(created),
        'all 192 new detector warmups and exactly actually created context cohorts including tails are paid without old target facts')
    by_stage = {stage:sum(life['stages'][stage]['acquisition']['warmup']['raw_tiles']
        +(RAW if life['stages'][stage]['context_route']['created'] else 0) for life in lives) for stage in STAGES}
    require(account['new_raw_tiles_by_stage'] == by_stage, 'actual extra context creation and acquisition enter the appropriate stage budget')
    economic = inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+warm+actor
    require(account['inherited_costs_per_arm'] == dict.fromkeys(ARMS, inherited)
        and account['economic_training_raw_tiles_per_arm'] == dict.fromkeys(ARMS, economic), 'all three algorithms pay original SOURCE dynamics and the same actual new observed facts')
    return economic


def check_accounting(document, inherited):
    account = document['accounting']; lives = document['by_lifecycle']; parents = document['parent_receipts']
    economic = check_training_budget(account, inherited, lives)
    rows = [life['stages'][stage] for life in lives for stage in STAGES]; acquisitions = [row['acquisition'] for row in rows]
    trained = [row for row in rows if row['context_route']['created']]
    counts_fields = (('new_warmup_environment_counts', 'environment_counts'), ('new_warmup_direct_counts', 'direct_counts'), ('new_warmup_memory_counts', 'memory_counts'))
    for field, key in counts_fields:
        require(account[field] == sum_counts(acquisition['warmup'][key] for acquisition in acquisitions), 'actual '+field)
    require(account['new_training_environment_counts'] == sum_counts([acquisition['warmup']['environment_counts'] for acquisition in acquisitions]
        +[row['acquisition']['training']['counts']['environment'] for row in trained]), 'actual all-raw new physical training environment work')
    for kind in ('environment', 'planning', 'learning'):
        require(account['new_actor_counts'][kind] == sum_counts(row['acquisition']['training']['counts'][kind] for row in trained), 'actual SOURCE acquisition '+kind+' work')
    require(account['acquisition_native_setup_counts'] == sum_counts(acquisition['native_setup_counts'] for acquisition in acquisitions)
        and close(account['acquisition_cpu_seconds'], sum(acquisition['cpu_seconds'] for acquisition in acquisitions)), 'only actually created native acquisition actors and their complete CPU are paid')
    require(account['reconstruction_counts'] == sum_counts(acquisition['reconstruction']['counts'] for acquisition in acquisitions)
        and account['reconstruction_memory_counts'] == sum_counts(acquisition['reconstruction']['memory_counts'] for acquisition in acquisitions)
        and close(account['reconstruction_cpu_seconds'], sum(acquisition['reconstruction']['cpu_seconds'] for acquisition in acquisitions)), 'all detector and optional model reconstruction work remains paid')
    require(account['excluded_tail_raw_tiles'] == sum(row['dataset']['costs']['excluded_tail_raw_tiles'] for row in trained), 'all actual new unfinished tails remain paid without labels')
    contexts = {str(life['lifecycle']):len(life['context_bank']['banks']) for life in lives}
    require(account['total_contexts_created'] == account['physical_acquisitions'] == sum(contexts.values())
        and account['contexts_per_lifecycle'] == contexts and account['context_router_counts'] == sum_counts(life['context_bank']['counts'] for life in lives)
        and close(account['context_router_cpu_seconds'], sum(life['context_bank']['route_cpu_seconds'] for life in lives)), 'actual blind context growth detections and readonly probes retain their work')
    for arm in ARMS:
        values = [row['arms'][arm] for row in rows]; fits = [value['fit'] for value in values]
        require(account['processed_training_samples'][arm] == sum(value['processed_training_samples'] for value in values)
            and close(account['fit_cpu_seconds'][arm], sum(fit['cpu_seconds'] for fit in fits)), 'actual '+arm+' fitted samples and CPU')
        for field, key in (('fit_counts', 'learning_counts'), ('fit_target_counts', 'target_counts'), ('fit_normalization_counts', 'normalization_counts'),
            ('fit_consolidation_counts', 'consolidation_counts'), ('fit_representation_counts', 'representation_counts'), ('fit_setup_counts', 'setup_counts')):
            require(account[field][arm] == sum_counts(nonpeak(fit.get(key, {})) for fit in fits), 'actual '+arm+' '+field)
        evaluations = [evaluation for value in values for evaluation in value['evaluations'].values()]
        for kind in ('environment', 'planning'):
            require(account['evaluation_counts_per_arm'][arm][kind] == sum_counts(evaluation['counts'][kind] for evaluation in evaluations), 'actual '+arm+' new evaluation '+kind+' costs')
        require(account['evaluation_representation_counts'][arm] == sum_counts(evaluation['representation_counts'] for evaluation in evaluations)
            and close(account['evaluation_cpu_seconds_per_arm'][arm], sum(evaluation['cpu_seconds'] for evaluation in evaluations)), 'all actual '+arm+' static evaluation work')
    for arm in LEARNERS:
        weights = [life['context_bank']['private_weight_bytes_per_arm'][arm] for life in lives]
        setups = [bank['head_setup'][arm] for life in lives for bank in life['context_bank']['banks']]
        require(account['private_head_weight_bytes_created'][arm] == sum(weights) and account['peak_private_weight_bytes_per_lifecycle'][arm] == max(weights)
            and account['head_setup_counts'][arm] == sum_counts(setup['setup_counts'] for setup in setups)
            and close(account['head_setup_cpu_seconds'][arm], sum(setup['setup_cpu_seconds'] for setup in setups)), 'actual '+arm+' private SOURCE-initialized context capacity and allocation CPU')
    require(account['new_evaluation_games'] == 30720 and account['new_sequence_compute_closed'], 'all actual new five-cell evaluation games and complete new-sequence compute inventory')
    require([parent['parent'] for parent in parents] == list(range(4)) and all(parent['source_setup']['checkpoint_loads'] == 1
        and parent['source_setup']['new_leaf_updates'] == 0 for parent in parents), 'four original SOURCE checkpoint loads with no new source fitting')
    require(account['canonical_trace_bytes'] == sum(parent['trace_bytes'] for parent in parents), 'all actual new canonical tape storage is retained')
    require(close(account['worker_cpu_seconds'], sum(parent['cpu_seconds'] for parent in parents))
        and close(account['compiler_cpu_seconds'], sum(parent['compiler_cpu_seconds'] for parent in parents)), 'new worker and compiler CPU is counted within its correct scope')
    return economic


def audit(directory):
    directory = Path(directory); document = json_file(directory/'summary.json'); settings = document['settings']
    require(document['schema'] == 'acfqp.first_adapt.v308' and document['status'] == 'EXPERIMENT_COMPLETE'
        and document['scientific_gate'] == 'NOT_A_FORMAL_GATE', 'complete new-sequence first-adaptation terminal document')
    equal_tree(settings, json_file(directory/'configuration.json'), 'unchanged frozen V308 complete algorithm configuration')
    expected = dict(source_inputs='ORIGINAL_SOURCE_PROVENANCE_AND_COSTS_ONLY_NO_OLD_TARGET_FACTS', lifecycles=list(range(64)), parents=4,
        arms=list(ARMS), stages=list(STAGES), tasks=dict(A1='A', B='B', A2='A'), true_probabilities=dict(A=.1, B=.5),
        observations='NEW_SOURCE_WARMUP_EACH_STAGE_NEW_SOURCE_COHORT_ONLY_IF_OBSERVED_CONTEXT_CREATED',
        router='UNCHANGED_V305_BETA_1_1_SAME_VERSUS_DISJOINT_LOG_BAYES_FACTOR', log_bayes_factor_threshold=0.,
        context_statistics='CURRENT_STAGE_WARMUP_RAW_SPAWNS_ONLY_COMMITTED_ONCE_BEFORE_TRAINING',
        minimum_detection_raw=256, raw_budget_per_created_context=RAW, fit_fraction=.8, alpha=.0025,
        query=dict(reward_weight=1., failure_penalty=4., goal_bonus=4.), context_initialization='ORIGINAL_SOURCE_FOR_EVERY_NEW_BANK',
        adaptation='ONE_FIT_ONLY_ON_FIRST_OBSERVED_CONTEXT_CREATION_REUSE_WITHOUT_REFIT', context_baseline='MC_USES_IDENTICAL_ROUTING_BANKS_AND_FACTUAL_FIT_SAMPLES',
        representations=dict(CONTEXT_MC='UNCHANGED_V290_EPISODE_MEAN_MC', CONTEXT_LOCAL='UNCHANGED_V301_LOCAL_REWARD_AND_SIGMOID_RISK'),
        seed_warmup={stage:308100000000+i*100000 for i,stage in enumerate(STAGES)}, seed_training={stage:308200000000+i*100000 for i,stage in enumerate(STAGES)},
        seed_evaluation=308900000000, evaluation_task_offset=100000, evaluation_games_per_cell=32, evaluation_cells=list(CELLS), max_steps=8192,
        planning_probability='FIRST_ENCOUNTER_OBSERVED_TASK_FIT_BELIEF_OR_DETECTOR_IF_REUSED_FIXED_ACROSS_ARMS_AND_CHECKPOINTS',
        evaluation_routing='ACTUAL_STAGE_ROUTE_FOR_CURRENT_TASK_READ_ONLY_FIRST_DETECTOR_ROUTING_FOR_RETENTION_PROBES', primary=PRIMARY,
        net_gain='CONTEXT_LOCAL_minus_SOURCE_FINAL_AB', retention='ZERO_MARGIN_CI_LOWER_NONNEGATIVE_FOR_A_AFTER_B_B_AFTER_A2_AND_FINAL_A_VS_A1',
        bootstrap_draws=20000, bootstrap_seed=30800001, interval_scope=INTERVAL_SCOPE, new_evaluation_games=30720, old_target_training_raw_reused=0,
        stop_rule='RETAIN_MISROUTES_EXTRA_CONTEXTS_CUTOFFS_AND_NEGATIVE_RESULTS_WITHOUT_ROUTER_OR_FIT_TUNING')
    for key, value in expected.items():
        require(settings[key] == value, 'registered frozen first-adaptation '+key)
    original = json_file(settings['source_summary'])
    require(document['source_provenance'] == original['source_provenance'] and len(document['source_provenance']['parents']) == 4,
        'only the four original SOURCE parent identities and inherited source costs carry into the new experiment')
    old_costs = original['accounting']['inherited_costs_per_arm']['SOURCE']
    inherited = {key:old_costs[key] for key in ('source_training_raw_tiles', 'source_training_games', 'source_training_environment_counts',
        'source_training_seconds', 'dynamics_raw_tiles', 'dynamics_costs')}
    lives = document['by_lifecycle']
    require([life['lifecycle'] for life in lives] == list(range(64)) and all(life['parent'] == life['lifecycle']%4 for life in lives),
        'all 64 new training and evaluation lifecycles under their original four frozen SOURCE parents')
    worlds, rows_read = read_canonical(document)
    records = []; processed = Counter(); cutoffs = 0
    for life in lives:
        record, counts, value = check_lifecycle(life, worlds); records.append(record); processed.update(counts); cutoffs += value
    check_result_summary(document['summary'], records, cutoffs); economic = check_accounting(document, inherited)
    summary = document['summary']; account = document['accounting']
    return dict(status='PASS', independent_valid=True, lifecycles=64, fixed_source_parents=4, canonical_rows=rows_read,
        physical_detection_stages=192, physical_acquisitions=account['physical_acquisitions'], total_contexts_created=account['total_contexts_created'],
        new_training_environment_observations=account['new_training_environment_observations'], old_target_training_raw_reused=0,
        processed_training_samples=dict(processed), new_evaluation_games=30720, evaluation_cutoffs=cutoffs,
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS, economic), primary_local_over_mc_supported=summary['primary_local_over_mc_supported'],
        final_net_gain_supported=summary['final_net_gain_supported'], final_task_gain_supported=summary['final_task_gain_supported'],
        retention_status=summary['retention_status'], retained_gain_supported=summary['retained_gain_supported'],
        primary_utility=summary['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC'], new_sequence_compute_closed=True,
        method='One independent literal physical reconstruction of all new warmup and optional model cohort tapes, '
            'online LIBRARY raw-rank updates and complete natural game labels; warmup-only independent context evidence '
            'and prototype commits; matched MC/LOCAL original-SOURCE first adaptations, actual return routing, frozen '
            'reuse, full score suffix labels, paired whole-game endpoint gains and retention, and actual new costs.',
        limitations='Original SOURCE parents are reused, so intervals remain conditional on four parents. Evaluation '
            'actions, experimental weights and bootstrap draws are not recomputed. Saved intervals are checked for '
            'scope and feasible range. Matched facts and contexts do not equalize private capacity, parameter writes '
            'or compute. Complete new-sequence cost accounting does not measure all historical SOURCE CPU. Continued '
            'improvement within a known context and general strategic learning are not established by this experiment.', errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    directory = parser.parse_args().output
    try:
        result = audit(directory)
    except ValueError as error:
        result = dict(status='FAIL', independent_valid=False, errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False)); raise SystemExit(not result['independent_valid'])


if __name__ == '__main__':
    main()
