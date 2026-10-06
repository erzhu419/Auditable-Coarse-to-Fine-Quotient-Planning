# V288：回报波动与共享特征的一次更新诊断

冻结于本轮读取标签作比较与来源预测计算之前。复用审核PASS的V285单 A、
16life、四个原V120来源。uniform/competition各4个预选棋盘独立报告；不重选
棋盘、动作、标签、学习率或预算。没有新环境、续行、拟合或控制策略。

## 预测与标签

每棋盘纳入全部合法的nonwinning afterstate，winning目标为解析终态，不进入
可训练特征矩阵，其已付续行仍计成本。用标准确定性swipe复原afterstate/score，
与留存first_score核对。V_i是原QueryTD直接叶预测（含query offset），不是
V285的H2 full_tail proxy。两批各32个 `suffix_utility` 为当前动作之后的回报，
不得加入first_score。continuation固定为原ORACLE_H2，生成概率A=.1。

实际n-tuple共有32个feature occurrence，重复地址保留重数。K_ij为两个状态的
feature multiplicity向量内积，原实现一次更新严格满足
ΔV_j=.0025×(target_i−V_i)×K_ij；实际内核没有除以32。
每项更新均从原冻结表开始，是孤立更新，不累计更新或修改正式权重。

donor i 的discovery32均值为μ_Di，recipient j的validation32均值为μ_Vj。
记β=.0025K、d=μ_Di−V_i，均值标签更新对独立validation的MSE差为
2βd(V_j−μ_Vj)+(βd)^2。
32个单样本标签更新的平均MSE差恰等于该差加β²×discovery population variance。
后者称经验标签波动惩罚，不能当作已知真实条件噪声；均值标签仍有有限采样误差。

## 端点与权重

每life/group构建全部有向i→j，包括K=0的保护状态。分别报告SELF、
SAME_BOARD_OTHER_ACTION、OTHER_BOARD；同棋盘依据预选state_id，不据标签。
先recipient的actions均重→boards均重，再donor的actions均重→boards均重，
最后16life均重。uniform与competition不混合，合法动作更多的棋盘不多投票。

主端点uniform OTHER_BOARD mean_label_delta_mse（正表示一次均值更新造成
其他棋盘预测损失）；single_label_mean_delta_mse和经验标签波动惩罚为机制
对照，competition为独立次cohort。所有有符号life差与退化例留存，不过滤零K。
四固定来源内重采整life20000次，seed28800001；CI仅条件于这些来源。

## 成本、留存与边界

新增环境观察和实际价值更新均为零。来源价值训练、动力学、原V281获取账本及
本次使用的V285单A全部64条/动作续行费用单列，原物理获取不重复执行。
记录本轮原始文件读取、确定性swipe、feature编码、kernel/预测/公式计算、
复制/驻留、编译和协调CPU及墙钟。所有输出在 `reports/ntuple_interference_v288/`，
只保存compact query标签/features和pair矩阵，不保存大CSV或新checkpoint。

此诊断识别固定cohort、既定更新的一次局部效应；它不检验连续拟合或新H2控制。
V285的ORACLE_H2后续策略与V287留存actor不同，不能归因V287全部退化，
也不能证明表示类不可能。只有实测结果支持时才选择巩固或表示修改；
原U005科学Gate保持FAIL，U006不运行。
