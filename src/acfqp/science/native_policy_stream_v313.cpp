// Actual frozen LOCAL or LINEAR_WIN policy callbacks on the physical raw stream.
#include "native_value_stream_v286.cpp"

namespace {
using LocalChoose=int (*)(const int32_t*,const int32_t*,int,const double*,const double*,
    int,const int32_t*,const int64_t*,const int32_t*,double,int32_t*,int64_t*,
    double*,double*,int32_t*,uint64_t*,uint64_t*);
using LinearChoose=int (*)(const int32_t*,const int32_t*,int,const double*,const double*,
    const int32_t*,const int64_t*,const int32_t*,double,int32_t*,int64_t*,
    double*,double*,int32_t*,uint64_t*,uint64_t*);
using LocalPredict=void (*)(const int32_t*,const int32_t*,int,const double*,const double*,
    int,double*,uint64_t*);
using LinearPredict=void (*)(const int32_t*,const int32_t*,int,const double*,const double*,
    double*,uint64_t*);

int h2_choose(void* callback,int kind,const int32_t* board,const int32_t* patterns,
    int radix,const double* reward,const double* second,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,double model_p,int32_t* moved,
    int64_t* scores,double* tails,double* values,int32_t* legal,
    uint64_t* planning,uint64_t* representation) {
    if (!kind) return reinterpret_cast<LocalChoose>(callback)(board,patterns,radix,
        reward,second,0,table,line_scores,cells,model_p,moved,scores,tails,values,legal,
        planning,representation);
    return reinterpret_cast<LinearChoose>(callback)(board,patterns,radix,reward,
        second,table,line_scores,cells,model_p,moved,scores,tails,values,legal,
        planning,representation);
}
}

extern "C" int direct_choose_v313(void* predict,int kind,const int32_t* board,
    const int32_t* patterns,int radix,const double* reward,const double* second,
    const int32_t* table,const int64_t* line_scores,const int32_t* cells,
    int32_t* moved,int64_t* scores,double* tails,double* values,int32_t* legal,
    uint64_t* planning,uint64_t* representation) {
    ++planning[3];
    if (*std::max_element(board,board+16)>=radix) { ++planning[6]; return -2; }
    int best=-1; double maximum=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        int32_t* after=moved+16*action;
        std::copy(board,board+16,after); scores[action]=0;
        ++planning[0]; ++planning[17];
        for (int line=0; line<4; ++line) {
            const int32_t* positions=cells+16*action+4*line; int index=0;
            for (int i=0; i<4; ++i) index=index*radix+board[positions[i]];
            for (int i=0; i<4; ++i) after[positions[i]]=table[4*index+i];
            scores[action]+=line_scores[index]; ++planning[1];
        }
        legal[action]=!std::equal(board,board+16,after);
        if (!legal[action]) continue;
        ++planning[2]; ++planning[3]; ++planning[18];
        if (*std::max_element(after,after+16)>=radix) {
            tails[action]=4.; ++planning[6]; ++planning[19];
        } else {
            double predicted[4];
            if (!kind) {
                reinterpret_cast<LocalPredict>(predict)(after,patterns,radix,reward,
                    second,0,predicted,representation);
                tails[action]=predicted[3];
            } else {
                reinterpret_cast<LinearPredict>(predict)(after,patterns,radix,reward,
                    second,predicted,representation);
                tails[action]=predicted[2];
            }
            ++planning[4]; planning[5]+=32;
        }
        values[action]=scores[action]/2048.+tails[action];
        if (best<0 || values[action]>maximum) { best=action; maximum=values[action]; }
    }
    return best;
}

