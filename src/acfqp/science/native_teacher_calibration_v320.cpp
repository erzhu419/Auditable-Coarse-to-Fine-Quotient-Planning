// V320: saved DIRECT branch followed by the frozen FIRST H2 policy in the real world.
#include "native_split_risk_v301.cpp"
#include <cstdio>

namespace {
enum CalibrationWork { ROLLOUT_STARTS, SAVED_SPAWNS, RNG_STREAMS, DIRECT_ACTIONS,
    H2_ACTIONS, TERMINAL_WINS, TERMINAL_LOSSES, ACTION_CUTOFFS, TRACE_ROWS,
    TRACE_BYTES, PROBE_SNAPSHOTS, PROBE_BYTES };
}

extern "C" int continue_targets_v320(const int32_t* roots,int n,int repeats,
    const int32_t* start_cells,const int32_t* start_ranks,const int32_t* direct_actions,
    const int32_t* target_kinds,const uint64_t* seeds,const int32_t* patterns,int radix,
    const double* reward,const double* risk,const int32_t* table,const int64_t* line_scores,
    const int32_t* cells,double model_p,double true_p,int max_steps,const char* trace_path,
    const int32_t* probe_slots,int64_t* metrics,int32_t* final_boards,
    int32_t* probe_preboards,int32_t* probe_moved,int64_t* probe_scores,
    double* probe_tails,double* probe_values,int32_t* probe_legal,int32_t* probe_info,
    uint64_t* environment,uint64_t* planning,uint64_t* representation,uint64_t* counts) {
    FILE* trace=std::fopen(trace_path,"wb");
    if (!trace) return 1;
    const auto finish=[&](int code) { return std::fclose(trace) ? 2 : code; };
    for (int group=0; group<n; ++group) for (int member=0; member<repeats; ++member) {
        const int index=group*repeats+member,slot=probe_slots[index];
        ++counts[ROLLOUT_STARTS]; ++counts[SAVED_SPAWNS]; ++counts[RNG_STREAMS];
        std::mt19937_64 rng(seeds[index]);
        int32_t board[16]; std::copy(roots+16*group,roots+16*group+16,board);
        const int start_cell=start_cells[index],start_rank=start_ranks[index];
        if (start_cell<0 || start_cell>=16 || board[start_cell] || (start_rank!=1 && start_rank!=2)) return finish(3);
        board[start_cell]=start_rank; // Already paid and retained in V319; no random draw here.
        int status=ground_status(board,radix,environment),steps=0; int64_t score=0,raw=0;
        if (status==-1) {
            if (target_kinds[index]!=3 || direct_actions[index]!=-1) return finish(4);
        } else if (status || (target_kinds[index]!=1 && target_kinds[index]!=2)) return finish(4);
        while (!status && steps<max_steps) {
            int selected=direct_actions[index];
            if (!steps) {
                ++counts[DIRECT_ACTIONS];
                if (selected<0 || selected>=4) return finish(5);
            } else {
                int32_t moved[64]={},legal[4]={}; int64_t scores[4]={}; double tails[4]={},values[4]={};
                ++counts[H2_ACTIONS];
                selected=split_choose_v301(board,patterns,radix,reward,risk,0,table,line_scores,cells,
                    model_p,moved,scores,tails,values,legal,planning,representation);
                if (selected<0) return finish(6);
                if (slot>=0) for (int boundary=0; boundary<2; ++boundary) {
                    if (!boundary && steps!=1) continue;
                    const int offset=slot*2+boundary;
                    std::copy(board,board+16,probe_preboards+16*offset);
                    std::copy(moved,moved+64,probe_moved+64*offset);
                    std::copy(scores,scores+4,probe_scores+4*offset);
                    std::copy(tails,tails+4,probe_tails+4*offset);
                    std::copy(values,values+4,probe_values+4*offset);
                    std::copy(legal,legal+4,probe_legal+4*offset);
                    probe_info[2*offset]=steps+1; probe_info[2*offset+1]=selected;
                    ++counts[PROBE_SNAPSHOTS];
                    counts[PROBE_BYTES]+=16*4+64*4+4*8+8*8+4*4+2*4;
                }
            }
            int32_t after[16]; int64_t gained;
            if (!ground_swipe(board,selected,after,gained)) return finish(7);
            ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES];
            if (!steps && (target_kinds[index]==2)!=(*std::max_element(after,after+16)>=radix)) return finish(8);
            std::copy(after,after+16,board); score+=gained;
            int spawn_cell,spawn_rank;
            spawn_raw(board,true_p,rng,spawn_cell,spawn_rank,1,environment);
            ++environment[TRANSITIONS]; ++steps; ++raw;
            status=ground_status(board,radix,environment);
            const int32_t row[]={group,member,steps,selected,static_cast<int32_t>(gained),spawn_cell,spawn_rank,status};
            if (std::fwrite(row,sizeof(int32_t),8,trace)!=8) return finish(9);
            ++counts[TRACE_ROWS]; counts[TRACE_BYTES]+=sizeof(row);
        }
        ++counts[status==1 ? TERMINAL_WINS : status==-1 ? TERMINAL_LOSSES : ACTION_CUTOFFS];
        metrics[4*index]=score; metrics[4*index+1]=steps;
        metrics[4*index+2]=status; metrics[4*index+3]=raw;
        std::copy(board,board+16,final_boards+16*index);
    }
    return finish(0);
}
