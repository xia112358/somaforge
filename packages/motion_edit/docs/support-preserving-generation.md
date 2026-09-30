# 编辑轨迹的支撑保持与站立段裁剪

## 当前接触区域运动口径（2026-09-30）

**目标修正：还原原始物理执行，不用几何滑移代价创造新的执行。**
2026-09-30 的 `support_coverage_repair` 与 `support_budget_repair` 是已停用的
几何优化诊断，不能作为正式动力学参考。旧几何聚合优化器及其专用材料点传输模块
已移到系统回收站，不再提供可执行入口；原始执行代表不能通过优化姿态制造“物理还原”。
持续接触激活不意味着部位必须固定；原始载荷转移、卸载时的姿态调整应保留。
几何预算、接触激活与真实载荷速度是不同证据，不能互相冒充。

`versions/raw_execution_reference_20260930` 提供完整执行代表的对照：
用事件对齐后的全身距离选择原始执行，但导出时保留它的原始物理时钟及姿态，
不应用时间拉伸、逐帧均值、IK 或滑移优化。原始速度/控制通道保存在
`original_state.npz`，载荷通过原录制的环境/帧索引及哈希追溯；固定姿态重新查询
只用于该姿态的 Newton 接触标签，不冒充原轨迹同次求解的动力学载荷。

`native_contact_pivot_and_region_motion_v3` 统一聚合、Motion Edit 原生修复、事件几何运动验收和
`scripts/analyze_contact_region_motion.py` 的逐步统计。每步只读取当前 Newton 已激活、
已分配且经共享主表面筛选的点对，将同一个机器人局部材料点变换到下一帧，计算切向位移。
下一步可随真实前掌／后跟接触变化选取不同区域，不比较两个不同 witness 的世界位置。

几何运动项使用实际接触样本的最小切向位移 `pivot`，衡量是否存在低运动支点，
允许绕它转动。同时保留 q25、中位数、q75、最大值和样本数，不用最低点掩盖区域运动。
这些几何样本无候选受力分配，不能解释为面积、受力比例或整个足部无滑动。
`support` 兼容字段与 `pivot` 相同；q25 仅在 `lower_quartile` 诊断字段中保留。
旧 v2 报告必须按其原 schema 解释，不能把旧 `support=q25` 当新支点指标。

优化和验收共用同一支点实现；事件阶段内累加逐步 `pivot` 位移，不因前掌／后跟
样本变化重置。默认几何预算改为按同部位源支撑时段去重汇总每步运动，
取 `中位数 + 3×MAD` 后乘事件步数；源累计运动超预算会标记为质量问题，
不再用累计运动本身兜底，也不再用异常事件的 P95 放大预算。
初始化一次并保留统计依据；候选更新不重新放宽预算。不再隐式使用6 cm。
这是源轨迹的几何统计预算，不是从受力速度推出来的摩擦滑移容差，也没有覆盖所有示范。
预算不参与接触激活判断。无实际激活接触的步骤记为缺测，候选几何点对不能
补成支撑测量；优化可保留源样本作恢复引导，验收仍报告缺测并不通过。
下文历史实验采用的旧中位数／候选点测量保持历史含义，不能冒充当前口径的验收结果。

几何最低点不定位真实承重支撑点，不能作为承重支撑验收。`phase_support` 显式标记
`support_location_status=unknown_without_same_solve_per_constraint_force`；其 `passed`
只表示几何运动预算通过。真实支撑运动由 `newton_support.support_motion` 在已验证的
激活／分配／主表面点对上，按同次 MJWarp 求解的法向力加权计算作用点切向相对速度 RMS。
另报受力点最低／最高运动；即使一个受力点静止，其余受力点滑动仍反映在RMS中。
不以单个材料点、不以多个点的平均速度，也不以虚构的接触点包围区域代替真实支撑。
原始力、作用位置、速度保留独立审计；力不重新定义接触。零合力或缺失逐约束力时，
支撑位置明确未知，不认为静止。旧 raw Newton force 全零且仅有部位合力的记录无法补出
逐接触点受力，必须按新增 `solver_support_semantics` 重新采集。

当前 `newton_mjwarp_force_bearing_point_motion_v3` 同时保存求解前、求解后作用点速度，
以及由同次约束评估的 `xpos/xmat` 换算的 Newton 刚体局部作用点坐标；不能用积分后位姿反算。
`cvel` 是受力修正前的速度；主运动指标使用本次求解后的 `qvel`，经实际 `cdof` 和
刚体祖先链构造作用点速度，不运行额外物理步、不修改求解器状态。力与作用位置来自
同次求解，几何仍是该次约束评估的积分前几何；不得与记录的积分后位姿冒充严格同帧。
真实主表面通过同一原生场景有限三角面映射和共享主表面选择器归属；所有原始约束点保留。
正式分析入口为 `scripts/analyze_recorded_support.py`，缺少受力、速度、实际场景映射或
当前 Newton 版本证据时明确拒绝，不能用旧部位合力或裸距离重新生成支撑点。
它输出逐部位速度中位数／P95／P99；这些分布尚不是自动验收阈值。当前录制仅保存
每个控制周期最后一次物理求解，不能将速度样本冒充完整子步积分的滑移路程。

