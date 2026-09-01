# 华为 `.hinote` / PENCILENGINE 格式记录

以下记录描述了在 **华为笔记 15.0.14.295** 上经过设备验证的结构。

## `.hinote` 压缩包

一个 `.hinote` 导出文件是包含以下内容的 ZIP 压缩包：

```text
<note-id>.jhinote
pages/<page-id>.jhinote
files/*
custom_md.jhinote
```

`.jhinote` 负载是经过 GZIP 压缩的 JSON。

手写内容位于 `files/*.bin` PENCILENGINE 文件中。

## 原生 PDF 笔记

PDF 笔记将原始 PDF 作为一个顶层附件保存，而不是将每一页转换成图片：

```text
顶层 <note-id>.jhinote
    customNoteContent.attachment[].attachType = 3
    customNoteContent.attachment[].id = <pdf-attachment-id>

files/<uuid>_pdf
    原始 PDF 字节
```

每个 PDF 页面在 `pages/<page-id>.jhinote` 中使用：

```json
{
  "background": "base1",
  "bkgAttachmentId": "<pdf-attachment-id>",
  "bkgAttachmentIndex": 0
}
```

`bkgAttachmentIndex` 是 PDF 的从零开始页面索引。页面的 PENCILENGINE 附件、图片和文本元素继续作为 PDF 上方的可编辑覆盖层。导入 PDF 笔记通常使用 `noteType=101` 和 `noteIcon=import_pdf`；页面缩略图是预览用途，不能代替 PDF 页面正文。

## v15.0.14.295 使用的 PENCILENGINE 布局

经过测试的普通手写文件使用：

```text
196 字节文件头

每条笔迹重复：
    108 字节样式记录
    16 字节点表头
    N × 36 字节点数据
    64 字节链接/尾部

12 字节尾标记
```

这与一些假定样式记录更短的旧版公开解析器不同。

## 点数据

对于经过测试的 36 字节点步长：

| 点内偏移 | 类型 | 含义 |
|---:|---|---|
| +4 | 大端浮点数 | x |
| +8 | 大端浮点数 | y |
| +16 | 大端浮点数 | 压力 |

## v1.0.0 使用的样式记录字段

| 偏移 | 在测试文件中的含义 |
|---:|---|
| +8 | 普通笔迹的哨兵值；在原生几何记录中也表示图形代码 |
| +56 | `pen_type` |
| +64 | B 颜色浮点数 |
| +68 | G 颜色浮点数 |
| +72 | R 颜色浮点数 |
| +76 | 测试荧光笔的有效/渲染透明度 |
| +80 | 测试荧光笔的选择/界面透明度 |
| +84 | 宽度/基础宽度字段 |

### 颜色顺序

华为笔记 15.0.14.295 将测试笔迹的 RGB 通道存储为 **B、G、R**，而不是 R、G、B。

对于源颜色 `#364C7E`，v1.0.0 大致写入：

```text
+64 = 0x7E / 255
+68 = 0x4C / 255
+72 = 0x36 / 255
```

## 观察到的笔型

| 华为 `pen_type` | 工具 |
|---:|---|
| 1 | 钢笔 |
| 2 | 圆珠笔 |
| 3 | HB 铅笔 |
| 4 | 马克笔 |
| 5 | 荧光笔 |
| 11 | 2B 铅笔 |
| 12 | 秀丽/书法笔 |
| 13 | 毛笔 |

对于测试源笔记，v1.0.0 只需要 1/2/3/5，另加使用圆珠笔渲染的原生几何图形。

## 链表结构

逆向工程的一项关键结果是：196 字节文件头像根链接一样指向第 1 条笔迹，每个 64 字节的笔迹尾部都链接到下一条笔迹。

对于普通的后续链接尾部：

```text
tail + 16 = next_point_count × 36 + 140
tail + 48 = next_point_count × 36 + 20
```

转换器会为每条生成的笔迹重建这些值。

### 文件头 → 第一条笔迹

等价的根字段包括：

```text
header + 136 = 48
header + 144 = 65538
header + 148 = first_point_count × 36 + 140
header + 168 = 68
header + 172 = 52
header + 176 = 120
header + 180 = first_point_count × 36 + 20
```

测试布局在 `header+152..167` 存储一个类似 UUID 的 16 字节字段，并在 `header+188` 存储一个类似序列号的值。

实验期间，如果不重建文件头根指针，每个页面只显示第一条笔迹。

## END 尾部

最后一条笔迹使用区别于普通后续链接尾部的 END 布局。v1.0.0 会为每个 PENCILENGINE 页面写入一条 END 记录。

## 原生几何图形

华为几何工具的输出也存储在 PENCILENGINE 内。受控样本显示，几何记录使用圆珠笔渲染（`pen_type=2`）和紧凑的规范点集，例如：

| 华为图形代码 | 测试图形 | 参考样本中的典型点数 |
|---:|---|---:|
| 0 | 直线 | 2 |
| 7 | 矩形 | 5 |
| 10 | 圆/椭圆 | 361 |
| 16 | 曲线 | 101 |

一些原生图形页面在最后一条笔迹之后还包含扩展 UUID 索引。设备 A/B 测试发现省略该索引不会造成用户可见的选择/变换差异，因此 v1.0.0 不要求它。

## SHA-256 元数据

观察到的校验和行为使用普通 SHA-256：

- `fileMdStr`：文件内容的大写 SHA-256；
- `fileNameMdStr`：文件名字符串的小写 SHA-256。

页面元数据还包含一个记录文件哈希的 `detailFileMap`。
