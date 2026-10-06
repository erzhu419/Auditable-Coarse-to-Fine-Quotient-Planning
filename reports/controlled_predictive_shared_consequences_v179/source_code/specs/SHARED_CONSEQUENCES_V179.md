# V179：共享动作后果，固定精确 H3 标签

V178 的合法性、goal和merge候选均未达到两折fit-child支持，有效树只使用vacancy；SOURCE/TARGET均不优于ONE。本轮替换分区与动作常数：在全部47个SOURCE H3根上拟合唯一共享动作后果模型，24个TARGET H3根只用于冻结选择后的诊断。12个来源设计组、6个目标设计组、原ordinal15 H2排除、goal rank11、固定后续教师goal_1_risk_1、完整精确R/F/S、效用R−F+S不变。设计组不是独立整局。

仅从canonical当前棋盘计算四次确定性swipe，不抽spawn；每个合法afterstate以唯一纯旋转使该动作朝DOWN，不反射。六维phi顺序固定：已达到rank11、vacancy数量、压缩row正rank相等邻接数、压缩column相等邻接数、row rank10相邻对数、column rank10相邻对数。各线去零保序，相邻允许重叠。所有71根特征缓存一次，不添加坐标、动作ID、额外特征或结果相关选择。

每SOURCE根的全部合法动作对(a,b)形成phi_a−phi_b与精确([R_a−r_a,F_a,S_a]−[R_b−r_b,F_b,S_b])，每对权重1/该根动作对数，每根总权重1。以sqrt(weight)缩放设计和完整向量，唯一np.linalg.lstsq(rcond=None)拟合6×3最小范数系数，无截距、ridge、调参、候选搜索或额外fold拟合。旧fold仅来源元数据。预测相对向量phi_a W+[r_a,0,0]，首reward只加一次；F/S不是绝对概率，不裁剪。ACTIONS顺序DOWN/LEFT/RIGHT/UP、EPS1e-12。单合法动作强制选择；其他需要每合法动作至少4个不同训练根且处在同一观测动作对连通分量，否则复用共同最大首reward回退。不存在child节点，本轮不修改旧树支持阈值。

只拟合SHARED；V178 STRUCTURE、V177 RAW/ONE及选择原样继承。输入先复制V178 stage_checks/run/roots/models/choices与V177 source_labels，冻结模型和SHARED选择后再复制V178完整labels。已暴露旧标签不因读取次序变成新鲜确认。完整SOURCE与独立副本一致；不重算旧kernel、旧fit或tape。记录继承成本链、新特征、矩阵/求解、选择、读取及纯测试成本，无物理样本、SOURCE整局或原生权重更新。

主诊断TARGET SHARED−ONE、oracle−SHARED，另报SHARED−RAW/STRUCTURE的完整向量与regret改变；SOURCE设计组等权、TARGET根等权，两种均值及逐根记录保留。无新Gate或随机CI，不以结果改配置。SHARED摘要只复用旧统计函数，空树适配器不作为实际模型；其树字段移除，model_kind标明SHARED。

额外诊断在每根将相同六维phi的合法动作归类，各类内按已知首reward最大、ACTIONS并列选择代表；用精确效用在代表间取最优。这个乐观“表示受限oracle”忽略跨根和线性约束，只给当前预测/并列规则的上界，不保证可学到。保留它相对ONE的有符号差、full oracle损失及所有同phi动作对的真实完整/去首reward向量差。此诊断不影响拟合或选择。

协议、实现、纯测试和wrappers在正式fit前按原字节留存。独立分析用另一swipe实现/手写旋转重建特征、weighted SVD重建唯一回归、支持、全部选择和统计；基线/标签逐项比对继承文件。输入字节在分析结束比对一次，源码字节由stage比对一次，不增加hash。失败付费记录保持，执行不一致为HOLD；负科学结果原样保留。中途产物仅reports/v179_runtime_tmp与reports/controlled_predictive_shared_consequences_v179。

限制：这是旧目标、有限H3、固定后续教师的机制诊断；六个聚合统计可能丢失具体布局，跨根线性约束另有限制。结果不能证明一般战略或长程多回合学习。既有H2基线、U005 FAIL、U006未启动保持。
