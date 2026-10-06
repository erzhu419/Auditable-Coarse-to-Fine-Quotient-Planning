#include <algorithm>
#include <cstdint>

namespace {
constexpr int occurrences = 32;
int64_t table_size(int radix) {
    int64_t size = 1;
    for (int i = 0; i < 6; ++i) size *= radix;
    return size;
}
void addresses(const int32_t* board, const int32_t* patterns, int radix,
               int64_t* indices) {
    const int64_t stride = table_size(radix);
    for (int occurrence = 0; occurrence < occurrences; ++occurrence) {
        int64_t address = 0;
        for (int cell = 0; cell < 6; ++cell)
            address = address * radix + board[patterns[occurrence * 6 + cell]];
        indices[occurrence] = (occurrence / 8) * stride + address;
    }
}
int swipe(const int32_t* board, int action, int radix, const int32_t* table,
          const int64_t* scores, const int32_t* action_cells,
          int32_t* after, int64_t* score, uint64_t* counts) {
    std::copy(board, board + 16, after);
    *score = 0;
    ++counts[0]; // replay_swipe_calls
    for (int line = 0; line < 4; ++line) {
        const int32_t* cells = action_cells + action * 16 + line * 4;
        int index = 0;
        for (int i = 0; i < 4; ++i) index = index * radix + board[cells[i]];
        for (int i = 0; i < 4; ++i) after[cells[i]] = table[index * 4 + i];
        *score += scores[index];
        ++counts[1]; // replay_line_table_lookups
    }
    return !std::equal(board, board + 16, after);
}
}

extern "C" uint64_t success_fit_v127(const int32_t* boards, int n,
        const int32_t* patterns, int radix, uint64_t* visits, uint64_t* wins,
        int success) {
    uint64_t updates = 0;
    for (int board = 0; board < n; ++board) {
        const int32_t* cells = boards + 16 * board;
        if (*std::max_element(cells, cells + 16) >= radix) continue;
        int64_t indices[occurrences];
        addresses(cells, patterns, radix, indices);
        std::sort(indices, indices + occurrences);
        const int64_t* end = std::unique(indices, indices + occurrences);
        for (const int64_t* i = indices; i != end; ++i) {
            ++visits[*i]; wins[*i] += success; ++updates;
        }
    }
    return updates;
}

extern "C" void success_predict_v127(const int32_t* boards, int n,
        const int32_t* patterns, int radix, const uint64_t* visits,
        const uint64_t* wins, double prior, double* output) {
    for (int board = 0; board < n; ++board) {
        const int32_t* cells = boards + 16 * board;
        if (*std::max_element(cells, cells + 16) >= radix) {
            output[board] = 1.; continue;
        }
        int64_t indices[occurrences];
        addresses(cells, patterns, radix, indices);
        double sum = 0.;
        for (int i = 0; i < occurrences; ++i)
            sum += (static_cast<double>(wins[indices[i]]) + prior)
                   / (static_cast<double>(visits[indices[i]]) + 1.);
        output[board] = sum / occurrences;
    }
}

// Reconstruct only retained transitions. Random spawns are records, never draws.
extern "C" int success_replay_v127(const int32_t* initial, const int32_t* actions,
        const int32_t* spawn_cells, const int32_t* spawn_ranks,
        const int64_t* recorded_scores, int n, int radix,
        const int32_t* table, const int64_t* line_scores, const int32_t* action_cells,
        const int32_t* final_board, int32_t* afterstates, uint64_t* counts,
        int32_t* failed_step) {
    int32_t board[16];
    std::copy(initial, initial + 16, board);
    for (int step = 0; step < n; ++step) {
        *failed_step = step;
        if (actions[step] < 0 || actions[step] >= 4) return 1;
        for (int i = 0; i < 16; ++i)
            if (board[i] < 0 || board[i] >= radix) return 2;
        int32_t* after = afterstates + 16 * step;
        int64_t score = 0;
        if (!swipe(board, actions[step], radix, table, line_scores, action_cells, after, &score, counts)) return 3;
        if (score != recorded_scores[step]) return 4;
        int cell = spawn_cells[step], rank = spawn_ranks[step];
        if (cell < 0 || cell >= 16 || after[cell] != 0 || (rank != 1 && rank != 2)) return 5;
        std::copy(after, after + 16, board);
        board[cell] = rank;
        ++counts[2]; // replay_recorded_spawns
    }
    if (!std::equal(board, board + 16, final_board)) return 6;
    return 0;
}
