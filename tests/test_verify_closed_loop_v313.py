"""Finite actual-kernel regressions for V313 actor/head ownership and paid facts."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_closed_loop_v313 as audit

from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_split_risk_v301 import QUERY, SplitLeaf
from acfqp.science.native_linear_win_v311 import LinearWinLeaf
from acfqp.science.native_policy_stream_v313 import NativePolicyStream
from acfqp.science.closed_loop_versions_v313 import save_version, snapshot_weights
from acfqp.science.native_replay_fit_v307 import fit_masked_split
from acfqp.science.native_masked_linear_v313 import fit_masked_linear
from acfqp.science import closed_loop_run_v313 as run
from acfqp.science.natural_model_revision_v281 import load_leaf
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory

BUILD = Path(__file__).resolve().parents[1]/'reports/closed_loop_v313/runtime/tests/auditor'


@pytest.fixture(scope='module')
def actors():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    template = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    local, linear = SplitLeaf(template, 'LOCAL_RISK', BUILD), LinearWinLeaf(template, BUILD)
    local.risk_weights[:] = np.random.default_rng(313001).normal(0., .4, local.risk_weights.shape)
    linear.win_weights[:] = np.random.default_rng(313002).normal(.015625, .05, linear.win_weights.shape)
    local.freeze(); linear.freeze()
    return source, local, linear


def second(leaf):
    return leaf.risk_weights if leaf.kind == 'LOCAL_RISK' else leaf.win_weights


@pytest.fixture(scope='module')
def physical(actors):
    _, local, _ = actors
    seed = audit.post_seed(0, 'A', 1)
    stream = NativePolicyStream(local, seed, BUILD)
    try:
        receipt = stream.advance(.37, .1, 64)
        draws = stream.common_draws(seed, 1000)
    finally:
        stream.close()
    row = dict(receipt, counts=deepcopy(receipt['counts']), bank_update_counts={}, td_examples=[],
        actor_head_updates=0, actor_version={'arm': 'CLOSED_LOCAL', 'version': 0, 'context_id': 0},
        model_p_four=.37)
    return row, draws


def world(row):
    identity = {key: row[key] for key in ('actor_head_updates', 'actor_version', 'model_p_four')}
    return audit.BatchWorld(row['start']['stream_seed'], 64, .1, identity, 'LOCAL_RISK', radix=4)


def probes(row, local):
    stream = world(row); stream.train(row)
    def saved(probe):
        return dict(episode=probe['episode'], step=probe['step'], raw_index=probe['raw_index'],
            preboard=probe['board'], chosen_action=probe['action'], h2_value=probe['value'],
            action_values=row['action_records'][probe['index']]['action_values'])
    return stream, dict(first=[saved(p) for p in stream.first_probes], last=[saved(p) for p in stream.last_probes])


def test_all_fresh_seed_coordinates_are_distinct_and_disjoint():
    post = {audit.post_seed(life, task, round_index) for life in range(16) for task in audit.TASKS for round_index in (1, 2)}
    assert len(post) == 64
    initial = {313200000000+life*10000000+task*100000 for life in range(16) for task in (0, 1)}
    evaluation = {audit.evaluation_seed(life, task, episode) for life in range(16) for task in audit.TASKS for episode in range(32)}
    assert not (post & initial or post & evaluation)


def test_independent_mt19937_64_matches_actual_native_cell_rank_uniforms(physical):
    row, actual = physical
    rng = audit.TileRandom(row['start']['stream_seed'])
    assert np.array_equal(np.array([[rng.random(), rng.random()] for _ in range(1000)]), actual)


@pytest.mark.parametrize('index', (1, 2))
def test_literal_full_h2_uses_actual_both_heads_and_all_candidate_values(actors, index):
    leaf = actors[index]
    board = [1, 2, 0, 0, 2, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
    expected = leaf.choose(board, .37)
    actual = audit.literal_choose(board, leaf.reward_weights.reshape(-1), second(leaf).reshape(-1),
        leaf.kind, .37, radix=4)
    assert expected['action'] == actual['action']
    audit.equal_tree(expected['action_values'], actual['action_values'], 'literal candidate values')


def test_complete_finite_raw_batch_reconstructs_actual_boundary_and_head_probes(physical, actors):
    row, _ = physical; leaf = actors[1]
    rebuilt, stored = probes(row, leaf)
    head = audit.HeadVersions(leaf.reward_weights, 'fresh-source.npz', {}, leaf.kind)
    head.terminal[:] = second(leaf).reshape(-1)
    assert rebuilt.check_probes(head, stored) == 16
    assert rebuilt.state == row['end']


@pytest.mark.parametrize('field', ('cell', 'rank'))
def test_legal_but_wrong_seeded_spawn_is_rejected(physical, field):
    row, _ = physical; changed = deepcopy(row)
    changed['raw_spawns'][0][field] = 1-changed['raw_spawns'][0][field] if field == 'cell' else 3-changed['raw_spawns'][0][field]
    with pytest.raises(ValueError, match='cell/rank draw'):
        world(row).train(changed)


def test_stale_or_wrong_context_actor_version_is_rejected(physical):
    row, _ = physical; changed = deepcopy(row); changed['actor_version']['context_id'] = 1
    with pytest.raises(ValueError, match='frozen head version'):
        world(row).train(changed)


def test_intra_batch_parameter_update_is_rejected(physical):
    row, _ = physical; changed = deepcopy(row); changed['counts']['learning'] = {'td_updates': 1}
    with pytest.raises(ValueError, match='batch actor is frozen'):
        world(row).train(changed)


def test_scalar_only_actor_with_wrong_terminal_parameters_fails_real_action_probe(physical, actors):
    row, _ = physical; leaf = actors[1]
    rebuilt, stored = probes(row, leaf)
    wrong = audit.HeadVersions(leaf.reward_weights, 'fresh-source.npz', {}, leaf.kind)
    with pytest.raises(ValueError, match='frozen actor weights|literal candidate'):
        rebuilt.check_probes(wrong, stored)


def test_saved_probe_cannot_substitute_a_different_physical_board(physical, actors):
    row, _ = physical; leaf = actors[1]
    rebuilt, stored = probes(row, leaf); stored['last'][0]['preboard'] = [0]*16
    head = audit.HeadVersions(leaf.reward_weights, 'fresh-source.npz', {}, leaf.kind)
    with pytest.raises(ValueError, match='actual tape boundaries'):
        rebuilt.check_probes(head, stored)


def test_sparse_versions_reassemble_source_initial_and_actual_zero_reversion(tmp_path, actors):
    source, local, _ = actors
    local.reward_weights.flags.writeable = True; local.risk_weights.flags.writeable = True
    original_reward, original_risk = local.reward_weights.copy(), local.risk_weights.copy()
    identity = dict(lifecycle=0, parent=0, context_id=0, arm='CLOSED_LOCAL')
    provenance = dict(parent=0, checkpoint='fresh-source.npz')
    try:
        local.reward_weights[0, 0] += 1.
        v0 = save_version(local, provenance, 0, 0, 'FIRST_LOCAL', 0, tmp_path/'v0.npz')
        previous = snapshot_weights(local)
        local.reward_weights[0, 0] = source.weights[0, 0]
        local.risk_weights[0, 0] = 0.
        v1 = save_version(local, provenance, 0, 0, 'CLOSED_LOCAL', 1, tmp_path/'v1.npz', base=v0, previous=previous)
        rebuilt = audit.HeadVersions(source.weights, provenance['checkpoint'], identity, local.kind)
        rebuilt.apply(v0); rebuilt.apply(v1)
        assert np.array_equal(rebuilt.reward, local.reward_weights.reshape(-1))
        assert np.array_equal(rebuilt.terminal, local.risk_weights.reshape(-1))
        assert rebuilt.changed_parameters == 2
        stale = dict(v1, base_file=None)
        with pytest.raises(ValueError, match='sequential previous-weight base'):
            audit.HeadVersions(source.weights, provenance['checkpoint'], identity, local.kind).apply(stale)
    finally:
        local.reward_weights[:] = original_reward; local.risk_weights[:] = original_risk
        local.freeze()


def test_prefix_quota_keeps_winning_skip_and_midgame_full_label_suffix():
    games = [dict(steps=4, status='WON', score=128), dict(steps=5, status='LOST', score=256),
        dict(steps=3, status='LOST', score=64)]
    selected = audit.prefix_selection(games, 2, 5)
    assert selected['eligible_samples'] == 8 and selected['selected_samples'] == 5
    assert selected['last_selected_step'] == 5
    assert selected['selection_mask'] == [True, True, True, False, True, True, False, False, False, False, False, False]
    assert games[1]['steps'] == 5 and games[1]['score'] == 256 and games[1]['status'] == 'LOST'


def test_direct_and_h2_cannot_reference_different_actual_heads():
    direct = dict(head_version=dict(version=2, file='own_v2.npz'), estimated_p_four=.37)
    audit.check_same_evaluation_head(direct, dict(direct))
    with pytest.raises(ValueError, match='same learned head'):
        audit.check_same_evaluation_head(direct, dict(direct, head_version=dict(version=2, file='other_v2.npz')))


def test_source_full_cpu_is_carried_once_and_not_added_to_contained_setup_twice():
    source = dict(worker_cpu_seconds=10., compiler_cpu_seconds=1., coordinator_cpu_seconds=2.,
        full_source_cpu_seconds=13., wall_seconds=6., includes_source_setup_training_checkpoint_save=True)
    account = dict(worker_cpu_seconds=4., compiler_cpu_seconds=1., coordinator_cpu_seconds=2.,
        wall_seconds=4., source_and_target_cpu_seconds=20., source_and_target_wall_seconds=10.)
    audit.check_source_target_compute(account, source)
    account['source_and_target_cpu_seconds'] += 1.
    with pytest.raises(ValueError):
        audit.check_source_target_compute(account, source)


@pytest.mark.parametrize('kind', ('LOCAL_RISK', 'LINEAR_WIN2'))
def test_actual_masked_fit_keeps_full_natural_game_targets_at_midgame_quota(actors, kind):
    source, collector, _ = actors
    seed = audit.post_seed(0, 'A', 2)
    native = NativePolicyStream(collector, seed, BUILD)
    try:
        receipt = native.advance(.37, .1, 256)
    finally:
        native.close()
    row = dict(receipt, bank_update_counts={}, td_examples=[], actor_head_updates=0,
        actor_version={'arm': 'CLOSED_LOCAL', 'version': 1, 'context_id': 0}, model_p_four=.37)
    identity = {key: row[key] for key in ('actor_head_updates', 'actor_version', 'model_p_four')}
    factual = audit.BatchWorld(seed, 256, .1, identity, collector.kind, radix=4)
    factual.train(row)
    n = 4*len(factual.games)//5
    assert n > 0 and factual.games[0]['status'] == 'WON'
    end = factual.ends[-1]; fit_end = factual.ends[n-1]
    boards = [audit.swipe(record['preboard'], action)[0] for record, action in zip(receipt['action_records'], receipt['actions'])]
    dataset = dict(afterstates=np.asarray(boards[:end], dtype=np.int32), rewards=np.asarray(receipt['scores'][:end], dtype=np.float64)/2048.,
        ends=np.asarray(factual.ends, dtype=np.int64), terminal_codes=np.asarray([1 if game['status']=='WON' else -1 for game in factual.games], dtype=np.int32),
        fit_game_count=n, fit_step_end=fit_end)
    selection = audit.prefix_selection(factual.games, n, 2)
    template = QueryTD(QueryParent(source, QUERY, QUERY, .5), 'PRIOR', BUILD)
    leaf = SplitLeaf(template, kind, BUILD) if kind == 'LOCAL_RISK' else LinearWinLeaf(template, BUILD)
    mask = np.asarray(selection['selection_mask'][:fit_end], dtype=np.int32)
    fitted = fit_masked_split(leaf, dataset, mask, BUILD) if kind == 'LOCAL_RISK' else fit_masked_linear(leaf, dataset, mask, BUILD)
    public = {key:value for key,value in selection.items() if key != 'selection_mask'}
    assert audit.check_masked_fit(fitted, factual.games, factual.scores, n, 2, public) == 2
    assert fitted['last_sample']['reward_target'] > 0.
    wrong = deepcopy(fitted)
    wrong['last_sample']['risk_target' if kind == 'LOCAL_RISK' else 'win_target'] = 0.
    with pytest.raises(ValueError, match='actual WIN residuals'):
        audit.check_masked_fit(wrong, factual.games, factual.scores, n, 2, public)


def test_frozen_driver_configuration_matches_independent_v313_contract():
    source = BUILD.parents[3]/'fresh_source_v312/source_summary.json'
    settings = json.loads(json.dumps(run.configuration(source)))
    audit.equal_tree(settings, audit.expected_configuration(source), 'V313 frozen configuration')
    changed = dict(settings, initial_raw_per_task=131172)
    with pytest.raises(ValueError, match='initial_raw_per_task'):
        audit.equal_tree(changed, audit.expected_configuration(source), 'V313 frozen configuration')


@pytest.mark.parametrize('stage', ('A0', 'B0'))
def test_actual_initial_detector_new_python_seeds_and_factual_rank_memory(stage):
    root = Path(__file__).resolve().parents[1]
    source = json.loads((root/'reports/fresh_source_v312/source_summary.json').read_text())['source_provenance']['parents'][0]
    template, _ = load_leaf(source, BUILD)
    before = dict(template.counts); memory = SpawnMemory('LIBRARY')
    seed = audit.warmup_seed(20, stage, 0); probability = audit.PROBABILITIES[stage[0]]
    game = run_episode(seed, lambda board, step: template.choose(board, QUERY)['action'], probability, 8192)
    raw = [dict(row, kind='INITIAL') for row in game['initial_spawns']]
    raw += [dict(kind='POST_ACTION', cell=row['spawned_cell'], rank=row['spawned_rank']) for row in game['steps']]
    events = []
    for spawn in raw:
        event = memory.observe(spawn['rank'])
        if event is not None:
            events.append(event)
    summary = dict(seed=seed, score=game['return_score'], status=game['status'], steps=game['steps_count'],
        utility=game['return_score']/2048.+(4. if game['status']=='WON' else -4.))
    direct = {key:value-before.get(key, 0) for key,value in template.counts.items() if value-before.get(key, 0)}
    row = dict(kind='WARMUP', lifecycle=20, parent=0, phase=stage, true_p_four=probability,
        summary=summary, raw_spawns=raw, actions=[step['action'] for step in game['steps']],
        scores=[step['score'] for step in game['steps']], final_board=game['final_board'],
        memory_events=events, counts=dict(environment=game['work'], direct=direct))
    world = audit.InitialWorld(20, stage); world.warmup(row)
    assert world.memory.obs == len(raw) and world.warm_games == [summary]
    wrong = deepcopy(row); wrong['raw_spawns'][0]['rank'] = 3-wrong['raw_spawns'][0]['rank']
    with pytest.raises(ValueError, match='cell/rank draw'):
        audit.InitialWorld(20, stage).warmup(wrong)


def accounting_document():
    root = Path(__file__).resolve().parents[1]
    source = json.loads((root/'reports/fresh_source_v312/source_summary.json').read_text())
    inherited = source['accounting']['inherited_costs_per_arm']['SOURCE']; lives = []
    def evaluation():
        return dict(game_summaries=[{} for _ in range(32)], cpu_seconds=.2, counts=dict(environment={'initial_spawns':64}))
    def version(path, index):
        return dict(file=path, saved_bytes=30, scan_parameters=20, copy_parameters=0 if index==0 else 20,
            save_cpu_seconds=.1, copy_cpu_seconds=0. if index==0 else .1)
    for life_id in range(16):
        life = dict(lifecycle=life_id, parent=life_id%4, initial={}, rounds={}, final_direct={}, private_head_weight_bytes=160)
        for task in audit.TASKS:
            life['initial'][task] = dict(acquisition=dict(warmup=dict(raw_tiles=256), training=dict(raw_tiles=audit.INITIAL_RAW)),
                dataset=dict(costs=dict(excluded_tail_raw_tiles=7)), first_fits={arm:dict(cpu_seconds=.1) for arm in ('FIRST_LOCAL','FIRST_LINEAR')},
                head_versions={arm:version(f'{life_id}/{task}/{arm}_v0',0) for arm in ('FIRST_LOCAL','FIRST_LINEAR')},
                evaluations={arm:dict(H2=evaluation()) for arm in audit.ARMS[:3]})
            life['final_direct'][task] = {arm:evaluation() for arm in audit.DIRECT_ARMS}
        for round_index in (1,2):
            life['rounds'][str(round_index)] = {}
            for task in audit.TASKS:
                names = ('SHARED_LOCAL','CLOSED_LINEAR') if round_index==1 else audit.UPDATING_ARMS
                collectors = {arm:dict(acquisition=dict(training=dict(raw_tiles=audit.POST_RAW),cpu_seconds=.2),
                    dataset=dict(costs=dict(excluded_tail_raw_tiles=9))) for arm in names}
                arms = {arm:dict(fit=dict(trained_afterstates=17,learning_counts={'td_updates':17},cpu_seconds=.3),
                    head_version=version(f'{life_id}/{task}/{arm}_v{round_index}',round_index), evaluations=dict(H2=evaluation())) for arm in audit.UPDATING_ARMS}
                life['rounds'][str(round_index)][task] = dict(collectors=collectors,arms=arms)
        lives.append(life)
    provenance = source['source_provenance']; parents = [dict(parent=p,cpu_seconds=3.,compiler_cpu_seconds=2.,trace_bytes=20,
        source_setup=dict(checkpoint_loads=1,new_leaf_updates=0,inherited_updates=provenance['parents'][p]['updates'])) for p in range(4)]
    return dict(by_lifecycle=lives,parent_receipts=parents,source_provenance=provenance,
        accounting=run.build_accounting(inherited,lives,parents,5.,8.)), inherited


@pytest.mark.parametrize('wrong', ('shared_raw', 'source_cpu'))
def test_whole_v313_cost_inventory_keeps_shared_economic_raw_and_source_cpu_once(wrong):
    document, inherited = accounting_document()
    audit.check_accounting(document, inherited)
    if wrong == 'shared_raw':
        document['accounting']['economic_training_raw_tiles_per_arm']['CLOSED_LOCAL'] -= 16*2*audit.POST_RAW
    else:
        document['accounting']['economic_source_and_target_cpu_seconds'] += document['accounting']['version_save_cpu_seconds']
    with pytest.raises(ValueError):
        audit.check_accounting(document, inherited)
