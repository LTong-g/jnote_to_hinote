# 版本化转换核心

## 冻结的 v1.0.0 核心

旧版基于参考文件、经过设备验证的转换核心是：

`src/jnotes2hinote/converter_v1_0_0.py`

SHA-256：

`ee551f236053b141f4f6d66425367cdf268a87f6b777c885b2a1c6f2553d7287`

该模块在 v1.0.0 发布后保持不变，`CORE_SHA256.txt` 持续记录此哈希。

## 历史 v1.1.0 核心

`src/jnotes2hinote/converter_v1_1_0.py`

该核心引入了自包含的华为 PENCILENGINE 生成逻辑，并作为历史 v1.1.0 实现保留。

## 当前 v1.1.1 核心

`src/jnotes2hinote/converter_v1_1_1.py`

v1.1.1 保留自包含架构，并修正普通不透明几何图形的宽度映射。后续行为变化应新增版本化核心，不要重写历史核心。
