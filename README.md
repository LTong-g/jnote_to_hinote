# Jnotes2Hinote

英文文档：[README.en.md](README.en.md)

将 **Jideos 云记 `.Jnotes`** 笔记转换为 **华为笔记 `.hinote`**，并在已验证的格式范围内保留华为原生、可编辑的手写笔迹。

> **已验证兼容版本：** 云记 **3.2.3.2** → 华为笔记 **15.0.14.295**。其他版本目前尚未验证。

## v1.1.0 可保留的内容

- 多页笔记结构
- 华为原生、可编辑的 PENCILENGINE 笔迹
- 笔迹坐标和逐点压力
- 华为使用的 BGR 浮点颜色布局
- 验证笔记中使用的圆珠笔、钢笔、HB 铅笔和荧光笔映射
- 经过设备标定的荧光笔宽度和透明度
- 目前支持的直线、曲线、矩形、圆等几何图形，并尽量转换为华为原生可编辑图形笔迹
- 部分半透明平滑曲线会转换为华为原生荧光笔笔迹，并保留透明度
- 图片和图片型贴纸
- 基本的可编辑文本框
- 封面图片
- 华为原生纸张背景

## v1.1.0 不再需要华为参考笔记

从 v1.1.0 开始，转换器会直接生成华为笔记 15.0.14.295 所需的笔迹和图形数据，不再需要从华为笔记导出 `reference.hinote` 或 `shape-reference.hinote`。

旧版 v1.0.0 转换核心仍原样保存在 `src/jnotes2hinote/converter_v1_0_0.py`。

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

- **纸胶带：** 尚未确认华为原生等价物；v1.1.0 会跳过，而不会静默栅格化。
- **音频：** 已研究 Jnotes 音频和华为附件的存储方式，但 v1.1.0 尚未启用音频转换。
- **文字排版：** 文本仍可编辑，但字体效果、换行和行距可能不同。
- **普通笔宽：** 荧光笔宽度已经过设备标定；不同普通笔型的最终视觉粗细可能与源笔记不同。
- **几何图形粗细：** 目前支持的几何图形使用设备验证过的固定粗细档位（2、4、8）；源笔记中的任意粗细不一定能一一对应。
- **兼容性：** 只有云记 3.2.3.2 → 华为笔记 15.0.14.295 经过设备验证。

转换重要笔记前，请阅读 [docs/limitations.md](docs/limitations.md)，并保留原始文件备份。

## 逆向记录

- [Jnotes 格式](docs/format-jnotes.md)
- [华为 `.hinote` / PENCILENGINE 格式](docs/format-hinote.md)
- [映射规则](docs/mapping.md)
- [兼容性](docs/compatibility.md)
- [逆向过程时间线](docs/reverse-engineering.md)
- [v1.0.0 验证摘要](docs/validation-v1.0.0.md)
- [v1.1.0 验证摘要](docs/validation-v1.1.0.md)

## 安全与备份

请始终保留原始 `.Jnotes`，并在导入转换后的文件前导出/备份华为笔记。这是一个基于逆向工程的非官方互操作项目，不属于华为或 Jideos 产品。

## 开发

```bash
pip install -e ".[dev]"
pytest
```

版本化核心分别保存在：

```text
src/jnotes2hinote/converter_v1_0_0.py  # 冻结的旧版参考文件核心
src/jnotes2hinote/converter_v1_1_0.py  # 当前的无参考文件核心
```

后续修改应新增版本化核心，不要重写冻结的 v1.0.0 核心。

## 许可证

MIT，详见 [LICENSE](LICENSE)。

## 免责声明

本项目独立且非官方，与 Jideos 或华为不存在隶属、授权或赞助关系。产品和公司名称仅用于描述文件格式互操作性。