Motion Edit 的 `support_slip` 只读报告引用经过校验的 motion 和实际 Newton 标签，
显示每个接触样本从当前姿态到下一姿态的材料点切向位移箭头，统计最低／中位／最大。
绿色最低点只表示几何支点，橙色其他点不自动判为错误；箭头倍率不改变统计数值。
旧 `support_motion` 固定点曲线仍是历史材料点诊断，不作为新滑移标记。

已退役的几何聚合实验曾使用源受力证据限定支撑部位和表面，
候选可在同一末端的实际接触子体之间转移，不固定源受力的碰撞子体。
并定期重新查询候选的实际 Newton 接触点。其运动区间为 `[start,end)`；
终点姿态接触仍保留，但不误算完成事件后的下一步。每步对同一个候选材料点计算切向运动，
取真实接触样本中的最小值：允许绕实际支点转动，不插值构造虚拟支点，也不将
不同 witness 的位置变化记作滑动。缺少实际支点单独报告，由接触恢复约束处理，
不能当成零滑动通过。此项仅衡量几何上是否存在低运动支点，不能认证整个接触
区域无滑动或候选的实际受力分配。policy 只用于提取原始执行轨迹；不使用旧 policy
跟踪聚合结果作为此次验收。

以下 `force_support_v3_20260930` 为历史源材料点实验，其优化器和专用模块已退役。
当时每步跟踪同一个局部材料点，但允许后续步骤换支撑点；
逐点平方切向运动按实际源法向力加权，不先平均速度制造虚构静止支点。
每条执行先独立归一化受力，再等权聚合执行，接触点多的执行不会多占票数。
此运动项不包含接触距离目标；接触激活、约束分配、共享主表面和全身穿透仍由新 Newton
查询独立验证。聚合候选的材料点运动是源受力位置上的 FK 诊断，不能声称候选执行后
仍有相同受力分配。对照版只关闭这一运动项，其他目标一致。
正式数据集不会自动切换到实验结果。

### 承重点事件聚合对照（2026-09-30）

`force_support_v3_20260930` 补录原 `model_06000.pt` 的16环境完整执行，15条完整轨迹
参与拟合；末段仍裁剪到931帧，事件假设、双接触完成要求保持。两版均采用相同的
200步优化和原生接触／全身避碰要求；对照版仅关闭承重点运动项。
多接触完成要求按其真实部位分别提供几何恢复引导，使用实际 `includemargin` 上界，
不把整个脚已接触当作脚尖、脚跟同时成立，也不吸引到固定1 mm。
源材料点贴面引导在候选点缺失时仍提供梯度，但其本身不生成接触真值。

| 同一源受力位置／权重下的 FK 运动指标 | 聚合前 | 对照版 | 承重点版 |
| --- | ---: | ---: | ---: |
| 全部支撑阶段合计（cm） | 39.670 | 65.774 | 18.961 |
| 320–470左脚（cm） | 3.933 | 7.488 | 2.710 |
| 320–470右脚（cm） | 6.153 | 6.109 | 5.567 |

两版均通过33项事件检查，926–931帧脚尖／脚跟持续双接触，初始化 Newton 模型未检测到
穿透；逐帧接触170／171附近仍有两条差异，但事件级验收通过，不能把它们另立成事件。
承重点版最大关节步进12.237°（源12.179°），最大二阶差分6.536°（源7.266°）；
原有不连续性尚未完全消除。右脚320–470阶段改善有限。
这些数值不等同于候选接触部位的实际滑动，旧承重点在候选转动后可能已不再支撑。
正式实验目录包含 `source/`、新的固定姿态 Newton 标签、完整求解器补录证据、对照和
哈希 manifest；`training_ready=false`，训练入口和现有数据清单未变更。

### 实际接触支点聚合对照（2026-09-30）

`support_site_retry_20260930` 复用同一15条原始 rollout 受力证据和事件对齐，
两版各优化200步，只开关候选接触支点运动项，每10步重查候选实际接触。
完整导出后的独立 Newton 复查，源／对照／新约束累计几何支点运动分别约
24.57／58.16／3.30 cm。三版767个支撑步骤均无支点缺测，事件验收通过，
926–931帧均保持脚尖／脚跟双接触。两版候选未检测到穿透、无整帧失去全部接触；
仍有两条逐帧接触差异，按既有事件噪声规则处理。新约束版最大关节步进12.231°，
二阶差分6.529°，源既有的关节跳变未解决。

`site_audit.json` 保存阶段统计与事件结果，`*_candidate_sites.npz` 保存实际支点
局部坐标供审计。指标是实际接触样本中的低运动支点存在性，不代表整片接触区域
无滑动或承重成立；原始 rollout 的受力运动仍独立分析。此实验不执行 policy 跟踪，
不切换训练清单，`training_ready=false`。

生成应限制支撑部位自身的切向滑移，同时允许真实支点上的转动与支撑位置转换。
源材料点云的运动保留为诊断，不能直接解释为候选滑动。这是轨迹优化要求，
不是新的接触定义。

### 历史统一接口复查（遗漏开头支撑，不能作为当前验收）

