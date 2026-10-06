// Frozen FIRST H2 query calls, ground one-step labels and rootgroup-only commits.
#include "native_split_risk_v301.cpp"

namespace {
struct QueryPoint { int32_t board[16]; int64_t path[4]; };
enum QueryCount { ANCHORS, LEAF_QUERIES, POOL_CELLS, POOL_PATH_FIELDS,
    SELECTOR_DRAWS, VALID_ANCHORS, SELECTED_ROOTS, POOL_BYTES_PEAK };
enum SupervisionCount { ROOTS, REPLICAS, START_SPAWNS, DIRECT_CHOICES, DIRECT_CANDIDATES,
    DIRECT_LEGAL_CANDIDATES, TEACHER_PREDICTIONS, TEACHER_REWARD_READS, TEACHER_WIN_READS,
    ANALYTIC_WIN_CANDIDATES, TARGET_BOOTSTRAPS, TARGET_WINS, TARGET_LOSSES, BRANCH_CHECKS };
enum GroupTarget { GROUP_TARGETS, REWARD_REPLICA_READS, WIN_REPLICA_READS,
    REWARD_MEAN_SUMS, WIN_MEAN_SUMS, MEAN_DIVISIONS, NOISE_RESIDUALS,
    NOISE_SQUARES, NOISE_SUMS, NOISE_DIVISIONS, NOISE_ROOTS };
enum GroupNorm { ROOTGROUPS, GROUP_FEATURES, GROUP_OCCURRENCES, GROUP_DIGITS,
    GROUP_ADDRESS_PRODUCTS, GROUP_SORTS, GROUP_SORT_ITEMS, GROUP_SORT_COMPARISONS,
    GROUP_DENOMINATOR_VISITS, GROUP_UNIQUE_ADDRESSES, GROUP_REWARD_GRADIENT_PRODUCTS,
    GROUP_WIN_GRADIENT_PRODUCTS, GROUP_DIVISIONS, GROUP_UPDATE_PRODUCTS,
    GROUP_COMMITS, GROUP_REWARD_COMMITS, GROUP_WIN_COMMITS,
    GROUP_REWARD_WRITES, GROUP_WIN_WRITES, GROUP_WORKSPACE_BYTES };

double query_leaf_value(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,int kind,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,uint64_t* planning,uint64_t* representation,std::vector<QueryPoint>& pool,
    int root_action,int spawn_cell,int spawn_rank) {
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
            double predicted[4]; split_prediction(after,patterns,radix,reward,risk,kind,predicted,representation);
            tail=predicted[3]; ++planning[4]; planning[5]+=32;
            QueryPoint point; std::copy(after,after+16,point.board);
            point.path[0]=root_action; point.path[1]=spawn_cell; point.path[2]=spawn_rank; point.path[3]=action;
            pool.push_back(point);
        }
        const double value=score/2048.+tail;
        if (value>chosen) chosen=value;
    }
    if (!legal) { ++planning[26]; return -4.; }
    return chosen;
}

int query_choose(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,int kind,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,double probability,
    int32_t* moved,int64_t* scores,double* tails,double* values,int32_t* legal,
    uint64_t* planning,uint64_t* representation,std::vector<QueryPoint>& pool) {
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
                const double tail=query_leaf_value(spawned,patterns,radix,reward,risk,kind,
                    table,line_scores,cells,planning,representation,pool,action,cell,rank);
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

}

extern "C" void query_roots_v319(const int32_t* anchors,int n,uint64_t seed,
    const int32_t* patterns,int radix,const double* reward,const double* risk,
    const int32_t* table,const int64_t* line_scores,const int32_t* cells,double model_p,
    int32_t* roots,int32_t* valid,int64_t* provenance,int32_t* chosen_actions,int32_t* chosen_after,
    int32_t* moved,int64_t* scores,double* tails,double* values,int32_t* legal,
    uint64_t* planning,uint64_t* representation,uint64_t* counts) {
    std::mt19937_64 rng(seed); std::vector<QueryPoint> pool;
    for (int anchor=0; anchor<n; ++anchor) {
        ++counts[ANCHORS]; pool.clear();
        const int best=query_choose(anchors+16*anchor,patterns,radix,reward,risk,0,
            table,line_scores,cells,model_p,moved+64*anchor,scores+4*anchor,
            tails+4*anchor,values+4*anchor,legal+4*anchor,planning,representation,pool);
        chosen_actions[anchor]=best;
        std::copy(best<0 ? anchors+16*anchor : moved+64*anchor+16*best,
            best<0 ? anchors+16*anchor+16 : moved+64*anchor+16*(best+1),chosen_after+16*anchor);
        const double draw=uniform(rng); ++counts[SELECTOR_DRAWS];
        counts[LEAF_QUERIES]+=pool.size(); counts[POOL_CELLS]+=16*pool.size();
        counts[POOL_PATH_FIELDS]+=4*pool.size();
        counts[POOL_BYTES_PEAK]=std::max(counts[POOL_BYTES_PEAK],uint64_t(pool.capacity()*sizeof(QueryPoint)));
        provenance[6*anchor+5]=pool.size(); valid[anchor]=!pool.empty();
        if (!pool.empty()) {
            const int64_t selected=static_cast<int64_t>(draw*pool.size());
            const QueryPoint& point=pool[selected];
            std::copy(point.board,point.board+16,roots+16*anchor);
            std::copy(point.path,point.path+4,provenance+6*anchor);
            provenance[6*anchor+4]=selected;
            ++counts[VALID_ANCHORS]; ++counts[SELECTED_ROOTS];
        }
    }
}

