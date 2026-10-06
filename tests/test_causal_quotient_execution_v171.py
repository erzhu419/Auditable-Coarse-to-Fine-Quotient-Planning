"""Scripted current-frame selection and unsupported fallback, with no RNG draws."""
from collections import Counter
from copy import deepcopy

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science import controlled_predictive_causal_quotient_v171 as core
from test_causal_quotient_core_v171 import payload, row, edge

BOARDS = [(1, 2)+(0,)*14, (0, 1, 0, 2)+(0,)*12, (0,)*12+(1, 0, 2, 3), (0,)*8+(1, 2, 0, 3)+(0,)*4]


class Teacher:
    def __init__(self): self.counts, self.calls = Counter(choose_calls=7), []
    def choose(self, board, query):
        self.calls.append((tuple(board), deepcopy(query)))
        self.counts.update(choose_calls=1, value_predictions=4)
        return dict(action='LEFT', afterstate=list(board), score=0)


def episode(monkeypatch, models, mode, steps=3, illegal=None):
    spawn_count, status_count = [0], [0]
    def spawn(board, rng, counts, p_four):
        index = spawn_count[0]; spawn_count[0] += 1
        if index == 0: return (1,)+(0,)*15, 0, 1
        if index == 1: return BOARDS[0], 1, 2
        return BOARDS[index-1], index-2, 1
    def status(board, counts):
        index = status_count[0]; status_count[0] += 1
        counts['ground_state_status_calls'] += 1
        return 'LOST' if index == steps else 'ACTIVE'
    def swipe(board, action):
        return tuple(board), 0, action.value != illegal
    monkeypatch.setattr(core, '_spawn', spawn)
    monkeypatch.setattr(core, '_status', status)
    monkeypatch.setattr(core.ground, 'swipe_board_v1', swipe)
    bank = {query: Teacher() for query in core.QUERIES}
    result = core.run_episode(bank, models, 0, mode, 17150000, max_steps=steps)
    assert result['result']['environment_counts'].get('environment_random_draws', 0) == 0
    assert all(query == core.QUERIES['risk1'] for _, query in bank['risk1'].calls)
    assert bank['risk8'].calls == []
    return result, bank


def models_for(action='DOWN'):
    states = sorted({core.state_key(board) for board in BOARDS})
    return [core.compile_model(payload([row(state, action, [edge('WON', 1.+life)]) for state in states],
                 {state: [0., 0., 0.] for state in states}, life)) for life in range(4)]


def test_replan_current_D4_frame_and_load_frozen_whole_vector_each_step(monkeypatch):
    models = models_for()
    frozen = deepcopy([(model.payload, model.tables, model.counts) for model in models])
    result, bank = episode(monkeypatch, models, 'SAME_D3')
    frames = set()
    for step, choice in enumerate(result['choices']):
        _, frame = core.canonical_frame(BOARDS[step]); frames.add(frame)
        expected = ground.transform_action_v1(ground.Swipe2048Action('DOWN'), core.INVERSE[D4Transform(frame)]).value
        decision = choice['model_decision']
        assert decision['selected_source_life'] == 0 and decision['selected_canonical_action'] == 'DOWN'
        assert decision['transform'] == frame and decision['state'] == core.state_key(BOARDS[step])
        assert result['actions'][step] == expected and choice['phase'] == 'quotient'
        assert decision['candidates'][0]['components'] == [1., 0., 1.]
    assert len(frames) > 1 and bank['risk1'].calls == []
    assert result['module']['model_decisions'] == result['module']['decisions'] == 3
    assert result['result']['policy_counts']['quotient_ground_legality_swipe_calls'] == 12
    assert result['result']['policy_counts']['quotient_action_transports'] == 12
    assert [(model.payload, model.tables, model.counts) for model in models] == frozen


def test_unsupported_states_fall_back_same_step_and_legal_filter_blocks_illegal_estimates(monkeypatch):
    empty = [core.compile_model(payload([], life=life)) for life in range(4)]
    fallback, bank = episode(monkeypatch, empty, 'SAME_D1')
    assert fallback['module']['unsupported_fallbacks'] == fallback['module']['h2_calls'] == 3
    assert len(bank['risk1'].calls) == 3 and all(choice['model_decision']['fallback'] for choice in fallback['choices'])
    models = models_for()
    _, frame = core.canonical_frame(BOARDS[0])
    illegal = ground.transform_action_v1(ground.Swipe2048Action('DOWN'), core.INVERSE[D4Transform(frame)]).value
    # Ensure the teacher's fixture action stays legal for this observation.
    assert illegal != 'LEFT'
    blocked, bank = episode(monkeypatch, models, 'SAME_D1', steps=1, illegal=illegal)
    assert blocked['choices'][0]['model_decision']['candidates'] == []
    assert blocked['module']['model_decisions'] == 0 and blocked['module']['h2_calls'] == 1


def test_transfer_keeps_source_specific_vectors_and_excludes_own_teacher(monkeypatch):
    state = core.state_key(BOARDS[0])
    vectors = [(100., 'WON'), (10., 'LOST'), (9., 'WON'), (0., 'LOST')]
    models = [core.compile_model(payload([row(state, 'DOWN', [edge(terminal, reward)])], {state: [0., 0., 0.]}, life))
              for life, (reward, terminal) in enumerate(vectors)]
    result, _ = episode(monkeypatch, models, 'XFER_D1', steps=1)
    decision = result['choices'][0]['model_decision']
    assert decision['eligible_models'] == [1, 2, 3]
    assert decision['selected_source_life'] == 2 and decision['selected_canonical_action'] == 'DOWN'
    picked = next(candidate for candidate in decision['candidates'] if candidate['source_life'] == 2)
    assert picked['components'] == [9., 0., 1.] and picked['utility'] == 10.
    assert all(candidate['source_life'] != 0 for candidate in decision['candidates'])
