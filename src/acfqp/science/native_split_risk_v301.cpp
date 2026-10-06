// V301: two separately fitted factual heads and the unchanged H2/world order.
#include "native_value_stream_v286.cpp"
#include <cmath>
#include <vector>

namespace {
enum SplitLearning { SAMPLES, COMBINED_PREDICTIONS, ALL_LOOKUPS, ALL_WRITES,
    REWARD_OCCURRENCES, REWARD_PREDICTIONS, RISK_PREDICTIONS, REWARD_LOOKUPS,
    RISK_LOOKUPS, REWARD_WRITES, RISK_WRITES };
enum SplitTarget { GAME_LABELS, LABEL_ASSIGNMENTS, REWARD_SUFFIX_ASSIGNMENTS,
    REWARD_SUFFIX_ADDITIONS, SPLIT_GOAL_CHECKS, WINNING_SKIPS,
    UTILITY_SUFFIX_ASSIGNMENTS, UTILITY_SUFFIX_ADDITIONS };
enum SplitNormalization { FIT_GAMES, ADDRESS_EXTRACTIONS, ADDRESS_OCCURRENCES,
    ADDRESS_DIGIT_READS, ADDRESS_MULTIPLY_ADDS, SORT_CALLS, SORT_ITEMS,
    SORT_COMPARISONS, DENOMINATOR_OCCURRENCE_VISITS, UNIQUE_ADDRESSES,
    REWARD_GRADIENT_PRODUCTS, REWARD_GRADIENT_SUMS, RISK_GRADIENT_PRODUCTS,
    RISK_GRADIENT_SUMS, GLOBAL_DENOMINATOR_SUMS, NORMALIZATION_DIVISIONS,
    UPDATE_PRODUCTS, GAME_COMMITS, REWARD_COMMITS, RISK_COMMITS,
    REWARD_PARAMETER_WRITES, RISK_PARAMETER_WRITES, GLOBAL_ZERO_DENOMINATORS,
    ADDRESS_DENOMINATOR_SEARCHES, ADDRESS_DENOMINATOR_COMPARISONS,
    FEATURE_BUFFER_BYTES_PEAK };
enum SplitRepresentation { RISK_SIGMOIDS, LOCAL_RISK_LOOKUPS,
    GLOBAL_FEATURE_EXTRACTIONS, GLOBAL_BOARD_CELL_VISITS, EMPTY_NODE_VISITS,
    EMPTY_NEIGHBOR_PROBES, ADJACENCY_PAIR_VISITS, GLOBAL_LINE_CELL_VISITS,
    COMPRESSED_PAIR_COMPARISONS, MONOTONE_PAIR_COMPARISONS,
    MAX_TILE_NEIGHBOR_PROBES, GLOBAL_DOT_PRODUCTS, GLOBAL_WEIGHT_READS,
    GLOBAL_DOT_MULTIPLICATIONS, GLOBAL_DOT_ADDITIONS, COMBINED_ADDITIONS,
    COMBINED_MULTIPLICATIONS, RISK_LOG_LOSS_EVALUATIONS,
    COMPONENT_ROOT_CHECKS, MAX_CELL_CHECKS, ADJACENCY_SOURCE_VISITS,
    TILE_MASS_EXPONENTIATIONS, GLOBAL_FEATURE_DIVISIONS, GLOBAL_FEATURE_WRITES };

void split_addresses(const int32_t* board, const int32_t* patterns, int radix,
                     int64_t* output) {
    int64_t stride=1;
    for (int digit=0; digit<6; ++digit) stride*=radix;
    for (int tuple=0; tuple<32; ++tuple) {
        int64_t address=0;
        for (int digit=0; digit<6; ++digit)
            address=address*radix+board[patterns[tuple*6+digit]];
        output[tuple]=(tuple/8)*stride+address;
    }
}

double split_ntuple(const int64_t* addresses, const double* weights) {
    double value=0.;
    for (int occurrence=0; occurrence<32; ++occurrence) value+=weights[addresses[occurrence]];
    return value;
}

void split_global_features(const int32_t* b, int radix, double* x, uint64_t* c) {
    std::fill(x,x+20,0.);
    ++c[GLOBAL_FEATURE_EXTRACTIONS];
    int empty=0, maximum=0, second=0, rank_sum=0, rank1=0, rank2=0, edge_occupied=0;
    double mass=0., top_mass=0., second_mass=0.;
    for (int i=0; i<16; ++i) {
        ++c[GLOBAL_BOARD_CELL_VISITS];
        const int rank=b[i];
        empty+=rank==0; rank_sum+=rank; rank1+=rank==1; rank2+=rank==2;
        if (rank>=maximum) { second=maximum; maximum=rank; }
        else if (rank>second) second=rank;
        const int row=i/4,col=i%4;
        edge_occupied+=rank!=0 && (row==0 || row==3 || col==0 || col==3);
        const double tile=rank ? std::ldexp(1.,rank) : 0.;
        c[TILE_MASS_EXPONENTIATIONS]+=rank!=0;
        mass+=tile;
        if (tile>=top_mass) { second_mass=top_mass; top_mass=tile; }
        else if (tile>second_mass) second_mass=tile;
    }
    bool seen[16]={}; int components=0, largest=0;
    for (int root=0; root<16; ++root) {
        ++c[COMPONENT_ROOT_CHECKS];
        if (b[root] || seen[root]) continue;
        ++components; int queue[16],begin=0,end=1; queue[0]=root; seen[root]=true;
        while (begin<end) {
            const int current=queue[begin++]; ++c[EMPTY_NODE_VISITS];
            const int row=current/4,col=current%4;
            const int adjacent[]={row>0 ? current-4 : -1,row<3 ? current+4 : -1,
                col>0 ? current-1 : -1,col<3 ? current+1 : -1};
            for (int neighbor:adjacent) {
                ++c[EMPTY_NEIGHBOR_PROBES];
                if (neighbor>=0 && !b[neighbor] && !seen[neighbor]) {
                    seen[neighbor]=true; queue[end++]=neighbor;
                }
            }
        }
        largest=std::max(largest,end);
    }
    int max_count=0,max_empty=0,max_equal=0,corner=0,edge=0;
    for (int i=0; i<16; ++i) {
        ++c[MAX_CELL_CHECKS];
        if (!maximum || b[i]!=maximum) continue;
        ++max_count; const int row=i/4,col=i%4;
        corner|=(row==0 || row==3) && (col==0 || col==3);
        edge|=row==0 || row==3 || col==0 || col==3;
        const int adjacent[]={row>0 ? i-4 : -1,row<3 ? i+4 : -1,
            col>0 ? i-1 : -1,col<3 ? i+1 : -1};
        int vacant=0,equal=0;
        for (int neighbor:adjacent) {
            ++c[MAX_TILE_NEIGHBOR_PROBES];
            if (neighbor>=0) { vacant+=b[neighbor]==0; equal+=b[neighbor]==maximum; }
        }
        max_empty=std::max(max_empty,vacant); max_equal=std::max(max_equal,equal);
    }
    int equal_pairs=0,difference=0;
    for (int i=0; i<16; ++i) {
        ++c[ADJACENCY_SOURCE_VISITS];
        if (i%4<3) { ++c[ADJACENCY_PAIR_VISITS]; equal_pairs+=b[i]>0 && b[i]==b[i+1]; difference+=std::abs(b[i]-b[i+1]); }
        if (i/4<3) { ++c[ADJACENCY_PAIR_VISITS]; equal_pairs+=b[i]>0 && b[i]==b[i+4]; difference+=std::abs(b[i]-b[i+4]); }
    }
    int compressed_equal=0,monotone=0;
    for (int direction=0; direction<2; ++direction) for (int line=0; line<4; ++line) {
        int packed[4],n=0;
        for (int position=0; position<4; ++position) {
            ++c[GLOBAL_LINE_CELL_VISITS];
            const int rank=b[direction==0 ? 4*line+position : 4*position+line];
            if (rank) packed[n++]=rank;
        }
        bool up=true,down=true;
        for (int i=1; i<n; ++i) {
            ++c[COMPRESSED_PAIR_COMPARISONS]; ++c[MONOTONE_PAIR_COMPARISONS];
            compressed_equal+=packed[i]==packed[i-1];
            up=up && packed[i]>=packed[i-1]; down=down && packed[i]<=packed[i-1];
        }
        monotone+=up || down;
    }
    const double values[]={1.,empty/16.,components/8.,largest/16.,maximum/double(radix),
        second/double(radix),rank_sum/(16.*radix),double(corner),double(edge),max_count/16.,
        max_empty/4.,max_equal/4.,equal_pairs/24.,difference/(24.*radix),compressed_equal/24.,
        monotone/8.,rank1/16.,rank2/16.,mass ? (top_mass+second_mass)/mass : 0.,edge_occupied/12.};
    std::copy(values,values+20,x);
    c[GLOBAL_FEATURE_DIVISIONS]+=mass ? 17 : 16;
    c[GLOBAL_FEATURE_WRITES]+=20;
}

double split_sigmoid(double logit, uint64_t* representation) {
    ++representation[RISK_SIGMOIDS];
    if (logit>=0.) return 1./(1.+std::exp(-logit));
    const double e=std::exp(logit); return e/(1.+e);
}

double split_logit(const int64_t* addresses, const double* global,
    int kind, const double* risk, uint64_t* representation) {
    if (!kind) {
        representation[LOCAL_RISK_LOOKUPS]+=32;
        return split_ntuple(addresses,risk);
    }
    double logit=0.; ++representation[GLOBAL_DOT_PRODUCTS];
    for (int j=0; j<20; ++j) {
        logit+=risk[j]*global[j];
        ++representation[GLOBAL_WEIGHT_READS]; ++representation[GLOBAL_DOT_MULTIPLICATIONS];
        ++representation[GLOBAL_DOT_ADDITIONS];
    }
    return logit;
}

double split_combine(double reward, double probability, uint64_t* representation) {
    representation[COMBINED_ADDITIONS]+=2; ++representation[COMBINED_MULTIPLICATIONS];
    return reward+8.*(probability-.5);
}

void split_prediction(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,int kind,double* result,uint64_t* representation) {
    int64_t addresses[32]; split_addresses(board,patterns,radix,addresses);
    double global[20];
    if (kind) split_global_features(board,radix,global,representation);
    result[0]=split_ntuple(addresses,reward);
    result[2]=split_logit(addresses,global,kind,risk,representation);
    result[1]=split_sigmoid(result[2],representation);
    result[3]=split_combine(result[0],result[1],representation);
}

void split_swipe(const int32_t* board,int action,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,int radix,int32_t* after,
    int64_t& score,uint64_t* planning) {
    std::copy(board,board+16,after); score=0; ++planning[0];
    for (int line=0; line<4; ++line) {
        const int32_t* positions=cells+16*action+4*line; int index=0;
        for (int i=0; i<4; ++i) index=index*radix+board[positions[i]];
        for (int i=0; i<4; ++i) after[positions[i]]=table[4*index+i];
        score+=line_scores[index]; ++planning[1];
    }
}

double split_leaf_value(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,int kind,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,uint64_t* planning,uint64_t* representation) {
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
        }
        const double value=score/2048.+tail;
        if (value>chosen) chosen=value;
    }
    if (!legal) { ++planning[26]; return -4.; }
    return chosen;
}
}

