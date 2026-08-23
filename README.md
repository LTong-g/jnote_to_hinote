# Jnotes2Hinote

将 **云记 / Jideos Jnotes 的 `.Jnotes`** 笔记转换为 **华为笔记 / Huawei Notes 的 `.hinote`**，并在已逆向确认的格式范围内尽量保留华为原生可编辑笔迹。

> **已实机验证的版本组合：云记 3.2.3.2 → 华为笔记 15.0.14.295。** 其他版本目前均视为未验证。

英文文档：[README.en.md](README.en.md)

## v1.1.1 已支持

- 多页笔记
- 华为原生 PENCILENGINE 可编辑笔迹
- 笔迹坐标与逐点压力值
- 华为笔记 15.0.14.295 使用的 BGR 浮点颜色
- 测试笔记中涉及的圆珠笔、钢笔、HB 铅笔、荧光笔
- 已通过实机标定的荧光笔宽度与透明度
- 已确认的 Jnotes type 6 / type 7 几何图形
- 半透明 type 6 / subtype 12“荧光笔生成的曲线”迁移为华为原生荧光笔
- 图片与图片型贴纸
- 基本文本框
- 封面图片
- 华为原生纸张模板

## v1.1.1 不需要华为参考笔记

转换器直接由代码生成经验证的 Huawei Notes 15.0.14.295 PENCILENGINE 文件头、样式记录、节点记录、笔迹链和已支持的几何结构，因此不再需要自行制作：

- `reference.hinote`
- `shape-reference.hinote`

v1.0.0 的参考文件方案仍原样保存在 `src/jnotes2hinote/converter_v1_0_0.py`，历史核心不会被修改。

## 安装

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
pip install -e .
```

macOS/Linux：

```bash
source .venv/bin/activate
pip install -e .
```

## 使用

```bash
jnotes2hinote input.Jnotes output.hinote
```

或者：

```bash
python -m jnotes2hinote input.Jnotes output.hinote
```

输出 JSON 转换报告：

```bash
jnotes2hinote input.Jnotes output.hinote --report conversion-report.json
```

测试时只转换前 5 页：

```bash
jnotes2hinote input.Jnotes test.hinote --pages 5
```

## 已知限制

- **纸胶带：** 尚未确认华为原生等价对象；v1.1.1 会跳过，不会静默栅格化。
- **音频：** 已理解双方相关存储结构，但 v1.1.1 尚未启用音频转换。
- **文本排版：** 文本保持可编辑，但字体度量、换行和行距可能不同。
- **普通笔宽：** 荧光笔已经实机标定；普通笔族之间的视觉等宽尚未完成完整标定。
- **几何宽度：** 普通不透明 type 6/type 7 与普通笔迹采用相同的直接映射：Jnotes `d` 原值写入 Huawei `style+84`，包括小数宽度。
- **版本兼容：** 当前仅实机验证云记 3.2.3.2 → 华为笔记 15.0.14.295。

转换重要笔记前请阅读 [docs/limitations.md](docs/limitations.md)，并保留原始文件备份。

## 格式研究文档

- [云记格式](docs/format-jnotes.md)
- [Huawei `.hinote` / PENCILENGINE 格式](docs/format-hinote.md)
- [映射规则](docs/mapping.md)
- [兼容性](docs/compatibility.md)
- [逆向过程](docs/reverse-engineering.md)
- [v1.0.0 验证摘要](docs/validation-v1.0.0.md)
- [v1.1.0 验证摘要](docs/validation-v1.1.0.md)
- [v1.1.1 修复验证摘要](docs/validation-v1.1.1.md)

## 安全与备份

导入转换后的文件前，请始终保留原始 `.Jnotes` 文件，并导出或备份华为笔记。这个项目是基于逆向工程的非官方互操作工具，不是 Huawei 或 Jideos 的产品。

## 开发

```bash
pip install -e ".[dev]"
pytest
```

不同版本的转换核心分别保留：

```text
src/jnotes2hinote/converter_v1_0_0.py  # 冻结的旧版参考文件核心
src/jnotes2hinote/converter_v1_1_0.py  # 历史 v1.1.0 自包含核心
src/jnotes2hinote/converter_v1_1_1.py  # 当前自包含核心
```

后续行为变化应新增版本化核心，不要重写历史核心。

## 许可证

MIT，见 [LICENSE](LICENSE)。

## 免责声明

本项目独立且非官方，与 Jideos 或 Huawei 没有隶属、授权或赞助关系。项目中出现的产品和公司名称仅用于说明文件格式互操作关系。
