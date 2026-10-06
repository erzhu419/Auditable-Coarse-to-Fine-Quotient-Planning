#include <algorithm>
#include <cstdint>
#include <utility>

namespace {
bool goal(const int32_t* board, int radix) {
    return *std::max_element(board, board + 16) >= radix;
}

void addresses(const int32_t* board, const int32_t* patterns, int radix,
               int64_t* indices) {
    int64_t stride = 1;
    for (int i = 0; i < 6; ++i) stride *= radix;
    for (int occurrence = 0; occurrence < 32; ++occurrence) {
        int64_t address = 0;
        for (int i = 0; i < 6; ++i)
            address = address * radix + board[patterns[occurrence * 6 + i]];
        indices[occurrence] = (occurrence / 8) * stride + address;
    }
}
}

extern "C" void residual_predict_v130(const int32_t* boards, int n,
        const int32_t* patterns, int radix, const double* weights, double* output) {
    for (int row = 0; row < n; ++row) {
        const int32_t* board = boards + row * 16;
        output[row] = 0.;
        if (goal(board, radix)) continue;
        int64_t indices[32];
        addresses(board, patterns, radix, indices);
        for (int i = 0; i < 32; ++i) output[row] += weights[indices[i]];
    }
}

// Repeated occurrences from both boards are merged before the squared norm.
// work: occurrences, union addresses, nonzero addresses, L1 difference,
//       table reads, table writes, update occurrences, terminal boards.
extern "C" void residual_pair_fit_v130(const int32_t* boards,
        const int32_t* patterns, int radix, double* weights,
        double base_gap, double target_gap, double rate,
        double* output, uint64_t* work) {
    std::pair<int64_t, int> features[64];
    int n = 0;
    for (int side = 0; side < 2; ++side) {
        const int32_t* board = boards + side * 16;
        if (goal(board, radix)) { ++work[7]; continue; }
        int64_t indices[32]; addresses(board, patterns, radix, indices);
        for (int i = 0; i < 32; ++i)
            features[n++] = {indices[i], side == 0 ? 1 : -1};
    }
    work[0] = n;
    std::sort(features, features + n);
    int64_t indices[64]; int differences[64]; int changed = 0;
    double residual_gap = 0., denominator = 0.;
    for (int first = 0; first < n;) {
        int end = first, difference = 0;
        while (end < n && features[end].first == features[first].first)
            difference += features[end++].second;
        ++work[1];
        if (difference != 0) {
            indices[changed] = features[first].first;
            differences[changed++] = difference;
            residual_gap += weights[features[first].first] * difference;
            denominator += difference * difference;
            work[3] += difference < 0 ? -difference : difference;
        }
        first = end;
    }
    work[2] = work[4] = changed;
    const double error = target_gap - (base_gap + residual_gap);
    if (denominator != 0.) {
        for (int i = 0; i < changed; ++i)
            weights[indices[i]] += rate * error * differences[i] / denominator;
        work[5] = changed; work[6] = work[3];
    }
    output[0] = residual_gap; output[1] = error; output[2] = denominator;
}

// SCRATCH needs the identified transition program, never source value weights.
extern "C" void residual_actions_v130(const int32_t* board, int radix,
        const int32_t* table, const int64_t* line_scores,
        const int32_t* action_cells, int32_t* moved, int64_t* scores,
        int32_t* legal) {
    for (int action = 0; action < 4; ++action) {
        int32_t* after = moved + action * 16;
        std::copy(board, board + 16, after);
        scores[action] = 0;
        for (int line = 0; line < 4; ++line) {
            const int32_t* cells = action_cells + action * 16 + line * 4;
            int index = 0;
            for (int i = 0; i < 4; ++i) index = index * radix + board[cells[i]];
            for (int i = 0; i < 4; ++i) after[cells[i]] = table[index * 4 + i];
            scores[action] += line_scores[index];
        }
        legal[action] = !std::equal(board, board + 16, after);
    }
}
