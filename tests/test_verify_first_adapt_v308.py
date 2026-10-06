"""Finite actual-world fixtures and reachable first-adaptation audit failures."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_first_adapt_v308 as audit


@pytest.fixture(scope='module')
def prefix():
    # Reuse a finite factual fixture, not a new experimental world or old training input.
    rows = []
    with gzip.open(ROOT/'reports/continual_v303/parent_0_records.jsonl.gz', 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if row['kind'] == 'WARMUP':
                row['summary']['seed'] = audit.warmup_seed(0, 'A1', len(rows)); rows.append(row)
            elif row['kind'] == 'TRAIN':
                for state in (row['start'], row['end'], *row['completed_games']):
                    state['stream_seed'] = audit.training_seed(0, 'A1')
                return rows, row


def warmed(prefix):
    world = audit.StageWorld(0, 'A1')
    for row in prefix[0]:
        world.warmup(deepcopy(row))
    return world


def detector(world, created=True, context=0):
    belief = dict(memory=dict(method='LIBRARY', **world.memory.learned()), estimated_p_four=world.memory.probability())
    stats = audit.observed_statistics(belief['memory'])
    route = dict(statistics=stats, scores=[], context_id=context, created=created, prototype_before=None,
        prototype_after=dict(context_id=context, **stats, visits=1))
    return dict(kind='DETECTION_SNAPSHOT', lifecycle=world.life, parent=world.life%4, phase=world.stage,
        true_p_four=.5 if world.stage == 'B' else .1, detector_belief=belief, route=route)


def test_actual_complete_warmup_and_first_chunk_reconstruct_full_physics_and_observed_blocks(prefix):
    world = warmed(prefix); world.detect(detector(world)); row = deepcopy(prefix[1]); world.train(row)
    assert world.state == row['end'] and world.memory.obs == world.warm_raw+len(row['raw_spawns'])
    assert world.train_counts['environment']['raw_tile_productions'] == len(row['raw_spawns'])


def test_detector_initial_tile_must_occupy_an_empty_cell(prefix):
    row = deepcopy(prefix[0][0]); row['raw_spawns'][1]['cell'] = row['raw_spawns'][0]['cell']
    with pytest.raises(ValueError, match='empty cell'):
        audit.StageWorld(0, 'A1').warmup(row)


def test_detector_merge_score_is_independent_of_saved_terminal_summary(prefix):
    row = deepcopy(prefix[0][0]); row['scores'][0] += 4
    with pytest.raises(ValueError, match='independent merge score'):
        audit.StageWorld(0, 'A1').warmup(row)


def test_detector_does_not_fabricate_natural_terminal_labels(prefix):
    row = deepcopy(prefix[0][0]); row['summary']['status'] = 'CUTOFF'
    with pytest.raises(ValueError, match='natural terminal outcome'):
        audit.StageWorld(0, 'A1').warmup(row)


def test_detector_seed_is_new_not_old_retained_target_seed(prefix):
    row = deepcopy(prefix[0][0]); row['summary']['seed'] = 303100000000
    with pytest.raises(ValueError, match='fresh complete SOURCE detector game'):
        audit.StageWorld(0, 'A1').warmup(row)


def test_routing_cannot_precede_paid_256_raw_detector_observations():
    world = audit.StageWorld(0, 'A1')
    with pytest.raises(ValueError, match='before any training acquisition'):
        world.detect(detector(world))


def test_detector_belief_cannot_include_later_model_cohort_observations(prefix):
    world = warmed(prefix); row = detector(world); row['detector_belief']['memory']['observations_seen'] += 1
    with pytest.raises(ValueError, match='only its observed completed warmup'):
        world.detect(row)


def test_training_must_follow_actual_context_creation_not_only_stage_label(prefix):
    world = warmed(prefix)
    with pytest.raises(ValueError, match='newly created observed context'):
        world.train(deepcopy(prefix[1]))
    world.detect(detector(world, created=False))
    with pytest.raises(ValueError, match='newly created observed context'):
        world.train(deepcopy(prefix[1]))


def test_new_model_chunk_cannot_substitute_true_probability_for_observed_online_memory(prefix):
    world = warmed(prefix); world.detect(detector(world)); row = deepcopy(prefix[1]); row['model_p_four'] = .1
    with pytest.raises(ValueError, match='preceding observed online LIBRARY'):
        world.train(row)


def test_new_model_chunk_cannot_drop_the_continuous_pending_boundary(prefix):
    world = warmed(prefix); world.detect(detector(world)); row = deepcopy(prefix[1]); row['end']['pending_afterstate'] = None
    with pytest.raises(ValueError, match='end boards pending states'):
        world.train(row)


def test_new_source_acquisition_never_fits_learner_parameters(prefix):
    world = warmed(prefix); world.detect(detector(world)); row = deepcopy(prefix[1]); row['counts']['learning'] = dict(td_updates=1)
    with pytest.raises(ValueError, match='does not fit a learned bank'):
        world.train(row)


def observed(n, k):
    return dict(memory=dict(observations_seen=n, modules=[dict(id=0, alpha=1+k, beta=1+n-k)], pending=dict(n=0, fours=0)))


def route_for(belief, prototypes):
    stats = audit.observed_statistics(belief['memory']); scores = audit.route_scores(stats, prototypes)
    best = max(scores, key=lambda row:(row['log_bayes_factor'], -row['context_id'])) if scores else None
    created = best is None or best['log_bayes_factor'] < 0.
    context = len(prototypes) if created else best['context_id']; before = None if created else prototypes[context]
    after = dict(context_id=context, observations=stats['observations']+(before['observations'] if before else 0),
        fours=stats['fours']+(before['fours'] if before else 0), visits=(before['visits'] if before else 0)+1)
    return dict(statistics=stats, scores=scores, context_id=context, created=created, prototype_before=deepcopy(before), prototype_after=after)


def test_actual_observed_a_b_a_routes_pool_only_new_warmups_and_reuse_without_fit():
    prototypes = []
    for n,k,expected in ((300,30,(0,True)), (300,150,(1,True)), (300,32,(0,False))):
        belief = observed(n,k); result = audit.check_detection_route(route_for(belief,prototypes), belief, prototypes)
        assert result == expected
    assert prototypes == [dict(context_id=0, observations=600, fours=62, visits=2), dict(context_id=1, observations=300, fours=150, visits=1)]


def test_actual_third_distribution_creates_and_retains_a_third_context():
    prototypes = [dict(context_id=0,observations=300,fours=30,visits=1), dict(context_id=1,observations=300,fours=150,visits=1)]
    belief = observed(300,270)
    assert audit.check_detection_route(route_for(belief,prototypes), belief, prototypes) == (2,True)
    assert len(prototypes) == 3


def test_prototype_cannot_receive_model_fit_prefix_or_heldout_counts():
    prototypes = []; belief = observed(300,30); route = route_for(belief,prototypes)
    route['prototype_after']['observations'] += audit.RAW
    with pytest.raises(ValueError, match='current paid warmup'):
        audit.check_detection_route(route, belief, prototypes)


def test_negative_context_evidence_cannot_force_reuse_of_a_known_task_bank():
    prototypes = [dict(context_id=0,observations=300,fours=30,visits=1)]
    belief = observed(300,150); route = route_for(belief,prototypes); route.update(created=False,context_id=0)
    with pytest.raises(ValueError, match='negative evidence creates'):
        audit.check_detection_route(route, belief, prototypes)


def test_retention_probe_routes_readonly_from_first_task_detector():
    prototypes = [dict(context_id=0,observations=600,fours=62,visits=2), dict(context_id=1,observations=300,fours=150,visits=1)]
    belief = observed(300,30); before = deepcopy(prototypes)
    route = dict(kind='READ_ONLY_FIRST_DETECTOR', statistics=audit.observed_statistics(belief['memory']),
        scores=audit.route_scores(audit.observed_statistics(belief['memory']),prototypes), context_id=0)
    assert audit.check_probe_route(route, belief, prototypes) == 0 and prototypes == before
    route['context_id'] = 1
    with pytest.raises(ValueError, match='highest-evidence context'):
        audit.check_probe_route(route, belief, prototypes)


@pytest.fixture(scope='module')
def setups():
    old = json.loads((ROOT/'reports/continual_v303/summary.json').read_text())['by_lifecycle'][0]['head_setup']
    return dict(CONTEXT_MC=old['MC'], CONTEXT_LOCAL=old['LOCAL_RISK'])


def test_mc_and_local_new_contexts_copy_same_source_prior_with_zero_risk(setups):
    audit.check_bank_setup(setups)
    wrong = deepcopy(setups); wrong['CONTEXT_LOCAL']['setup_counts']['initialized_zero_risk_parameters'] = 0
    with pytest.raises(ValueError, match='zero risk logits'):
        audit.check_bank_setup(wrong)


def test_context_mc_cannot_share_unfitted_source_instead_of_own_bank(setups):
    wrong = deepcopy(setups); wrong['CONTEXT_MC']['source_weights_shared'] = True
    with pytest.raises(ValueError, match='copies the same original SOURCE'):
        audit.check_bank_setup(wrong)


def budget():
    inherited = dict(source_training_raw_tiles=200,dynamics_raw_tiles=4)
    lives = []
    for life in range(64):
        stages = {stage:dict(context_route=dict(created=stage!='A2'), acquisition=dict(warmup=dict(raw_tiles=300),
            training=dict(raw_tiles=audit.RAW) if stage!='A2' else None)) for stage in audit.STAGES}
        lives.append(dict(lifecycle=life,stages=stages))
    warm = 192*300; actor = 128*audit.RAW
    account = dict(old_target_training_raw_reused=0,physical_detection_stages=192,physical_acquisitions=128,
        new_training_environment_observations=warm+actor,new_warmup_raw_tiles=warm,new_actor_raw_tiles=actor,
        new_raw_tiles_by_stage=dict(A1=64*(300+audit.RAW),B=64*(300+audit.RAW),A2=64*300),
        inherited_costs_per_arm=dict.fromkeys(audit.ARMS,inherited),economic_training_raw_tiles_per_arm=dict.fromkeys(audit.ARMS,204+warm+actor))
    return account,inherited,lives


def test_all_three_algorithms_pay_actual_new_detections_cohorts_and_tails():
    account,inherited,lives = budget(); assert audit.check_training_budget(account,inherited,lives) == 204+192*300+128*audit.RAW
    account['new_training_environment_observations'] -= 192*300
    with pytest.raises(ValueError, match='all 192 new detector warmups'):
        audit.check_training_budget(account,inherited,lives)


def test_return_detector_context_creation_is_not_assumed_free_or_forced_absent():
    account,inherited,lives = budget(); lives[0]['stages']['A2']['context_route']['created'] = True
    lives[0]['stages']['A2']['acquisition']['training'] = dict(raw_tiles=audit.RAW)
    with pytest.raises(ValueError, match='actually created context cohorts'):
        audit.check_training_budget(account,inherited,lives)


def test_formal_input_account_cannot_include_old_a1_target_training_facts():
    account,inherited,lives = budget(); account['old_target_training_raw_reused'] = audit.RAW
    with pytest.raises(ValueError, match='without old target facts'):
        audit.check_training_budget(account,inherited,lives)


def support():
    return dict(complete_game_endpoints=True, primary_local_over_mc_supported=True,
        primary_local_over_mc_status='SUPPORTED_'+audit.INTERVAL_SCOPE,
        final_ab_contrasts=dict(CONTEXT_LOCAL_minus_CONTEXT_MC=dict(ci95=[.2,.5]),CONTEXT_LOCAL_minus_SOURCE=dict(ci95=[.1,.4])),
        final_net_gain_supported=True, final_task_gain_supported=dict(A=False,B=False), final_dual_task_gain_supported=False,
        cells={cell:dict(paired_contrasts=dict(CONTEXT_LOCAL_minus_SOURCE=dict(ci95=[-.1,.2]))) for cell in ('A2_A','A2_B')},
        checkpoint_contrasts={name:dict(CONTEXT_LOCAL=dict(ci95=[0.,0.])) for name in audit.CHECKPOINTS},
        retention_status={name:'SUPPORTED_NONDECREASE' for name in ('A_after_B','B_after_A2','A_final_vs_A1')}, retention_supported=True,retained_gain_supported=True)


def test_matched_mc_contribution_net_source_gain_and_retention_are_separate():
    value = support(); audit.check_support(value,0)
    value['final_ab_contrasts']['CONTEXT_LOCAL_minus_CONTEXT_MC']['ci95'] = [-.2,.1]
    value.update(primary_local_over_mc_supported=False,primary_local_over_mc_status='NOT_SUPPORTED_'+audit.INTERVAL_SCOPE)
    with pytest.raises(ValueError, match='requires matched-MC contribution'):
        audit.check_support(value,0)


def test_positive_final_mean_does_not_override_supported_retention_loss():
    value = support(); value['checkpoint_contrasts']['A_final_vs_A1']['CONTEXT_LOCAL']['ci95'] = [-.4,-.1]
    value['retention_status']['A_final_vs_A1'] = 'SUPPORTED_LOSS'; value['retention_supported'] = False
    with pytest.raises(ValueError, match='all three zero-margin retention'):
        audit.check_support(value,0)


def test_single_task_gain_is_not_dual_task_gain_or_required_by_retained_rule():
    value = support(); value['cells']['A2_A']['paired_contrasts']['CONTEXT_LOCAL_minus_SOURCE']['ci95'] = [.1,.2]
    value['final_task_gain_supported']['A'] = True; audit.check_support(value,0)
    value['final_dual_task_gain_supported'] = True
    with pytest.raises(ValueError, match='individual final task gains'):
        audit.check_support(value,0)


def test_cutoff_cannot_support_any_new_algorithm_gain():
    with pytest.raises(ValueError, match='complete game endpoints'):
        audit.check_support(support(),1)