`support_motion_v3_validation.json` 使用18个显式支撑事件和该事件目标表面的全部
实际接触样本，不再沿用旧实验的源受力子体限制或端点后多算一步的区间。
源／对照／新约束几何支点累计分别为21.32／55.57／3.28 cm；
当时源和新约束均在旧源统计预算内，对照13段超预算。旧预算范围约0.07–6.58 cm，
按各事件源每步P95和时长生成；当时 `SourcePhaseMotion` 对源轨迹的损失为0。
上述统计未覆盖0–103；当前已补齐实际持续接触时段，并改用同部位 median+3MAD，
旧“3.28 cm”和旧预算不能代替完整轨迹的新验收。
新约束版143–171左脚支点累计约0.059 cm，但区域样本中位累计约4.578 cm，
说明不能单凭支点统计给出整片无滑动结论。该分布也不代表受力比例。

`original_loaded_motion_episodes.json` 另保存原始执行的受力点最低、最高及加权RMS
速度和各部位P95/P99；只统计各环境首次不中断执行，重置后样本排除，失败执行标记。
候选无同次求解受力，始终明确未知，不把源的受力权重转成候选滑移真值。

## 编辑约束

- 第 0 帧参与与后续帧相同的 IK；不再用独立 `initial_qpos` 覆盖、锁死输出首帧。
- 接触编辑窗口不缩短源接触区间。
- 按末端合并连续接触段；足跟、足尖和碰撞形状切换不重置支撑。
- 同一段使用一致的刚性编辑与源材料点运动，保留示范中的滚动。
- 单点材料样本补姿态约束；线接触的滚动自由度保留。
- `support_residual_scale` 默认 100，是优化残差系数，不是接触距离阈值；有限权重不保证接触可行。
- `support_rotation_policy=episode_yaw` 保持整段编辑航向；`authored_surface` 是待验收的替代方案，不能因材料点误差更小就认为更好。
- `support_origin_policy=median` 使用整段参考平移中位数；`landing` 使用段首参考，防止后续参考改变首次落点。
- `support_approach_seconds` 可在接触前增加独立软接近任务（默认 0，须通过实际验证后在计划中启用）。任务将落点材料样本沿源 FK 反向搬运，保留接近期间的高度变化，以五次平滑函数渐增残差权重；不延长源接触 mask，也不把接近任务计为接触。
- 仅渐增权重仍可能导致最优姿态突然变化。接近窗口起点记录已求解的实际材料点位置，目标以同一平滑函数从该位置对应的源运动偏移过渡到支撑目标；偏移只初始化一次，后续迭代不移动目标原点。
- 朝向补足同样沿上述接近阶段过渡：使用落地时需要补足的轴，将源朝向沿时间搬运；从窗口起点实际朝向记录一次旋转偏移，再沿最短旋转弧消退。位置、朝向共用窗口、相位和权重。线接触原本允许的滚动不会因此被锁定。`support_approach_orientation=False` 仅用于关闭朝向过渡的消融对照。
- 时间差分只引用真实历史：第 0 帧不施加速度／相邻帧平滑项，第 0、1 帧不施加加速度项，关节与 root 同步处理。源姿态可作求解初值，但不能冒充输出轨迹的负帧历史。
- 旧 `native_hard_release` 会按源帧号禁止提前接触。它可能与软接近发生冲突；关闭此优化约束的实验必须重新查询真实接触时序，不能声称旧时序仍然保持。

## 验收

### 目标去重版本

计划 metadata 的 `augmentation_objective=consolidated_v1` 启用去重目标；
未指定时拒绝生成，不再隐式选择旧目标。去重版本尚需逐轨迹 Newton 验收。

最终 IK 按四类职责组织：

|职责|内容|去除的重叠|
|---|---|---|
|末端任务|接近阶段、表面法向、切向支撑、有限表面边界、退化材料点的朝向补足|支撑期用 episode 权重替换弱表面参考，不再叠加另一份 XYZ 残差；不再优化额外逐帧落点坐标|
|姿态参考|Laplacian 全身参考、关节/root 偏移代价、非支撑期足部朝向|支撑期关闭重复的整足朝向先验|
|修正连续性|相对参考的关节速度/加速度、root 修正速度/加速度|不使用绝对相邻姿态静止项，也不再叠加落点时序项|
|碰撞|相对源参考的加深惩罚、自碰撞|关闭双向距离相似吸引；参考距离仍用于计算允许的源几何基准|

接近和支撑共享编译出的材料点目标，接近阶段不会修改真实接触 mask。
法向支撑强度保持原来的 episode 系数，避免去重时同时放松法向接触要求。
Laplacian 是目标传播阶段，末端按 episode 保持、材料点固定采样分别解决时间身份和空间身份，不能当作重复机制删除。
此版本仍是逐帧 IK，不代表整段联合优化或动力学执行。

### 实际检查

正式检查使用 `scripts/analyze_contact_region_motion.py` 的材料点区域统计、
`event_acceptance` 的事件级检查及原生查询的 `full_robot_separation`。
旧逐帧一致性审计入口已退役。完整对齐轨迹需分别检查：

1. 校验权威资产、motion/labels 哈希绑定和当前 Newton 接触语义。
2. 通过共享主表面选择器读取真实有效接触；保留原始点对审计。
3. 分开报告缺失／新增接触、未分配约束、无接触帧与原始穿透距离。
4. 在相邻帧跟踪同一个材料点，按末端报告相对源运动的额外位移。
5. 报告真实首步位移。IK 返回成功不能替代上述检查。
6. 扫描全部相邻帧的末端位移、关节增量及二阶差分，覆盖接触建立、释放和摆动阶段。持续支撑稳定不能掩盖接触切换时跳变。

