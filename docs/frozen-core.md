# 版本化转换核心

## 冻结的 v1.0.0 核心

旧版基于参考文件、经过设备验证的转换核心是：

`src/jnotes2hinote/converter_v1_0_0.py`

SHA-256：

`5e8422ac8f6c05d6ced734e9c6a50095ff56719cf32de3237b41e21d0d98aee6`

该文件作为当前公开的 v1.0.0 历史核心，不再进行源码整理或行为调整。后续转换行为应放入新的版本化核心；`CORE_SHA256.txt` 记录其当前哈希。

## 历史 v1.1.0 核心

`src/jnotes2hinote/converter_v1_1_0.py`

该核心引入了自包含的华为 PENCILENGINE 生成逻辑，并作为历史 v1.1.0 实现保留。

## 当前 v1.1.1 核心

`src/jnotes2hinote/converter_v1_1_1.py`

v1.1.1 保留自包含架构，并修正普通不透明几何图形的宽度映射。后续行为变化应新增版本化核心，不要重写历史核心。
