// Exact retained-stream replay. Reuse the arithmetic and feature order of V120.
#include "controlled_predictive_ntuple_kernel_v120.cpp"
#include <array>
#include <cmath>
#include <cstring>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

namespace {
enum Category { LOSS=0, WIN_BOUNDARY=1, BOOTSTRAP=2 };
struct Probe {
    std::array<int32_t, 16> old_board, new_board;
    std::map<int64_t, int> coefficients;
    std::array<double, 3> exact{};
    std::array<uint64_t, 3> overlap{};
};
struct Replay {
    double* weights;
    const int32_t *patterns, *table, *cells;
    const int64_t* scores;
    int radix;
    double reward, goal, failure, first_shift, second_shift, offset, alpha;
    bool shifted;
    std::vector<Probe> probes;
    std::unordered_map<int64_t, std::vector<std::pair<int, int>>> postings;
    std::unordered_map<int64_t, std::array<double, 3>> changes;
    std::vector<int> overlap, touched;
    std::vector<double> direct;
    std::vector<unsigned char> seen;
    std::array<uint64_t, 16> counts{};
    std::array<uint64_t, 3> categories{};
    // error sum, absolute error sum, absolute actual weight changes, max |error|.
    std::array<double, 12> stats{};
    std::string error;

    bool won(const int32_t* b) const {
        return *std::max_element(b,b+16)>=radix;
    }
    double value(const int32_t* b) const {
        return won(b) ? 0. : prediction(b,patterns,radix,weights);
    }
    void feature_gap(Probe& p) {
        int64_t indices[32];
        if (!won(p.old_board.data())) {
            addresses(p.old_board.data(),patterns,radix,indices);
            for (auto x:indices) --p.coefficients[x];
        }
        if (!won(p.new_board.data())) {
            addresses(p.new_board.data(),patterns,radix,indices);
            for (auto x:indices) ++p.coefficients[x];
        }
        for (auto it=p.coefficients.begin();it!=p.coefficients.end();) {
            if (!it->second) it=p.coefficients.erase(it); else ++it;
        }
    }
    bool check(bool ok,const char* why,int step) {
        if (!ok) error=std::string(why)+" at retained segment step "+std::to_string(step);
        return ok;
    }
    bool update(const int32_t* board,double target,double stored_raw,double stored_error,
                int category,int step) {
        if (!check(!won(board),"goal afterstate cannot be fitted",step)) return false;
        int64_t indices[32];
        addresses(board,patterns,radix,indices);
        double before=0.;
        for (auto x:indices) before+=weights[x];
        const double raw=target-offset, error_value=raw-before;
        if (!check(raw==stored_raw,"raw TD target mismatch",step) ||
            !check(error_value==stored_error,"TD error mismatch",step)) return false;
        ++counts[3]; ++counts[4]; ++counts[5]; counts[6]+=32;
        ++categories[category];
        stats[category*4]+=error_value;
        stats[category*4+1]+=std::abs(error_value);
        stats[category*4+3]=std::max(stats[category*4+3],std::abs(error_value));
        std::sort(indices,indices+32);
        touched.clear();
        for (int first=0;first<32;) {
            int end=first+1;
            while (end<32 && indices[end]==indices[first]) ++end;
            const int multiplicity=end-first;
            const int64_t address=indices[first];
            const double previous=weights[address];
            weights[address]+=alpha*error_value*multiplicity;
            const double actual=weights[address]-previous;
            ++counts[7]; stats[category*4+2]+=std::abs(actual);
            auto at=postings.find(address);
            if (at!=postings.end()) {
                changes[address][category]+=actual;
                ++counts[8];
                for (auto item:at->second) {
                    const int p=item.first, coefficient=item.second;
                    if (!seen[p]) { seen[p]=1; touched.push_back(p); overlap[p]=0; direct[p]=0.; }
                    overlap[p]+=multiplicity*coefficient;
                    direct[p]+=actual*coefficient;
                    ++counts[9];
                }
            }
            first=end;
        }
        for (int p:touched) {
            if (overlap[p]) ++probes[p].overlap[category];
            if (std::equal(board,board+16,probes[p].old_board.begin()) ||
                std::equal(board,board+16,probes[p].new_board.begin())) {
                probes[p].exact[category]+=direct[p]; ++counts[10];
            }
            seen[p]=0;
        }
        return true;
    }
};
}

extern "C" void* td_attribution_create_v132(double* weights,const int32_t* patterns,
    int radix,const int32_t* table,const int64_t* scores,const int32_t* cells,
    const double* query,int shifted,const int32_t* old_boards,const int32_t* new_boards,int n) {
    Replay* r=new Replay;
    r->weights=weights;r->patterns=patterns;r->radix=radix;r->table=table;r->scores=scores;r->cells=cells;
    r->reward=query[0];r->goal=query[1];r->failure=query[2];r->first_shift=query[3];
    r->second_shift=query[4];r->offset=query[5];r->alpha=query[6];r->shifted=shifted;
    r->probes.resize(n);r->overlap.resize(n);r->direct.resize(n);r->seen.resize(n);
    for (int p=0;p<n;++p) {
        auto& probe=r->probes[p];
        std::copy(old_boards+p*16,old_boards+(p+1)*16,probe.old_board.begin());
        std::copy(new_boards+p*16,new_boards+(p+1)*16,probe.new_board.begin());
        r->feature_gap(probe);
        for (auto item:probe.coefficients) r->postings[item.first].push_back({p,item.second});
    }
    return r;
}

