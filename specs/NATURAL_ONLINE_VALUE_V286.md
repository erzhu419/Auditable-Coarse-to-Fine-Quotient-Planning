# V286：自然在线价值学习（三臂冻结协议）

冻结时点：实现与有限测试之后、任何正式新训练或评估之前。
不使用 V285 的 MC 动作标签训练。沿用四个 V120 risk_goal@4096 来源，
16 条新的 target life（parent=life%4）；没有新的独立来源训练。

## 核心比较

三臂都用同一个 V115 LIBRARY 路由数学、相同 H2 搜索和 risk_goal 查询：
FROZEN 保留初始叶；ORDINARY_TD 一张持续 TD 表；PERSISTENT_TD 按已学
module_id 保存 TD 表，新访问 module 从同一来源表初始化，旧表再访问时保留。
alpha=.0025 沿用 V120/V131；不搜索 alpha、阈值或预算。

V286 的 memory 输入是**全部实际生成的 tile rank，包括每局两块初始 tile**。
这与 V281 的 post-action-only 输入不同，旧 cohort 不合并。
各 life 用一次真实 DIRECT 完整游戏暖启动，若观察不足256则继续完整游戏；
全部反馈导入 LIBRARY 后克隆给三臂，warmup 不更新价值。

每臂连续经历 A(.1)→B(.5)→A′(.1)，每相位恰 131072 个新 raw tile 观察。
初始 tile 与 post-action tile 均计入；阶段边界按观察数发生，可在整局内部。
三臂共用连续 mt19937_64 随机流，每次 spawn 固定 cell/rank 两个 draw，
游戏终局不重置该流。因此相同 raw 前缀的 rank、memory 和路由一致。
控制器只接已观测 rank 和预测 p，不接相位标签或真实 p。

## 因果 TD 与暂停

H2 在当前 bank 中选择下一实际动作；其即时得分与该动作 afterstate 的叶值
形成 sampled SARSA 目标，**不能用 H2 expected action value 作 TD target**。
target 在更新前读取；更新上一实际动作保存的 bank，执行此前选定的动作，
不重选。跨 module 时 target 读当前 bank，credit 写之前保存的 bank。
query offset 遵循 V131：预测转换一次，raw target 扣 offset 一次。
LOSStarget=-4；winning next action 的上一 pending target=score/2048+4；
winning afterstate 不拟合。实际动作后仍 spawn，再判终态并提交观察。

native 只在下一 raw memory block 提交点或预算边界前执行，返回后 host 提交
所有已发生 rank，再决定下一 bank。块末不提前规划下一动作或补 pending target。
预算暂停保留棋盘、单个初始 tile、RNG、pending afterstate/bank 和游戏得分；
相位切换只改变后续环境生成规律，不重置学习者或制造终态。
游戏上限8192，真实 cutoff 单独记录；quota 暂停不是 cutoff。

## 独立整局评估与端点

每 phase 末固定参数、当前 active bank 和 memory 预测 p，执行16个新种子完整
游戏（上限8192），不更新 memory/TD，不改变训练棋盘、RNG或pending。
三臂同 life×phase 的16评估种子相同。A′末另以 PERSISTENT 的同一 head/p
进行 DIRECT16局，对照 H2 模型规划贡献；不增加第四训练臂。

主端点：PERSISTENT−ORDINARY 的三相等权平均评估局 utility；
独立报告 A′ 保留端点。PERSISTENT−FROZEN、ORDINARY−FROZEN 和 H2−DIRECT
为贡献对照。utility=score/2048+4*WON−4*LOST，全部负例/cutoff保留。
每相位16局均重→三相均重life→16life均重；四个固定parent内重采整life，
20000 bootstrap、seed28600001，CI仅条件于这四个旧来源。

## 种子、留存与计费

warmup Python seed=286100000000+life*1000000+episode；
连续训练 native seed=286200000000+life*10000000（没有 arm 或 phase 项）；
评估 native seed=286500000000+life*1000000+phase_index*100000+episode。
DIRECT 复用 A′评估 seed。三个 stream 家族互不重叠。

来源训练和共同暖启动列物理成本及逐臂继承成本；每臂新增训练 raw预算均为
6291456，总新训练 raw=18874368。所有 initial、真实执行、TD更新、memory
路由、head创建/复制/驻留字节、H2后继、评估和计算时间分别计费。
匹配的是总训练环境观察，CPU及独立评估观察不强行相等，而是完整报告。
每chunk留 start/end状态、raw ranks/cells/kinds、动作/得分、路由和更新计数；
完整评估局留 compact outcome，不生成大checkpoint或逐步棋盘文件。
全部输出在 `reports/natural_online_value_v286/`。

若普通TD足够，接受普通参数学习贡献；若持久TD无额外收益，不声称模块保留
产生新增优势；若两种TD都退化于FROZEN，停止把“加TD”当成已成立的修复。
原 U005 Gate保持FAIL，U006不运行。
