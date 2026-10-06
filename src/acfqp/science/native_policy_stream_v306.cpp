// Frozen full reward/risk H2 policy on the existing actual-world raw stream.
#include "native_split_risk_v301.cpp"

extern "C" void* native_policy_create_v306(uint64_t seed) { return new Stream(seed); }
extern "C" void native_policy_delete_v306(void* handle) { delete static_cast<Stream*>(handle); }
extern "C" void native_policy_state_v306(void* handle, int32_t* board,
    int32_t* pending, int64_t* info) {
    native_stream_state_v286(handle, board, pending, info);
}

extern "C" int native_policy_advance_v306(void* handle,
    const int32_t* patterns, int radix, const double* reward, const double* risk,
    const int32_t* table, const int64_t* line_scores, const int32_t* cells,
    double model_p, double environment_p, int tile_budget, int max_steps,
    int64_t* raw_rows, int64_t* actions, double* values_out, int64_t* games,
    int32_t* lengths, uint64_t* environment, uint64_t* planning,
    uint64_t* representation, uint64_t* work) {
    Stream& s=*static_cast<Stream*>(handle);
    int n_raw=0, n_actions=0, n_games=0;
    while (n_raw<tile_budget) {
        if (s.status!=0) {
            if (s.status!=3) {
                ++s.episode; s.game_start=s.raw; s.step=s.score=0; s.initial=0;
                s.status=3; s.has_pending=false; s.pending_bank=-1;
                std::fill(s.board,s.board+16,0); ++work[STARTS];
            }
            while (s.initial<2 && n_raw<tile_budget) {
                int cell_out, rank_out;
                spawn_raw(s.board,environment_p,s.rng,cell_out,rank_out,0,environment);
                int64_t* row=raw_rows+4*n_raw++;
                row[0]=s.episode; row[1]=0; row[2]=cell_out; row[3]=rank_out;
                ++s.initial; ++s.raw;
            }
            if (s.initial<2) break;
            s.status=ground_status(s.board,radix,environment);
            if (s.status!=0) {
                complete(s,games,n_games,work);
                continue;
            }
            if (n_raw==tile_budget) break;
        }
        int32_t moved[64], legal[4], after[16]; int64_t scores[4], actual_score;
        double tails[4], values[4]; ++work[CHOICES];
        const int chosen=split_choose_v301(s.board,patterns,radix,reward,risk,0,
            table,line_scores,cells,model_p,moved,scores,tails,values,legal,
            planning,representation);
        if (chosen<0 || !ground_swipe(s.board,chosen,after,actual_score)) return 1;
        const bool winning=*std::max_element(after,after+16)>=radix;
        s.has_pending=!winning; s.pending_bank=winning ? -1 : 0;
        if (!winning) std::copy(after,after+16,s.pending);
        std::copy(after,after+16,s.board);
        ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES];
        int cell_out, rank_out;
        spawn_raw(s.board,environment_p,s.rng,cell_out,rank_out,1,environment);
        int64_t* raw=raw_rows+4*n_raw;
        raw[0]=s.episode; raw[1]=1; raw[2]=cell_out; raw[3]=rank_out;
        int64_t* action=actions+5*n_actions;
        action[0]=s.episode; action[1]=s.step; action[2]=chosen;
        action[3]=actual_score; action[4]=n_raw;
        values_out[n_actions]=values[chosen];
        ++n_raw; ++n_actions; ++s.raw; ++s.posts; ++s.step; s.score+=actual_score;
        ++environment[TRANSITIONS];
        s.status=ground_status(s.board,radix,environment);
        if (s.status==-1) { s.has_pending=false; s.pending_bank=-1; }
        if (s.status==0 && s.step==max_steps) {
            s.status=2; s.has_pending=false; s.pending_bank=-1;
        }
        if (s.status!=0) complete(s,games,n_games,work);
    }
    lengths[0]=n_raw; lengths[1]=n_actions; lengths[2]=n_games;
    return 0;
}
