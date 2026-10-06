// One chronological factual pass; all features and updates use unchanged V120.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

extern "C" double ntuple_value_v120(const int32_t*, const int32_t*, int, const double*);
extern "C" double ntuple_update_v120(const int32_t*, const int32_t*, int, double*,
    double, double, int32_t*);

namespace {
enum Learning { UPDATES, PREDICTIONS, LOOKUPS, UNIQUE_WRITES, OCCURRENCES };
enum Target { GOAL_CHECKS, ANALYTIC_TAILS, TERMINAL_TARGETS, NEXT_REWARDS,
    SUFFIX_GAMES, SUFFIX_ASSIGNMENTS, SUFFIX_ADDITIONS, TARGET_SUBTRACTIONS,
    PREDICTION_SHIFTS, SKIPPED_WINNING, BUFFER_DOUBLES_PEAK };

bool won(const int32_t* board, int goal, uint64_t* targets) {
    ++targets[GOAL_CHECKS];
    return *std::max_element(board,board+16)>=goal;
}

void suffix_targets(int64_t start, int64_t end, const double* rewards,
    double terminal, std::vector<double>& values, uint64_t* counts) {
    values.resize(end-start);
    counts[BUFFER_DOUBLES_PEAK]=std::max(counts[BUFFER_DOUBLES_PEAK],
        static_cast<uint64_t>(values.capacity()));
    ++counts[SUFFIX_GAMES];
    double suffix=terminal;
    for (int64_t i=end; i-->start;) {
        values[i-start]=suffix;
        suffix+=rewards[i];
        ++counts[SUFFIX_ASSIGNMENTS]; ++counts[SUFFIX_ADDITIONS];
    }
}
}

extern "C" void fit_retained_v287(const int32_t* afterstates, const double* rewards,
    const int64_t* ends, const int32_t* terminal_codes, int n_fit_games,
    const int32_t* patterns, int radix, double* weights, double goal, double failure,
    double failure_shift, double success_shift, double alpha, int method,
    uint64_t* learning, uint64_t* targets, int64_t* example_indices,
    double* example_values) {
    std::vector<double> suffixes;
    int64_t start=0;
    for (int game=0; game<n_fit_games; ++game) {
        const int64_t end=ends[game];
        const double terminal=terminal_codes[game]==1 ? goal : -failure;
        if (method==1) suffix_targets(start,end,rewards,terminal,suffixes,targets);
        for (int64_t i=start; i<end; ++i) {
            if (won(afterstates+16*i,radix,targets)) { ++targets[SKIPPED_WINNING]; continue; }
            double target;
            if (method==1) target=suffixes[i-start];
            else if (i+1==end) { target=terminal; ++targets[TERMINAL_TARGETS]; }
            else {
                double tail;
                if (won(afterstates+16*(i+1),radix,targets)) {
                    tail=goal; ++targets[ANALYTIC_TAILS];
                } else {
                    const double raw=ntuple_value_v120(afterstates+16*(i+1),patterns,radix,weights);
                    tail=raw+failure_shift+success_shift;
                    ++learning[PREDICTIONS]; learning[LOOKUPS]+=32;
                    targets[PREDICTION_SHIFTS]+=2;
                }
                target=rewards[i+1]+tail; ++targets[NEXT_REWARDS];
            }
            const double raw_target=target-(failure_shift+success_shift);
            ++targets[TARGET_SUBTRACTIONS];
            int32_t unique=0;
            const double error=ntuple_update_v120(afterstates+16*i,patterns,radix,weights,
                raw_target,alpha,&unique);
            ++learning[PREDICTIONS]; learning[LOOKUPS]+=32;
            learning[UNIQUE_WRITES]+=unique; learning[OCCURRENCES]+=32;
            if (!learning[UPDATES]) {
                example_indices[0]=game; example_indices[1]=i;
                example_values[0]=target; example_values[1]=raw_target;
                example_values[2]=error; example_values[3]=raw_target-error;
            }
            example_indices[2]=game; example_indices[3]=i;
            example_values[4]=target; example_values[5]=raw_target;
            example_values[6]=error; example_values[7]=raw_target-error;
            ++learning[UPDATES];
        }
        start=end;
    }
}

extern "C" void score_retained_v287(const int32_t* afterstates, const double* rewards,
    const int64_t* ends, const int32_t* terminal_codes, int first_game, int n_games,
    const int32_t* patterns, int radix, const double* weights, double goal, double failure,
    double failure_shift, double success_shift, double* game_metrics,
    uint64_t* predictions, uint64_t* targets) {
    std::vector<double> suffixes;
    int64_t start=first_game ? ends[first_game-1] : 0;
    for (int game=first_game; game<n_games; ++game) {
        const int64_t end=ends[game];
        suffix_targets(start,end,rewards,terminal_codes[game]==1 ? goal : -failure,suffixes,targets);
        double count=0., residual=0., squares=0., absolute=0., predicted=0., actual=0.;
        for (int64_t i=start; i<end; ++i) {
            if (won(afterstates+16*i,radix,targets)) { ++targets[SKIPPED_WINNING]; continue; }
            const double raw=ntuple_value_v120(afterstates+16*i,patterns,radix,weights);
            const double value=raw+failure_shift+success_shift;
            ++predictions[PREDICTIONS]; predictions[LOOKUPS]+=32;
            targets[PREDICTION_SHIFTS]+=2;
            const double error=value-suffixes[i-start];
            ++count; residual+=error; squares+=error*error; absolute+=std::abs(error);
            predicted+=value; actual+=suffixes[i-start];
        }
        double* output=game_metrics+6*(game-first_game);
        output[0]=count; output[1]=residual/count; output[2]=squares/count;
        output[3]=absolute/count; output[4]=predicted/count; output[5]=actual/count;
        start=end;
    }
}
