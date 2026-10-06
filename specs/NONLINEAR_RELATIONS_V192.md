# V192：固定98维输入的共享非线性后果学习

V191精确排除98维线性评分实现全部SOURCE/JOINT正确排序；TARGET单独正容量不能当来源学习。本轮固定V190输入与SOURCE143/36组，换RBF RKHS函数类，不使用容量见证或旧TARGET标签训练/选参。

每合法action的已有relation_features是98维中心x；同根全部无序action pairs构成行p，scale=sqrt(1/该根pair数)，Yp=scale×完整tail差，其中tail=(R−首reward,F,S)。N为所有训练根数，含forced根；forced根不制造pair标签。SOURCE缓存直接沿V191，零新swipe/编码。仅训练根的全部中心间严格正的平方欧氏距离取median M，每个design各一次；无数据标准化、截距或新特征词典。

k(x,z)=exp(−gamma||x−z||²/M)。固定gamma按0.25、1、4，lambda按0.0001、0.001、0.01、0.1、1排列，共15候选，全部正lambda。K为中心Gram，B每pair行在两个中心处为±scale，H=BKBᵀ数值对称化(H+Hᵀ)/2。对每gamma分解H一次，以eigen filter解alpha=(H+Nlambda I)⁻¹Y；C=Bᵀalpha，预测tail=k(x,X)C。损失SSE/N+lambda alphaᵀHalpha（三分量均计入），不clip预测、eigenvalues或概率。

36来源组排序奇偶两折各18组；所有中心、M、支持信息只来自该fold训练组。每候选按实际完整留出R−F+S的等来源组均值选参，EPS1e−12平局先gamma再lambda网格顺序。两fold的3gamma共6eigen分解、30predictor；全SOURCE按选定gamma/lambda再1分解/1predictor，共3design、7分解、31predictors。模型保留中心、C、alpha、pair关系、训练矩阵与损失信息，不保留大eigenvector数组。SOURCE实际错误/遗憾在冻结模型后单独记录。

推理只读observables和缓存phi。98列按Python sum顺序求平方距离，math.exp计算kernel，再按中心顺序Python sum求各分量；首reward加一次。MIN_ACTION_ROOTS=4、action/pair支持连通性、ACTIONS DOWN/LEFT/RIGHT/UP、EPS及回退规则沿V190，不以预测向量当校准概率。

模型/参数冻结后才生成4副本×24个新TARGET：seed=1920200+24*replica+index，name=v192_target_r{replica:02d}_{index:02d}，horizon3。沿V69固定16次randint1..10，24边先水平后垂直，index边两端rank1+index%10，其余格sample(index%3)置零。V184观测cohort=FRESH；V185几何cache与V190关系cache各一次。所有NONLINEAR、RELATION、LINEAR、INTERACT、RIDGE、LAYOUT、SHARED、OLD_SHARED、ONE与FALLBACK选择保存后，才计算标签；ORACLE只在标签打开后。

标签沿V184 V69 FULL、goal1/risk1教师、完整精确R/F/S，每board状态上限200000。新增96kernel/plan，留native/canonical fractions、紧凑teacher policy与成本，不留大kernel。主比较NONLINEAR−LINEAR/RELATION/OLD_SHARED，全部8controls、replica、RFS、遗憾、错误增减及收益集中度保存。不新增科学Gate或按目标调整网格。

真实输入读前冻结源码/协议/tests/wrappers原字节；八输入按序V191stage/run/roots、V190model、V190继承expanded_models/baseline_models/learned_rule/v188_models。SOURCE只用roots['SOURCE']；旧TARGET不训练。输入全部protocol_frozen留存；phase protocol_frozen(0reads)→source_selection(8)→models_frozen→target_roots→target_choices_frozen→target_labels→complete，其余8reads。main/audit各一次、threads1。失败保留已付学习/label尝试，后续不运行。

独立审计重建全部design/M/B/H、来源组与选择/训练统计；31次直接shifted线性solve（不重eigen/SVD），逐元素容差固定1e−8×(1+abs独立值)认证保存alpha/C，认证后用保存数组独立重放实际EPS决策。eigen谱仅作为原分解元数据留存，不独立重做谱分解。标签沿已审计native/canonical绑定/成本，不重积分旧/新kernel或重fit旧模型。输入字节比较一次、源码stage比较一次，无hash。

留存全部中心距离、Gram、pair构建、分解、filters、source验证/target评分、读取与旧成本链。中途仅reports/v192_runtime_tmp（含pytest目录），结果仅reports/controlled_predictive_nonlinear_relations_v192。零新物理随机样本、SOURCE游戏或native更新。

下一步：若非线性仅改善SOURCE拟合而留出/新TARGET不改善，定位来源覆盖或关系组合的迁移限制；若稳胜冻结强对照，再固定模型做独立新cohort确认。限制：有限H3与固定后续教师，核回归并非一般战略学习已解决；保持H2、U005 FAIL、U006未启动。