没有固定 handle 时，旧 `fixed_contact_drift` 指标现在是 `null/not_applicable`，不再给出零漂移的假象。
这些检查不会自动设置 `training_ready=true`；接触激活不等于承重、无滑动或动力学可执行。

## 裁剪

`scripts/compact_edited_stationary.py` 接受已有证据支持的站立区间：保留起点，移除 `(start,end]`，不插值姿态。
每帧保留 `source_frame_indices`，记录切口 `seam_frames` 和连续片段范围。
速度只在连续片段内部计算，避免把裁掉的几秒时间伪装成一个时间步。
裁剪产物必须重新查询 Newton 接触并重建事件，不能沿用旧缓存或拼接旧标签。
未经单独验收的接缝不可作为跨段训练动作。

正式实验产物放在 `runtime/current/motions/climb00_contact_dataset/repairs/`。
旧 207 条及当前训练 manifest 不因单个候选生成成功而自动替换。

## 统一入口与原生几何修复

### 旧路径退役（2026-09-28）

正式生成只保留 `rollout_authority.generate_contact_aware_pyroki_preview` 实现。
CLI、编辑器和批处理共用该后端及 `generation.contract` 校验：

- plan/taskspace 必须显式声明 `augmentation_objective=consolidated_v1` 和
  `free_surface_contacts=true`。缺失版本不再默认 `legacy`，旧计划必须按事件和真实表面重建。
- 源 motion 必须通过权威 G1 资产指纹校验；IK 不接受其他 URDF。
- IK 不再接受裸 LTE keypoints，不再忽略未解析的语义部位或接触任务。
  链接只按名称或显式别名匹配，不做子串猜测；不把缺失足部球体替换成踝关节。
- 旧 `apply_contact_edit_plan_to_motion` 实现、公开导出、旧导入别名、
  旧 subprocess 调用和重复接触提取实现已退役。
  LTE 模块保留当前接触图和几何阶段使用的内部函数，不保留旧轨迹生成入口。
- 旧格式拒绝测试替代旧入口成功测试。现存 207 个 `design_v2` 计划通过配置校验，
  这仅证明格式可用，不表示增广轨迹通过物理验收。

四个经确认的旧文件已移入系统回收站。旧数据、checkpoint、训练 manifest
未删除或替换；它们也不会因为入口清理而自动获得新的接触语义版本。

`generate-ref --plan ... --output-motion ...` 和
`generate-ref --plan-manifest ... --output-motion-dir ...` 共用
`generate_contact_aware_pyroki_preview`。旧 LTE CLI 与旧增广队列已移除；
不能用 proxy 误差、旧硬锚点元数据或源接触图把候选直接标为合格。
每个候选的 `.generation.json` 保存实际求解目标与 `training_ready=false`。

`native_contact_refinement.refine_trajectory` 对候选进行软轨迹修复：

- 保持接触按事件区间表达，足部形状切换及帧噪声不重新切事件。
- 每次更新重查当前政策配置初始化的 Newton 场景，验证 fingerprint。
- 全身环境碰撞、自碰撞及接触激活均取实际 witness；未分配接触报错。
- 接触／避碰统一复用 `contact_solver.contact_regions.unified_region_objective`，不再调用激活后归零的 `selected_contact_activation_deficit`。
- 通过完整 Newton witness 张量读取全身点对，真实主表面使用 source-triangle normal-fan；不再用旧 HTTP 精简点对训练。
- 缺少候选点对时，用权威碰撞区域的完整表面采样向事件绑定的有限主表面提供梯度；缺少源目标则报错，不把无候选记为成功。
- 接近目标按真实主表面绑定。不同固定子链接的材料点先经 FK 转到共同末端坐标，不能直接混用局部坐标。
- 保留相对原候选的支撑材料点运动与二阶连续性。毫米尺度仅归一化损失，不定义接触阈值。
- 周期性复查全部帧；只有无全身穿透、所有事件接触实现且无缺失候选才通过。

这仍是运动学修复。后续须重新写出 canonical motion、执行实际接触重标注，
再验证轨迹连续性与动力学执行；不能把静态复查成功等同于可承重或可执行。

### 共享区域损失接入（2026-09-28）

`regional_contact_refinement.EventContactRegions` 只把训练中的单箱接近几何
适配为事件绑定的任意有限水平面；区域划分、区间上下界、固定区域归一化、
稳健惩罚及双侧梯度聚合直接调用共享实现，不复制第二份训练损失。
当前共享优化区间上界为实际 `includemargin`，下界为零；此前区域路径仍使用
0.05 倍 margin，已在 2026-09-29 改正。区间仅用于优化，真实接触仍由
`CONSTRAINT`、`dist < includemargin` 与约束分配决定。边界处零残差不等于激活。
原有支撑材料点运动、相对参考连续性和姿态偏移正则保留。

