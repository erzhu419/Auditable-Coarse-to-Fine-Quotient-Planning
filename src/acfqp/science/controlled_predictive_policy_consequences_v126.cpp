#include <algorithm>
#include <cstdint>

namespace {
constexpr int occurrences = 32;
int64_t head_size(int radix) {
    int64_t size = 4;
    for (int i = 0; i < 6; ++i) size *= radix;
    return size;
}
void addresses(const int32_t* board, const int32_t* patterns, int radix,
               int64_t* indices) {
    const int64_t stride = head_size(radix) / 4;
    for (int occurrence = 0; occurrence < occurrences; ++occurrence) {
        int64_t address = 0;
        for (int cell = 0; cell < 6; ++cell)
            address = address * radix + board[patterns[occurrence * 6 + cell]];
        indices[occurrence] = (occurrence / 8) * stride + address;
    }
}
void prediction(const int32_t* board, const int32_t* patterns, int radix,
                const double* weights, double* out) {
    int64_t indices[occurrences];
    addresses(board, patterns, radix, indices);
    const int64_t size = head_size(radix);
    for (int head = 0; head < 3; ++head) {
        out[head] = 0.;
        for (int i = 0; i < occurrences; ++i)
            out[head] += weights[head * size + indices[i]];
    }
}
}

extern "C" void consequences_value_v126(const int32_t* board, const int32_t* patterns,
        int radix, const double* weights, double* out) {
    prediction(board, patterns, radix, weights, out);
}

extern "C" void consequences_update_v126(const int32_t* board, const int32_t* patterns,
        int radix, double* weights, const double* target, double alpha,
        double* errors, int32_t* unique_updates) {
    int64_t indices[occurrences];
    addresses(board, patterns, radix, indices);
    const int64_t size = head_size(radix);
    for (int head = 0; head < 3; ++head) {
        double before = 0.;
        for (int i = 0; i < occurrences; ++i)
            before += weights[head * size + indices[i]];
        errors[head] = target[head] - before;
    }
    std::sort(indices, indices + occurrences);
    *unique_updates = 0;
    for (int first = 0; first < occurrences;) {
        int end = first + 1;
        while (end < occurrences && indices[end] == indices[first]) ++end;
        for (int head = 0; head < 3; ++head)
            weights[head * size + indices[first]] += alpha * errors[head] * (end - first);
        ++*unique_updates;
        first = end;
    }
}

// Caller supplies the identified line program; no sampled successor is generated.
extern "C" void consequences_actions_v126(const int32_t* board, const int32_t* patterns,
        int radix, const double* weights, const int32_t* table,
        const int64_t* line_scores, const int32_t* action_cells,
        int32_t* moved, int64_t* scores, double* vectors, int32_t* legal,
        uint64_t* counts) {
    for (int action = 0; action < 4; ++action) {
        int32_t* after = moved + action * 16;
        std::copy(board, board + 16, after);
        scores[action] = 0;
        ++counts[0]; // learned_swipe_calls
        for (int line = 0; line < 4; ++line) {
            const int32_t* cells = action_cells + action * 16 + line * 4;
            int index = 0;
            for (int i = 0; i < 4; ++i) index = index * radix + board[cells[i]];
            for (int i = 0; i < 4; ++i) after[cells[i]] = table[index * 4 + i];
            scores[action] += line_scores[index];
            ++counts[1]; // line_table_lookups
        }
        legal[action] = !std::equal(board, board + 16, after);
        if (!legal[action]) continue;
        ++counts[2]; // legal_swipes
        ++counts[3]; // learned_terminal_checks
        double* result = vectors + action * 3;
        if (*std::max_element(after, after + 16) >= radix) {
            result[0] = 0.; result[1] = 0.; result[2] = 1.;
            ++counts[6]; // terminal_goal_bypasses
        } else {
            prediction(after, patterns, radix, weights, result);
            counts[4] += 3; // component_predictions
            counts[5] += 3 * occurrences; // table_lookups
        }
    }
}
