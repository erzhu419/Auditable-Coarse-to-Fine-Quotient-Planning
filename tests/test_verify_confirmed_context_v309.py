"""New finite detector tapes and reachable confirmed-context audit failures."""
from copy import deepcopy
from math import log
from pathlib import Path
import sys

import pytest

from acfqp.domains import standard_2048 as ground
from acfqp.science.confirmed_context_v309 import ConfirmedContexts
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_confirmed_context_v309 as audit


def observed(n, k):
    return dict(memory=dict(observations_seen=n, modules=[dict(id=0, alpha=1+k, beta=1+n-k)],
        pending=dict(n=0, fours=0)))


def prototypes():
    return [dict(context_id=0, observations=300, fours=30, visits=1),
        dict(context_id=1, observations=300, fours=150, visits=1)]


def make_look(router, belief, index=0, stage='A2'):
    n = belief['memory']['observations_seen']
    return dict(kind='DETECTOR_LOOK', lifecycle=0, parent=0, phase=stage, look_index=index,
        detector_raw_tiles=n, at_cap=n >= audit.DETECTOR_CAP, **router.probe(belief['memory']))


def finish(router, belief, look):
    decision = {key:value for key,value in look.items()
        if key not in ('kind', 'lifecycle', 'parent', 'phase', 'look_index', 'detector_raw_tiles', 'at_cap')}
    if decision['decision'] == 'PENDING_CONFIRMATION':
        decision['decision'] = 'CAP_REUSE_UNRESOLVED'
    return router.commit(belief['memory'], decision)


def router_with_banks():
    router = ConfirmedContexts(); router.banks = prototypes()
    return router


def test_independent_five_encounters_retain_two_banks_and_commit_each_detector_once():
    router = ConfirmedContexts(); checked = []
    for stage,n,k,expected in (('A1',300,30,(0,True)), ('B1',300,150,(1,True)),
            ('A2',300,32,(0,False)), ('B2',300,148,(1,False)), ('A3',300,31,(0,False))):
        belief = observed(n,k); look = make_look(router,belief,stage=stage); route = finish(router,belief,look)
        assert audit.check_detection_route(route,belief,checked,[look]) == expected
    assert checked == router.banks
    assert checked[0]['observations'] == 900 and checked[0]['visits'] == 3
    assert checked[1]['observations'] == 600 and checked[1]['visits'] == 2


def test_ambiguous_candidate_observes_independent_new_ranks_before_resolved_reuse():
    router = router_with_banks(); before = deepcopy(router.banks)
    first = make_look(router,observed(300,55)); final_belief = observed(600,80)
    second = make_look(router,final_belief,1)
    assert first['decision'] == 'PENDING_CONFIRMATION' and second['decision'] == 'REUSE'
    assert router.banks == before
    route = finish(router,final_belief,second)
    assert audit.check_detection_route(route,final_belief,before,[first,second]) == (0,False)
    assert before[0]['observations'] == 900 and before[0]['fours'] == 110 and before[0]['visits'] == 2


def test_strong_third_context_really_creates_and_uses_a_third_bank():
    router = router_with_banks(); checked = deepcopy(router.banks); belief = observed(300,270)
    look = make_look(router,belief); route = finish(router,belief,look)
    assert look['decision'] == 'CONFIRMED_NEW' and look['novelty_log_odds'] >= log(99.)
    assert audit.check_detection_route(route,belief,checked,[look]) == (2,True)
    assert checked == router.banks and checked[2]['observations'] == 300
    route['context_id'] = 0
    with pytest.raises(ValueError,match='resolved final route'):
        audit.check_detection_route(route,belief,prototypes(),[look])


def test_novelty_uses_uniform_existing_mixture_not_only_best_bank():
    router = router_with_banks(); belief = observed(300,55); look = make_look(router,belief)
    assert look['novelty_log_odds'] == pytest.approx(-look['scores'][0]['log_bayes_factor']+log(2.))
    route = finish(router,observed(4096,650),make_look(router,observed(4096,650)))
    look['novelty_log_odds'] = -look['scores'][0]['log_bayes_factor']
    with pytest.raises(ValueError,match='mixture evidence'):
        audit.check_detection_route(route,observed(4096,650),prototypes(),[look])


