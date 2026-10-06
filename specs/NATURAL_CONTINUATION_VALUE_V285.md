# V285：独立续行动作排序诊断（冻结于新续行前）

目标：检验 V283 的 H2(true p) 动作评分是否正确排列固定
ORACLE_H2 策略下的完整未来收益。估计对象是 Q^π_ORACLE(s,a)，不是真实最优 Q。
这次不训练或修改价值、模型记忆、旧实验或科学 Gate。

## 棋盘与分组

沿用 V281 四个冻结父模型、16 条 memory life、A(.1)/B(.5)/A′(.1)。
每个 life×phase 只用原 LIBRARY_H2 第一个游戏（episode_index=0）。
各取 4 个均匀 decision index floor(k*n/4), k=0..3；另取 4 个竞争棋盘：
V283 中 true-p full 与 zero-nonterminal-tail short 动作不同的 index，
排除前述均匀 index 后排序，取 floor(k*m/4)。共 384 个棋盘。
48 组竞争候选实际均至少 159 个，排除均匀棋盘后足够；不需要回退选择。
选择只读取留存棋盘、当前评分与 index，不读取后续 utility。
两组独立报告；竞争组不能代表全部自然决策分布。

## 续行与独立验证

每个合法首动作强制执行一次，随后以相位真实 p、原冻结叶、原 V135 H2
继续至 WON/LOST。没有重置初始棋盘或生成初始两块 tile；首步之后也 spawn
再判断终态。最多 8192 步（含首步），不更新权重或 memory。
实际转移用独立标准 2048 合并规则，不用学习规则生成环境。

各动作有 discovery 32 条及 validation 32 条续行。discovery 以完整
utility = total_score/2048 + 4*WON - 4*LOST 的均值选 winner（动作名打破平局）。
validation 只检验已选 winner−固定 full proxy，不重新选择 winner，也不截掉负值。
同一 validation 同时报告 short−full 和原留存 LIBRARY−full。
suffix_utility 扣除强制首步奖励，仅用于 tail 校准。

环境 RNG 为原生 mt19937_64；每步两个 [0,1) 抽样，先 cell 后 rank。
每个 state/batch/replica 的所有首动作共用 seed；规划不消费 RNG。
seed = 28500000000 + life*1000000 + phase_index*100000 + state_slot*1000
       + batch_index*100 + replica_index。
state_slot=0..7（uniform 0..3，competition 4..7），batch=0/1，replica=0..31。
因此动作间配对，两批及不同棋盘之间不重叠；该流不同于原 Python 游戏流。

## 统计与计费

每组每 phase 的 4 棋盘均重；3 phase 均重形成 life 均值；16 life 均重。
固定 4 parent 内重抽完整 life，parent 均重，20,000 bootstrap，seed=28500001。
区间只条件于这四个冻结父模型；另报每 phase、每 parent 和负收益 life。
主诊断端点为两组 discovery-winner 的独立 validation 收益差；其它对照为解释性。

记录每条续行的 seed/action/batch/score/status/steps/final_board；不保存逐步大棋盘。
所有续行实际环境转移、规划工作、CPU/墙钟和输出体积单独计费。
来源训练、V281 原采样成本仍列为继承成本，不当作本次免费获得的能力。
最多 98,304 条完整续行（实际按合法动作数）；四个父模型分别并行执行。
8192 步内标准 2048 必终结：未赢时总质量≤16*1024，每次 spawn 增至少 2。
若产生 CUTOFF，保留记录并检查环境语义，不用冻结叶补尾或当作失败。

## 解释边界与下一步

稳定正 validation 差说明当前 H2 代理存在该固定策略下可恢复的动作排序损失，
为目标反馈价值学习提供依据，但不把它全归因于叶误差（H2 截断也参与）。
若证据不明确，报告有限 MC 分辨率和样本范围，不据此新增阈值调参。
自然整局的净学习收益、独立新来源及总成本比较仍须后续冻结学习实验。
