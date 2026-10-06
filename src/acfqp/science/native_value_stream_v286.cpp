// Reuse the independent standard-world primitives; historical files stay intact.
#include "native_continuation_v285.cpp"

extern "C" double ntuple_value_v120(const int32_t*, const int32_t*, int, const double*);
extern "C" double ntuple_update_v120(const int32_t*, const int32_t*, int, double*,
    double, double, int32_t*);
extern "C" int ntuple_choose_v120(const int32_t*, const int32_t*, int, const double*,
    const int32_t*, const int64_t*, const int32_t*, double, double, int32_t*, int64_t*,
    double*, double*, int32_t*, uint64_t*);

namespace {
enum ExtraEnvironment { RAW_TILES=6, INITIAL_TILES, POST_TILES };
enum Learning { UPDATES, PREDICTIONS, LOOKUPS, TABLE_UPDATES, OCCURRENCES };
enum StreamWork { CHOICES, STARTS, COMPLETIONS, WINS, LOSSES, CUTOFFS, CENSORED };
struct Parameters {
    const int32_t *patterns, *extra, *table, *cells;
    const int64_t* scores;
    int radix, mode, convert;
    double *weights;
    double source_goal, goal, failure, failure_shift, success_shift;
};
struct Stream {
    std::mt19937_64 rng;
    uint64_t seed;
    int32_t board[16] = {}, pending[16] = {};
    int64_t episode=-1, step=0, score=0, raw=0, posts=0, game_start=0, pending_bank=-1;
    int status=4, initial=0;
    bool has_pending=false;
    explicit Stream(uint64_t value): rng(value), seed(value) {}
};

int choose(const int32_t* board, const Parameters& p, double model_p, int depth,
           int32_t* moved, int64_t* scores, double* tails, double* values,
           int32_t* legal, uint64_t* counts) {
    if (depth == 2) return frozen_leaf_choose_v135(board,p.patterns,p.extra,p.radix,
        p.mode,p.weights,p.table,p.scores,p.cells,p.source_goal,p.goal,p.failure,
        p.failure_shift,p.success_shift,1.-model_p,model_p,p.convert,
        moved,scores,tails,values,legal,counts);
    ++counts[3];
    if (*std::max_element(board,board+16)>=p.radix) {
        ++counts[6];
        return -2;
    }
    const uint64_t before = counts[0];
    const int raw = ntuple_choose_v120(board,p.patterns,p.radix,p.weights,p.table,
        p.scores,p.cells,1.,p.source_goal,moved,scores,tails,values,legal,counts);
    counts[17] += counts[0]-before;
    if (raw < 0) return raw;
    int best=-1; double value=-std::numeric_limits<double>::infinity();
    for (int a=0; a<4; ++a) if (legal[a]) {
        ++counts[18];
        const bool goal=*std::max_element(moved+16*a,moved+16*(a+1))>=p.radix;
        counts[19] += goal;
        const double converted=goal ? scores[a]/2048.+p.goal
            : p.convert ? values[a]+p.failure_shift+p.success_shift : values[a];
        values[a]=converted;
        if (best<0 || converted>value) { best=a; value=converted; }
    }
    return best;
}

void spawn_raw(int32_t* board, double probability, std::mt19937_64& rng,
               int& cell_out, int& rank_out, int kind, uint64_t* counts) {
    int empty[16], n=0;
    for (int i=0; i<16; ++i) if (!board[i]) empty[n++]=i;
    const double cell_draw=uniform(rng), rank_draw=uniform(rng);
    cell_out=empty[static_cast<int>(cell_draw*n)];
    rank_out=rank_draw<1.-probability ? 1 : 2;
    board[cell_out]=rank_out;
    counts[RANDOM_DRAWS]+=2; ++counts[RAW_TILES];
    ++counts[kind==0 ? INITIAL_TILES : POST_TILES];
}

void update(const int32_t* after, double* weights, double target, int64_t bank,
            int64_t raw, int64_t episode, int64_t step, int kind,
            const Parameters& p, uint64_t* counts, int64_t* events,
            double* event_values, int& n_events) {
    int32_t unique=0;
    const double raw_target=target-(p.failure_shift+p.success_shift);
    const double error=ntuple_update_v120(after,p.patterns,p.radix,weights,raw_target,.0025,&unique);
    ++counts[UPDATES]; ++counts[PREDICTIONS]; counts[LOOKUPS]+=32;
    counts[TABLE_UPDATES]+=unique; counts[OCCURRENCES]+=32;
    int64_t* row=events+5*n_events;
    row[0]=raw; row[1]=episode; row[2]=step; row[3]=bank; row[4]=kind;
    event_values[3*n_events]=target; event_values[3*n_events+1]=raw_target;
    event_values[3*n_events+2]=error;
    ++n_events;
}

void complete(Stream& s, int64_t* games, int& n_games, uint64_t* work) {
    int64_t* row=games+6*n_games++;
    row[0]=s.episode; row[1]=s.game_start; row[2]=s.raw;
    row[3]=s.step; row[4]=s.score; row[5]=s.status;
    ++work[COMPLETIONS]; ++work[s.status==1 ? WINS : s.status==-1 ? LOSSES : CUTOFFS];
}
}