正式复现入口为 `scripts/refine_motion_contacts.py`，需要显式传入 motion、
events、support-phases、event-reference-contacts、taskspace、checkpoint、manifest、
binding、continuity-reference 与新的 output 目录。
它启动专用 Newton 查询 worker，不启动训练；`--audit-frames` 保存同一次查询的
CPU 与设备接触证据交叉核验。历史 tmp 驱动所用的精简 HTTP query 已不满足
新接口，不能作为备用修复路径。所有输出保持 `training_ready=false`。

验证记录：

- h110 v4 成品经当前完整 witness 查询，初始即为零缺接触、零穿透，
  因而未执行优化；这不是新损失的修复收益，旧报告不能直接作为当前失败真值。
- 从 `motions_full` 未修复 h110 候选重跑 240 步：最大穿透
  12.668 → 1.203 mm；缺接触部位帧 16 → 0（第 32 步后始终为零）；
  最终仍有 32 帧存在负距离，`passed=false`、`training_ready=false`。
- 第 282、283 帧同一次 Newton 查询的 CPU 与设备主表面接触结果一致；
  全部原始查询结果保存在输出目录的 `*_same_pass_audit.json`。
- 结果目录：`runtime/current/motions/climb00_contact_dataset/versions/`
  `event_consensus_207_20260928/native_refinement_v7raw/`
  `pair48_10_h110_dp0p000_ap20_ru_m050/`。未替换训练 manifest，未启动剩余 204 条。
- 完整 Motion Edit 与共享区域目标测试共 423 项、3 项子测试通过；随后新增的
  通用有限面／训练单箱接近代价等价测试也通过。predictor 文件未修改。

### 事件三态与源轨迹连续性修复

增广事件是稀疏意图，不能把所有非 required 的部位当作 release。适配层显式
传入 release mask；未约束的部位只参与全身避碰，不被强制离面。共享训练目标
不传该参数时保持原有完整接触计划语义，predictor 未改动。

显式释放采用 `release_events`，每项为 `part_index`、`start_frame`、
`end_frame_exclusive`、`scope: whole_endpoint`。与 required 重叠时报错。
旧 touchdown 的 `release_frame` 不用于推导整个末端释放：真实数据中它可跨越
该部位在其他表面的有效支撑。没有显式释放证据就保持未约束，不补造离面要求。
显式释放的优化下界为实际 pair `includemargin`；验收仍读取实际有效接触，
任一向上主表面的已实现接触都会计为 release violation。

`--continuity-reference` 必须指向未经过增广 IK、逐帧对齐的聚合源 motion。
校验权威资产、帧数、fps 和关节名称，重排到 canonical joint order。
关节一阶、二阶差分对齐源轨迹；静态偏移允许存在。编辑后的候选继续作为
姿态偏移及世界空间材料点参考，不把未变换的源 root/世界坐标套到新地形。
配置源连续性时执行完整优化步数，不因静态接触提前通过就保留跳变。
报告独立记录真实接触、穿透、释放违例和连续性残差；`passed` 仅表示静态
几何验收，所有候选仍为 `training_ready=false`。

h110 同一未修复候选重跑 240 步，结果保存于
`native_refinement_v8/pair48_10_h110_dp0p000_ap20_ru_m050/`：

| 指标 | 初始 | 旧版 240 步 | 三态＋源连续性 240 步 |
| --- | ---: | ---: | ---: |
| 最大穿透 mm | 12.668 | 1.203 | 0.634 |
| 存在穿透的帧数 | 34 | 32 | 45 |
| 缺接触部位帧数 | 16 | 0 | 1 |
| 最大单帧关节变化 ° | 22.384 | 22.368 | 16.292 |

新版缺接触为第 171 帧左手，仍未通过静态验收。关节速度残差
0.9060 → 0.6628，二阶差分残差 0.2405 → 0.1082；改善不等于跳变已消除。
旧版延长到 640 步仍为 22.383°，因此仅延长旧优化不能解决参考错误。
当前事件文件没有明确整个末端释放事件，5112 个未约束部位帧不再被误当作释放。
`comparison.json` 保存全部过渡的关节和末端连续性审计及旧版对比。
426 项回归测试、3 项子测试通过；静态仓库检查无错误。未替换训练数据，
未启动剩余 204 条增广。

### 缺失点对材料点引导与输出平滑

`event_material_recovery_output_smoothness_v1` 在没有匹配目标主表面的 Newton
点对时，使用事件已有的局部材料点及有限面内部目标进行软恢复。没有事件材料点
则报错，不虚构接触目标。恢复点对后关闭该补充项，继续共享区域损失；引导不会
修改真实接触标签或放宽激活条件。归一化读取本次查询的实际 configured margin。

末端平滑从“相对坏候选的二阶差分”改为“输出材料点的二阶差分”，避免把原 IK
跳变当作必须保持的参考运动。支撑运动项、源关节差分和姿态先验保留。
所有修改作用于通用增广修复，不包含特定帧号或部位的例外规则。

h110 从同一未修复候选运行 240 步，产物保存在
`native_refinement_v9/pair48_10_h110_dp0p000_ap20_ru_m050/`。

| 指标 | v8 | v9 |
| --- | ---: | ---: |
| 缺接触部位帧数 | 1 | 0 |
| 最大穿透 mm | 0.634 | 0.691 |
| 存在穿透的帧数 | 45 | 49 |
| 第 29 帧最大关节变化 ° | 16.292 | 16.161 |

