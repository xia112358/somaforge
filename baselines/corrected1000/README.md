# corrected1000 baseline

当前基线：`tmp/full1000_regionfix5000_20260925/main1000/step_1000.pt`。
目录名中的 5000 是历史命名，本次主训练为 1000 轮。
初始化：Stage-A → execution adapter 20 → warmup 10 → main 1000。
开启 region_plan、unified_contact、event_roles，使用持续并行 rollout；无失败重试。

主代码在仓库 `packages/climb00_pipeline` 和 `packages/somaforge_core`。
本目录 `tmp/` 保存训练、评估、查看器入口及导入依赖的原样快照，另保存实际运行配置、训练进度与新旧 motion8 长递推记录。sha256.json 校验快照及本地基线权重。

## 恢复入口

在项目根目录，确保 tmp 已存在且可写，然后执行：

```bash
cp -a baselines/corrected1000/tmp/. tmp/
```

运行环境见 `scripts/source_isaaclab3_newton_setup.sh` 和 `configs/newton-main-requirements.txt`。
训练实际命令保存在 `tmp/full1000_regionfix5000_20260925/run.sh`，仅作为运行记录；不要无意重跑覆盖原目录。
数据、Stage-A 权重、Newton 查询服务所需的 policy checkpoint、训练后权重及本地 IsaacLab/Newton 运行环境不在此 Git 快照内，运行前须按配置提供并核对路径。复制入口不等于已具备全部训练依赖。

## 验证与限制

本次同步前 47 项定向测试通过，覆盖预测器、区域、空间匹配、并行池、训练变体和主表面接触筛选。
原始长递推仍有已知问题：当前 motion8 在参考事件链之后额外 10 步中，5 步六部位无有效接触。此版本是可追踪的实验基线，不代表长递推已解决。
两版参考链分别为 19 和 17 段，终点不对应同一示范物理时刻；不能将这一对照直接当成训练改动的因果证明。
