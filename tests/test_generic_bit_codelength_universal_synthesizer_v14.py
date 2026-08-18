from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    _signed_gamma_bits,
    _unsigned_gamma_bits,
)


def test_v14_integer_prefix_code_lengths_are_exact_and_total():
    assert [_unsigned_gamma_bits(value) for value in range(5)] == [1, 3, 3, 5, 5]
    assert [_signed_gamma_bits(value) for value in (0, 1, -1, 2, -2)] == [
        1,
        3,
        3,
        5,
        5,
    ]
