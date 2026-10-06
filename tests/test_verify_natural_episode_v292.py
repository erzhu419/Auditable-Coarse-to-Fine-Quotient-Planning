from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_natural_episode_v292 as audit


def terminal_chunk(arm='MEAN_H2'):
    memory=audit.Memory();memory.consume([1]*256)
    start=dict(episode=3,step=10,return_score=40,initial_count=2,game_start_raw=488,
        status='ACTIVE',pending_bank_id=0,raw_tiles=500,post_action_spawns=492,stream_seed=292200000000)
    end=dict(start,step=11,return_score=44,status='LOST',pending_bank_id=None,
        raw_tiles=501,post_action_spawns=493,random_draw_position=1002,
        board=[1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,1])
    game=dict(episode=3,start_raw=488,end_raw=501,steps=11,score=44,status='LOST',stream_seed=start['stream_seed'])
    direct=arm.endswith('DIRECT')
    planning=dict(choose_calls=1,root_swipe_calls=4,learned_swipe_calls=4 if direct else 12,
        second_ply_swipe_calls=0 if direct else 8,leaf_choose_calls=0 if direct else 2,
        generated_spawn_outcomes=0 if direct else 2,expanded_postspawn_states=0 if direct else 2,
        spawn_rank1_outcomes=0 if direct else 1,spawn_rank2_outcomes=0 if direct else 1,
        expectimax_probability_products=0 if direct else 2,expectimax_probability_sums=0 if direct else 2,
        line_table_lookups=16 if direct else 48,value_predictions=1,table_lookups=32)
    row=dict(start=start,end=end,raw_spawns=[dict(episode=3,kind='POST_ACTION',rank=1,cell=0)],
        actions=['LEFT'],scores=[4],completed_games=[game],arm=arm,depth=1 if direct else 2,
        active_bank_id=0,module_id_before=memory.active,model_p_four=memory.probability(),
        actor_weights_readonly=True,leaf_updates_before=128,leaf_updates_after=128,
        bank_update_counts={},td_examples=[],counts=dict(environment=dict(sampled_transitions=1,
            post_action_spawns=1,initial_spawns=0,raw_tile_productions=1,environment_random_draws=2,
            ground_explicit_swipe_calls=1,ground_state_status_calls=1,ground_status_internal_swipe_calls=4,
            ground_swipe_calls=5,episodes_started=0,episodes_completed=1,won_games=0,lost_games=1,cutoff_games=0),
            planning=planning,learning={}))
    return row,memory


@pytest.mark.parametrize('arm',['MEAN_H2','MEAN_DIRECT'])
def test_terminal_short_chunk_stops_without_finishing_the_memory_block(arm):
    row,memory=terminal_chunk(arm)
    assert audit.check_training_chunk(row,100,memory)==row['completed_games']
    assert memory.n==0


def test_next_game_initial_spawn_before_fit_is_rejected():
    row,memory=terminal_chunk()
    row['raw_spawns'].append(dict(episode=4,kind='INITIAL',rank=1,cell=1))
    row['end'].update(raw_tiles=502,random_draw_position=1004)
    with pytest.raises(ValueError,match='before terminal fitting'):audit.check_training_chunk(row,100,memory)


def test_writable_mc_head_cannot_trigger_native_sarsa():
    row,memory=terminal_chunk();row['counts']['learning']={'td_updates':1}
    with pytest.raises(ValueError,match='SARSA'):audit.check_training_chunk(row,100,memory)
    row['counts']['learning']={};row['actor_weights_readonly']=False
    with pytest.raises(ValueError,match='SARSA'):audit.check_training_chunk(row,100,memory)


def test_nonterminal_short_chunk_cannot_silently_delay_or_drop_a_fit():
    row,memory=terminal_chunk();row['completed_games']=[]
    with pytest.raises(ValueError,match='early pause'):audit.check_training_chunk(row,100,memory)


def test_direct_training_arm_must_actually_have_depth_one_work():
    row,memory=terminal_chunk('MEAN_DIRECT');row['depth']=2
    with pytest.raises(ValueError,match='actor depth'):audit.check_training_chunk(row,100,memory)