extern "C" int native_policy_advance_v313(void* handle,void* callback,int kind,
    const int32_t* patterns,int radix,const double* reward,const double* second,
    const int32_t* table,const int64_t* line_scores,const int32_t* cells,
    double model_p,double environment_p,int tile_budget,int max_steps,
    int64_t* raw_rows,int64_t* actions,double* values_out,int32_t* preboards,
    double* action_values,int32_t* action_legal,int64_t* games,
    int32_t* lengths,uint64_t* environment,uint64_t* planning,
    uint64_t* representation,uint64_t* work) {
    Stream& s=*static_cast<Stream*>(handle);
    int n_raw=0,n_actions=0,n_games=0;
    while (n_raw<tile_budget) {
        if (s.status!=0) {
            if (s.status!=3) {
                ++s.episode; s.game_start=s.raw; s.step=s.score=0; s.initial=0;
                s.status=3; s.has_pending=false; s.pending_bank=-1;
                std::fill(s.board,s.board+16,0); ++work[STARTS];
            }
            while (s.initial<2 && n_raw<tile_budget) {
                int cell_out,rank_out;
                spawn_raw(s.board,environment_p,s.rng,cell_out,rank_out,0,environment);
                int64_t* row=raw_rows+4*n_raw++;
                row[0]=s.episode; row[1]=0; row[2]=cell_out; row[3]=rank_out;
                ++s.initial; ++s.raw;
            }
            if (s.initial<2) break;
            s.status=ground_status(s.board,radix,environment);
            if (s.status!=0) { complete(s,games,n_games,work); continue; }
            if (n_raw==tile_budget) break;
        }
        int32_t moved[64],legal[4],after[16]; int64_t scores[4],actual_score;
        double tails[4],values[4]; ++work[CHOICES];
        const int chosen=h2_choose(callback,kind,s.board,patterns,radix,reward,second,
            table,line_scores,cells,model_p,moved,scores,tails,values,legal,planning,representation);
        std::copy(s.board,s.board+16,preboards+16*n_actions);
        std::copy(values,values+4,action_values+4*n_actions);
        std::copy(legal,legal+4,action_legal+4*n_actions);
        if (chosen<0 || !ground_swipe(s.board,chosen,after,actual_score)) return 1;
        const bool winning=*std::max_element(after,after+16)>=radix;
        s.has_pending=!winning; s.pending_bank=winning ? -1 : 0;
        if (!winning) std::copy(after,after+16,s.pending);
        std::copy(after,after+16,s.board);
        ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES];
        int cell_out,rank_out;
        spawn_raw(s.board,environment_p,s.rng,cell_out,rank_out,1,environment);
        int64_t* raw=raw_rows+4*n_raw;
        raw[0]=s.episode; raw[1]=1; raw[2]=cell_out; raw[3]=rank_out;
        int64_t* action=actions+5*n_actions;
        action[0]=s.episode; action[1]=s.step; action[2]=chosen;
        action[3]=actual_score; action[4]=n_raw;
        values_out[n_actions]=values[chosen];
        ++n_raw; ++n_actions; ++s.raw; ++s.posts; ++s.step; s.score+=actual_score;
        ++environment[TRANSITIONS]; s.status=ground_status(s.board,radix,environment);
        if (s.status==-1) { s.has_pending=false; s.pending_bank=-1; }
        if (s.status==0 && s.step==max_steps) {
            s.status=2; s.has_pending=false; s.pending_bank=-1;
        }
        if (s.status!=0) complete(s,games,n_games,work);
    }
    lengths[0]=n_raw; lengths[1]=n_actions; lengths[2]=n_games;
    return 0;
}

extern "C" int evaluate_direct_v313(const uint64_t* seeds,int n_games,void* predict,
    int kind,const int32_t* patterns,int radix,const double* reward,const double* second,
    const int32_t* table,const int64_t* line_scores,const int32_t* cells,
    double environment_p,int max_steps,int64_t* output,int32_t* final_boards,
    uint64_t* environment,uint64_t* planning,uint64_t* representation) {
    for (int game=0; game<n_games; ++game) {
        std::mt19937_64 rng(seeds[game]); int32_t board[16]={}; int position,rank;
        for (int initial=0; initial<2; ++initial) spawn_raw(board,environment_p,rng,position,rank,0,environment);
        int status=ground_status(board,radix,environment),steps=0; int64_t score=0;
        while (!status && steps<max_steps) {
            int32_t moved[64],legal[4],after[16]; int64_t scores[4],gained;
            double tails[4],values[4];
            const int chosen=direct_choose_v313(predict,kind,board,patterns,radix,reward,
                second,table,line_scores,cells,moved,scores,tails,values,legal,planning,representation);
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