extern "C" void td_attribution_destroy_v132(void* ptr) { delete static_cast<Replay*>(ptr); }
extern "C" const char* td_attribution_error_v132(void* ptr) { return static_cast<Replay*>(ptr)->error.c_str(); }

extern "C" void td_attribution_counts_v132(void* ptr,uint64_t* counts,uint64_t* categories,double* stats) {
    const Replay& r=*static_cast<Replay*>(ptr);
    std::copy(r.counts.begin(),r.counts.end(),counts);
    std::copy(r.categories.begin(),r.categories.end(),categories);
    std::copy(r.stats.begin(),r.stats.end(),stats);
}

extern "C" int td_attribution_segment_v132(void* ptr,int n,int32_t* board,int32_t* pending,
    int has_pending,const int32_t* actions,const int64_t* stored_scores,const int32_t* spawn_cells,
    const int32_t* spawn_ranks,const double* chosen,const double* raw_chosen,
    const double* targets,const double* raw_targets,const double* errors,
    int terminal,const double* terminal_data,int32_t* pending_result) {
    Replay& r=*static_cast<Replay*>(ptr);r.error.clear();
    for (int step=0;step<n;++step) {
        int32_t moved[64],legal[4];int64_t scores[4];double tails[4],values[4];uint64_t work[7]={};
        if (!r.check(!r.won(board),"transition begins at goal",step)) return -1;
        ntuple_choose_v120(board,r.patterns,r.radix,r.weights,r.table,r.scores,r.cells,
            r.reward,0.,moved,scores,tails,values,legal,work);
        r.counts[11]+=work[0];r.counts[12]+=work[1];r.counts[13]+=work[4];r.counts[14]+=work[5];
        int best=-1;double best_value=-std::numeric_limits<double>::infinity();
        double corrected[4],raw[4];
        for (int a=0;a<4;++a) {
            if (!legal[a]) continue;
            const bool goal=r.won(moved+a*16);
            raw[a]=goal ? static_cast<double>(scores[a])/2048. : values[a];
            corrected[a]=goal ? static_cast<double>(scores[a])/2048.+r.goal :
                (r.shifted ? values[a]+r.first_shift+r.second_shift : values[a]);
            if (best<0 || corrected[a]>best_value) { best=a;best_value=corrected[a]; }
        }
        const int a=actions[step];
        if (!r.check(best==a,"greedy action mismatch",step) ||
            !r.check(legal[a] && scores[a]==stored_scores[step],"legal swipe or score mismatch",step) ||
            !r.check(corrected[a]==chosen[step],"chosen value mismatch",step) ||
            !r.check(raw[a]==raw_chosen[step],"chosen raw value mismatch",step)) return -1;
        ++r.counts[0]; ++r.counts[1];r.counts[2]+=2;
        if (has_pending) {
            if (!r.check(targets[step]==corrected[a],"TD target mismatch",step)) return -1;
            const int category=r.won(moved+a*16) ? WIN_BOUNDARY : BOOTSTRAP;
            if (!r.update(pending,corrected[a],raw_targets[step],errors[step],category,step)) return -1;
        } else if (!r.check(std::isnan(targets[step]) && std::isnan(raw_targets[step]) &&
                           std::isnan(errors[step]),"unexpected pending update",step)) return -1;
        has_pending=!r.won(moved+a*16);
        if (has_pending) std::copy(moved+a*16,moved+(a+1)*16,pending);
        std::copy(moved+a*16,moved+(a+1)*16,board);
        const int cell=spawn_cells[step],rank=spawn_ranks[step];
        if (!r.check(cell>=0 && cell<16 && board[cell]==0 && (rank==1 || rank==2),
                     "recorded spawn mismatch",step)) return -1;
        board[cell]=rank;++r.counts[15];
    }
    if (terminal) {
        if (!r.check(has_pending,"loss lacks pending update",n) ||
            !r.check(terminal_data[0]==-r.failure,"terminal target mismatch",n)) return -1;
        if (!r.update(pending,-r.failure,terminal_data[1],terminal_data[2],LOSS,n)) return -1;
        has_pending=0;
    }
    if (has_pending) std::copy(pending,pending+16,pending_result);
    return has_pending;
}

extern "C" void td_attribution_summary_v132(void* ptr,double* contributions,double* exact,
    uint64_t* overlap,uint64_t* counts,uint64_t* categories,double* stats) {
    const Replay& r=*static_cast<Replay*>(ptr);
    std::copy(r.counts.begin(),r.counts.end(),counts);
    std::copy(r.categories.begin(),r.categories.end(),categories);
    std::copy(r.stats.begin(),r.stats.end(),stats);
    for (size_t p=0;p<r.probes.size();++p) {
        for (int category=0;category<3;++category) {
            double value=0.;
            for (auto feature:r.probes[p].coefficients) {
                auto at=r.changes.find(feature.first);
                if (at!=r.changes.end()) value+=feature.second*at->second[category];
            }
            contributions[p*3+category]=value;
            exact[p*3+category]=r.probes[p].exact[category];
            overlap[p*3+category]=r.probes[p].overlap[category];
        }
    }
}
