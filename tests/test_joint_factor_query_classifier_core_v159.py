from acfqp.joint_factor_query_classifier_core_v159 import (
    evaluate_joint_factor_query_expression_v159,
    synthesize_joint_factor_query_classifier_v159,
)


def test_v159_finite_grammar_derives_conjunctive_factor_query_rule():
    positive = ((1, 4), (1, 4), (1, 4), (3, 3), (4, 4), (4, 16))
    failed = ((1, 4), (2, 2), (2, 2), (2, 4), (4, 4), (4, 16))
    modular = ((1, 1), (1, 6), (2, 3), (2, 3), (2, 4), (2, 6), (2, 11))
    expression, _mdl, evaluated, separating = synthesize_joint_factor_query_classifier_v159(
        ((positive, True), (failed, False), (modular, False))
    )
    assert evaluated == 9_216
    assert separating > 0
    assert evaluate_joint_factor_query_expression_v159(expression, positive)[0] is True
    assert evaluate_joint_factor_query_expression_v159(expression, failed)[0] is False
    assert evaluate_joint_factor_query_expression_v159(expression, modular)[0] is False