第 171 帧左手接触恢复；29、171、282、283 帧同一次查询的 CPU 与设备
主表面筛选结果一致。源关节二阶差分残差为 0.1006（v8 为 0.1082），
但速度残差为 0.6709（v8 为 0.6628），不能概括为连续性全面改善。
本轮解决缺接触，跳变改善很小，残余穿透略差；仍为 `passed=false`，
不能发布为可用训练增广。`comparison.json` 保存完整连续性及接触审计。
428 项测试、3 项子测试通过，仓库静态检查无错误。正式数据与 predictor 未改。

### 当前验收：动作的建立／保持／释放

`action_contact_acceptance_v1` 取代未采用的源接触阶段模板方案。只根据每个动作的
source/target surface 与 touchdown 意图检查建立、保持、释放；不比较源轨迹的
阶段数量、各阶段长度或精确触地帧。开始和结束都在同一表面的非活动末端属于保持，
因此不会因旧 `persistent_parts` 遗漏含噪支撑而完全不检查这段。

源示范仅标定统一时间容差：已声明保持的动作中，同一末端／表面两次实际接触间
的有界空缺；当前数据最大为 6 帧（50 Hz 下 0.12 秒）。不同表面的接触不能当作
空缺填补，裁剪缺口不跨越。稳定建立／释放沿用已有 3 帧证据要求，在动作完成
附近的容差窗口检查，不硬卡单个终点。保持检查允许动作交接边界的同一时间容差，
但要求中间持续支撑，不能把长期断触当噪声。全部原始 Newton 激活、分配、点对保留。

优化与验收使用同一动作要求，并抑制已被事件容差接受的边界偏移／短断点修正。
正式修复入口新增必填 `--event-reference-contacts`；`--audit-only` 仅重新查询并
验收，不更新姿态。旧阶段模板 schema 直接拒绝，没有备用入口。接触事件、全身
穿透分别报告；通过接触不代表滑动、跳变或动力学已合格，仍不自动发布训练数据。

`event_acceptance_v11/` 保存当前合同和复核报告。对已保存的完整、同姿态 Newton
点对重新验算（校验激活、分配、q 与文件哈希），不复用旧通过标志：

- 源示范：44 项动作接触检查全部通过。
- v8：43/44，通过建立左手接触；失败为动作 0004 右手保持，183–193 连续 11 帧断触。
- v9：41/44；失败为动作 0000 左脚保持和动作 0004 双手保持。
- 旧版“第 171 帧左手失败”不再作为单帧否决项；穿透和连续性数值没有改变。

这些是新验收结果，不是新一轮轨迹优化结果。旧 `event_acceptance_v10` 阶段匹配
报告仅为已弃用实验记录，不是当前验收基线。

### 冻结旧 207 的同条件基线

基线固定为归档 `temporal207_training_v2_ready` 的原始姿态，207 个 motion 文件
逐一核对内容哈希。`baseline207_comparison/baseline_lock.json` 记录完整清单；
这是比较基线，不是重新声明全部旧数据已通过物理验收。

首个对照为完全同名 h110：`pair48_10_h110_dp0p000_ap20_ru_m050`。
旧轨迹在与 v8/v9 相同的 terrain、canonical robot、Newton model fingerprint
中重新查询。`protocol.json` 冻结相同动作合同及验收代码哈希；全部结果使用当前
同一验收重新计算，不比较不同版本报告中的旧通过标志，也不修改原姿态。

| 指标 | 旧 207 | v8 | v9 |
| --- | ---: | ---: | ---: |
| 动作接触检查通过 | 43/44 | 43/44 | 41/44 |
| 最大穿透 mm | 3.265 | 0.634 | 0.691 |
| 最大单帧关节变化 ° | 11.579 | 16.292 | 16.161 |
| 第 29 帧右髋 yaw 变化 ° | 0.806 | 16.292 | 16.161 |
| 第 0→1 帧 root 位移 mm | 52.209 | 6.181 | 13.170 |

新版减少最大穿透及开头 root 跳动，但新增严重关节跳变；v9 还减少了通过的
接触要求。新生成器未经 refinement 的候选在第 29 帧已跳变 22.384°，所以退化
起于生成阶段，后续修补仅部分减小了它。不能以局部改善认定整条轨迹更好。

本轮决策：v8、v9 不晋级。实验修复仍只由独立脚本调用，不接入正式生成或替换
训练 manifest。后续只针对旧基线可复现的缺陷做单项修复；固定同一比较协议，
出现新增跳变或支撑退化的候选不采用。此结论只覆盖本条同条件对照，不能推及
全部 207 条或动力学执行。完整证据及决策见 `baseline207_comparison/comparison.json`。

### 从旧基线直接修复的首轮结果

`baseline207_repair_v1/h110/` 从旧 207 原 h110 姿态直接运行 240 步，未经过
引入第 29 帧跳变的新生成器。场景、动作合同、验收代码与冻结协议一致，未改
通过条件。本轮没有再修改求解器代码。

| 指标 | 旧 207 | 旧基线修复 240 步 |
| --- | ---: | ---: |
| 动作接触检查通过 | 43/44 | 44/44 |
| 最大穿透 mm | 3.265 | 1.390 |
| 第 29 帧右髋 yaw 变化 ° | 0.806 | 0.689 |
| 第 0→1 帧 root 位移 mm | 52.209 | 25.909 |
| 最大单帧关节变化 °（均在第 891 帧） | 11.579 | 11.827 |
| 原始负距离帧数（诊断） | 13 | 69 |

