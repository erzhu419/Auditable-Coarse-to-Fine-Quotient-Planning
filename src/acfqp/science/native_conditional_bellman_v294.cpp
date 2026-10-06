// Fixed source values plus occurrence-normalized, optionally p-conditioned residuals.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

namespace {
enum Count { PREDICTIONS, SOURCE_LOOKUPS, RESIDUAL_LOOKUPS, SOURCE_ADDS,
    RESIDUAL_MULTIPLIES, RESIDUAL_ADDS, QUERY_SHIFTS, ANALYTIC_WINS,
    BASIS_CALLS, BASIS_SQUARES, BASIS_ROOTS, BASIS_DIVISIONS,
    MODEL_SWIPES, MODEL_LINES, MODEL_LEGAL, MODEL_WINS, MODEL_LOSSES,
    MODEL_GOALS, SPAWNS, PROBABILITY_PRODUCTS, PROBABILITY_SUMS,
    ROOT_SWIPES, SECOND_SWIPES, CONTROL_TARGETS, SUFFIX_ASSIGNMENTS,
    SUFFIX_ADDITIONS, SKIPPED_WINNING, EXTRACTIONS, FEATURES, DIGITS,
    ADDRESS_ADDS, SORT_ITEMS, SORT_COMPARISONS, COUNT_VISITS,
    UNIQUE_ADDRESSES, GRADIENT_ADDS, DIVISIONS, UPDATE_MULTIPLICATIONS,
    WRITES, GAME_COMMITS, UPDATES, UPDATE_OCCURRENCES, ERROR_SUBTRACTIONS,
    BUFFER_BYTES_PEAK, DENOM_COMPARISONS, BASIS_ADDITIONS };

struct Parameters {
    const int32_t *patterns, *table, *cells;
    const int64_t* scores;
    const double *source, *residual;
    int radix, banks;
    int64_t parameters;
    double goal, failure, failure_shift, success_shift;
};

void basis(double p, int banks, double* b, uint64_t* counts) {
    b[0]=1.; b[1]=0.;
    if (banks==1) return;
    const double left=1.-p;
    const double norm=std::sqrt(left*left+p*p);
    b[0]=left/norm; b[1]=p/norm;
    ++counts[BASIS_CALLS]; counts[BASIS_SQUARES]+=2;
    ++counts[BASIS_ROOTS]; counts[BASIS_DIVISIONS]+=2;
    counts[BASIS_ADDITIONS]+=2;
}

bool won(const int32_t* board, int radix) {
    return *std::max_element(board,board+16)>=radix;
}

void addresses(const int32_t* board, const Parameters& p, int64_t* output,
               uint64_t* counts) {
    const int64_t stride=p.parameters/4;
    for (int tuple=0; tuple<32; ++tuple) {
        int64_t address=0;
        for (int cell=0; cell<6; ++cell)
            address=address*p.radix+board[p.patterns[tuple*6+cell]];
        output[tuple]=(tuple/8)*stride+address;
    }
    ++counts[EXTRACTIONS]; counts[FEATURES]+=32;
    counts[DIGITS]+=192; counts[ADDRESS_ADDS]+=192;
}

double prediction(const int64_t* features, const Parameters& p, const double* b,
                  uint64_t* counts) {
    // Match the effective raw table's arithmetic, including its summation order.
    double value=0.;
    for (int occurrence=0; occurrence<32; ++occurrence) {
        const int64_t a=features[occurrence];
        double weight=p.source[a]+b[0]*p.residual[a];
        if (p.banks==2) weight+=b[1]*p.residual[p.parameters+a];
        value+=weight;
    }
    ++counts[PREDICTIONS]; counts[SOURCE_LOOKUPS]+=32;
    counts[RESIDUAL_LOOKUPS]+=32*p.banks; counts[SOURCE_ADDS]+=32;
    counts[RESIDUAL_MULTIPLIES]+=32*p.banks;
    counts[RESIDUAL_ADDS]+=32*p.banks;
    counts[QUERY_SHIFTS]+=2;
    return value+p.failure_shift+p.success_shift;
}

double value(const int32_t* board, const Parameters& p, const double* b,
             uint64_t* counts) {
    if (won(board,p.radix)) { ++counts[ANALYTIC_WINS]; return p.goal; }
    int64_t features[32]; addresses(board,p,features,counts);
    return prediction(features,p,b,counts);
}

bool swipe(const int32_t* board, int action, const Parameters& p,
           int32_t* after, int64_t& score, uint64_t* counts) {
    std::copy(board,board+16,after); score=0; ++counts[MODEL_SWIPES];
    for (int line=0; line<4; ++line) {
        const int32_t* cells=p.cells+16*action+4*line;
        int index=0;
        for (int i=0; i<4; ++i) index=index*p.radix+board[cells[i]];
        for (int i=0; i<4; ++i) after[cells[i]]=p.table[4*index+i];
        score+=p.scores[index]; ++counts[MODEL_LINES];
    }
    const bool legal=!std::equal(board,board+16,after);
    counts[MODEL_LEGAL]+=legal;
    return legal;
}

double direct_value(const int32_t* board, const Parameters& p, const double* b,
                    uint64_t* counts) {
    if (won(board,p.radix)) { ++counts[MODEL_GOALS]; return p.goal; }
    double best=-std::numeric_limits<double>::infinity();
    for (int action=0; action<4; ++action) {
        int32_t after[16]; int64_t score;
        ++counts[SECOND_SWIPES];
        if (!swipe(board,action,p,after,score,counts)) continue;
        double tail;
        if (won(after,p.radix)) {
            tail=p.goal; ++counts[MODEL_WINS];
        } else tail=value(after,p,b,counts);
        const double q=static_cast<double>(score)/2048.+tail;
        if (q>best) best=q;
    }
    if (best==-std::numeric_limits<double>::infinity()) {
        ++counts[MODEL_LOSSES]; return -p.failure;
    }
    return best;
}

double expected_control(const int32_t* after, double probability,
                        const Parameters& p, const double* b, uint64_t* counts) {
    int empty=0;
    for (int cell=0; cell<16; ++cell) empty+=after[cell]==0;
    double expectation=0.;
    for (int cell=0; cell<16; ++cell) if (!after[cell]) {
        for (int rank=1; rank<=2; ++rank) {
            int32_t spawned[16]; std::copy(after,after+16,spawned); spawned[cell]=rank;
            ++counts[SPAWNS];
            const double outcome=direct_value(spawned,p,b,counts);
            const double weight=(rank==1 ? 1.-probability : probability)/empty;
            expectation+=weight*outcome;
            ++counts[PROBABILITY_PRODUCTS]; ++counts[PROBABILITY_SUMS];
        }
    }
    return expectation;
}

void example(int64_t step, double target, double before, double error, double prob,
             uint64_t updates, int64_t* indices, double* values) {
    if (!updates) {
        indices[0]=step; values[0]=target; values[1]=before;
        values[2]=error; values[3]=prob;
    }
    indices[1]=step; values[4]=target; values[5]=before;
    values[6]=error; values[7]=prob;
}

Parameters parameters(const int32_t* patterns, int radix, const double* source,
    const double* residual, int banks, const int32_t* table, const int64_t* scores,
    const int32_t* cells, double goal, double failure, double fs, double gs) {
    int64_t count=4;
    for (int i=0; i<6; ++i) count*=radix;
    return Parameters{patterns,table,cells,scores,source,residual,radix,banks,count,
        goal,failure,fs,gs};
}
}

