# Generator

Predictor 和 Infiller 的独立实现，以及数据、训练、生成 rollout 工具。
WBT policy、环境、仿真训练与执行仍位于 `src/holosoma/`。

2026-10-10：当前统一基线为
[`predictor.v1_latest.20261010`](../../baselines/predictor_v1_latest_20261010/README.md)。
训练入口使用 `full1000_position_predictor_v1`，默认共享观测
编码器梯度，保留原 root＋部位平均读出。新的形状—目标表面统一区间 loss 默认启用；
网络架构版本与区间 loss 语义版本是独立的。
训练从零初始化，采用100轮预热＋1000轮反馈日程，使用
loaded-material207_joint_v12 数据，keep材料区域保持权重为1。
基线checkpoint固定为`v1_shared_interval_scratch1100_20261009/step_1000.pt`，
原始运行位于`runtime/current/models/generator/`。该运行记录到1002轮、最后保存1000轮，
没有1100轮完成报告；登记为后续比较起点，不声称全程完成或物理执行通过。
新训练输出默认`runtime/current/models/generator/v1_shared_interval_new_run`，
每次运行应显式传入未使用的`--output`目录。checkpoint不作为scratch初始化权重。
v2 整体改版未被采用为基线；代码保留作显式实验，通过
`--architecture full1000_position_predictor_v2 --no-execution-observation-gradients` 选择。
架构记录见 [structured-predictor](docs/structured-predictor.md)。
正式递推入口为 `python -m generator.evaluate_position_rollout`；旧tmp启动器只转发此实现。
完整checkpoint仅能由评估或显式只读梯度审计加载，不能作为训练初始化。

旧scratch配方、source550及control500已[封存](../../baselines/README.md)，
不再作为当前训练默认值。保存的历史配置、原始数据、权重和源代码快照用于对照；
历史v1的编码器、token与checkpoint不能直接当作v2。
原始启动记录和925 checkpoint的30次递推保留用于同条件比较，不重写历史架构。
该递推来自训练集motion4，前15次有示范，第6次首次失败，后15次继续自主预测；
不能作为留出泛化或实际承重、无滑移结论。

```python
from generator.structured_position_predictor import StructuredPositionPredictor
from generator.neural_infiller import G1ConstrainedKeypointInfiller, G1ContactAwareQInfiller
from generator.unified_interaction import InteractionQInfiller
```

从仓库根目录 `source scripts/source_somaforge.sh` 后使用新入口，例如
`python -m generator.train_q_infiller --help`。

依赖方向为 `generator → contact_solver → somaforge_core`；共享 FK、预测结果结构、
高度图坐标约定在 core。网络中的几何损失调用 contact_solver。
旧 `climb00_pipeline` 模块是同一实现模块的兼容别名，旧导入和模块 CLI 保留；
历史兼容模型保留原参数名与forward；新的v2使用显式版本校验。旧错误机器人资产产物仍无效。
回归测试按实现归入 `generator/tests`、`contact_solver/tests` 和
`somaforge_core/tests`；`test_package_boundaries.py` 单独验证历史兼容入口。

普通 predictor batch 的可选约束训练入口为
`python -m generator.train_full1000_position --constraint-training ...`。
使用同一 predictor、数据划分和 Newton 查询，每个 batch 一次受约束 AdamW 更新。
默认分支不变；当前先支持固定接触意图的 reference batch，未接入递推 rollout。
使用说明和边界见 [minibatch-training](../contact_solver/docs/minibatch-training.md)。

大批量持续池（`train_full1000_position --parallel-rollouts --gpu-pipeline`）采用验收后提交：
A → B′ 通过现有任务、几何、端点接触保持及已启用的进度验证，才将 B′ 放回输入并推进目标。
失败输出仍参与本轮 loss/backprop，但下一轮保留本次预测前的完整 A 和目标 B；
即使 A 来自之前成功的递推，窗口内也原样保留。
严重穿透、无有效接触等失败同样回退，不把失败 B′ 用于 B′ → B 训练。