右手保持事件修复，且未引入此前第 29 帧的大跳变；但最大关节步长略增，负距离
分布仍需检查，不能只用最大穿透下降宣称全面改善。`passed=false`、
`training_ready=false`，不替换原数据、不批量发布。`comparison.json` 保存与旧基线
的完整逐项比较，`motion.npz` 为本轮候选，原始旧 207 文件保持不变。

### Historical source-relative expansion (invalidated, 2026-09-28)

The old runner initialized from archived `temporal207_training_v2_ready` poses
and measured additional motion relative to the new source. That failed to inherit
the rebuilt source trajectory. This initialization path has been removed; the
archive index now supplies only edit IDs, never initial poses.

Support motion compares the same local material point at adjacent frames with
its source displacement, transformed by the authored surface rotation. Only the
tangential difference is penalized. The cumulative residual resets on an
endpoint/surface episode boundary, not a change of foot contact sample. This
preserves source rolling while exposing slow accumulated augmentation drift.
The source pose sequence is not edited. Historical labels are not reused as
current contact truth.

The old relative-motion acceptance could pass an already sliding candidate and
its inferred keep roles did not match the v5 phases. Those reports do not certify
support supervision. Current acceptance checks absolute material motion over
explicit v5 phases and uses the accepted h110 residual-depth allowance; it does
not expand that allowance to match a poor initializer. Neither metric changes
the native contact activation rule. Refinement retains its best audited iterate.

Historical batches live under `source_support_expansion*`; their reports cannot
be reused by the corrected objective. Missing terrain bindings are
created by the current Newton worker before refinement.
Full poses and cropped poses are retained (remove 472–699, retain 471), and the
crop contract forbids supervision across the seam. Cropped contact labels remain
explicitly pending fresh native relabeling; `training_ready` stays false.

### Concurrent expansion

`expand_source_preserving_augmentations.py --workers 3 --query-worlds 32`
uses three trajectory jobs, each with a 32-world native query worker. Scene
manifest/binding preparation and taskspace compilation are serialized to avoid
shared-cache races; optimization jobs overlap. Completed reports are reused
without recompilation. Each optimizer uses one CPU thread; the launcher limits
OMP/OpenBLAS/MKL threads to one. `status.json` lists all active jobs, and new
acceptance reports record wall-clock seconds (including preparation/waiting).
The historical run was `source_support_expansion_parallel_v4`, reusing v3 results.
Concurrency itself did not change acceptance thresholds or optimization losses.
Its support contract was subsequently invalidated as described below.

### Correction: inherit the explicit v5 support phases

The old expansion reports above do **not** certify support-preserving training
supervision. They reconstructed `keep` from endpoint surfaces and initialized
from old augmented poses. In particular, the source's first 0–103 action has no
persistent support role; interpreting its left foot as `keep` was incorrect.

The corrected runner requires `--support-phases` and verifies exact agreement
with the source event roles (18 keep phases and 15 establishment events here).
The contact contract is now `explicit_action_contact_acceptance_v2`: identical
endpoint surfaces cannot invent a keep or release role. The initializer is a
fresh authored IK edit of `source/motion.npz`; source hashes and edit provenance
are stored. Old augmented candidates cannot be reused under this contract.

Optimization additionally uses an absolute material-motion budget on source
contact samples for explicit keep phases. Acceptance independently measures
same-material tangential motion from fresh Newton witnesses, grouped per endpoint
and frame, then accumulated within each declared phase. The 6 cm path budget is
an augmentation motion criterion, not a contact threshold and not the old
endpoint-only 6 cm statistic. Native geometry witnesses can measure motion during
short activation holes without changing the event-level contact evidence. Missing
motion measurements are reported rather than credited as zero motion.

The aggregate source has zero loss under the new motion-budget term. The initial
rigid-transform-only diagnostic did not adapt sufficiently to edited terrain;
The complete source IK initializer was first tested in
`explicit_v5_source_pilot_v3`. Its three candidates passed contact events, but
none passed the combined geometry/support acceptance. These remain diagnostics.
`explicit_v5_source_pilot_v4` additionally normalizes the phase-motion violation
by the same 1 mm optimization scale used for geometric residuals (not by the
6 cm motion budget), and selects lower penetration among otherwise equally
passing candidates. This is objective version `explicit_phase_source_recovery_v3`;
older objective reports cannot be silently reused. Initializer source/plan hashes
are checked before refinement. The editor's object-typed joint names are converted
to Unicode before refinement so that its inputs require no pickle loading.
The subsequent smaller-step diagnostic exposed another mismatch: source material
samples can cease to represent the edited trajectory's contact location. Objective
`explicit_phase_source_recovery_v4` refreshes these samples from each native audit,
using exactly the same material-motion calculation for optimization and acceptance.
Missing native groups retain source samples only as guidance, never as validation.
Every complete phase is checked for numerical agreement of both metrics.
Cached results must also match hashes of the source, native labels, event file,
support phases and edit plan, as well as optimization steps and learning rate;
matching an old motion ID alone is insufficient.

