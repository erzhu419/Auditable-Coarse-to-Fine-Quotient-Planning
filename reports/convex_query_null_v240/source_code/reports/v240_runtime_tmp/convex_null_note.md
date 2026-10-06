# V240：两个实际方向的连续凸坏原假设

仅覆盖risk的RETURN→SHORT和RETURN→RETRY，固定ε=1/20及V239必要行全部付费计数；不推广其他方向。
RETURN→SHORT有h=dc−sc−4+8s−4D_DEL+4D_LOST−ε，坏原假设h≥0与行simplex相交为凸集。
RETURN→RETRY有gap=d(8r−4−retry_cost)，d=0不可能达到ε；在d>0下等价于h=r−a−b/d≥0，a=(4+retry_cost)/8，b=ε/8。
h为凹函数，因此该坏原假设也是凸集；二分类loglikelihood f对(d,r)凹，线性情形的完整分类f对各行概率凹。
任意λ≥0令F=f+λh，坏原假设上f≤F。F在任意内点x的切线满足F(z)≤F(x)+∇F(x)·(z−x)。
线性情形取每行simplex的精确支撑，得到U=f(x)上界+λh(x)+Σrow[max_c v_c−Σc v_c x_c]。
继续情形取整个[0,1]^2支撑，得到U=f(x)上界+λh(x)+Σi[max(v_i,0)−v_i x_i]；覆盖所有d>0的坏参数。
v=∇F(x)，分类梯度n_c/x_c；继续情形二分类梯度k/x−(n−k)/(1−x)，∇h=(b/d²,1)。
除loglikelihood的向外界外，point、λ、h、梯度和支撑均可精确有理重算。point不需要满足坏约束。
局部优化器只建议point/λ；其成功状态不提供证明。只有logM向下界−U向上界严格超过log960向上界，才排除全域坏原假设。
候选反例须同时精确满足simplex、gap>ε及M≤960L；一例即可阻塞该固定比较。未找到反例或全域证书仍为unknown。
反例成员关系只指该比较的固定必要投影区域；不声称满足所有八族的交集。原证书、采样、费用和科学Gate不变。
