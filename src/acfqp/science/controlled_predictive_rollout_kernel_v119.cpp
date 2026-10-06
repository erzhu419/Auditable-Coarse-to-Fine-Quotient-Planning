// Finite fixed-policy rollouts using only supplied learned rewrite tables.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>

namespace {
struct Move { int32_t board[16]; int64_t score; int empty; };

int classify(const int32_t* board, int goal, const int32_t* table,
             const int64_t* scores, const int32_t* cells, Move* moves,
             bool* legal, uint64_t* counts) {
    ++counts[2];
    for (int i = 0; i < 16; ++i) if (board[i] >= goal) return 1;
    bool active = false;
    for (int a = 0; a < 4; ++a) {
        ++counts[3]; counts[4] += 4;
        Move& move = moves[a]; move.score = 0;
        for (int line = 0; line < 4; ++line) {
            const int32_t* cc = cells + 16*a + 4*line;
            int index = 0;
            for (int j = 0; j < 4; ++j) index = index*goal + board[cc[j]];
            move.score += scores[index];
            for (int j = 0; j < 4; ++j) move.board[cc[j]] = table[4*index+j];
        }
        move.empty = 0; legal[a] = false;
        for (int i = 0; i < 16; ++i) {
            move.empty += move.board[i] == 0;
            legal[a] = legal[a] || move.board[i] != board[i];
        }
        if (legal[a]) { active = true; ++counts[5]; }
    }
    return active ? 0 : -1;
}

int action(const Move* moves, const bool* legal, int policy,
           const int32_t* snake, const double* weights) {
    int best = -1;
    double best_primary = 0, best_secondary = 0;
    // Supplied action topology is in sorted action-name order. Strict > keeps ties.
    for (int a = 0; a < 4; ++a) if (legal[a]) {
        double primary, secondary;
        if (policy == 0) { primary = moves[a].score; secondary = moves[a].empty; }
        else if (policy == 1) { primary = moves[a].empty; secondary = moves[a].score; }
        else {
            primary = 0; secondary = moves[a].score;
            for (int pos = 0; pos < 16; ++pos) {
                int rank = moves[a].board[snake[pos]];
                primary += (rank ? std::ldexp(1.0, rank) : 0.0) * weights[pos];
            }
        }
        if (best < 0 || primary > best_primary ||
                (primary == best_primary && secondary > best_secondary)) {
            best = a; best_primary = primary; best_secondary = secondary;
        }
    }
    return best;
}

bool spawn(int32_t* board, const double* draws, int location, const int32_t* ranks,
           const double* cumulative, int n_ranks, uint64_t* counts) {
    int empty[16], n = 0;
    for (int i = 0; i < 16; ++i) if (board[i] == 0) empty[n++] = i;
    if (!n) return false;
    int cell = location == 1 ? empty[0] : location == 2 ? empty[n-1]
        : empty[std::min(static_cast<int>(draws[0]*n), n-1)];
    int rank = ranks[n_ranks-1];
    for (int i = 0; i < n_ranks; ++i) if (draws[1] < cumulative[i]) {
        rank = ranks[i]; break;
    }
    board[cell] = rank; ++counts[0];
    return true;
}
}

extern "C" int rollout_v119(
    const int32_t* boards, int n_boards, int horizon, int replicas, int goal,
    const int32_t* table, const int64_t* scores, const int32_t* cells,
    const int32_t* snake, const double* weights, int location,
    const int32_t* spawn_ranks, const double* cumulative, int n_ranks,
    const double* draws, double* output, uint64_t* counts) {
    std::fill(output, output + n_boards*9, 0.0);
    std::fill(counts, counts+6, uint64_t(0));
    for (int b = 0; b < n_boards; ++b) for (int policy = 0; policy < 3; ++policy) {
        double* target = output + b*9 + policy*3;
        for (int replica = 0; replica < replicas; ++replica) {
            int32_t board[16]; std::memcpy(board, boards+b*16, sizeof(board));
            int64_t reward = 0;
            for (int step = 0; step <= horizon; ++step) {
                const double* pair = draws + (replica*(horizon+1)+step)*2;
                if (!spawn(board, pair, location, spawn_ranks, cumulative, n_ranks, counts))
                    return 1;
                Move moves[4]; bool legal[4];
                int status = classify(board, goal, table, scores, cells, moves, legal, counts);
                if (status) { target[status == 1 ? 2 : 1] += 1.0; break; }
                if (step == horizon) break;
                int selected = action(moves, legal, policy, snake, weights);
                std::memcpy(board, moves[selected].board, sizeof(board));
                reward += moves[selected].score; ++counts[1];
            }
            target[0] += static_cast<double>(reward)/2048.0;
        }
        for (int metric = 0; metric < 3; ++metric) target[metric] /= replicas;
    }
    return 0;
}
