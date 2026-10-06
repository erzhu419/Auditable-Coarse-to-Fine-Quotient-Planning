# V291：整局巩固的独立训练历史确认

冻结于新获取、拟合与评价之前。V290学习方法、来源、alpha=.0025及H2保持
不变，三臂FROZEN/NORMALIZED_SEQUENTIAL_MC/EPISODE_MEAN_MC；不再重演已退化
的原未归一化MC。64个新life id0..63，四个原V120来源各16个，parent=life%4。
一次固定cohort和样本量，不筛历史、不选最佳前缀、不按结果追加样本或调参。

## 新获取与冻结分割

每life使用原冻结来源表，在true p_four=.1下做DIRECT完整暖启动，直到
LIBRARY memory.observations_seen>=256，所有initial/post-action raw均observe。
warmup种子291100000000+life×1000000+game，实际暖启动游戏/观察全部计费。
随后新的FROZEN H2 actor连续获取131,072个raw观察，包含initial tile；
生成概率由已观测prefix的library memory给出，每64边界更新，来源表永远不训练。
actor stream seed291200000000+life×10000000；不取旧V287/V290任何目标历史。
三臂共用这一物理获取，样本和记忆完全相同。

只使用本A预算内的完整自然终态游戏，按时间前floor(4N/5)拟合、其余留出。
末未完成game不借未来/B后缀，完整获取和排除尾段仍付费。若暖启动/获取出现
真实8192步cutoff，保留记录并中止本确认，不伪造自然终态。两学习臂使用全部
fit nonwinning afterstate，winning解析处理；MC后缀、query offset、真实32次
特征重数及地址归一化完全沿用冻结V290实现，无表示、阈值或学习率搜索。

## 新完整游戏与判定

每臂/life32个新配对H2游戏，共6,144局；种子
291900000000+life×1000000+episode。H2 depth2、true p=.1；全部臂使用同一
fit-prefix memory预测p，评估不更新价值或memory。MAX_STEPS8192，所有
WON/LOST/CUTOFF显式保留，cutoff不能算完整终局确认。

主学习端点MEAN−FROZEN新完整游戏utility（score/2048±4）；先32局均重，
再64life均重。独立净收益要求该配对95%CI下界>0且无cutoff。
主预测端点MEAN−FROZEN完整新heldout游戏MSE，游戏内→游戏→life等权；
MAE、有符号bias及NSEQ−FROZEN/MEAN−NSEQ均为预定次端点，不替代主判断。
四个固定来源内分别重采16整life，20,000次，seed29100001，保留全部
有符号差/退化例；区间条件于这些旧来源，不称独立来源预训练确认。

## 成本、留存与后续

每臂经济训练成本包含四原来源价值训练、来源动力学、64新暖启动及所有
8,388,608个A raw，旧来源取得一次，新actor取得一次供三臂。旧V290目标数据
不作为新训练输入；先导获取/评估费用另作开发证据，不能当作免费独立确认。
分别保留源/私有表复制、样本/目标构建、真实写表/归一化/聚合及缓冲峰值、
新环境与H2规划工作、编译/worker/协调CPU和墙钟，不以相同样本数冒充相同写入。
输出在 `reports/independent_episode_v291/`，canonical actor获取压缩留存，
不保存大棋盘CSV或新checkpoint。获取边界快照不是额外评估游戏。

若主净收益成立，下一阶段原样推进A→B→A′连续学习、修正与能力保留；
若未成立，保留失败及预测结果，重新判断目标/规划接口，不继续本法的调参循环。
本轮是离线整局学习对新事实历史的确认，未证明闭环在线战略或结构学习。
原U005 Gate保持FAIL，U006不启动；本轮不是原正式Gate。
