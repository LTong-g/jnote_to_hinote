# Jnotes2Hinote

将 **云记 / Jideos Jnotes 的 `.Jnotes`** 笔记转换为 **华为笔记的 `.hinote`**，并在已逆向确认的格式范围内尽量保留华为原生、可框选、可擦除的可编辑笔迹。

> **已实机验证版本：云记 3.2.3.2 → 华为笔记 15.0.14.295。** 其他版本目前均视为未验证。

## v1.1.0 已支持

- 多页笔记
- 华为原生 PENCILENGINE 可编辑笔迹
- 笔迹坐标与逐点 pressure
- 华为笔记 15.0.14.295 使用的 BGR 浮点颜色
- 测试笔记中涉及的圆珠笔、钢笔、HB 铅笔、荧光笔
- 已通过实机标定的荧光笔宽度与透明度
- 已确认的 Jnotes type 6 / type 7 几何图形
- 半透明 type 6 / subtype 12“荧光笔变曲线”对象迁移为华为原生荧光笔
- 图片与图片型贴纸
- 基本文本框
- 封面图片
- 华为原生纸张模板

## v1.1.0 不再需要华为参考笔记

从 v1.1.0 开始，转换器直接由代码生成经实机验证的华为笔记 15.0.14.295 PENCILENGINE 文件头、样式记录、点记录、笔迹链和已支持的几何结构。

因此不再需要自己制作：

- `reference.hinote`
- `shape-reference.hinote`

v1.0.0 的 reference 方案仍原样保存在 `src/jnotes2hinote/converter_v1_0_0.py`，不修改历史核心。

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

- **纸胶带：** 尚未确认华为原生等价对象；v1.1.0 会跳过，不会静默栅格化。
- **音频：** 已理解双方相关存储结构，但 v1.1.0 尚未启用音频转换。
- **文本排版：** 文本保持可编辑，但字体度量、换行和行距可能不同。
- **普通笔宽：** 荧光笔已经实机标定；普通笔族之间的视觉等宽尚未做完整标定。
- **几何宽度：** 当前使用 v0.5.1 实机验证过的离散宽度规则，而不是未经验证的连续换算公式。
- **版本兼容：** 当前仅实机验证云记 3.2.3.2 → 华为笔记 15.0.14.295。

转换重要笔记前建议阅读 [docs/limitations.md](docs/limitations.md)，并保留原始文件备份。

## 格式研究文档

- [云记格式](docs/format-jnotes.md)
- [Huawei `.hinote` / PENCILENGINE 格式](docs/format-hinote.md)
- [映射规则](docs/mapping.md)
- [兼容性](docs/compatibility.md)
- [逆向过程](docs/reverse-engineering.md)
- [v1.0.0 验证摘要](docs/validation-v1.0.0.md)
- [v1.1.0 验证摘要](docs/validation-v1.1.0.md)

## 开发

```bash
pip install -e ".[dev]"
pytest
```

版本核心分别保留：

```text
src/jnotes2hinote/converter_v1_0_0.py  # 冻结的 reference 方案
src/jnotes2hinote/converter_v1_1_0.py  # 当前无 reference 方案
```

## 许可证

MIT，见 [LICENSE](LICENSE)。

## 免责声明

本项目是独立、非官方的文件互操作与逆向研究项目，与 Jideos 或 Huawei 无隶属、授权或赞助关系。
