# Generator

Predictor 和 Infiller 的独立实现，以及数据、训练、生成 rollout 工具。
WBT policy、环境、仿真训练与执行仍位于 `src/holosoma/`。

```python
from generator.full1000_position_predictor import Full1000PositionPredictor
from generator.neural_infiller import G1ConstrainedKeypointInfiller, G1ContactAwareQInfiller
from generator.unified_interaction import InteractionQInfiller
```

从仓库根目录 `source scripts/source_somaforge.sh` 后使用新入口，例如
`python -m generator.train_q_infiller --help`。

依赖方向为 `generator → contact_solver → somaforge_core`；共享 FK、预测结果结构、
高度图坐标约定在 core。网络中的几何损失调用 contact_solver。
旧 `climb00_pipeline` 模块是同一实现模块的兼容别名，旧导入和模块 CLI 保留；
本次搬迁没有改变网络参数名或 forward 算法，也不赋予旧错误机器人资产产物有效性。
现有回归测试保留在 `packages/climb00_pipeline/tests/`，同时验证兼容入口。
