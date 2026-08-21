# 版本化转换核心

## 冻结的 v1.0.0 核心

旧版基于参考文件、经过设备验证的转换核心是：

`src/jnotes2hinote/converter_v1_0_0.py`

SHA-256：

`ee551f236053b141f4f6d66425367cdf268a87f6b777c885b2a1c6f2553d7287`

该模块在 v1.0.0 发布后保持不变，`CORE_SHA256.txt` 持续记录此哈希。

## 当前 v1.1.0 核心

`src/jnotes2hinote/converter_v1_1_0.py`

该核心直接生成经过验证的 PENCILENGINE 结构，移除了对华为参考笔记的依赖。未来行为变更应引入新的版本化核心，而不是重写历史版本核心。
