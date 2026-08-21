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
4. 保持 `src/jnotes2hinote/converter_v1_0_0.py` 冻结。新的转换行为应放入新的版本化核心模块。

## 开发

```bash
python -m venv .venv
# Windows：.venv\\Scripts\\activate
# macOS/Linux：source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