extern "C" void split_features_v301(const int32_t* board,int radix,double* output,uint64_t* representation) {
    split_global_features(board,radix,output,representation);
}

extern "C" void split_predict_v301(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,int kind,double* output,uint64_t* representation) {
    split_prediction(board,patterns,radix,reward,risk,kind,output,representation);
}

extern "C" int split_choose_v301(const int32_t* board,const int32_t* patterns,int radix,
    const double* reward,const double* risk,int kind,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,double probability,
    int32_t* moved,int64_t* scores,double* tails,double* values,int32_t* legal,
    uint64_t* planning,uint64_t* representation) {
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
                const double tail=split_leaf_value(spawned,patterns,radix,reward,risk,kind,
                    table,line_scores,cells,planning,representation);
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

extern "C" void fit_split_v301(const int32_t* afterstates,const double* rewards,
    const int64_t* ends,const int32_t* terminal_codes,int n_fit_games,
    const int32_t* patterns,int radix,double* reward_weights,double* risk_weights,
    int kind,double alpha,uint64_t* learning,uint64_t* targets,
    uint64_t* normalization,uint64_t* representation,int64_t* examples,double* values) {
    int64_t start=0;
    std::vector<double> suffixes,reward_errors,risk_errors,global_features,
        reward_gradients,risk_gradients,global_denominators;
    std::vector<int64_t> steps,features,sorted,unique,denominators;
    for (int game=0; game<n_fit_games; ++game) {
        const int64_t end=ends[game]; const double label=terminal_codes[game]==1 ? 1. : 0.;
        ++targets[GAME_LABELS]; suffixes.resize(end-start); double suffix=0.;
        for (int64_t step=end; step-->start;) {
            suffixes[step-start]=suffix; suffix+=rewards[step];
            ++targets[REWARD_SUFFIX_ASSIGNMENTS]; ++targets[REWARD_SUFFIX_ADDITIONS];
        }
        ++normalization[FIT_GAMES]; steps.clear(); features.clear(); global_features.clear();
        for (int64_t step=start; step<end; ++step) {
            ++targets[SPLIT_GOAL_CHECKS];
            if (*std::max_element(afterstates+16*step,afterstates+16*step+16)>=radix) {
                ++targets[WINNING_SKIPS]; continue;
            }
            steps.push_back(step); features.resize(features.size()+32);
            split_addresses(afterstates+16*step,patterns,radix,features.data()+features.size()-32);
            ++normalization[ADDRESS_EXTRACTIONS]; normalization[ADDRESS_OCCURRENCES]+=32;
            normalization[ADDRESS_DIGIT_READS]+=192; normalization[ADDRESS_MULTIPLY_ADDS]+=192;
            if (kind) {
                global_features.resize(global_features.size()+20);
                split_global_features(afterstates+16*step,radix,global_features.data()+global_features.size()-20,representation);
            }
        }
        sorted=features; ++normalization[SORT_CALLS]; normalization[SORT_ITEMS]+=sorted.size();
        std::sort(sorted.begin(),sorted.end(),[normalization](int64_t a,int64_t b) {
            ++normalization[SORT_COMPARISONS]; return a<b;
        });
        unique.clear(); denominators.clear();
        for (size_t i=0; i<sorted.size(); ++i) {
            ++normalization[DENOMINATOR_OCCURRENCE_VISITS];
            if (!i || sorted[i]!=sorted[i-1]) { unique.push_back(sorted[i]); denominators.push_back(1); }
            else ++denominators.back();
        }
        normalization[UNIQUE_ADDRESSES]+=unique.size();
        reward_errors.resize(steps.size()); risk_errors.resize(steps.size());
        reward_gradients.assign(unique.size(),0.); risk_gradients.assign(kind ? 20 : unique.size(),0.);
        global_denominators.assign(20,0.);
        // Both predictions are read from the same game-start heads before any write.
        for (size_t sample=0; sample<steps.size(); ++sample) {
            const int64_t step=steps[sample]; const int64_t* row=features.data()+32*sample;
            const double reward=split_ntuple(row,reward_weights);
            const double logit=split_logit(row,kind ? global_features.data()+20*sample : nullptr,
                kind,risk_weights,representation);
            const double probability=split_sigmoid(logit,representation);
            const double combined=split_combine(reward,probability,representation);
            reward_errors[sample]=suffixes[step-start]-reward; risk_errors[sample]=label-probability;
            if (!learning[SAMPLES]) {
                examples[0]=game; examples[1]=step;
                const double v[]={suffixes[step-start],label,reward,probability,combined,reward_errors[sample],risk_errors[sample]};
                std::copy(v,v+7,values);
            }
            examples[2]=game; examples[3]=step;
            const double v[]={suffixes[step-start],label,reward,probability,combined,reward_errors[sample],risk_errors[sample]};
            std::copy(v,v+7,values+7);
            ++learning[SAMPLES]; ++learning[COMBINED_PREDICTIONS]; ++learning[REWARD_PREDICTIONS];
            ++learning[RISK_PREDICTIONS]; learning[REWARD_LOOKUPS]+=32; learning[ALL_LOOKUPS]+=32;
            learning[REWARD_OCCURRENCES]+=32; ++targets[LABEL_ASSIGNMENTS];
            if (!kind) { learning[RISK_LOOKUPS]+=32; learning[ALL_LOOKUPS]+=32; }
        }
        // Accumulate occurrence contributions in sample order. Repeated addresses count repeatedly.
        for (size_t sample=0; sample<steps.size(); ++sample) {
            int64_t local[32]; std::copy(features.data()+32*sample,features.data()+32*(sample+1),local);
            ++normalization[SORT_CALLS]; normalization[SORT_ITEMS]+=32;
            std::sort(local,local+32,[normalization](int64_t a,int64_t b) {
                ++normalization[SORT_COMPARISONS]; return a<b;
            });
            for (int first=0; first<32;) {
                int next=first+1; while (next<32 && local[next]==local[first]) ++next;
                ++normalization[ADDRESS_DENOMINATOR_SEARCHES];
                const auto at=std::lower_bound(unique.begin(),unique.end(),local[first],[normalization](int64_t a,int64_t b) {
                    ++normalization[ADDRESS_DENOMINATOR_COMPARISONS]; return a<b;
                })-unique.begin();
                reward_gradients[at]+=(next-first)*reward_errors[sample];
                ++normalization[REWARD_GRADIENT_PRODUCTS]; ++normalization[REWARD_GRADIENT_SUMS];
                if (!kind) {
                    risk_gradients[at]+=(next-first)*risk_errors[sample];
                    ++normalization[RISK_GRADIENT_PRODUCTS]; ++normalization[RISK_GRADIENT_SUMS];
                }
                first=next;
            }
            if (kind) for (int j=0; j<20; ++j) {
                const double x=global_features[20*sample+j];
                risk_gradients[j]+=x*risk_errors[sample]; global_denominators[j]+=x;
                ++normalization[RISK_GRADIENT_PRODUCTS]; ++normalization[RISK_GRADIENT_SUMS];
                ++normalization[GLOBAL_DENOMINATOR_SUMS];
            }
        }
        if (!unique.empty()) { ++normalization[GAME_COMMITS]; ++normalization[REWARD_COMMITS]; }
        for (size_t address=0; address<unique.size(); ++address) {
            reward_weights[unique[address]]+=alpha*reward_gradients[address]/denominators[address];
            ++learning[REWARD_WRITES]; ++learning[ALL_WRITES]; ++normalization[REWARD_PARAMETER_WRITES];
            ++normalization[NORMALIZATION_DIVISIONS]; ++normalization[UPDATE_PRODUCTS];
        }
        bool risk_committed=false;
        for (size_t address=0; address<risk_gradients.size(); ++address) {
            const double denominator=kind ? global_denominators[address] : denominators[address];
            if (!denominator) { ++normalization[GLOBAL_ZERO_DENOMINATORS]; continue; }
            const size_t index=kind ? address : unique[address];
            risk_weights[index]+=alpha*risk_gradients[address]/denominator;
            risk_committed=true; ++learning[RISK_WRITES]; ++learning[ALL_WRITES];
            ++normalization[RISK_PARAMETER_WRITES]; ++normalization[NORMALIZATION_DIVISIONS];
            ++normalization[UPDATE_PRODUCTS];
        }
        normalization[RISK_COMMITS]+=risk_committed;
        const uint64_t bytes=8*(suffixes.capacity()+reward_errors.capacity()+risk_errors.capacity()+global_features.capacity()+
            reward_gradients.capacity()+risk_gradients.capacity()+global_denominators.capacity()+steps.capacity()+features.capacity()+
            sorted.capacity()+unique.capacity()+denominators.capacity());
        normalization[FEATURE_BUFFER_BYTES_PEAK]=std::max(normalization[FEATURE_BUFFER_BYTES_PEAK],bytes);
        start=end;
    }
}

extern "C" void score_split_v301(const int32_t* afterstates,const double* rewards,
    const int64_t* ends,const int32_t* terminal_codes,int first_game,int n_games,
    const int32_t* patterns,int radix,const double* reward,const double* risk,int kind,
    double* output,double* components,uint64_t* learning,uint64_t* targets,uint64_t* representation) {
    std::vector<double> suffixes,utility_suffixes;
    int64_t start=first_game ? ends[first_game-1] : 0;
    for (int game=first_game; game<n_games; ++game) {
        const int64_t end=ends[game]; const double label=terminal_codes[game]==1 ? 1. : 0.;
        suffixes.resize(end-start); utility_suffixes.resize(end-start);
        double suffix=0.,utility_suffix=label==1. ? 4. : -4.; ++targets[GAME_LABELS];
        for (int64_t step=end; step-->start;) {
            suffixes[step-start]=suffix; suffix+=rewards[step];
            ++targets[REWARD_SUFFIX_ASSIGNMENTS]; ++targets[REWARD_SUFFIX_ADDITIONS];
            utility_suffixes[step-start]=utility_suffix; utility_suffix+=rewards[step];
            ++targets[UTILITY_SUFFIX_ASSIGNMENTS]; ++targets[UTILITY_SUFFIX_ADDITIONS];
        }
        double sum[6]={},split[9]={}; int count=0;
        for (int64_t step=start; step<end; ++step) {
            ++targets[SPLIT_GOAL_CHECKS];
            if (*std::max_element(afterstates+16*step,afterstates+16*step+16)>=radix) {
                ++targets[WINNING_SKIPS]; continue;
            }
            double predicted[4]; split_prediction(afterstates+16*step,patterns,radix,reward,risk,kind,predicted,representation);
            const double target=utility_suffixes[step-start];
            const double error=predicted[3]-target,reward_error=predicted[0]-suffixes[step-start],risk_error=predicted[1]-label;
            sum[1]+=error; sum[2]+=error*error; sum[3]+=std::abs(error); sum[4]+=predicted[3]; sum[5]+=target;
            split[0]+=reward_error; split[1]+=reward_error*reward_error; split[2]+=std::abs(reward_error);
            split[3]+=risk_error*risk_error;
            split[4]+=std::max(predicted[2],0.)-label*predicted[2]+std::log1p(std::exp(-std::abs(predicted[2])));
            ++representation[RISK_LOG_LOSS_EVALUATIONS];
            split[5]+=risk_error; split[6]+=predicted[1]; ++count;
            ++learning[COMBINED_PREDICTIONS]; ++learning[REWARD_PREDICTIONS]; ++learning[RISK_PREDICTIONS];
            learning[REWARD_LOOKUPS]+=32; learning[ALL_LOOKUPS]+=32;
            if (!kind) { learning[RISK_LOOKUPS]+=32; learning[ALL_LOOKUPS]+=32; }
            ++targets[LABEL_ASSIGNMENTS];
        }
        sum[0]=count;
        for (int j=1; j<6; ++j) sum[j]=count ? sum[j]/count : 0.;
        for (int j=0; j<7; ++j) split[j]=count ? split[j]/count : 0.;
        split[7]=label; split[8]=count;
        std::copy(sum,sum+6,output+6*(game-first_game));
        std::copy(split,split+9,components+9*(game-first_game)); start=end;
    }
}

extern "C" int evaluate_split_v301(const uint64_t* seeds,int n_games,const int32_t* patterns,
    int radix,const double* reward,const double* risk,int kind,const int32_t* table,
    const int64_t* line_scores,const int32_t* cells,double model_p,double environment_p,int max_steps,
    int64_t* output,int32_t* final_boards,uint64_t* environment,uint64_t* planning,uint64_t* representation) {
    for (int game=0; game<n_games; ++game) {
        std::mt19937_64 rng(seeds[game]); int32_t board[16]={}; int position,rank;
        for (int initial=0; initial<2; ++initial) spawn_raw(board,environment_p,rng,position,rank,0,environment);
        int status=ground_status(board,radix,environment),steps=0; int64_t score=0;
        while (!status && steps<max_steps) {
            int32_t moved[64],legal[4],after[16]; int64_t scores[4],gained; double tails[4],values[4];
            const int chosen=split_choose_v301(board,patterns,radix,reward,risk,kind,table,line_scores,cells,
                model_p,moved,scores,tails,values,legal,planning,representation);
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
