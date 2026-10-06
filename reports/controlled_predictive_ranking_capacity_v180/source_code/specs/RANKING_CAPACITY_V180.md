# V180：固定表示的共享动作排序能力

V179 的TARGET效用相对ONE为+0.016831，闭合22.7% headroom，但仍有6个正regret根且成功概率下降。逐根表示受限oracle保留98.5%目标headroom，不代表存在一个共享系数同时达到。本轮只诊断这一容量问题，不训练或部署新预测器。

固定V179全部47 SOURCE/24 TARGET H3根、cached六维action_features、精确完整R/F/S、已知首reward、goal rank11、固定后续教师及效用R−F+S。共享评分类为s_a=r_a+phi_a·beta，beta六维无界（等于W_R−W_F+W_S）。不加特征、交互、截距、动作偏置、参数界或额外数据。相同phi类按首reward最大、ACTIONS DOWN/LEFT/RIGHT/UP与EPS1e-12选代表；真实效用最大值以内EPS的全部代表均属于optimal集合。非最优代表以外的无损并列不加约束。

SOURCE、TARGET、JOINT各进行独立容量搜索。在每根任取一个最优代表a，要求其压过全部非最优代表b：A行=[phi_b−phi_a,1]、b行=r_a−r_b，变量=[beta,delta]；另显式delta≤1。最大化共同间隔delta，beta和delta均无下界。LP始终可行（delta可足够负），solver失败是执行错误；负间隔不是solver infeasible。此正间隔能力诊断不要求复现某个任意oracle并列动作。

先只加唯一最优根约束；全部代表同为最优的根无需约束。对全根评价该解；正间隔全根见证可结束。否则按root_id第一个违反的多最优根，将其全部optimal按ACTIONS顺序分支，DFS。每次LP是部分约束松弛，精确非正上界可剪整个子树，避免枚举已证明失败的最优替代。不得用单个最优分支失败宣称整体失败。搜索穷尽或正见证结束，不调整参数/求解界。

每LP保存原native结果、rational beta评价与稀疏dual。dual从返回support进行一次精确有理平衡，权重lambda≥0，满足A^T lambda=(0,...,0,1)，则b^T lambda为全局间隔上界；奖励浮点是原精确二进制值，以Fraction留存。beta无界，因此近似stationarity不替代精确等式。正见证须全部根某最优压过所有非最优的exact gap>EPS，且实际EPS/ACTIONS选择在optimal集合。所有terminal上界<0为weak_infeasible；存在零上界且无正见证为no_positive_margin。后者不自动证明弱边界可达或确定性策略绝不可能；仅全根确有gap≥0时保存weak_witness。

为解释冲突是否必须补充信息，每条dual ranking support在badphi的六维tuple加lambda，在bestphi减lambda。所有feature vertex净流为零时，同一证据也消去任意共享g(phi)，上界不限于线性模型。只有失败scope全部剪枝叶都具此性质且分支覆盖成立，才报告任意共享函数的同一限制；不平衡仅说明此证据没有排除非线性，不能证明非线性可达。这个解释不增加LP或模型拟合。

原V179系数只用于重放既有评分/选择，不能把oracle-label容量见证当新学习方法或验证收益。另检查cached goal_reached=1动作的精确标签为[首reward,0,1]，排除终止/奖励语义错位；不一致则停止容量解释并保留执行HOLD。完整向量与物理kernel不重新估计。

正式运行前留存协议、实现、纯测试与wrappers原字节。六份继承输入为V179 stage_checks、run、roots、labels、models、summary，先复制再运算；旧目标已暴露。独立分析重新构建classes/最优集合/约束，逐项验证exact dual、见证及整棵分支覆盖，不调用生产新core或LP，不重fit旧模型。输入字节由分析比对一次、源码由stage比对一次，不增加hash。保留所有LP/symbolic求解、缓存/输入与纯测试成本、继承账本。输出仅reports/v180_runtime_tmp与reports/controlled_predictive_ranking_capacity_v180。

下一步依据数学证据决定：共同正间隔允许但SOURCE拟合未达到时，检验SOURCE决策目标与迁移；仅线性容量冲突时检验更丰富共享函数；证据同时排除任意g(phi)时补充可迁移状态信息。不能靠优化计算或继续采样修复表示丢失的信息。

限制：这是旧有限H3根的表示/函数类诊断，不能证明一般战略或多回合学习，也不构成新的科学Gate或独立确认。零间隔结论保留并列边界，原V179收益及其成功概率下降均保留。既有H2、U005 FAIL、U006未启动不变。