def test_cap_reuse_preserves_observations_fours_visits_and_retained_unresolved_status():
    router = router_with_banks(); checked = deepcopy(router.banks); belief = observed(4096,650)
    look = make_look(router,belief); route = finish(router,belief,look)
    assert look['decision'] == 'PENDING_CONFIRMATION' and look['at_cap']
    assert route['decision'] == 'CAP_REUSE_UNRESOLVED' and not route['prototype_committed']
    assert audit.check_detection_route(route,belief,checked,[look]) == (0,False)
    assert checked == prototypes() == router.banks and route['prototype_before'] == route['prototype_after']


@pytest.mark.parametrize('field', ['observations','fours','visits'])
def test_cap_cannot_commit_uncertain_counts_or_increment_visits(field):
    router = router_with_banks(); belief = observed(4096,650); look = make_look(router,belief)
    route = finish(router,belief,look); route['prototype_after'][field] += 1
    with pytest.raises(ValueError,match='capped ambiguity preserves'):
        audit.check_detection_route(route,belief,prototypes(),[look])


def test_cap_before_budget_is_not_an_authorized_fallback():
    router = router_with_banks(); belief = observed(300,55); look = make_look(router,belief)
    route = finish(router,belief,look)
    with pytest.raises(ValueError,match='cannot finalize before'):
        audit.check_detection_route(route,belief,prototypes(),[look])


@pytest.mark.parametrize('first_counts',[(300,30),(4096,650)])
def test_only_pending_uncapped_evidence_permits_another_look(first_counts):
    router = router_with_banks(); first = make_look(router,observed(*first_counts))
    belief = observed(first_counts[0]+300,first_counts[1]+30)
    second = make_look(router,belief,1); route = finish(router,belief,second)
    with pytest.raises(ValueError,match='only genuinely ambiguous evidence'):
        audit.check_detection_route(route,belief,prototypes(),[first,second])


def test_training_or_future_observations_cannot_enter_final_router_pool():
    router = router_with_banks(); belief = observed(300,30); look = make_look(router,belief)
    route = finish(router,belief,look)
    with pytest.raises(ValueError,match='without training leakage'):
        audit.check_detection_route(route,observed(600,60),prototypes(),[look])


def test_provisional_look_cannot_have_already_committed_a_prototype():
    router = router_with_banks(); belief = observed(300,30); look = make_look(router,belief)
    route = finish(router,belief,look); look['prototype_committed'] = True
    with pytest.raises(ValueError,match='immutable-prior'):
        audit.check_detection_route(route,belief,prototypes(),[look])


def actual_game_row(index, memory, stage='A2', kind='WARMUP'):
    def choose(board, step):
        for action in ground.Swipe2048Action:
            if ground.swipe_board_v1(board,action)[2]:
                return action.value
        raise AssertionError('fixture policy called on a terminal board')
    game = run_episode(audit.warmup_seed(0,stage,index),choose,.1,8192)
    assert game['status'] in ('WON','LOST')
    raw = [dict(value,kind='INITIAL') for value in game['initial_spawns']]
    raw.extend(dict(rank=step['spawned_rank'],cell=step['spawned_cell'],kind='POST_ACTION') for step in game['steps'])
    events = []
    for spawn in raw:
        event = memory.observe(spawn['rank'])
        if event is not None:
            events.append(event)
    steps = game['steps_count']
    direct = dict(choose_calls=steps,inner_choose_calls=steps,inner_learned_swipe_calls=4*steps,
        inner_line_table_lookups=16*steps,inner_table_lookups=128*steps,inner_value_predictions=4*steps,
        td_updates=0,inner_td_updates=0)
    return dict(kind=kind,lifecycle=0,parent=0,phase=stage,true_p_four=.1,
        summary=dict(seed=game['seed'],score=game['return_score'],status=game['status'],steps=steps,
            utility=game['return_score']/2048.+(4. if game['status']=='WON' else -4.)),
        raw_spawns=raw,actions=[step['action'] for step in game['steps']],scores=[step['score'] for step in game['steps']],
        final_board=game['final_board'],memory_events=events,counts=dict(environment=game['work'],direct=direct))


