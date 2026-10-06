# V170：持续策略程序与整局后果学习（冻结协议）

V169 的四步、单probe路线已关闭。本轮在获取新终局标签之前冻结以下
持续控制语法、训练／对照／验证预算与种子。继承 V169 的四个只读历史，
旧终局标签不参加训练；双query bank加载/setup保留，risk8零决策。
H2保持当前策略，U005 FAIL，U006不启动。

执行程序为两个控制节点，从node0开始。每节点有probe_action（四方向）、
true_action/false_action（四方向或H2调用）、true_next/false_next（0/1）。
每个物理决策重新取CURRENT棋盘D4最小框架，按原有首变换tie规则transport
probe；learned swipe合法且合并计分>0为true，否则false。COND使用当前bit；
LATCHED仅缓存每node首次观察bit，以后使用该缓存，但仍实际计算并计费当前
probe。选定branch同时控制action和next-node。合法direct执行一步；H2叶
调用自身risk1 H2；非法direct同一步调用H2，仍更新node，下一步继续观察。
每局重新初始化node0、两个latch空值，不重复四步词或永久退出controller。

SOURCE每历史4个新H2完整游戏，共16。每fold只用其余三历史的全部当前
predecision棋盘与实际动作，不筛选来源终局返回。逐状态取CURRENT D4框架、
transport来源动作，对四probe逐一记录合法正merge条件及动作频次。
probe的fit_count为true/false各最大动作频次之和，取最高两个不同probe，
tie方向字典序；条件众数动作为叶，tie动作字典序，无观察条件叶为H2。
parent0两node采用上述source叶，true边去另一node，false边留本node。
parent1用同probe/边、全部H2叶，行为等同incumbent、额外计算成本仍计。
两个node及其初始边是明确的有界先验；终局后果训练才能支持战略收益。
缺来源roster／不同parent停止；SOURCE cutoff仅保留观察标签和已付成本。

G1/G2固定两代beam2，各fold54物理槽：两个parent，再按parent、node0/1、
probe/true_action/false_action/true_next/false_next顺序列所有单字段替换；
probe替代DOWN/LEFT/RIGHT/UP，action再加H2，next替代0/1，跳过原值。
每parent26变异，重复程序仍逐槽执行，不能增加独立标签数。
每候选在其余三历史各2个新完整游戏seed上物理执行COND与LATCHED，
H2每fold/history/episode共享一次。每代2,616局，两代5,232。
只有实际整局terminal reward/failure/success向量用于fitness；不能将不同
策略轨迹的局部A/B或终局分量组合。episode→history→三TRAIN历史等权；
COND risk1整局效用选两个不同parent，tie程序字段字典序、首次slot，
负winner保留。所有要求的物理局缺失、重复、cutoff/null或身份/向量不一致
都保留数据并停止全部下游；TRAIN cutoff是incomplete，不解释为效用阴性。

FINAL两个parent在三TRAIN历史各4个新完整游戏上执行H2/COND/LATCHED，
共240局；按COND整局效用选一个程序，其同程序LATCHED不另行选择。
先冻结四fold全部program，再EVAL：每历史32个新ordinary-initial-state
游戏seed，H2/COND/LATCHED三个物理arm，共384局、128配对样本。
不按局部起点或来源优势筛选，不追加游戏、不因轨迹差异停止计费。

全轮5872完整游戏（SOURCE16，controlled5856）。每局保守上限8192步；
最多48,103,424真实转移。环境GOAL_RANK=11、16格，合并守恒数值总量，
初态两tile总量至少4，每合法步spawn至少+2；ACTIVE每格值≤1024，总量
≤16384。第8191步后总量至少16386，故此前必WON/LOST。此上限来自环境
结构，在新交互前确定；保留cutoff路径以如实报告实现异常或不完整数据。

BASE=17000000000。SOURCE seed=BASE+10,000,000+life×1,000,000+replica0–3。
G1/G2/FINAL seed=BASE+20,000,000/30,000,000/40,000,000+
heldout×1,000,000+life×100,000+episode（G0–1，FINAL0–3）。
EVAL seed=BASE+50,000,000+life×1,000,000+episode0–31。
程序/slot/arm不进入seed；初始两spawn和后续生成都消耗对应游戏的同一个
独立环境RNG，各arm共用uniform采样流，不等同相同棋盘轨迹。阶段流分离。

主对比COND−LATCHED，并报告COND−H2、LATCHED−H2与所有分量/逐历史。
每历史32个完整配对差的均值与样本方差，再四既有历史等权，正态CI95。
推进要求主对比和COND−H2效用区间下界均>0；未通过不采纳。不完整EVAL
不丢游戏，阻止受影响统计。区间条件于冻结teacher、训练选择和四既有历史，
包含新初态／整局生成的采样不确定性；crossfold TRAIN重叠，不推断新历史总体。
LATCHED仍使用CURRENT D4、合法性回退和H2，主对照只隔离每node首访之后
持续刷新probe bit的价值；不能归因为全部状态信息或全候选最佳消融搜索。

留存每decision的node/frame/probe/current bit/used bit/latch/leaf/action/
next/fallback，统计持续node访问、bit变化、direct/H2/非法回退及整局控制比例。
独立重放新来源/完整游戏，重建来源标签、变异、物理terminal选择与配对CI。
保留生成/观察/graph/teacher/回退/采样、测试及继承成本，无新neural权重更新；
不把H2调用或source知识当免费，不宣称采样效率。
源码/协议采样前保存在source_code/，结算原始字节比较一次，无新增hash。
这是首次有界持续控制实验；一般战略学习、结构增长与新历史收益仍需实证。
