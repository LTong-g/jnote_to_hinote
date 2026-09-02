# Jnotes2Hinote

将云记（Jnotes）的 `.Jnotes` / `.jnote` 笔记转换为华为笔记的 `.hinote` 文件，方便把笔记导入华为笔记后继续查看和编辑。

目前已实机验证的版本组合是：**云记 3.2.3.2 → 华为笔记 15.0.14.295**。其他版本没有经过验证，转换结果可能有所不同。

当前版本：**v1.5.0**。项目提供桌面图形界面，也支持命令行批量转换。

英文版：[README.en.md](README.en.md)

## 推荐用法：桌面界面

如果你只是想转换笔记，建议使用图形界面。它支持选择多个文件、文件夹或路径清单，并会显示转换进度、成功结果和错误信息。

### 使用 Windows 打包版

如果你拿到的是 Windows 打包版，请运行：

```text
dist/Jnotes2Hinote/Jnotes2Hinote.exe
```

请保留 `Jnotes2Hinote` 文件夹中的其他文件，不能只复制 exe 文件。打包版不需要另外安装 Python。

### 从源码启动

需要 Python 3.10 或更高版本。在项目根目录打开终端，执行：

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
jnotes2hinote-gui
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m jnotes2hinote.gui
```

### 基本操作

1. 点击“添加文件”“添加文件夹”或“添加 TXT 清单”，也可以直接将这些输入拖到输入列表。
2. 如需搜索文件夹内的所有子文件夹，勾选递归搜索。
3. 选择输出文件夹，设置重名文件的处理方式，然后开始转换。

界面采用左右两列布局：左侧管理输入和输出设置，右侧显示转换结果与运行日志；中间分隔条可以拖动调整各区域大小。

程序会自动识别 `.Jnotes` 和 `.jnote` 文件。TXT 清单按每行一个路径读取；空行和以 `#` 开头的行会被忽略。某个路径无法读取或转换失败时，程序会记录错误并继续处理其他路径。

GUI 的完整说明见：[图形界面使用说明](docs/gui.md)。

## 命令行用法

命令行适合需要脚本化处理或批量转换的情况。安装项目后，可以使用 `jnotes2hinote` 命令；也可以把下面的命令中的 `jnotes2hinote` 换成 `python -m jnotes2hinote`。

### 转换一个文件

```bash
jnotes2hinote input.Jnotes output.hinote
```

### 转换文件夹

默认只处理文件夹的直接子级：

```bash
jnotes2hinote notes output
```

如果要连同所有子文件夹一起处理，使用 `--recursive`：

```bash
jnotes2hinote notes output --recursive
```

### 同时输入多个路径

可以在一次命令中混合输入多个文件和文件夹：

```bash
jnotes2hinote notes-a notes-b meeting.Jnotes output
```

### 使用 TXT 路径清单

TXT 文件每行写一个文件或文件夹路径：

```text
notes-a
notes-b/meeting.Jnotes
```

然后将 TXT 文件作为输入：

```bash
jnotes2hinote paths.txt output --recursive
```

清单中的相对路径以 TXT 文件所在文件夹为基准。批量转换会跳过无效路径、无法读取的路径和转换失败的文件，并继续处理其余输入；错误会显示在终端中，也可以写入报告。

### 常用选项

生成 JSON 转换报告：

```bash
jnotes2hinote notes output --recursive --report conversion-report.json
```

先转换前 5 页进行测试：

```bash
jnotes2hinote input.Jnotes test.hinote --pages 5
```

批量转换时，输出参数必须是文件夹。输出文件默认使用原文件名；如果出现重名，命令行转换器会自动添加序号。输入和输出不要使用同一个路径，并建议保留原始 `.Jnotes` 文件。

## 转换内容与注意事项

在支持范围内，转换结果会保留华为笔记中的可编辑内容，而不是把整页简单合并成一张图片。当前支持的内容包括：

- 多页笔记
- PDF 笔记的原始 PDF 页面，页面内容不会栅格化
- 可编辑的手写笔迹，包括常见笔型、颜色和逐点压力
- 部分线条、曲线、矩形和圆形
- 图片、图片型贴纸和页面缩略图
- 基本文本框
- 常见的空白、横线、点阵和方格纸张

以下内容可能无法转换，或与原笔记显示不同：

- 纸胶带对象和音频目前不会转换
- PDF 笔记依赖华为笔记对导入 PDF 的支持；加密 PDF、多个 PDF 混合页面目前未经过设备验证
- 文本仍可编辑，但字体、换行和行距可能变化
- 普通笔型的视觉粗细可能与原笔记不同
- 部分图形或特殊对象可能无法完全保留原有外观

转换后请在华为笔记中检查重要页面、图片、文本和笔迹。处理重要资料前，请先备份原始笔记，并优先用副本进行测试。

本项目是基于逆向工程的非官方互操作工具，不是华为或 Jideos 的官方产品。

## 其他文档

- [图形界面使用说明](docs/gui.md)
- [限制与兼容性说明](docs/limitations.md)
- [兼容性记录](docs/compatibility.md)
- [云记文件格式](docs/format-jnotes.md)
- [华为笔记文件格式](docs/format-hinote.md)
- [转换映射规则](docs/mapping.md)
- [v1.0.0 验证摘要](docs/validation-v1.0.0.md)
- [v1.1.0 验证摘要](docs/validation-v1.1.0.md)
- [v1.1.1 修复验证摘要](docs/validation-v1.1.1.md)
- [v1.1.2 修复验证摘要](docs/validation-v1.1.2.md)
- [v1.2.0 PDF 转换验证摘要](docs/validation-v1.2.0.md)

## 开发

安装开发依赖并运行测试：

```bash
pip install -e ".[dev]"
pytest
```

参与格式研究或代码开发前，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT，见 [LICENSE](LICENSE)。
