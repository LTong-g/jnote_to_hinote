# 参与贡献

欢迎贡献，尤其欢迎可复现的格式发现和兼容性报告。

## 格式研究规则

1. 不要提交私人笔记、个人导出的笔记、账户数据或专有应用资产。
2. 优先使用专门为测试制作的最小化合成样本。
3. 对新的二进制字段结论，请同时提供：
   - 源应用和目标应用版本；
   - 受控实验；
   - 字节偏移与观测值；
   - 结果是否经过设备验证。
4. 不要修改历史版本的转换行为；当前公开的历史核心也不再做源码整理。新的转换行为应放入新的版本化核心模块。

## 开发

```bash
python -m venv .venv
# Windows：.venv\\Scripts\\activate
# macOS/Linux：source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

Windows 打包路径支持 PyInstaller 5.13 及以上版本。运行 `scripts/clean_build.ps1 -WhatIf` 可以预览构建目录清理；只有显式增加 `-IncludeDist` 才会删除 `dist`。
