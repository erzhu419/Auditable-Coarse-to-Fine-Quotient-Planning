"""Independent current-state labels, measured game selection and graph replay."""
from collections import Counter
from copy import deepcopy
from math import sqrt

import pytest

from scripts import analyze_controlled_predictive_persistent_strategy_v170 as audit
from acfqp.science import controlled_predictive_persistent_strategy_v170 as core
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from test_consequence_generation_core_v168 import source_game

RULE = LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),((1,.9),(2,.1)),'uniform')
ROWS = []


def program(leaf='DOWN'):
    return dict(nodes=[dict(probe_action='LEFT',true_action=leaf,false_action=leaf,true_next=1,false_next=1),
                       dict(probe_action='DOWN',true_action=leaf,false_action=leaf,true_next=0,false_next=0)])


def selection_fixture(phase='G1'):
    parents = [program(),program('H2')]
    slots = audit.mutations(parents) if phase != 'FINAL' else [dict(candidate_slot=i,program=p) for i,p in enumerate(parents)]
    cell = dict(heldout_life=3,query='risk1',phase=phase,parents=parents,slots=slots,complete=True,issues=[])
    rows = []
    for life in range(3):
        for episode in range(4 if phase == 'FINAL' else 2):
            alternatives = [('H2','H2',None,None)]+[(f"P{slot['candidate_slot']}_{route}",route,slot['candidate_slot'],slot['program']) for slot in slots for route in ('COND','LATCHED')]
            for mode,route,slot,candidate in alternatives:
                reward = 100. if route == 'H2' else 20. if route == 'COND' and slot == (1 if phase == 'FINAL' else 2) else 1.
                rows.append(dict(phase=phase,life=life,heldout_life=3,query='risk1',episode=episode,mode=mode,route=route,arm=route,
                    candidate_slot=slot,seed=audit.branch_seed(phase,life,episode,3),score=reward*2048.,steps=10,status='LOST',
                    components=[reward,1.,0.],utility=reward-1.,module=dict(program=candidate,arm=route)))
    return [cell],rows


def eval_fixture():
    rows = []
    for life in range(4):
        for episode in range(32):
            for mode in audit.MODES:
                reward = 0. if mode == 'H2' else 1. if mode == 'LATCHED' else episode+1.
                module = dict(program=None if mode == 'H2' else program(),arm=mode,**{key:0 for key in audit.MODULE_COUNTS},node_visits=[0,0])
                module['h2_calls'] = 10 if mode == 'H2' else 1
                if mode != 'H2': module.update(decisions=10,direct_decisions=9,control_transitions=10,node_switches=9,node_visits=[5,5],live_predicate_changes=4,latch_divergences=3 if mode == 'LATCHED' else 0)
                rows.append(dict(phase='EVAL',life=life,heldout_life=life,query='risk1',episode=episode,mode=mode,route=mode,arm=mode,
                    candidate_slot=None,seed=audit.branch_seed('EVAL',life,episode),score=reward*2048.,steps=10,status='LOST',components=[reward,1.,0.],utility=reward-1.,module=module))
    return rows


def test_ground_source_probe_tables_match_learned_current_board_labels():
    rows = [source_game(life,replica) for life in range(4) for replica in range(4)]
    independent = audit.source_candidates(rows)
    for heldout in range(4):
        assert audit._equal(core.source_candidates(rows,{life:RULE for life in range(4) if life != heldout},heldout),independent[heldout])
        assert independent[heldout]['counts']['decision_windows'] == 96
        assert independent[heldout]['counts']['probe_checks'] == 384
        assert independent[heldout]['counts']['board_transforms'] == 768
        assert len(independent[heldout]['probe_tables']) == 4
        assert all(node['true_action'] == node['false_action'] == 'H2' for node in independent[heldout]['parents'][1]['nodes'])


def test_independent_54_slot_graph_mutations_include_action_and_control_changes():
    parents = [program(),program('H2')]
    independent = audit.mutations(parents)
    assert independent == core.mutate(parents) and len(independent) == 54
    assert any(slot['program']['nodes'][0]['true_next'] == 0 for slot in independent)
    assert any(slot['program']['nodes'][1]['probe_action'] == 'UP' for slot in independent)