extern "C" int supervise_v319(const int32_t* roots,int n,int repeats,uint64_t seed,
    const int32_t* patterns,int radix,const double* reward,const double* risk,
    const int32_t* table,const int64_t* line_scores,const int32_t* cells,double true_p,
    double* targetreward,double* targetwin,int32_t* selected,int32_t* kinds,
    int32_t* spawn_cells,int32_t* spawn_ranks,uint64_t* environment,
    uint64_t* planning,uint64_t* representation,uint64_t* counts) {
    std::mt19937_64 rng(seed);
    for (int root=0; root<n; ++root) {
        ++counts[ROOTS];
        for (int replica=0; replica<repeats; ++replica) {
            const int index=root*repeats+replica; ++counts[REPLICAS];
            int32_t board[16]; std::copy(roots+16*root,roots+16*root+16,board);
            int cell,rank; spawn_raw(board,true_p,rng,cell,rank,1,environment);
            spawn_cells[index]=cell; spawn_ranks[index]=rank; ++counts[START_SPAWNS];
            targetreward[index]=targetwin[index]=0.; selected[index]=-1; kinds[index]=3;
            const int status=ground_status(board,radix,environment);
            if (status==-1) { ++counts[TARGET_LOSSES]; continue; }
            int best=-1; double maximum=-std::numeric_limits<double>::infinity();
            int32_t best_after[16]; int64_t best_score=0;
            ++counts[DIRECT_CHOICES]; ++planning[3];
            for (int action=0; action<4; ++action) {
                int32_t after[16]; int64_t score;
                split_swipe(board,action,table,line_scores,cells,radix,after,score,planning);
                ++counts[DIRECT_CANDIDATES]; ++planning[17];
                if (std::equal(board,board+16,after)) continue;
                ++counts[DIRECT_LEGAL_CANDIDATES]; ++planning[2]; ++planning[3]; ++planning[18];
                double rt=score/2048.,pt,tail; int kind;
                if (*std::max_element(after,after+16)>=radix) {
                    pt=1.; tail=4.; kind=2; ++counts[ANALYTIC_WIN_CANDIDATES];
                    ++planning[6]; ++planning[19];
                } else {
                    double prediction[4]; split_prediction(after,patterns,radix,reward,risk,0,prediction,representation);
                    rt+=prediction[0]; pt=prediction[1]; tail=prediction[3]; kind=1;
                    ++counts[TEACHER_PREDICTIONS]; counts[TEACHER_REWARD_READS]+=32; counts[TEACHER_WIN_READS]+=32;
                    ++planning[4]; planning[5]+=32;
                }
                const double value=score/2048.+tail;
                if (best<0 || value>maximum) {
                    best=action; maximum=value; best_score=score; std::copy(after,after+16,best_after);
                    targetreward[index]=rt; targetwin[index]=pt; selected[index]=action; kinds[index]=kind;
                }
            }
            int32_t actual[16]; int64_t gained;
            if (best<0 || !ground_swipe(board,best,actual,gained)) return 1;
            ++environment[EXPLICIT_SWIPES]; ++environment[ALL_SWIPES]; ++environment[TRANSITIONS];
            ++counts[BRANCH_CHECKS];
            if (gained!=best_score || !std::equal(actual,actual+16,best_after)) return 2;
            ++counts[kinds[index]==2 ? TARGET_WINS : TARGET_BOOTSTRAPS];
        }
    }
    return 0;
}

