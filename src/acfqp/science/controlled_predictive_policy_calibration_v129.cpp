#include <cstdint>

// Same scalar occurrence order as V120, batched without action enumeration.
extern "C" void policy_tail_values_v129(const int32_t* boards, int n,
        const int32_t* patterns, int radix, const double* weights, double* output) {
    int64_t stride = 1;
    for (int i = 0; i < 6; ++i) stride *= radix;
    for (int board = 0; board < n; ++board) {
        const int32_t* cells = boards + 16 * board;
        double value = 0.;
        for (int occurrence = 0; occurrence < 32; ++occurrence) {
            int64_t address = 0;
            for (int cell = 0; cell < 6; ++cell)
                address = address * radix + cells[patterns[occurrence * 6 + cell]];
            value += weights[(occurrence / 8) * stride + address];
        }
        output[board] = value;
    }
}