def test_physical_conditional_games_choose_negative_winner_without_latched_reselection():
    for phase in ('G1','G2','FINAL'):
        cells,rows = selection_fixture(phase)
        independent = audit.select_parents(cells,rows)
        assert audit._equal(core.choose_parents(cells,rows,phase),independent)
        assert independent[0]['selected_slots'][0] == (1 if phase == 'FINAL' else 2)
        winner = independent[0]['slot_scores'][independent[0]['selected_slots'][0]]
        assert winner['train_gain'] == -80. and winner['train_gain_vs_LATCHED'] == 19.


@pytest.mark.parametrize('failure',['cutoff','duplicate','seed'])
def test_bad_unselected_game_stops_without_replacement(failure):
    cells,rows = selection_fixture(); row = next(row for row in rows if row['mode'] == 'P53_LATCHED')
    if failure == 'cutoff': row.update(status='CUTOFF',utility=None)
    elif failure == 'duplicate': rows.append(deepcopy(row))
    else: row['seed'] += 1
    selected = audit.select_parents(cells,rows)[0]
    assert audit._equal(core.choose_parents(cells,rows,'G1')[0],selected)
    assert not selected['complete'] and selected['selected_parents'] == [] and len(selected['slot_scores']) == 54


def test_whole_episode_pairing_ci_and_repeated_feedback_counts():
    rows = eval_fixture(); independent = audit.eval_summary(rows)
    assert audit._equal(core.summarize_eval(rows),independent)
    stat = independent['comparisons'][0]['metrics']['utility']
    assert stat['mean'] == 15.5 and stat['mean_variance'] == pytest.approx(.6875)
    assert stat['conditional_episode_ci95'] == pytest.approx([15.5-1.96*sqrt(.6875),15.5+1.96*sqrt(.6875)])
    assert 'conditional_suffix_ci95' not in stat
    assert independent['program_diagnostics'][1]['episodes_with_repeated_node_visits'] == 128
    rows[0].update(status='CUTOFF',utility=None)
    assert not audit.eval_summary(rows)['complete']


class SmallTeacher:
    """Finite controller fixture; no native planning or scientific training."""
    def __init__(self): self.counts = Counter()
    def choose(self,board,query):
        self.counts['fixture_calls'] += 1
        for action in audit.ACTIONS:
            after,score,legal = audit.prior.ground.swipe_board_v1(tuple(board),audit.prior.ground.Swipe2048Action(action))
            if legal: return dict(action=action,afterstate=list(after),score=score)
        raise AssertionError('fixture requested a terminal-board action')


@pytest.mark.parametrize('arm',['H2','COND','LATCHED'])
def test_finite_multistep_replay_current_frame_latch_graph_and_rng(monkeypatch,arm):
    # Stub only the old H2-value verifier, while new controller/physical replay
    # compares its complete trace, work and RNG against independent ground logic.
    monkeypatch.setattr(audit.prior.prior.planning,'planning_counts_valid',lambda *args:True)
    monkeypatch.setattr(audit.prior.prior.local,'compact_choice_valid',lambda *args:True)
    monkeypatch.setattr(audit.prior.prior.h1,'root_choice_checks',lambda *args:{})
    row = core.run_episode({query:SmallTeacher() for query in ('risk1','risk8')},RULE,'risk1',None if arm == 'H2' else program(),arm,31,max_steps=8)
    ROWS.append(row)
    checks,_ = audit.replay_episode(row,max_steps=8)
    assert all(checks.values())
    assert row['result']['environment_counts']['initial_spawns'] == 2
    assert row['result']['environment_counts']['sampled_transitions'] == 8
    if arm == 'H2':
        assert row['module']['h2_calls'] == 8 and row['module']['decisions'] == 0
    else:
        assert row['module']['control_transitions'] == 8 and row['module']['node_visits'] == [4,4]
        wrong = deepcopy(row); wrong['choices'][4]['program_decision']['used_predicate'] = not wrong['choices'][4]['program_decision']['used_predicate']
        assert not audit.replay_episode(wrong,max_steps=8)[0]['controller_decisions']
        wrong = deepcopy(row); wrong['module']['current_node'] = 1
        assert not audit.replay_episode(wrong,max_steps=8)[0]['controller_module']
    wrong = deepcopy(row); wrong['spawned_ranks'][0] = 3
    assert not audit.replay_episode(wrong,max_steps=8)[0]['rng']