@pytest.fixture(scope='module')
def detector_rows():
    memory = SpawnMemory('LIBRARY'); rows = []
    while memory.observations_seen < 256:
        rows.append(actual_game_row(len(rows),memory))
    extra = actual_game_row(len(rows),memory,kind='CONFIRMATION')
    return rows,extra


def initial_world(detector_rows):
    world = audit.StageWorld(0,'A2')
    for row in detector_rows[0]:
        world.warmup(deepcopy(row))
    return world


def temporal_look(world, decision='PENDING_CONFIRMATION'):
    return dict(kind='DETECTOR_LOOK',lifecycle=0,parent=0,phase='A2',look_index=len(world.looks),
        statistics=audit.observed_statistics(world.memory.learned()),detector_raw_tiles=world.memory.obs,
        at_cap=world.memory.obs>=4096,prototype_committed=False,decision=decision)


def test_factual_initial_and_extra_games_reconstruct_all_physics_events_and_paid_tails(detector_rows):
    world = initial_world(detector_rows); world.look(temporal_look(world))
    world.warmup(deepcopy(detector_rows[1])); world.look(temporal_look(world,'REUSE'))
    assert world.confirmation_games == 1 and world.confirmation_raw == len(detector_rows[1]['raw_spawns'])
    assert world.memory.obs == world.initial_raw+world.confirmation_raw
    assert world.initial_raw >= 256 and len(world.looks) == 2


@pytest.mark.parametrize('decision,at_cap',[('REUSE',False),('CONFIRMED_NEW',False),('PENDING_CONFIRMATION',True)])
def test_extra_complete_game_cannot_follow_resolved_evidence_or_reached_cap(detector_rows,decision,at_cap):
    world = initial_world(detector_rows); look = temporal_look(world,decision); world.look(look)
    world.looks[-1]['at_cap'] = at_cap
    with pytest.raises(ValueError,match='only a genuinely ambiguous uncapped look'):
        world.warmup(deepcopy(detector_rows[1]))


def test_every_extra_game_requires_a_fresh_seed_and_new_factual_memory_events(detector_rows):
    world = initial_world(detector_rows); world.look(temporal_look(world)); row = deepcopy(detector_rows[1])
    row['summary']['seed'] -= 1
    with pytest.raises(ValueError,match='fresh complete SOURCE detector game'):
        world.warmup(row)
    row = deepcopy(detector_rows[1]); row['memory_events'].append(dict(kind='fabricated'))
    with pytest.raises(ValueError,match='literal observed memory event'):
        world.warmup(row)


def test_look_cannot_omit_paid_complete_game_overshoot(detector_rows):
    world = initial_world(detector_rows); look = temporal_look(world); look['detector_raw_tiles'] = 256
    with pytest.raises(ValueError,match='including natural overshoot'):
        world.look(look)


def test_confirmation_game_does_not_fabricate_natural_terminal_score(detector_rows):
    world = initial_world(detector_rows); world.look(temporal_look(world)); row = deepcopy(detector_rows[1])
    row['scores'][0] += 4
    with pytest.raises(ValueError,match='independent merge score'):
        world.warmup(row)


