// Reuse the original SOURCE H2 chooser and independent standard-world execution.
#include "native_value_stream_v286.cpp"

namespace {
enum StrategyCount { GUARDS, ENTRIES, EXITS, ACTIVE, FALLBACK, CHANGED,
    FEATURE_EVALUATIONS, FEATURE_CELL_READS, FEATURE_DISTANCES, FEATURE_DIVISIONS,
    DOT_MULTIPLIES, DOT_ADDS, SCORE_ADDS, STATE_WRITES, CORNER_RANK_CHECKS,
    CORNER_DISTANCES, ZERO_GAMES, GAME_RESETS, N_STRATEGY_COUNTS };
struct StrategyState { int corner=-1; bool build=false; int previous=-1; };

bool zero_strategy(const double* theta) {
    return theta[0]==0. && theta[1]==0. && theta[2]==0. && theta[3]==0.;
}

int distance(int cell_index, int corner) {
    return std::abs(cell_index/4-corner/4)+std::abs(cell_index%4-corner%4);
}

int strategy_action(const int32_t* board, const int32_t* moved, const int32_t* legal,
    const double* values, int source_action, int goal, const double* theta,
    StrategyState& state, uint64_t* counts, double* feature_output=nullptr) {
    if (zero_strategy(theta)) { ++counts[FALLBACK]; return source_action; }
    int empty=0;
    for (int i=0; i<16; ++i) empty+=board[i]==0;
    ++counts[GUARDS];
    if (state.build && empty<=2) {
        state.build=false; state.corner=-1; state.previous=-1;
        ++counts[EXITS]; counts[STATE_WRITES]+=3;
    } else if (!state.build && empty>=4) {
        int maximum=0;
        for (int i=0; i<16; ++i) {
            ++counts[CORNER_RANK_CHECKS];
            if (board[i]>board[maximum]) maximum=i;
        }
        const int corners[]={0,3,12,15};
        int chosen=0, nearest=7;
        for (int corner:corners) {
            const int d=distance(maximum,corner); ++counts[CORNER_DISTANCES];
            if (d<nearest) { nearest=d; chosen=corner; }
        }
        state.build=true; state.corner=chosen; state.previous=-1;
        ++counts[ENTRIES]; counts[STATE_WRITES]+=3;
    }
    if (!state.build) { ++counts[FALLBACK]; return source_action; }
    int selected=-1; double best=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) if (legal[action]) {
        const int32_t* after=moved+16*action;
        int spaces=0, maximum=-1, nearest=7; double weighted=0.;
        for (int i=0; i<16; ++i) {
            const int d=distance(i,state.corner);
            spaces+=after[i]==0; weighted+=after[i]*(6-d);
            if (after[i]>maximum) { maximum=after[i]; nearest=d; }
            else if (after[i]==maximum) nearest=std::min(nearest,d);
        }
        const double features[]={spaces/16.,-nearest/6.,weighted/(16.*6.*goal),
            static_cast<double>(action==state.previous)};
        ++counts[FEATURE_EVALUATIONS]; counts[FEATURE_CELL_READS]+=16;
        counts[FEATURE_DISTANCES]+=16; counts[FEATURE_DIVISIONS]+=3;
        double dot=0.;
        for (int k=0; k<4; ++k) {
            dot+=theta[k]*features[k];
            if (feature_output) feature_output[4*action+k]=features[k];
        }
        counts[DOT_MULTIPLIES]+=4; counts[DOT_ADDS]+=4; ++counts[SCORE_ADDS];
        const double score=values[action]+dot;
        if (selected<0 || score>best) { selected=action; best=score; }
    }
    ++counts[ACTIVE]; counts[CHANGED]+=selected!=source_action;
    state.previous=selected; ++counts[STATE_WRITES];
    return selected;
}
}

// The pure selector exposes the exact production guard/features for finite tests.
extern "C" int strategy_selection_v297(const int32_t* board, const int32_t* moved,
    const int32_t* legal, const double* values, int source_action, int goal,
    const double* theta, int32_t* state_values, double* features, uint64_t* counts) {
    StrategyState state{state_values[0],state_values[1]!=0,state_values[2]};
    const int action=strategy_action(board,moved,legal,values,source_action,goal,
        theta,state,counts,features);
    state_values[0]=state.corner; state_values[1]=state.build; state_values[2]=state.previous;
    return action;
}

extern "C" int strategy_evaluate_v297(const uint64_t* seeds, int n_seeds,
    const double* theta, const int32_t* patterns, const int32_t* extra, int radix,
    int mode, double* weights, const int32_t* table, const int64_t* line_scores,
    const int32_t* cells, double source_goal, double goal, double failure,
    double failure_shift, double success_shift, int convert, double model_p,
    double environment_p, int max_steps, int64_t* results, int32_t* final_boards,
    uint64_t* game_strategy, uint64_t* environment, uint64_t* planning,
    uint64_t* strategy) {
    const Parameters p{patterns,extra,table,cells,line_scores,radix,mode,convert,
        weights,source_goal,goal,failure,failure_shift,success_shift};
    for (int game=0; game<n_seeds; ++game) {
        uint64_t* work=game_strategy+N_STRATEGY_COUNTS*game;
        if (zero_strategy(theta)) {
            const int code=native_stream_evaluate_v286(seeds+game,1,patterns,extra,
                radix,mode,weights,table,line_scores,cells,source_goal,goal,failure,
                failure_shift,success_shift,convert,model_p,environment_p,2,max_steps,
                results+3*game,final_boards+16*game,environment,planning);
            if (code) return code;
            ++work[ZERO_GAMES]; work[FALLBACK]=results[3*game+1];
        } else {
            std::mt19937_64 rng(seeds[game]); int32_t board[16]={}; int cell_out,rank_out;
            StrategyState state; ++work[GAME_RESETS]; work[STATE_WRITES]+=3;
            for (int tile=0; tile<2; ++tile)
                spawn_raw(board,environment_p,rng,cell_out,rank_out,0,environment);
            int status=ground_status(board,radix,environment), steps=0; int64_t score=0;
            while (!status && steps<max_steps) {
                int32_t moved[64],legal[4],after[16]; int64_t scores[4],gained;
                double tails[4],values[4];
                const int source=choose(board,p,model_p,2,moved,scores,tails,values,legal,planning);
                if (source<0) return 1;
                const int selected=strategy_action(board,moved,legal,values,source,radix,theta,state,work);
                if (selected<0 || !ground_swipe(board,selected,after,gained)) return 1;
                ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES];
                std::copy(after,after+16,board); score+=gained;
                // Exactly as SOURCE: a winning action also pays its actual spawn.
                spawn_raw(board,environment_p,rng,cell_out,rank_out,1,environment);
                ++environment[TRANSITIONS]; ++steps;
                status=ground_status(board,radix,environment);
            }
            if (!status) status=2;
            results[3*game]=score; results[3*game+1]=steps; results[3*game+2]=status;
            std::copy(board,board+16,final_boards+16*game);
        }
        for (int count=0; count<N_STRATEGY_COUNTS; ++count) strategy[count]+=work[count];
    }
    return 0;
}