def single_fit(arm='MEAN_H2'):
    game=dict(episode=7,start_raw=131069,end_raw=131073,steps=2,score=12,status='LOST',stream_seed=audit.training_seed(0))
    scores=[4,8];method='NORMALIZED_SEQUENTIAL_MC' if arm=='NSEQ_H2' else 'EPISODE_MEAN_MC'
    mean=method=='EPISODE_MEAN_MC';writes=4 if mean else 8
    work=dict(games_processed=1,feature_extractions=2,feature_occurrences=64,feature_digit_reads=384,
        feature_address_multiply_adds=384,game_sort_calls=1,game_sort_items=64,
        address_occurrence_count_visits=64,address_occurrence_count_comparisons=63,
        sample_sort_calls=2,sample_sort_items=64,sample_unique_addresses=8,game_unique_addresses=4,
        address_denominator_searches=8,parameter_write_events=writes,normalization_divisions=writes,
        feature_index_buffer_int64_peak=64,sorted_feature_buffer_int64_peak=64,
        sample_step_buffer_int64_peak=2,sample_end_buffer_int64_peak=2,
        game_address_buffer_int64_peak=4,game_denominator_buffer_int64_peak=4,
        sample_address_buffer_int64_peak=4,sample_multiplicity_buffer_int64_peak=4,
        game_parameter_commits=int(mean),sample_parameter_commits=0 if mean else 2,
        weighted_residual_multiplications=8 if mean else 0,weighted_residual_accumulations=8 if mean else 0,
        parameter_update_multiplications=writes if mean else 2*writes,
        error_buffer_doubles_peak=2 if mean else 0,raw_prediction_buffer_doubles_peak=2 if mean else 0,
        address_gradient_buffer_doubles_peak=4 if mean else 0)
    work['native_buffer_bytes_peak']=8*(sum(v for k,v in work.items() if k.endswith('_peak'))+2)
    labels=audit.factual_targets(scores,'LOST')
    def sample(position):
        target=labels[position]
        return dict(episode=0,step=position,target=target,raw_target=target,error=target-1.,
            raw_prediction_before_update=1.,global_episode=7,global_raw_before_action=131071+position)
    fit=dict(method=method,alpha=.0025,fitted_games=1,fitted_steps=2,trained_afterstates=2,
        learning_counts=dict(td_updates=2,value_predictions=2,table_lookups=64,table_update_occurrences=64,table_updates=writes),
        target_counts=dict(goal_checks=2,suffix_games=1,suffix_target_assignments=2,suffix_reward_additions=2,
            raw_target_subtractions=2,skipped_winning_afterstates=0,target_buffer_doubles_peak=2),
        consolidation_counts=work,first_sample=sample(0),last_sample=sample(1),
        count_semantics=dict(td_updates='Nonwinning training samples processed',table_update_occurrences='not parameter writes'))
    row=dict(kind='GAME_FIT',lifecycle=0,arm=arm,phase='B',completion=game,fitted=True,
        old_value_updates=40,new_value_updates=42,fit=fit)
    return row,game,scores


@pytest.mark.parametrize('arm',['MEAN_H2','NSEQ_H2'])
def test_one_complete_game_across_phase_boundary_keeps_real_first_and_last_samples(arm):
    row,game,scores=single_fit(arm)
    assert audit.check_game_fit(row,game,scores,40)==2
    assert row['fit']['last_sample']['step']==1
    row['fit']['last_sample']['target']+=8/2048.
    with pytest.raises(ValueError,match='suffix target'):audit.check_game_fit(row,game,scores,40)


def test_game_fit_cannot_credit_an_unfinished_history_or_drop_earlier_phase_rewards():
    row,game,scores=single_fit()
    with pytest.raises(ValueError,match='immediately'):audit.check_game_fit(row,None,scores,40)
    with pytest.raises(ValueError,match='spans chunk/phase'):audit.check_game_fit(row,game,scores[1:],40)
    row['fit']['last_sample']['global_raw_before_action']+=1
    with pytest.raises(ValueError,match='actual episode/raw'):audit.check_game_fit(row,game,scores,40)


def test_actual_cutoff_receipt_is_skipped_not_given_loss_targets():
    row,game,scores=single_fit();game['status']='CUTOFF'
    row.update(fitted=False,new_value_updates=40,fit=dict(method='SKIPPED_CUTOFF',trained_afterstates=0,
        learning_counts={},target_counts={},consolidation_counts={},first_sample=None,last_sample=None))
    assert audit.check_game_fit(row,game,scores,40)==0
    row['fit']['target_counts']={'suffix_games':1}
    with pytest.raises(ValueError,match='censored'):audit.check_game_fit(row,game,scores,40)


def test_three_fresh_seed_families_are_disjoint_and_probe_reuse_is_exact():
    warm={audit.warmup_seed(life,game) for life in range(16) for game in range(256)}
    train={audit.training_seed(life) for life in range(16)}
    evaluate={audit.evaluation_seed(life,phase,game) for life in range(16) for phase in range(3) for game in range(32)}
    assert len(evaluate)==1536 and not warm&train and not warm&evaluate and not train&evaluate
    assert audit.evaluation_seed(0,0,0)==292900000000
