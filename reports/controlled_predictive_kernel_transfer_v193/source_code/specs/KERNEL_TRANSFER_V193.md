# V193：固定非线性模型的迁移诊断

V192 SOURCE拟合改善、TARGET96主比较为负。本轮不拟合、不求解、不调gamma/lambda、不生成棋盘/标签；固定98维缓存、RBF gamma1/lambda.001及现有中心/系数，仅定位整体覆盖、动作组合覆盖及局部后果排序问题。距离参照是描述性统计，不是新Gate或部署规则。

## Inputs and API

八输入按序留原字节：V192 runtime corrected_stage_checks.json → v192_stage_checks.json；V192 run/model/roots/choices/labels/summary/source_diagnostics.json（同名）。全部protocol_frozen读入。输出reports/controlled_predictive_kernel_transfer_v193；临时仅reports/v193_runtime_tmp。主入口诊断函数：

`diagnose(model, roots, choices, labels, previous_summary, source_diagnostics)`

返回dict(schema='acfqp.kernel_transfer.v193',complete,parameters,reference,root_records,summary,costs)。SOURCE来自roots['SOURCE']，TARGET来自roots['TARGET']；SOURCE真实完整向量已在root['action_components']，TARGET用labels。SOURCE诊断和TARGET NONLINEAR留存决定只做绑定；不重新评估SOURCE模型。V192阶段valid/status、143 SOURCE/36组、96 TARGET、中心根/动作与原98缓存一致。

## Frozen arithmetic and coverage

ACTIONS DOWN,LEFT,RIGHT,UP；EPS1e-12。模型中心原顺序；D为Python sum98平方差，M为冻结median_squared_distance。每root全部合法动作对每中心只算一次距离及6块距离：aggregate0:6、rank_nodes6:15、rank_pairs15:48、value_nodes48:57、value_pairs57:90、vacancy90:98。全D按原98顺序，块距离独立从相同平方差求和。

SOURCE校准用每root全部有序、不同合法动作对，排除与query同source_id的全部中心/棋盘。TARGET诊断pair先用留存summary的ORACLE动作o；NONLINEAR选择c!=o时第二端为c（包括真值平局）；c==o时第二端为按真实utility、ACTIONS/EPS选的最强其他动作。forced根pair为空，仍保留结果，不纳入pair统计。

每pair(a,b)，独立端点最近中心距离dA,dB；共同候选为同一SOURCE root的有序不同action中心(i,j)，不能从不同棋盘拼接。稳定平局按中心索引(i,j)字典顺序。独立距离=(dA+dB)/(2M)，最大端点=max(dA,dB)/M；joint=min(D(a,i)+D(b,j))/(2M)。coupling=joint-independent。6块各按相同共同pair候选求最小值/M/2，block_coupling=joint-sum(block_min)；另保留共同最近pair的6块距离贡献，和等于joint（浮点容差）。保留独立最近中心、joint最近pair元数据。

SOURCE有序pair校准只保存root/source/actions及上述标量/6块minimum，不存巨型距离矩阵。每metric汇总nearest-rank Q50/Q95/max（Qp=sort[ceil(p*n)-1]）。TARGET每metric保存经验percentile=count(reference<=value+EPS)/n。endpoint_outlier：max_individual>对应SOURCE Q95+EPS；pair_outlier：joint>对应Q95+EPS；composition_outlier：pair_outlier且非endpoint_outlier；block_composition_outlier：pair_outlier且6块各<=自己Q95+EPS。不得按目标改分位数或把这些标签解释成因果/信息充分性证明。

## Actual decisions and contributions

TARGET所有动作按V192固定算术复算k=math.exp(-gamma*D/M)，每分量按中心顺序Python sum(k*C)，R加一次first_reward；绑定留存三分量和实际ACTIONS/EPS选择。以已冻结fallback标志保留原fallback选择，不重新检验已审计的支持统计。每pair的true_gap、predicted_gap均first-second；reward/failure/success显式保留，utility=R-F+S。

每中心贡献(k_a-k_b)*C_j（三分量），按中心顺序汇总并加[first_reward_a-first_reward_b,0,0]；与直接预测差比较，固定1e-8*(1+abs(expected))。按source_id聚合全部36组贡献，保留按|utility|排序前5中心（平局中心索引），不存全部中心贡献副本。记录正/负utility质量。共同最近SOURCE pair保存真实tail_gap=(R-first_reward,F,S)差及其utility，与query真实tail_gap对照；二者|utility|>EPS且异号才叫label_direction_reversed。joint_distance严格==0.0且任一tail_gap分量绝对差>EPS另记exact_pair_label_conflict；该标志是三分量标签冲突，不等同必然动作错误，非零近邻不叫信息别名。

root_records原TARGET顺序，至少包括root/source/replica/stratum、selected/oracle/challenger/pair_kind、actual_vectors/utility/regret/error、LINEAR_action/utility/regret、new_error_vs_LINEAR/resolved_error_vs_LINEAR、prediction_vectors/replayed_action/replay_matches/predictions_match、true_gap/predicted_gap/immediate_gap、coverage、nearest_source_tail_gap/true_tail_gap/label_direction_reversed/exact_pair_label_conflict、contributions。

summary含ALL/ERROR/CORRECT/NEW_ERROR_VS_LINEAR/RESOLVED_ERROR_VS_LINEAR五组，每组n、pair_roots、mean_regret、mean_LINEAR_utility_delta、各coverage指标均值、endpoint/pair/composition/block_composition计数、covered_pair_errors（error且非pair_outlier）、covered_pair_label_reversals、label_direction_reversed及exact_pair_label_conflict计数。附V192三primary对照效用差、18新增/10修复的完整ID列表和largest_loss/gain IDs。所有96起点都留，不只看反例。

## Execution and verification

真实inputs读前冻结core/runner/auditor/spec/tests/runtime wrappers；main/audit各一次，失败保留paid ledger。phase protocol_frozen(0reads)→inputs_retained(8)→source_reference(8)→target_diagnostics(8)→complete(8)；diagnose返回后可依序记录后三phase，不声称这些时间是函数内部边界。

核距离、6块累加、SOURCE/TARGET ordered-pair候选检查、TARGET kernel exponentials/3分量products、中心/组贡献计入counts。新fit/solve/eigen/SVD/feature derivations/SOURCEgames/boards/reference kernels/exact labels/environment samples/nativeupdates全部0；读取及原V192成本链留存，不重复物理生成或SOURCE模型评分。

独立auditor不用main诊断函数、V192 fit/choose、原物理内核；独立重建覆盖、参照分位数、目标预测与贡献、所有分类和汇总，固定数值容差1e-8*(1+abs(expected))、动作/roster/flags精确；8输入字节一次、stage源码字节一次。tests仅合成：同组排除、不能跨root拼pair、6块拆分、firstreward只加一次、风险符号、EPS平局、forced输入、完整cohort而非只错误、wrong saved choice或contribution能被audit发现。main/audit已通过后不重复检查。

下一步根据留存证据选择需改变的来源覆盖或关系组合方式，不调当前核。有限H3、固定教师；一般战略学习仍未解决，H2保持，U005 FAIL，U006未启动。
