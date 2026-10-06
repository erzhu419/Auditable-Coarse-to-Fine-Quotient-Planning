# V290：完整游戏的共享地址巩固与同归一化顺序对照

冻结于正式拟合与新评估之前。复用审核PASS的V287完整事实A数据、四个
V120来源与16条life，保留原完整游戏前80%拟合/后20%留出、alpha=.0025、
初始化、MC后缀目标与一次游戏时间顺序，不新增训练环境观察。
本轮直接检验学习组织方法；V289锚点不作为方法选择或主评分端点。

## 四臂与地址质量

FROZEN来源表不拟合；EPISODIC_MC复现原逐样本顺序更新。
另外两臂每个完整游戏先用全部nonwinning afterstate的32次实际特征出现，
计算地址a的出现次数N_a=Σ_t c_ta，c为该状态内的真实重数。
winning afterstate解析处理，不进入地址统计或训练。

NORMALIZED_SEQUENTIAL_MC按原样本顺序，误差e_t使用当前表的原query预测；
每个实际地址写Δw_a=.0025×c_ta×e_t/N_a。
EPISODE_MEAN_MC在每游戏开始固定表计算所有e_t，按时间顺序汇总Σ_t c_ta e_t，
末尾每个地址只写一次Δw_a=.0025×Σ_t c_ta e_t/N_a。
两臂每地址名义系数总和均为alpha；差别在残差时点及合并写入。
后缀标签不含当前动作奖励，终态bonus为±4，raw表目标只减一次query offset。

不宣称两臂或原MC实际写表次数相同；原MC和归一化方法的有效步长不同。
MEAN与NSEQ若同样获益，归因于本轮归一化的净效果，不宣称聚合额外有效；
MEAN优于NSEQ才支持冻结残差/整局聚合的附加作用，仍非噪声唯一原因证明。

## 冻结终点与新游戏

主学习端点为EPISODE_MEAN_MC−FROZEN的新完整静态H2游戏utility：
score/2048+WON×4−LOST×4。每arm/life16局，种子
290500000000+life×1000000+episode，四臂配对同种子；true p_four=.1。
H2 depth2，使用同V287 fit-prefix memory预测p；评估不更新价值表或memory。
MAX_STEPS8192；自然终态与cutoff全部留存，cutoff不能作为完整终局证据。

主预测端点为完整heldout游戏的MEAN−FROZEN MSE，先每游戏全部nonwinning
afterstate均重、再游戏均重、life均重。完整来源/原MC的逐游戏评分和原MC
首尾更新/处理计数须精确复现V287。MAE和有符号bias另报，bias不定义优劣。
同时报告NSEQ−FROZEN、原MC−FROZEN、MEAN−NSEQ及MEAN−原MC的预测/utility差。
CI按四个固定来源内整life bootstrap20,000次，seed29000001，保留全部有符号
life及退化例。主学习结论必须优于FROZEN，不能只比退化原MC好。

## 成本与留存

每臂继承原V287同等来源、动力学、暖启动和全部A获取账本（包括排除尾段），
旧物理取得一次。本轮样本处理数相同、实际地址写入/预测/聚合数不同，分别
记录非winning训练样本、地址重数统计/查找、缓冲峰值、目标构建、写表、
新H2评估观察与规划、source/private复制字节、worker/编译/协调CPU和墙钟。
不新增来源或大checkpoint；输出仅在 `reports/episode_consolidation_v290/`。

预测改善而完整控制无净收益时，不称策略学习修复；两者均无改善则否定
此地址归一化/整局聚合干预，依据固定结果选择下一主线，不再做alpha网格。
本轮条件于四个旧来源与固定事实actor，不证明一般结构学习或长回合迁移。
原U005 Gate保持FAIL，U006不运行；本轮探索性学习实验不是正式Gate。
