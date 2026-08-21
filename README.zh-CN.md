# Jnotes2Hinote

将 **云记 / Jideos Jnotes 的 `.Jnotes`** 笔记转换为 **华为笔记 / Huawei Notes 的 `.hinote`**，并在已破解的格式范围内尽量保留华为原生、可框选、可擦除的可编辑笔迹。

> **已实机验证版本：云记 3.2.3.2 → 华为笔记 15.0.14.295。** 其他版本目前均视为未验证。

## v1.0.0 已支持

- 多页笔记
- 华为原生 PENCILENGINE 可编辑笔迹
- 笔迹坐标与逐点 pressure
- Huawei 15.0.14.295 使用的 BGR 浮点颜色
- 测试笔记中涉及的圆珠笔、钢笔、HB 铅笔、荧光笔
- 已通过实机标定的荧光笔宽度与透明度
- 已确认的 Jnotes type 6 / type 7 几何图形
- 图片与图片型贴纸
- 基本文本框
- 封面图片
- 华为原生纸张模板

## 为什么需要你自己的华为参考 `.hinote`

仓库不会附带华为应用二进制资产，也不会附带任何私人笔记。转换器会从**你自己用华为笔记导出的测试笔记**中提取 PENCILENGINE 结构模板。

需要准备：

1. `reference.hinote`：包含钢笔、圆珠笔、HB 铅笔、荧光笔各至少一笔；
2. `shape-reference.hinote`：如果源笔记含 type 6/7 图形，需要包含直线、曲线、矩形、圆/椭圆。

详细步骤见 [docs/reference-files.md](docs/reference-files.md)。

## 安装

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
pip install -e .
```

## 使用

```powershell
jnotes2hinote input.Jnotes output.hinote `
  --reference-hinote reference.hinote `
  --shape-reference-hinote shape-reference.hinote `
  --report conversion-report.json
```

先只转换前 5 页做测试：

```powershell
jnotes2hinote input.Jnotes test.hinote `
  --reference-hinote reference.hinote `
  --shape-reference-hinote shape-reference.hinote `
  --pages 5
```

## 当前限制

- **纸胶带**：尚未找到华为原生等价物；v1.0.0 会跳过，而不会悄悄把它变成错误的笔迹。
- **音频**：两边存储结构已经基本确认，但 v1.0.0 暂未启用音频迁移。
- **文字排版**：内容可迁移，但字体、换行、行距不保证像素级一致。
- **普通笔型视觉宽度**：尚未完成所有笔型的系统视觉标定；荧光笔已实机标定。
- **版本兼容性**：只有云记 3.2.3.2 → 华为笔记 15.0.14.295 经过实机验证。

## 文档

- [云记格式](docs/format-jnotes.md)
- [华为 hinote / PENCILENGINE 格式](docs/format-hinote.md)
- [转换映射](docs/mapping.md)
- [兼容性](docs/compatibility.md)
- [逆向过程](docs/reverse-engineering.md)
- [v1.0.0 验证摘要](docs/validation-v1.0.0.md)
- [限制](docs/limitations.md)

## v1.0.0 冻结规则

当前已验证核心位于：

```text
src/jnotes2hinote/converter_v1_0_0.py
```

后续若要修改转换行为，应新增版本模块，而不是直接重写 v1.0.0。

## 免责声明

这是独立、非官方的文件格式互操作项目，与云记/Jideos 或 Huawei/华为无隶属、授权或背书关系。导入前请备份原始笔记。
