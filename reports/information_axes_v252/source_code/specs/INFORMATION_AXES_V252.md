# V252冻结：集中采样后返场查询的信息轴诊断

V251 complete、independent valid、阶段10/11；两QUERY臂逐目标历史完全相同，返场仍48/72。集中A使困难类型获得2864–3072共享S/D样本，节省总样本0.56%，模型CPU增加81.63%，SHORT→DETOUR_RETRY的24个goal阻塞不变。本阶段不再搜索配额，区分当前已付终态中S/D和R各自允许的歧义。

只读V251 UNIFORM_SHARED与QUERY_SHARED，每臂全部24个A_RETURN goal所选SHORT、DETOUR_RETRY比较未获证的终态；每life8个、两臂life/index配对。先冻结整张48端点名单、源码与协议，再分类。QUERY_FIXED重复历史不作独立端点。不读results、laws、真概率或world；不采样、不调用优化器、不重打旧分、不生成查询证书。

每端点三个预声明候选，共144个状态：

- RETAINED：严格复用V248原profile恢复与一次SHORT修复。
- R_CENTERED：严格复用V248，将同一恢复D行的R DELIVERY固定当前原生R经验频率，再独立一次SHORT修复。
- SD_CENTERED：S、D全分类行固定当前原生各行经验频率，独立解析求R DELIVERY=q，使goal gap=STRICT=50001/1000000。设s=S DELIVERY，d=D DELIVERY，r=D RECOVERY，sc/dc为原公开cost，则q=(STRICT−sc+dc+4s−4d+r×retry_cost)/(4r)，R LOST=1−q。该候选不依赖旧profile恢复是否成功；r=0或q不在[0,1]时unknown，保留原因；不裁剪、不重试、不另选点。

各合法候选必须为完整simplex、严格gap恰为STRICT。逐个检查canonical S_D_FULL_R@960、全部8个原queryfamily@960、原9个完整分类执行事件source/pool/member@720/720/8640；不以边际包络替代完整事件，不重分配事件预算。保留原profile引用、候选来源/修复、经验行、逐行TV距离及所有精确membership。原两候选语义及unknown/paid_constraints_reject_candidate/full_region_bad_witness状态保持V248定义。

R_CENTERED全域坏核证明S/D歧义在R经验中心仍存在；SD_CENTERED全域坏核证明R歧义在S/D经验行仍存在。经验行不是已知真行。有限候选被排除或不可构造，不证明坏空间为空、R充分/必要或证书保守。任一全域坏核只能给同一终态、同一原区域的获证上限；每臂按三候选的唯一坏核端点并集计72−端点数，不重复计算候选，也不外推到新样本/新方法。

按arm/variant/life及配对端点汇总，保留SD/R固定对照、原费用与共享支出。独立审计不导入新producer/core，不读真值；从V251实际source/probe/普通批次增量累积nativeA/B，在各目标自己时点复算counts/member/原source-pool-member事件与费用。B改变前无B池，30切换快照，B共享批次后才目标，返场无B反向合并。不重审已独立valid的随机outcome生成，也不重新求旧planner/证书。

完成要求为48端点、144状态完整且独立valid；诊断允许负结果，不授算法资格。新代码/测试/协议分类前留存，实际退出码、耗时、stderr保留，全部临时产物在reports/v252_runtime_tmp，输出reports/information_axes_v252。原V25110/11、原Gate和U006状态保持。