Validation completed in `explicit_v5_source_pilot_v6` (three concurrent native
32-world queries, 1200 optimization steps, learning rate 2e-5). All exported
candidates passed 33 contact-event checks and 18 explicit support-motion phases.
The maximum discrepancy between optimization and audit motion metrics was below
4e-9 m. The selected iterate is re-queried before export.

| Terrain height | Maximum phase path (cm) | Maximum penetration (mm) | Reference accepted |
| --- | ---: | ---: | --- |
| 90 cm | 5.923 | 0.518 | yes |
| 100 cm | 5.482 | 2.608 | no: residual geometry |
| 110 cm | 5.984 | 4.221 | no: residual geometry |

This validates the support inheritance/measurement correction, not universal
edit feasibility. No 207-case expansion was launched from these pilots. The
accepted reference still requires fresh cropped contact labels and downstream
execution validation; no training manifest was replaced. Joint-step acceptance
only means no increase relative to the allowed reference, not dynamics safety.
The previous 207 trajectories remain historical diagnostic artifacts, not newly
certified predictor supervision. No training manifest has been replaced.

### Actual activation interval experiment (2026-09-29)

The regional objective and both missing-region geometry proxies now use the
actual pair/configured `includemargin` as their upper approach boundary. This
matches the existing non-regional execution interval. Activated contacts with
positive gaps inside this boundary have no extra attraction toward 1 mm.
Full-body penetration and explicit release penalties remain unchanged. Native
activation/allocation are still mandatory; zero loss at the exact boundary does
not certify contact. Frozen witness gradients remain active if FK exits the band.

`activation_interval_pilot_v1_20260929` repeats the same three v5 IK initializers,
1200 steps and 2e-5 learning rate against `explicit_v5_source_pilot_v6`. Only the
contact approach upper bound changed; the support budget and regularizers did
not change. Reports use `explicit_phase_source_recovery_v5` and
`native_activation_upper_gap_v1`, preventing reuse of the old 1 mm objective.

| Height | Last-phase left-foot material path, old → new (cm) | Max penetration, old → new (mm) |
| --- | ---: | ---: |
| 90 cm | 5.026 → 4.168 | 0.518 → 0.000 |
| 100 cm | 4.847 → 4.094 | 2.608 → 0.009 |
| 110 cm | 5.984 → 4.138 | 4.221 → 0.030 |

The source left-foot phase path is 4.124 cm. All three selected candidates pass
33 native contact-event checks, 18 support-motion phases and the existing
reference checks. Maximum phase paths are 5.501, 5.394 and 5.726 cm respectively.
Joint velocity/acceleration residuals improve in all three cases. Maximum joint
steps rise by about 0.056° in the 90/100 cm cases and decrease in the 110 cm case;
the latter still has an 18.746° step, so this result does not resolve all
trajectory-continuity concerns. No training manifest was replaced or full 207
expansion launched. `comparison.json` records the complete per-case comparison.

### Production replacement

The actual-margin interval is the sole regional implementation, rather than an
optional pilot mode. Both `scripts/refine_motion_contacts.py` and
`scripts/expand_source_preserving_augmentations.py` take their defaults from
`RefinementConfig`: 1200 steps and learning rate 2e-5. The objective schema is
shared by both entry points. Reuse requires the current interval schema on the
audit and acceptance report, as well as identical source/plan hashes and optimizer
parameters; old 1 mm results cannot be resumed as current candidates.

The full expansion is stored separately as `activation_interval_207_20260929`,
reusing only the three verified current-interval pilots. Fresh initialization
comes from the event-aligned v5 source. Cropped native contact labels and downstream
validation are still required before publication as training data. Existing
predictor data and training entry points are not changed by this replacement.
# Predictor 参考路径验收

`scripts/prepare_predictor_event_paths.py` 从源事件与当前 Newton 标签生成
整段参考路径证书及接受/拒绝事件表。明确 keep 约束必须通过；未声明 keep
的源实际接触时段只提供候选支撑，允许多个区域在事件内部接替覆盖。
材料点、脚尖/脚跟切换不会另起事件；拒绝段和裁剪间隙不会被跨接。

`generator.training_data.prepare` 读取新 manifest 的 `support_path_acceptance`，
核验证书、motion/contact/事件内容和缓存帧边界。旧 manifest 会明确报告
`legacy_unchecked`。这个证书验证示范整段，不验证网络尚未输出的中间轨迹。

当前正式切分位于 `versions/predictor_event_paths_20260930_final`：14 个接受
事件，917–931 完成/调整段排除。`training_ready=false`，没有替换训练缓存。
源相对预算不能证明源质量，0–103 的候选左脚几何 pivot 路程仍为 12.57 cm；
候选没有同次求解载荷数据，承重滑移依旧未知。

### Current support evidence contract (2026-09-30)

The preceding absolute keep-phase budget descriptions document historical v6
experiments. Current v7 preserves original phase motion and penalizes added
geometric motion; contact keep intent does not imply stationary measured support.
Collection, source load observations, edit invalidation, predictor supervision
and endpoint diagnostics share [the support evidence contract](../../../docs/support-semantics.md).
Edited candidates require actual execution to establish loads. Neither a geometric
pivot budget nor endpoint retention certifies loaded patch slip. Existing corpora
and training manifests have not been automatically migrated.