当前训练默认启用 `continuous_demonstration_training`：反馈阶段每个统计轮次仍遍历一次
原始训练示范，按示范接触条件训练同一个网络，使用现有完整损失。
持续池的自主条件调度和失败回退保持原样；示范分支不向池提交姿态，
也不把示范外状态配上旧示范目标。日志分别记录 `demonstration_predictions`
和持续池统计，因此与旧结果比较时需同时报告总预测数、更新数和训练耗时。
教师条件同时覆盖角色、部位、可见位置及新鲜 Newton 端点区域；区域分类 logits
仍由网络独立预测和监督。缺失真实区域证据明确标记为未知，不能暗用预测区域冒充教师条件。
历史配方的纯持续池阶段可用 `--no-continuous-demonstration-training` 对照，
该开关不恢复遗漏区域的旧教师语义；既有 checkpoint 的自主推理参数和接口不变。

年龄与前进历史只累计成功提交；连续失败累计 retries/rollbacks。
每槽每次预测均累计 attempts，成功、失败都计数，跨统计轮次保留。
达到 `parallel_episode_limit`（默认64次预测更新）后从训练集重新采样；
完整观测、目标索引一起替换，清空 attempts、重试、成功深度及前进历史，恢复示范监督。
第64次输出仍参与本轮反传，下次输入才切换；成功不会延长窗口。
日志中的 *_rejections 表示候选失败；periodic_resamples 单独统计周期刷新，
resets/timeout_resets 包含该刷新，rollbacks 只统计未到刷新边界的失败保留。
状态 schema 为 bounded_attempt_rollout_v5，保存 attempts、resample_interval 和 allow_post_demo。
完成最后示范目标后仍关闭示范监督并继续自主递推；后继不得进入验证集。
使用 `--no-parallel-allow-post-demo` 时，完成最后示范目标后立即重新采样，
不产生示范外输入；最后目标未通过验收时仍保留A，直至成功或达到64次刷新。
terminal_resets 与 periodic_resamples 分开计数，同时到期只记一次末尾重置。
`parallel_retry_limit` 仍为兼容参数，不单独截断；自主状态同样受64次窗口限制。
示范外默认开启，提交仅要求自身计划的实际接触、区域、位置、保持角色一致性和安全；
末帧的示范接触、位置和姿态不再作为目标。示范监督loss归零，几何、位置与保持loss继续反传。
自主keep使用训练集部位统计容许量；不沿用末帧动作的容许量。
`autonomous_inputs`记录实际用于优化的示范外输入数，区别于提交后处于自主状态的槽数。
此修改不解除 `--constraint-training` 暂只支持 reference batch 的限制。

`--acceptance-penetration-m`（当前默认0.005m）仅控制递推提交和任务验收。
原优化默认限值、Newton margin/gap、接触激活和全部loss不随它改变。
checkpoint分别保存运行验收与优化限值；递推评估继承checkpoint设置，显式覆盖可用于同容差对比。
缺少该设置的历史checkpoint保留原1mm验收。示范外评估同样检查自身接触、区域、位置和安全，
无未来示范时`task_acceptance=None`，不能将未知当作通过。

支撑运动统一使用 `source_loaded_tangent_material_motion_v1`：按原始实际受力点的
局部坐标跟踪相邻姿态的同一材料点，投影到所在表面的切平面，以原始载荷做RMS汇总，
再累计阶段运动。允许转动、足跟/前掌切换和卸载；不取单个最小位移点。
6 cm仅是该几何参考累计运动的预算，不是Newton接触阈值，也不证明新执行无滑移。
完整轨迹和独立原始载荷观测具备时，共用 `somaforge_core.loaded_material_motion`。
裁剪/软拼接后必须按新姿态和帧映射重算；跨删除区间的接缝缺少相邻原始求解证据，标为未知。

当前模型仅输出下一事件端点，缺少完整执行轨迹和逐帧实际载荷，
支撑运动报告为unknown，不施加路径运动loss或gate。
原 `predicted_contact_retention_weight`、`require_endpoint_contact_retention`、
`endpoint_contact_tolerance_m`配置已移除，旧首尾6 cm规则不能再启用。
实际Newton接触、穿透、关节限位、端点布局和保持意图一致性检查仍生效。
有完整执行观测时，可通过 `require_observed_support=True`严格要求实际支撑验证。

