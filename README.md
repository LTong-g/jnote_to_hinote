# Jnotes2Hinote

把 **云记 / Jideos Jnotes 的 `.Jnotes` 笔记**转换为**华为笔记的 `.hinote` 文件**，并在支持范围内尽量保留可编辑的笔迹、图片和文本。

> **目前已实机验证的版本组合：云记 3.2.3.2 → 华为笔记 15.0.14.295。** 其他版本尚未验证，转换结果可能不同。

英文文档：[README.en.md](README.en.md)

## 适合什么场景

如果你有云记导出的 `.Jnotes` 文件，并希望在华为笔记中继续查看和编辑，可以使用本项目生成 `.hinote` 文件，再将它导入华为笔记。

## 支持转换的内容

- 多页笔记
- 可编辑的手写笔迹，包括常用笔型、颜色和逐点压力
- 部分线条、曲线、矩形和圆形等图形
- 图片、图片型贴纸和封面
- 基本文本框
- 常见的空白、横线、点阵和方格纸张

转换结果以华为笔记文件的形式保存，不会把整页内容简单合并为一张图片。

## 安装

需要 Python 3.10 或更高版本。请在项目根目录打开终端。

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

macOS/Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 转换笔记

最简单的用法：

```bash
jnotes2hinote input.Jnotes output.hinote
```

也可以使用 Python 模块方式运行：

```bash
python -m jnotes2hinote input.Jnotes output.hinote
```

转换时输出 JSON 报告：

```bash
jnotes2hinote input.Jnotes output.hinote --report conversion-report.json
```

测试时只转换前 5 页：

```bash
jnotes2hinote input.Jnotes test.hinote --pages 5
```

转换器只读取输入文件，并写入你指定的输出路径。请保留原始 `.Jnotes` 文件，并不要把输入和输出设为同一个路径。

## 导入华为笔记

转换完成后，将生成的 `.hinote` 文件导入华为笔记，然后检查重要页面、图片、文本和笔迹是否符合预期。正式转换整本笔记前，建议先使用 `--pages` 转换少量页面进行确认。

## 使用前请注意

- 当前只有云记 3.2.3.2 → 华为笔记 15.0.14.295 经过实机验证。
- 纸胶带对象目前不会转换。
- 音频目前不会转换。
- 文本仍可编辑，但字体效果、换行和行距可能与原笔记不同。
- 普通笔型的视觉粗细不一定与原笔记完全一致。
- 部分图形或特殊对象可能无法完全保留原有外观。
- 导入重要笔记前，请备份原始 `.Jnotes` 文件和华为笔记中的现有内容。

本项目是基于逆向工程的非官方互操作工具，不是 Huawei 或 Jideos 的产品。建议先用副本进行测试，再处理重要资料。

## 技术资料

普通用户可以从上面的安装和转换步骤开始。以下文档面向希望了解格式、兼容性或转换细节的用户和开发者：

- [限制与兼容性说明](docs/limitations.md)
- [兼容性记录](docs/compatibility.md)
- [云记文件格式](docs/format-jnotes.md)
- [华为笔记文件格式](docs/format-hinote.md)
- [转换映射规则](docs/mapping.md)
- [v1.0.0 验证摘要](docs/validation-v1.0.0.md)
- [v1.1.0 验证摘要](docs/validation-v1.1.0.md)
- [v1.1.1 修复验证摘要](docs/validation-v1.1.1.md)

## 开发

安装开发依赖并运行测试：

```bash
pip install -e ".[dev]"
pytest
```

贡献格式研究或代码前，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT，见 [LICENSE](LICENSE)。
