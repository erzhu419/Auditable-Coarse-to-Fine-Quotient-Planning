# V317：采样联合 greedy 备份与记录动作递推

冻结日期：2026-10-06。V316 重现 TD−MC 优势及 B 自身增长，但整体自身 FIRST 增益和 A 保留未确认。
当前目标沿 FIRST 的实际后继动作递推；H2 的内层选择则对联合效用取 greedy 最大值。
本轮只改变备份算子，检验这项有意近似是否影响学习收益，不预先把它认定为失败原因。

## 实验与共享事实

16 个新生命周期，parent=life%4，复用四个已核验 V312 SOURCE 和既有动力学。
A=.1、B=.5；各获取 131,072 raw 加真实检测开销，确认两个独立库，以完整游戏 80% FIT 观测固定库信念。
FIRST_LOCAL 用原 V301 MC 目标、alpha=.0025 首次拟合一次；从它私有复制 SARSA_LOCAL 和 GREEDY_LOCAL。
按 A_R1、B_R1、A_R2、B_R2 运行，每批由 FIRST v0 H2 获取同一个 65,536 raw 事实流。
两个学习臂共享全部事实，恰好拟合同一完整游戏 FIT 前缀的全部非 WIN 状态。
表示、当前预测、逐游戏残差/归一化提交、实际参数写入数、轮数和预算保持不变；尾部付费但不训练。
在既有物理 consume 循环内保存每个实际动作后的 post-spawn 棋盘，与 afterstate 一一对应；不再做第二遍世界重放。

## 两个备份算子

SARSA_LOCAL 原样使用 V314 实际下一动作奖励及 afterstate 目标，bootstrap 为自身该批开始快照。
GREEDY_LOCAL 在当前非 WIN afterstate 对应的实际 post-spawn 棋盘 b 上，由自身同一批开始快照选择：

`a* = argmax_legal [score(a)/2048 + U_tail(after(a))]`，
其中非 WIN 的 `U_tail=R_boot+8P_boot−4`，WIN 的 `U_tail=4`。

采用原 native DIRECT 的合法动作顺序和 first-max 平局规则；选择一次，用同一分支生成两个目标。
非 WIN 分支：R_target=score(a*)/2048+R_boot(after(a*))，W_target=P_boot(after(a*))。
选择分支立即 WIN：R_target=score(a*)/2048，W_target=1；该棋盘 LOST 无合法动作：R_target=0、W_target=0。
当前 WIN afterstate 不训练。禁止分别最大化两张表、读更新后的 bootstrap 或把当前动作奖励加入目标。
counterfactual 分支只用于学习目标；实际采集动作、游戏标签及 FIT/HELDOUT 边界保留原样。
R1 bootstrap=自身 v0，R2=自身 v1，整个批次固定；当前残差仍在每个游戏开始时读取。

保留两臂全部实际 FIT 目标；GREEDY 文件另保存 selected_action（unused/LOST 为 −1）。
旧 SARSA 目标格式为 V314，新 greedy 目标格式为 V317，策略稀疏版本沿用 V313。
计入所有额外合法动作展开、分支特征/表读取、sigmoid、观察棋盘保存和目标文件 CPU/字节；不均衡掉这些实际成本。

## 评估与唯一主终点

SOURCE/FIRST 初始化，SARSA/GREEDY 每轮后，每任务每生命周期 32 个配对自然 H2 游戏，最大 8192 步，共 6,144 个。
唯一主终点：最终 GREEDY_LOCAL−自身 FIRST_LOCAL，A/B 等权，95% CI 下界 >0。
保留增长另要求 A、B 各自最终−FIRST 的 95% CI 下界 ≥0。
算子干预 GREEDY−SARSA、净 SOURCE 收益、SARSA 自身/净 SOURCE 及首次适配收益分别报告，不能替代主终点。
20,000 次父组内配对生命周期 bootstrap，seed31700001；不合并旧数据或选择最好臂。
未确认不同库、出现不完整自然标签时保留整队列 HOLD，不删除或替换生命周期。

种子：warm317100000000+task_index×100000+life×1000000+game；
initial317200000000+task_index×100000+life×10000000；
post317500000000+life×10000000+task_index×1000000+round×100000；
eval317900000000+life×1000000+B×100000+episode。
配置写入后开始正式采集；冻结种子、表示、步长、预算、快照频率、分支选择及区间。

## 核验与范围

独立核验本轮新 raw、FIRST 动作探针、所有新版本，以及两臂全部实际目标。
Greedy 读取器按独立物理规则对四个动作向量化展开并核对每个 selected_action/联合目标；不重复完整模型拟合或评估。
SOURCE 物理复用、经济成本计一次，新采集物理共享、对两臂分别经济计费，独立核验计算另列。
全部中途文件在 reports/greedy_targets_v317。结果条件于固定 FIRST 状态覆盖、四个 SOURCE、固定库信念和近似表示。
本轮是新算子开发对照，不建立闭环增长或一般战略学习；U005 FAIL 保留，U006 不运行。
