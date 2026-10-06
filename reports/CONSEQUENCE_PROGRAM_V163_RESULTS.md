# V163：终局后果学习已实现，分支覆盖不足使验证停止

已实现从配对 A/B 干预的完整奖励、失败、成功向量学习程序分支，保留等起点、等历史权重及同候选对照。27 项测试通过；独立审计72/72、冻结源码86/86通过。

训练停止于留出历史3、risk1的P0：true40、false0、未进入分支8，无法辨识false分支的终局后果。其余15个候选组合完整。按冻结规则保留 `incomplete_training`，EVAL未启动；这轮没有验证收益结论。

32个新来源游戏及1,920条干预均终止，新增996,655次转移（来源31,288，干预965,367）。7张符号分支表已拟合，神经权重未更新；全部来源、测试、继承及逻辑映射成本留存。主运行／审计各一次，111.99/134.10秒，stderr均为0。

下一步检验支持感知的知识修订：仅更新有终局证据的条件，未观测条件保留已有来源规则并明确其未辨识状态；使用另行冻结算法和新TRAIN/EVAL，不改变本轮停止结果。保持H2；U005 FAIL，U006未启动。

[协议](../specs/CONSEQUENCE_PROGRAM_V163.md) · [独立结果与成本](controlled_predictive_consequence_program_v163/analysis.json) · [训练与未识别分支](controlled_predictive_consequence_program_v163/frozen_programs.json) · [源码比较](controlled_predictive_consequence_program_v163/source_comparison.json)
