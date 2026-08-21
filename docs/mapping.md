# v1.0.0 的 Jnotes → 华为映射规则

以下是冻结的 v1.0.0 转换核心所实现的规则。

## 笔型

| Jnotes 类型 | Jnotes 含义 | 华为 `pen_type` |
|---:|---|---:|
| 1 | 圆珠笔 | 2 |
| 2 | 钢笔 | 1 |
| 3 | 荧光笔 | 5 |
| 5 | 铅笔 | 3（HB） |

## 颜色

Jnotes 存储有符号 ARGB 整数。华为笔记 15.0.14.295 将测试笔迹颜色浮点数按 BGR 顺序存储：

```text
style+64 = B / 255
style+68 = G / 255
style+72 = R / 255
```

## 荧光笔

v1.0.0 保留的设备标定规则：

```text
华为宽度 = Jnotes d × 16 / 3
style+76 = min(80/255, source_alpha/255)
style+80 = min(80/255, source_alpha/255)
```

经过验证的笔记中的示例：

| Jnotes `d` | 华为宽度 |
|---:|---:|
| 3 | 16 |
| 3.68 | 19.6267 |
| 6 | 32 |

## 几何图形

经过测试的笔记使用了以下映射：

| Jnotes | 含义 | 华为图形代码 |
|---|---|---:|
| type 6, `b=0` | 规则化直线 | 0 |
| type 6, `b=12` | 规则化曲线 | 16 |
| type 6, `b=4` | 识别出的椭圆 | 10 |
| type 7, `b=3` | 矩形 | 7 |
| type 7, `b=4` | 圆/椭圆 | 10 |

几何图形使用华为圆珠笔几何记录（`pen_type=2`）进行渲染。

最终几何宽度规则：

```text
华为几何宽度 = Jnotes d / 3
```

不支持的 type 6/type 7 子类型会保留为可编辑的圆珠笔路径回退，而不是直接丢弃。

## 纸张背景

通过受控笔记确认的华为模板：

| 华为背景 | 含义 |
|---|---|
| `base1` | 空白 |
| `base4` | 宽横线 |
| `base5` | 窄横线 |
| `base6` | 点阵 |
| `base3` | 小/窄方格 |
| `base2` | 中/宽方格 |

v1.0.0 使用的 Jnotes 映射：

- `White_Line_paper_1_Paper`，界面尺寸 1–2 → `base5`
- `White_Line_paper_1_Paper`，界面尺寸 3+ → `base4`
- 其他横线模板（包括 `v-narrow-line-white`）→ `base4`
- `White_Graph_Paper`，界面尺寸 1–4 → `base3`
- `White_Graph_Paper`，界面尺寸 5+ → `base2`
- `White_Wide_Grid_Paper` → `base2`
- 点阵纸 → `base6`
- 空白纸/封面下方 → `base1`

在受控 Jnotes 样本中，界面纸张尺寸可以按以下方式从参数推导：

```text
界面尺寸 = horParts + 3
```

适用于已观察到的参数化模板（`-2 → 1`、`0 → 3`、`3 → 6`）。

## 图片和贴纸

Jnotes PNG/JPEG 图片字节会复制到华为 `files/`，并由 `elementType=1` 页面元素引用。因此图片型贴纸使用相同映射。

## 文本

Jnotes 文本会映射到带有 HTML 风格富文本标记的华为 `elementType=0`，用于支持的属性。字体度量和换行不保证完全一致。

## 纸胶带

尚未确认华为原生对象。冻结的 v1.0.0 会跳过 Jnotes type 10 纸胶带笔迹，并报告跳过数量。

## 音频

v1.0.0 未启用。