extern "C" void fit_supervision_v319(const int32_t* roots,int n,const double* targetreward,
    const double* targetwin,int repeats,const int32_t* patterns,int radix,
    double* reward,double* risk,double alpha,uint64_t* learning,uint64_t* targets,
    uint64_t* normalization,uint64_t* representation,int64_t* examples,double* values,double* noise) {
    double reward_noise=0.,win_noise=0.;
    for (int root=0; root<n; ++root) {
        ++targets[GROUP_TARGETS]; double rt=0.,pt=0.;
        for (int replica=0; replica<repeats; ++replica) {
            rt+=targetreward[root*repeats+replica]; pt+=targetwin[root*repeats+replica];
            ++targets[REWARD_REPLICA_READS]; ++targets[WIN_REPLICA_READS];
            ++targets[REWARD_MEAN_SUMS]; ++targets[WIN_MEAN_SUMS];
        }
        rt/=repeats; pt/=repeats; targets[MEAN_DIVISIONS]+=2;
        for (int replica=0; replica<repeats; ++replica) {
            const double dr=targetreward[root*repeats+replica]-rt,dp=targetwin[root*repeats+replica]-pt;
            reward_noise+=dr*dr; win_noise+=dp*dp;
            ++targets[REWARD_REPLICA_READS]; ++targets[WIN_REPLICA_READS];
            targets[NOISE_RESIDUALS]+=2; targets[NOISE_SQUARES]+=2; targets[NOISE_SUMS]+=2;
        }
        int64_t addresses[32],sorted[32]; split_addresses(roots+16*root,patterns,radix,addresses);
        std::copy(addresses,addresses+32,sorted); ++normalization[ROOTGROUPS];
        ++normalization[GROUP_FEATURES]; normalization[GROUP_OCCURRENCES]+=32;
        normalization[GROUP_DIGITS]+=192; normalization[GROUP_ADDRESS_PRODUCTS]+=192;
        ++normalization[GROUP_SORTS]; normalization[GROUP_SORT_ITEMS]+=32;
        std::sort(sorted,sorted+32,[normalization](int64_t a,int64_t b) {
            ++normalization[GROUP_SORT_COMPARISONS]; return a<b;
        });
        const double rp=split_ntuple(addresses,reward), pp=split_sigmoid(split_logit(addresses,nullptr,0,risk,representation),representation);
        const double combined=split_combine(rp,pp,representation),re=rt-rp,pe=pt-pp;
        const double sample[]={rt,pt,rp,pp,combined,re,pe};
        if (!root) { examples[0]=root; std::copy(sample,sample+7,values); }
        examples[1]=root; std::copy(sample,sample+7,values+7);
        ++learning[SAMPLES]; ++learning[COMBINED_PREDICTIONS]; ++learning[REWARD_PREDICTIONS]; ++learning[RISK_PREDICTIONS];
        learning[ALL_LOOKUPS]+=64; learning[REWARD_LOOKUPS]+=32; learning[RISK_LOOKUPS]+=32; learning[REWARD_OCCURRENCES]+=32;
        for (int first=0; first<32;) {
            int next=first+1; while (next<32 && sorted[next]==sorted[first]) ++next;
            const double multiplicity=next-first;
            normalization[GROUP_DENOMINATOR_VISITS]+=next-first; ++normalization[GROUP_UNIQUE_ADDRESSES];
            reward[sorted[first]]+=alpha*(multiplicity*re)/multiplicity;
            risk[sorted[first]]+=alpha*(multiplicity*pe)/multiplicity;
            ++normalization[GROUP_REWARD_GRADIENT_PRODUCTS]; ++normalization[GROUP_WIN_GRADIENT_PRODUCTS];
            normalization[GROUP_DIVISIONS]+=2; normalization[GROUP_UPDATE_PRODUCTS]+=2;
            ++normalization[GROUP_REWARD_WRITES]; ++normalization[GROUP_WIN_WRITES];
            ++learning[REWARD_WRITES]; ++learning[RISK_WRITES]; learning[ALL_WRITES]+=2;
            first=next;
        }
        ++normalization[GROUP_COMMITS]; ++normalization[GROUP_REWARD_COMMITS]; ++normalization[GROUP_WIN_COMMITS];
        normalization[GROUP_WORKSPACE_BYTES]=sizeof(addresses)+sizeof(sorted);
    }
    noise[0]=n ? std::sqrt(reward_noise/(n*repeats)) : 0.;
    noise[1]=n ? std::sqrt(win_noise/(n*repeats)) : 0.;
    if (n) { targets[NOISE_DIVISIONS]+=2; targets[NOISE_ROOTS]+=2; }
}
