# Jnotes2Hinote

将 **Jideos 云记 `.Jnotes`** 笔记转换为 **华为笔记 `.hinote`**，并在已逆向确认的格式范围内保留华为原生、可编辑的手写笔迹。

> **已验证兼容版本：** 云记 **3.2.3.2** → 华为笔记 **15.0.14.295**。其他版本目前尚未验证。

## v1.0.0 可保留的内容

- 多页笔记结构
- 华为原生、可编辑的 PENCILENGINE 笔迹
- 笔迹坐标和逐点压力
- 华为使用的 BGR 浮点颜色布局
- 测试笔记中使用的圆珠笔、钢笔、HB 铅笔和荧光笔映射
- 经过设备标定的荧光笔宽度和透明度
- 支持的 Jnotes type 6 / type 7 几何图形，并转换为华为几何样式的 PENCILENGINE 笔迹
- 图片和图片型贴纸
- 基本的可编辑文本框
- 封面图片
- 华为原生纸张背景

## 重要：必须准备参考 `.hinote` 文件

本项目不会附带华为二进制资产或私人笔记导出文件。转换器会从**你在自己的华为笔记中导出的测试笔记**提取 PENCILENGINE 结构模板。

你需要准备：

1. `reference.hinote`：一份包含以下示例的华为笔记：
   - 钢笔（`pen_type=1`）
   - 圆珠笔（`pen_type=2`）
   - HB 铅笔（`pen_type=3`）
   - 荧光笔（`pen_type=5`）
2. `shape-reference.hinote`：源笔记包含支持的 Jnotes type 6/7 几何图形时需要。请在其中至少创建：
   - 直线
   - 曲线
   - 矩形
   - 圆/椭圆

详见 [docs/reference-files.md](docs/reference-files.md)。

## 安装

```bash
python -m venv .venv
```

Windows：

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
jnotes2hinote input.Jnotes output.hinote \
  --reference-hinote reference.hinote \
  --shape-reference-hinote shape-reference.hinote \
  --report conversion-report.json
```

或者：

```bash
python -m jnotes2hinote input.Jnotes output.hinote \
  --reference-hinote reference.hinote \
  --shape-reference-hinote shape-reference.hinote
```

测试时只转换前 5 页：

```bash
jnotes2hinote input.Jnotes test.hinote \
  --reference-hinote reference.hinote \
  --shape-reference-hinote shape-reference.hinote \
  --pages 5
```

## 已知限制

- **纸胶带：** 尚未确认华为原生等价物；v1.0.0 会跳过，而不会静默地把它栅格化。
- **音频：** 已逆向确认 Jnotes 音频存储和华为通用附件存储，但 v1.0.0 尚未启用音频转换。
- **排版：** 文本可以编辑，但字体度量、换行和行距可能不同。
- **笔宽：** 荧光笔宽度已经过设备标定；普通笔类的视觉宽度尚未完成完整标定。
- **兼容性：** 只有云记 3.2.3.2 → 华为笔记 15.0.14.295 经过设备验证。

转换重要笔记前，请阅读 [docs/limitations.md](docs/limitations.md)。

## 逆向记录

仓库记录了转换器所依据的文件格式发现：

- [Jnotes 格式](docs/format-jnotes.md)
- [华为 `.hinote` / PENCILENGINE 格式](docs/format-hinote.md)
- [映射规则](docs/mapping.md)
- [兼容性](docs/compatibility.md)
- [逆向过程时间线](docs/reverse-engineering.md)
- [v1.0.0 验证摘要](docs/validation-v1.0.0.md)

## 安全与备份

请始终保留原始 `.Jnotes`，并在导入转换后的文件前导出/备份华为笔记。这是一个基于逆向工程的非官方互操作项目，不属于华为或 Jideos 产品。

## 开发

```bash
pip install -e ".[dev]"
pytest
```

v1.0.0 核心有意冻结在：

```text
src/jnotes2hinote/converter_v1_0_0.py
```

未来的行为变更应使用新的版本化核心，而不是重写经过设备验证的实现。

## 许可证

MIT，详见 [LICENSE](LICENSE)。

## 免责声明

本项目独立且非官方，与 Jideos 或华为不存在隶属、授权或赞助关系。产品和公司名称仅用于描述文件格式互操作性。