extern "C" void predict_conditional_v294(const int32_t* boards, int n,
    const double* probabilities, const int32_t* patterns, int radix,
    const double* source, const double* residual, int banks, double goal,
    double failure_shift, double success_shift, double* output, uint64_t* counts) {
    const auto p=parameters(patterns,radix,source,residual,banks,nullptr,nullptr,nullptr,
        goal,0.,failure_shift,success_shift);
    for (int i=0; i<n; ++i) {
        double b[2]; basis(probabilities[i],banks,b,counts);
        output[i]=value(boards+16*i,p,b,counts);
    }
}

extern "C" void fit_conditional_v294(const int32_t* boards, int n,
    const double* rewards, const double* probabilities, int terminal_code,
    const int32_t* patterns, int radix, const double* source, double* residual,
    int banks, const int32_t* table, const int64_t* scores, const int32_t* cells,
    double goal, double failure, double failure_shift, double success_shift,
    double alpha, int control, uint64_t* counts, int64_t* example_indices,
    double* example_values) {
    const auto p=parameters(patterns,radix,source,residual,banks,table,scores,cells,
        goal,failure,failure_shift,success_shift);
    std::vector<double> suffixes;
    if (!control) {
        suffixes.resize(n); double suffix=terminal_code==1 ? goal : -failure;
        for (int i=n; i-->0;) {
            suffixes[i]=suffix; suffix+=rewards[i];
            ++counts[SUFFIX_ASSIGNMENTS]; ++counts[SUFFIX_ADDITIONS];
        }
    }
    std::vector<int64_t> features, steps, sorted, unique, denominators;
    std::vector<double> coefficients, errors, gradients;
    for (int step=0; step<n; ++step) {
        if (won(boards+16*step,radix)) { ++counts[SKIPPED_WINNING]; continue; }
        steps.push_back(step); features.resize(features.size()+32);
        addresses(boards+16*step,p,features.data()+features.size()-32,counts);
        double b[2]; basis(probabilities[step],banks,b,counts);
        coefficients.push_back(b[0]); coefficients.push_back(b[1]);
        const double before=prediction(features.data()+features.size()-32,p,b,counts);
        const double target=control
            ? expected_control(boards+16*step,probabilities[step],p,b,counts)
            : suffixes[step];
        counts[CONTROL_TARGETS]+=control;
        const double error=target-before; ++counts[ERROR_SUBTRACTIONS];
        errors.push_back(error);
        example(step,target,before,error,probabilities[step],counts[UPDATES],
            example_indices,example_values);
        ++counts[UPDATES]; counts[UPDATE_OCCURRENCES]+=32*banks;
    }
    // All game-start targets and residuals above were read before any write.
    sorted=features; counts[SORT_ITEMS]+=sorted.size();
    std::sort(sorted.begin(),sorted.end(),[counts](int64_t a,int64_t b) {
        ++counts[SORT_COMPARISONS]; return a<b;
    });
    for (int64_t a:sorted) {
        ++counts[COUNT_VISITS];
        if (unique.empty() || unique.back()!=a) {
            unique.push_back(a); denominators.push_back(1);
        } else ++denominators.back();
    }
    counts[UNIQUE_ADDRESSES]+=unique.size();
    gradients.assign(banks*unique.size(),0.);
    for (size_t sample=0; sample<steps.size(); ++sample) {
        for (int occurrence=0; occurrence<32; ++occurrence) {
            const int64_t address=features[32*sample+occurrence];
            const auto found=std::lower_bound(unique.begin(),unique.end(),address,
                [counts](int64_t a,int64_t b) { ++counts[DENOM_COMPARISONS]; return a<b; });
            const size_t at=found-unique.begin();
            for (int bank=0; bank<banks; ++bank) {
                gradients[bank*unique.size()+at]+=coefficients[2*sample+bank]*errors[sample];
                ++counts[GRADIENT_ADDS];
            }
        }
    }
    if (!unique.empty()) ++counts[GAME_COMMITS];
    for (int bank=0; bank<banks; ++bank) for (size_t at=0; at<unique.size(); ++at) {
        residual[bank*p.parameters+unique[at]]+=alpha*gradients[bank*unique.size()+at]/denominators[at];
        ++counts[WRITES]; ++counts[DIVISIONS]; ++counts[UPDATE_MULTIPLICATIONS];
    }
    counts[BUFFER_BYTES_PEAK]=8*(suffixes.capacity()+features.capacity()+steps.capacity()
        +sorted.capacity()+unique.capacity()+denominators.capacity()+coefficients.capacity()
        +errors.capacity()+gradients.capacity());
}