端点位置loss与现有验收共用`2 * HEIGHTMAP_RESOLUTION_M`的XY RMS容差（当前4 cm）：
先对目标部位的平方误差求均值，再惩罚超出容差的RMS部分；进入范围后位置loss与
梯度均为零，不继续追精确点。GPU与普通路径共用此目标，原RMS诊断仍保留。
缺失点对、接触激活、部位区域和安全检查独立进行，零位置loss不表示任务通过。

统一避碰项从当前初始化的 Newton 场景读取完整碰撞实体及实际碰撞过滤，
对所有允许的地形／自碰撞形状对计算有符号 GJK/EPA 距离，使用其材料点经 FK
反传。地形 mesh 的独立封闭组件分别处理，完整包围也不会因缺少三角面候选而漏检。
不支持的非封闭／非凸实体明确报错。物理区间、权重和接触激活判定不变；
穿透验收及严重嵌入重置使用实际 Newton 深度与完整实体深度的最大值，原容差不变。
训练与编辑共用这条避碰路径，checkpoint 保存几何语义和场景 fingerprint。

统一接触训练使用固定的真实接触材料点计算缺失区域的趋近距离：启动时复用训练集
示范端点的实际Newton点对，将已激活、已分配、主向上表面上的机器人材料点绑定到
各自link局部坐标。验证集不进入材料点库；点库不提供目标姿态，也不是网络输入。
材料点库保存在`contact_material_skin.pt`，未观测区域的资产趋近代理显式报为未知。
它只是loss几何，接触实现仍由每次预测上的实际Newton点对判断。
所选材料点的两侧区间残差在碰撞候选出现后仍保留，深嵌入不会因为候选存在而关闭
向目标表面的恢复方向。有限表面按真实margin的边缘邻域计算距离，不要求投影
严格落在矩形内；示范中距顶面边缘仍在margin内的接触不会被额外处罚。

接触区间、完整实体避碰和keep材料运动统一使用`log1p(r²)`，各自原有的物理容许量、
残差尺度、汇总与权重保持原样。此前C1任务退出场在浅侧穿透中会放大错误方向，已
从训练目标移除。这里反传的是标量loss的真实FK导数，不求QP或注入自定义修正梯度。
这些改动不保证每次参数更新同时改善所有约束；完整学习和递推效果须通过新训练验证。
原生点对的不可用法线保留审计及验收拒绝，但不再屏蔽整条姿态的所有损失。
不可用的原生距离行不参与距离梯度；已验证完整实体距离和其他正常FK损失继续反传。
完整实体几何本身未知时仍明确报错，不能用零loss或替代接触标签掩盖。

训练入口可用`--keep-patch-weight 1.0`：仅对网络的keep意图增加材料区域几何保持
正则。当前材料点取自实际Newton的已分配有效接触，FK保持材料身份；在整个区域中
寻找最小切向运动，允许绕区域内支点转动。对应示范动作提供运动容许量，其他预测
keep使用训练集部位中位数，未观测部位标为未知。标定保存在`keep_patch_calibration.pt`；
日志记录loss、运动、超额及缺失项。最新用户指定基线的默认权重为1；
以下200轮实验是历史诊断，不能作为当前整段训练效果的结论。
这是端点意图正则，不提供实际载荷或累计滑移证据，也不改变接触真值和递推验收。

2026-10-05同种子、同数据、同日程的200轮实验（100示范＋100反馈）中，h100连续
30步的前15步保持部位材料区域平均运动由6.22cm降到2.98cm，30步最大穿透由
75.9mm降到25.8mm；但验证端点通过率由40.0%降到23.6%，递推通过前缀由1步降到0步。
这轮训练仍处于完整teacher计划阶段，后15步无示范目标。冻结真实训练池诊断中，
69个可比较样本有34个保持／接触实现姿态梯度反向，不能把减少运动等同于约束协调成功。
完整结果为`runtime/current/models/generator/keep_patch_scratch200_20261005/experiment_result.json`。
示范载荷只作reference，递推输出不能继承；缺少观测保留known mask和NaN。

全链路接触、承重、滑移与保持意图的统一口径见
[支撑证据](../../docs/support-semantics.md)。网络结构和示范数据不会因附加观测自动改变。
