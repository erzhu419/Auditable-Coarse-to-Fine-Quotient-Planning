# V297：直接学习可执行策略，先验证稳定任务的完整棋局收益

正式采样前冻结。V296没有检出固定SOURCE续行的一次动作收益，
停止该目标支线。V292已做自身策略整局MC价值回归，本轮改变学习
对象：以完整执行回报直接搜索状态化策略参数，SOURCE价值表只读。
先稳定A；跨环境修正、保留及持久知识库在净策略收益之后再检验。

## 策略语法与学习

每局从两次实际spawn开始，策略记忆重新初始化。空格>=4时进入
BUILD，取当前最大rank的最小index单元，再取距其最近角落
（角落顺序0,3,12,15平局），锁定目标角。空格<=2退出到SOURCE
脱困，清除上一BUILD动作；直到空格再次>=4才重新进入。
BUILD调用原SOURCE H2取得所有合法动作Q和afterstate，再按
Q+theta·f选动作，字典序平局；theta4各在[-1,1]。
f依次为afterstate空格/16、最大tile到锁角的最小Manhattan距离的
负值/6、sum(rank×(6−distance_to_corner))/(16×6×goal_rank)、
是否重复上一BUILD动作。角落与上一动作是持续记忆。非BUILD使用
SOURCE。零theta精确退化到原SOURCE H2，必须有限测试确认。

四旧来源、16条新life（parent=life%4），不复用旧carrier/动作标签。
规划p仅取来源已学spawn_distribution中的rank2分数；真实生成p=.1
只用于环境，不能提供给优化器。Query沿用score/2048、赢+4输−4，
最长8192步，真实截断加0并保留；禁止价值写入、MC标签拟合或SARSA。

CEM与RANDOM_SEARCH各四轮，每轮八个唯一参数程序、四次完整执行。
SOURCE零程序及当前incumbent（去重）先列，其余由Gaussian生成并
逐坐标clip[-1,1]。初始mean=0、sigma=.25；CEM按训练均值选top2，
更新mean=.5旧mean+.5精英mean，sigma=.5旧sigma+.5精英总体std，
sigma限定[.025,.5]。每轮incumbent取当轮最大均值，平局候选顺序。
RANDOM_SEARCH始终mean=0、sigma=.25，也保留当轮incumbent；其余
候选数、重复次数相同。提案使用同标准Gaussian随机流。两臂各
128个逻辑训练game/life，实际raw、CPU允许不同且分别计费。
相同theta、同p、同seed的程序只有一次物理执行，全部逻辑引用保留。

训练seed=297200010000+life×1000000+round×1000+replica；
提案seed=297300010000+life×1000000+round。测试世界仅29700003xxx。
完整四轮结束后固定最终theta，每方法32次新完整SCIENCE执行；
science seed=297900010000+life×1000000+game。科学结果不参与
候选选择、参数更新、停止或追加样本；所有负历史与SOURCE赢家保留。

## 判据、成本和边界

主CEM−SOURCE的新完整game utility；次CEM−RANDOM_SEARCH、
RANDOM_SEARCH−SOURCE。game→life等权；四固定来源内各抽四life，
20000次bootstrap，seed29700001。主CI严格正下界且所有训练/评价
无截断才支持稳定A上的完整策略收益。随机搜索控制隔离提案优化；
训练最大值及次比较不替代主端点。不筛除最终零程序或无动作变化。

记录实际初始/逐步spawn、所有候选执行、模型枚举、策略记忆/特征、
源加载/编译/CPU、提案与参数更新、物理与逻辑引用。来源训练和
动力学费用继承；旧carrier和V296发现/验证费用作为未使用开发证据，
不冒充本轮训练输入。相同候选/局数不是相同raw预算，本轮不建立
成本优势、跨环境学习或一般战略学习；U005 FAIL不变，U006不启动。
所有产物在reports/direct_strategy_v297/，不产生新checkpoint。
若主收益未成立，停止此冻结语法，不增加搜索轮次或调尺度继续追正。