extern "C" void score_actions_conditional_v294(const int32_t* boards, int n,
    const double* probabilities, const int32_t* patterns, int radix,
    const double* source, const double* residual, int banks, const int32_t* table,
    const int64_t* scores, const int32_t* cells, double goal, double failure,
    double failure_shift, double success_shift, int32_t* bests, int32_t* moved,
    int64_t* rewards, double* tails, double* values, int32_t* legal, uint64_t* counts) {
    const auto p=parameters(patterns,radix,source,residual,banks,table,scores,cells,
        goal,failure,failure_shift,success_shift);
    for (int row=0; row<n; ++row) {
        const int32_t* board=boards+16*row;
        double b[2]; basis(probabilities[row],banks,b,counts);
        if (won(board,radix)) { bests[row]=-2; ++counts[MODEL_GOALS]; continue; }
        int best=-1; double best_value=-std::numeric_limits<double>::infinity();
        for (int action=0; action<4; ++action) {
            const int slot=4*row+action;
            ++counts[ROOT_SWIPES];
            if (!swipe(board,action,p,moved+16*slot,rewards[slot],counts)) continue;
            legal[slot]=1;
            if (won(moved+16*slot,radix)) {
                tails[slot]=goal; ++counts[MODEL_WINS];
            } else tails[slot]=expected_control(moved+16*slot,probabilities[row],p,b,counts);
            values[slot]=static_cast<double>(rewards[slot])/2048.+tails[slot];
            if (best<0 || values[slot]>best_value) { best=action; best_value=values[slot]; }
        }
        if (best<0) ++counts[MODEL_LOSSES];
        bests[row]=best;
    }
}
