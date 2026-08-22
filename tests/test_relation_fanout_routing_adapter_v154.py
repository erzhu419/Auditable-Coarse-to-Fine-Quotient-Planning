from acfqp.generic_relation_fanout_routing_adapter_v154 import (
    build_relation_fanout_routing_adapter_v154,
    relation_fanout_routing_config_v154,
)
from acfqp.relation_coverage_acquisition_operator_v153 import (
    relation_coverage_then_path_stream_v153,
)


def test_v154_fanout_relation_is_observed_and_nonrelational_schema_rejects():
    config = relation_fanout_routing_config_v154()
    adapter = build_relation_fanout_routing_adapter_v154(1_047_503, config)
    batches = relation_coverage_then_path_stream_v153(adapter)
    assert [len(next(batches)) for _ in range(5)] == [2, 2, 2, 2, 2]

    incompatible = build_relation_fanout_routing_adapter_v154(
        1_047_503, config, incompatible=True
    )
    stream = relation_coverage_then_path_stream_v153(incompatible)
    observed = []
    try:
        while True:
            observed.append(next(stream))
    except ValueError as error:
        assert str(error) == "V153 raw initial observations exposed no positive relation coverage"
    assert len(observed) == 4
