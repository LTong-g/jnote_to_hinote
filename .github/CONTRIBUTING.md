# 参与贡献

欢迎贡献，尤其欢迎可复现的格式发现和兼容性报告。

## 格式研究规则

1. 不要提交私人笔记、账户数据或专有应用资产。
2. 优先使用专门为测试制作的最小化合成样本。
3. 新的二进制字段结论应说明源应用与目标应用版本、受控实验、字节偏移和设备验证状态。
4. 当前实现只维护在 converter.py、reader.py 和 thumbnail.py；历史版本由 Git 标签保存。
5. 改变转换行为时必须增加针对当前行为的回归测试，并更新 CHANGELOG.md。

## 开发

~~~bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
~~~

Windows 打包路径支持 PyInstaller 5.13 及以上版本。运行
scripts/clean_build.ps1 -WhatIf 可预览构建目录清理；只有显式增加
-IncludeDist 才会删除 dist。
