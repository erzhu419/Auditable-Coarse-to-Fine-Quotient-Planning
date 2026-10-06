"""Check the actual acquisition binding without invoking a native teacher."""
from copy import deepcopy
import gzip
import json

from scripts import run_controlled_predictive_fixed_program_v167 as runner


def test_acquisition_executes_BB_feedback_and_keeps_paired_trace_metadata(monkeypatch, tmp_path):
    root = dict(root_id='EVAL_SOURCE:0:risk1:0:0', phase='EVAL_SOURCE', life=0,
                query='risk1', replica=0, slot=0, board=[1, 2]+[0]*14)
    candidate = dict(candidate_id='P0', first_action='DOWN', probe_action='RIGHT',
                     true_suffix=['RIGHT', 'DOWN', 'RIGHT'],
                     false_suffix=['DOWN', 'RIGHT', 'DOWN'],
                     fixed_suffix=['RIGHT', 'DOWN', 'RIGHT'])
    program = runner.build_program(candidate)
    plans = runner.build_roster([root])[:2]
    calls, completed = [], []
    bank = {'risk1': object(), 'risk8': object()}
    records = {'risk1': {}, 'risk8': {}}

    class Rule:
        @classmethod
        def from_payload(cls, payload):
            obj = cls(); obj.payload = deepcopy(payload)
            return obj

        def to_payload(self):
            return deepcopy(self.payload)

    def branch(board, teachers, rule, query, selected, arm, seed, max_steps, p_four):
        calls.append(dict(board=board, bank=teachers, query=query, program=selected,
                          arm=arm, seed=seed, max_steps=max_steps, p_four=p_four))
        return dict(root_board=board, query=query, arm=arm, seed=seed,
                    module=dict(program=selected),
                    result=dict(score=2048, steps=3, status='WON',
                                components=[1., 0., 1.], utility=2.,
                                environment_counts={'sampled_transitions': 3},
                                policy_counts={'ground_swipes': 5},
                                program_setup_counts={'probes': int(arm == 'FEEDBACK')}))

    monkeypatch.setattr(runner, 'LearnedDynamics', Rule)
    monkeypatch.setattr(runner, 'build_roster', lambda roots: plans)
    monkeypatch.setattr(runner.prior, 'teachers', lambda source, folder: (bank, {}, {}, records))
    monkeypatch.setattr(runner.prior, 'finish_teachers', lambda *args: completed.append(args[0]))
    monkeypatch.setattr(runner, 'run_branch', branch)
    lifecycle = runner.branch_lifecycle(dict(life=0, rule={'frozen': True}),
                                       'EVAL', [root], program, tmp_path)
    assert [call['arm'] for call in calls] == ['H2', 'FEEDBACK']
    assert calls[0]['program'] is None and calls[1]['program'] == program
    assert calls[1]['program']['true_suffix'] == calls[1]['program']['false_suffix'] == candidate['false_suffix']
    assert calls[1]['program']['fixed_suffix'] == candidate['true_suffix']
    assert [call['seed'] for call in calls] == [16750000000]*2
    assert all(call['bank'] is bank and call['query'] == 'risk1' and
               call['max_steps'] == 2000 and call['p_four'] == .1 for call in calls)
    with gzip.open(tmp_path/lifecycle['branch_trace'], 'rt') as trace:
        rows = [json.loads(line) for line in trace]
    outcomes = json.loads((tmp_path/lifecycle['outcomes_ref']).read_text())
    assert len(rows) == len(outcomes) == lifecycle['physical_branches'] == 2
    assert all(all(row[key] == value for key, value in plan.items()) for row, plan in zip(rows, plans))
    assert [row['arm'] for row in outcomes] == ['H2', 'FEEDBACK']
    assert lifecycle['environment_counts'] == {'sampled_transitions': 6}
    assert lifecycle['policy_counts'] == {'ground_swipes': 10}
    assert lifecycle['program_setup_counts'] == {'probes': 1}
    assert lifecycle['rule_before'] == lifecycle['rule_after'] == {'frozen': True}
    assert completed == [bank] and lifecycle['teacher_bank'] is records
