// Exact FIT-board localization of both frozen LOCAL components at H2 leaves.
#include "native_split_risk_v301.cpp"

namespace {
enum SupportWork { MEMBERSHIP_QUERIES, ENCODED_CELLS, KEY_COMPARISONS,
    BASE_QUERIES, UPDATED_QUERIES };

void localized_prediction(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,const double* base_reward,const double* base_risk,
    const uint64_t* keys,int64_t size,double* predicted,uint64_t* representation,uint64_t* counts) {
    ++counts[MEMBERSHIP_QUERIES]; uint64_t key=0;
    for (int cell=0; cell<16; ++cell) {
        key|=uint64_t(board[cell])<<(4*cell); ++counts[ENCODED_CELLS];
    }
    int64_t low=0,high=size;
    while (low<high) {
        const int64_t middle=low+(high-low)/2; ++counts[KEY_COMPARISONS];
        if (keys[middle]<key) low=middle+1; else high=middle;
    }
    bool updated=false;
    if (low<size) { ++counts[KEY_COMPARISONS]; updated=keys[low]==key; }
    ++counts[updated ? UPDATED_QUERIES : BASE_QUERIES];
    split_prediction(board,patterns,radix,updated ? reward : base_reward,
        updated ? risk : base_risk,0,predicted,representation);
}

double localized_leaf_value(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,const double* base_reward,const double* base_risk,
    const uint64_t* support_keys,int64_t n_support,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,uint64_t* planning,uint64_t* representation,uint64_t* support_counts) {
    ++planning[20]; ++planning[3];
    if (*std::max_element(board,board+16)>=radix) { ++planning[6]; ++planning[27]; return 4.; }
    bool legal=false; double chosen=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        int32_t after[16]; int64_t score;
        split_swipe(board,action,table,line_scores,cells,radix,after,score,planning); ++planning[21];
        if (std::equal(board,board+16,after)) continue;
        legal=true; ++planning[2]; ++planning[3]; double tail;
        if (*std::max_element(after,after+16)>=radix) { ++planning[6]; tail=4.; }
        else {
            double predicted[4]; localized_prediction(after,patterns,radix,reward,risk,base_reward,base_risk,
                support_keys,n_support,predicted,representation,support_counts);
            tail=predicted[3]; ++planning[4]; planning[5]+=32;
        }
        const double value=score/2048.+tail;
        if (value>chosen) chosen=value;
    }
    if (!legal) { ++planning[26]; return -4.; }
    return chosen;
}
}

extern "C" int choose_localized_v318(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,const double* base_reward,const double* base_risk,
    const uint64_t* support_keys,int64_t n_support,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,double probability,
    int32_t* moved,int64_t* scores,double* tails,double* values,int32_t* legal,
    uint64_t* planning,uint64_t* representation,uint64_t* support_counts) {
    ++planning[3];
    if (*std::max_element(board,board+16)>=radix) { ++planning[6]; return -2; }
    int best=-1; double maximum=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        int32_t* after=moved+16*action;
        split_swipe(board,action,table,line_scores,cells,radix,after,scores[action],planning); ++planning[17];
        legal[action]=!std::equal(board,board+16,after);
        if (!legal[action]) continue;
        ++planning[2]; ++planning[3]; ++planning[18];
        if (*std::max_element(after,after+16)>=radix) {
            tails[action]=4.; ++planning[6]; ++planning[19];
        } else {
            int empty=0; for (int i=0; i<16; ++i) empty+=after[i]==0;
            double expectation=0.;
            for (int cell=0; cell<16; ++cell) if (!after[cell]) for (int rank=1; rank<=2; ++rank) {
                int32_t spawned[16]; std::copy(after,after+16,spawned); spawned[cell]=rank;
                ++planning[22]; ++planning[rank==1 ? 23 : 24]; ++planning[25];
                const double tail=localized_leaf_value(spawned,patterns,radix,reward,risk,base_reward,base_risk,
                    support_keys,n_support,table,line_scores,cells,planning,representation,support_counts);
                expectation+=((rank==1 ? 1.-probability : probability)/empty)*tail;
                ++planning[28]; ++planning[29];
            }
            tails[action]=expectation;
        }
        values[action]=scores[action]/2048.+tails[action];
        if (best<0 || values[action]>maximum) { best=action; maximum=values[action]; }
    }
    return best;
}

extern "C" int evaluate_localized_v318(const uint64_t* seeds,int n_games,const int32_t* patterns,
    int radix,const double* reward,const double* risk,const double* base_reward,const double* base_risk,
    const uint64_t* support_keys,int64_t n_support,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,double model_p,double environment_p,int max_steps,
    int64_t* output,int32_t* final_boards,uint64_t* environment,uint64_t* planning,uint64_t* representation,uint64_t* support_counts) {
    for (int game=0; game<n_games; ++game) {
        std::mt19937_64 rng(seeds[game]); int32_t board[16]={}; int position,rank;
        for (int initial=0; initial<2; ++initial) spawn_raw(board,environment_p,rng,position,rank,0,environment);
        int status=ground_status(board,radix,environment),steps=0; int64_t score=0;
        while (!status && steps<max_steps) {
            int32_t moved[64],legal[4],after[16]; int64_t scores[4],gained; double tails[4],values[4];
            const int chosen=choose_localized_v318(board,patterns,radix,reward,risk,base_reward,base_risk,
                support_keys,n_support,table,line_scores,cells,model_p,moved,scores,tails,values,legal,
                planning,representation,support_counts);
            if (chosen<0 || !ground_swipe(board,chosen,after,gained)) return 1;
            ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES];
            std::copy(after,after+16,board); score+=gained;
            spawn_raw(board,environment_p,rng,position,rank,1,environment);
            ++environment[TRANSITIONS]; ++steps; status=ground_status(board,radix,environment);
        }
        if (!status) status=2;
        output[3*game]=score; output[3*game+1]=steps; output[3*game+2]=status;
        std::copy(board,board+16,final_boards+16*game);
    }
    return 0;
}