extern "C" void* native_stream_create_v286(uint64_t seed) { return new Stream(seed); }
extern "C" void native_stream_delete_v286(void* handle) { delete static_cast<Stream*>(handle); }
extern "C" void native_stream_state_v286(void* handle, int32_t* board,
    int32_t* pending, int64_t* info) {
    const Stream& s=*static_cast<Stream*>(handle);
    std::copy(s.board,s.board+16,board); std::copy(s.pending,s.pending+16,pending);
    const int64_t values[]={s.episode,s.step,s.score,s.status,s.initial,s.has_pending,
        s.pending_bank,s.raw,s.posts,s.game_start,static_cast<int64_t>(s.seed)};
    std::copy(values,values+11,info);
}

extern "C" int native_stream_advance_v286(void* handle,
    const int32_t* patterns, const int32_t* extra, int radix, int mode,
    double* weights, double* previous_weights, const int32_t* table,
    const int64_t* line_scores, const int32_t* cells, double source_goal,
    double goal, double failure, double failure_shift, double success_shift,
    int convert, int64_t bank, int writable, int previous_writable,
    double model_p, double environment_p, int tile_budget, int max_postaction,
    int max_steps, int depth, int stop_on_game_end,
    int64_t* raw_rows, int64_t* actions, double* predictions,
    int64_t* update_events, double* update_values, int64_t* games,
    int32_t* lengths, uint64_t* environment, uint64_t* planning,
    uint64_t* active_learning, uint64_t* previous_learning, uint64_t* work) {
    Stream& s=*static_cast<Stream*>(handle);
    const Parameters p{patterns,extra,table,cells,line_scores,radix,mode,convert,
        weights,source_goal,goal,failure,failure_shift,success_shift};
    int n_raw=0, n_actions=0, n_updates=0, n_games=0;
    while (n_raw<tile_budget && n_actions<max_postaction) {
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
                if (stop_on_game_end) break;
                continue;
            }
            if (n_raw==tile_budget) break;
        }
        int32_t moved[64], legal[4], after[16]; int64_t scores[4], actual_score;
        double tails[4], values[4]; ++work[CHOICES];
        const int selected=choose(s.board,p,model_p,depth,moved,scores,tails,values,legal,planning);
        if (selected<0 || !ground_swipe(s.board,selected,after,actual_score)) return 1;
        const bool winning=*std::max_element(after,after+16)>=radix;
        const bool pending_active=s.pending_bank==bank;
        const bool fit_previous=s.has_pending && (pending_active ? writable : previous_writable);
        double next_tail=0.;
        if (fit_previous) {
            if (winning) next_tail=goal;
            else {
                const double raw_tail=ntuple_value_v120(after,patterns,radix,weights);
                next_tail=raw_tail+p.failure_shift+p.success_shift;
                ++active_learning[PREDICTIONS]; active_learning[LOOKUPS]+=32;
            }
        }
        // Read the new-bank target before modifying the saved old-bank weights.
        if (fit_previous)
            update(s.pending,pending_active ? weights : previous_weights,
                actual_score/2048.+next_tail,s.pending_bank,s.raw,s.episode,s.step,0,p,
                pending_active ? active_learning : previous_learning,
                update_events,update_values,n_updates);
        const int64_t step_before=s.step;
        s.has_pending=!winning; s.pending_bank=winning ? -1 : bank;
        if (!winning) std::copy(after,after+16,s.pending);
        std::copy(after,after+16,s.board);
        ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES];
        int cell_out, rank_out;
        spawn_raw(s.board,environment_p,s.rng,cell_out,rank_out,1,environment);
        int64_t* raw=raw_rows+4*n_raw;
        raw[0]=s.episode; raw[1]=1; raw[2]=cell_out; raw[3]=rank_out;
        int64_t* action=actions+5*n_actions;
        action[0]=s.episode; action[1]=step_before; action[2]=selected;
        action[3]=actual_score; action[4]=n_raw;
        predictions[2*n_actions]=values[selected]; predictions[2*n_actions+1]=next_tail;
        ++n_raw; ++n_actions; ++s.raw; ++s.posts; ++s.step; s.score+=actual_score;
        ++environment[TRANSITIONS];
        s.status=ground_status(s.board,radix,environment);
        if (s.status==-1 && s.has_pending) {
            if (writable) update(s.pending,weights,-failure,bank,s.raw,s.episode,step_before,
                1,p,active_learning,update_events,update_values,n_updates);
            s.has_pending=false; s.pending_bank=-1;
        }
        if (s.status==0 && s.step==max_steps) {
            s.status=2; work[CENSORED]+=s.has_pending;
            s.has_pending=false; s.pending_bank=-1;
        }
        if (s.status!=0) {
            complete(s,games,n_games,work);
            if (stop_on_game_end) break;
        }
    }
    lengths[0]=n_raw; lengths[1]=n_actions; lengths[2]=n_updates; lengths[3]=n_games;
    return 0;
}