def budget():
    inherited = dict(source_training_raw_tiles=200,dynamics_raw_tiles=4); lives = []
    for life in range(64):
        stages = {}
        for stage in audit.STAGES:
            created = stage in ('A1','B1'); extra = 200 if stage == 'A2' else 0
            warm = dict(raw_tiles=300+extra,initial_raw_tiles=300,confirmation_raw_tiles=extra,
                confirmation_games=int(bool(extra)),detector_looks=1+int(bool(extra)))
            stages[stage] = dict(context_route=dict(created=created,prototype_committed=True,
                decision='FIRST_CONTEXT' if stage=='A1' else 'CONFIRMED_NEW' if created else 'REUSE'),
                acquisition=dict(warmup=warm,training=dict(raw_tiles=audit.RAW) if created else None))
        lives.append(dict(lifecycle=life,stages=stages))
    warm,actor = 320*300+64*200,128*audit.RAW
    account = dict(old_target_training_raw_reused=0,physical_detection_stages=320,physical_acquisitions=128,
        new_training_environment_observations=warm+actor,new_warmup_raw_tiles=warm,new_actor_raw_tiles=actor,
        new_initial_detector_raw_tiles=320*300,new_confirmation_raw_tiles=64*200,new_confirmation_games=64,
        detector_looks=384,context_decisions=dict(FIRST_CONTEXT=64,CONFIRMED_NEW=64,REUSE=192),
        context_prototype_commits=320,unresolved_cap_stages=[],
        new_raw_tiles_by_stage={stage:64*(300+(200 if stage=='A2' else 0)+(audit.RAW if stage in ('A1','B1') else 0)) for stage in audit.STAGES},
        inherited_costs_per_arm=dict.fromkeys(audit.ARMS,inherited),
        economic_training_raw_tiles_per_arm=dict.fromkeys(audit.ARMS,204+warm+actor))
    return account,inherited,lives


def test_all_new_320_detectors_independent_confirmation_games_and_cohorts_are_paid():
    account,inherited,lives = budget()
    assert audit.check_training_budget(account,inherited,lives) == 204+320*300+64*200+128*audit.RAW
    account['new_confirmation_raw_tiles'] -= 1
    with pytest.raises(ValueError,match='confirmation observations'):
        audit.check_training_budget(account,inherited,lives)


def test_cap_accounting_cannot_hide_retained_unresolved_stage_or_claim_commit():
    account,inherited,lives = budget()
    lives[0]['stages']['A2']['context_route'].update(decision='CAP_REUSE_UNRESOLVED',prototype_committed=False)
    with pytest.raises(ValueError,match='retained unresolved cap stages'):
        audit.check_training_budget(account,inherited,lives)


def support():
    return dict(complete_game_endpoints=True,primary_local_over_mc_supported=True,
        primary_local_over_mc_status='SUPPORTED_'+audit.INTERVAL_SCOPE,
        final_ab_contrasts=dict(CONTEXT_LOCAL_minus_CONTEXT_MC=dict(ci95=[.2,.5]),CONTEXT_LOCAL_minus_SOURCE=dict(ci95=[.1,.4])),
        final_net_gain_supported=True,final_task_gain_supported=dict(A=False,B=False),final_dual_task_gain_supported=False,
        cells={cell:dict(paired_contrasts=dict(CONTEXT_LOCAL_minus_SOURCE=dict(ci95=[-.1,.2]))) for cell in ('A3_A','A3_B')},
        checkpoint_contrasts={name:dict(CONTEXT_LOCAL=dict(ci95=[0.,0.])) for name in audit.CHECKPOINTS},
        retention_status={name:'SUPPORTED_NONDECREASE' for name in audit.CHECKPOINTS},retention_supported=True,retained_gain_supported=True)


@pytest.mark.parametrize('name',list(audit.CHECKPOINTS))
def test_retained_gain_requires_every_one_of_seven_strict_comparisons(name):
    value = support(); audit.check_support(value,0)
    value['checkpoint_contrasts'][name]['CONTEXT_LOCAL']['ci95'] = [-.1,.1]
    value['retention_status'][name] = 'UNRESOLVED'; value['retention_supported'] = False
    with pytest.raises(ValueError,match='all seven zero-margin'):
        audit.check_support(value,0)