extern "C" int native_stream_evaluate_v286(const uint64_t* seeds, int n_seeds,
    const int32_t* patterns, const int32_t* extra, int radix, int mode,
    double* weights, const int32_t* table, const int64_t* line_scores,
    const int32_t* cells, double source_goal, double goal, double failure,
    double failure_shift, double success_shift, int convert,
    double model_p, double environment_p, int depth, int max_steps,
    int64_t* results, int32_t* final_boards, uint64_t* environment, uint64_t* planning) {
    const Parameters p{patterns,extra,table,cells,line_scores,radix,mode,convert,
        weights,source_goal,goal,failure,failure_shift,success_shift};
    for (int i=0; i<n_seeds; ++i) {
        std::mt19937_64 rng(seeds[i]); int32_t board[16]={}; int cell_out, rank_out;
        for (int tile=0; tile<2; ++tile)
            spawn_raw(board,environment_p,rng,cell_out,rank_out,0,environment);
        int status=ground_status(board,radix,environment), steps=0;
        int64_t score=0;
        while (!status && steps<max_steps) {
            int32_t moved[64], legal[4], after[16]; int64_t scores[4], gained;
            double tails[4], values[4];
            const int chosen=choose(board,p,model_p,depth,moved,scores,tails,values,legal,planning);
            if (chosen<0 || !ground_swipe(board,chosen,after,gained)) return 1;
            ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES];
            std::copy(after,after+16,board); score+=gained;
            spawn_raw(board,environment_p,rng,cell_out,rank_out,1,environment);
            ++environment[TRANSITIONS]; ++steps;
            status=ground_status(board,radix,environment);
        }
        if (!status) status=2;
        results[3*i]=score; results[3*i+1]=steps; results[3*i+2]=status;
        std::copy(board,board+16,final_boards+16*i);
    }
    return 0;
}
