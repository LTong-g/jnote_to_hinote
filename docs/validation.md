# 验证状态 / Validation status

当前实现针对以下版本组合进行过设备验证：

- 云记（Jnotes）3.2.3.2
- 华为笔记（Huawei Notes）15.0.14.295

其他版本可能使用不同的内部格式，尚未声明兼容。

## 已验证能力

- zip.Jzip 与 zip.Jnotes 两种 Jnotes 容器入口
- 普通笔迹、逐点压力、颜色与荧光笔
- 受支持的线条、曲线、矩形和圆形
- 图片、基本文本框与常见纸张背景
- 原始 PDF 附件与逐页背景引用
- 普通页、PDF 页、混排页与横向页缩略图
- 单文件、批量、CLI、GUI、输出路径保护与报告匿名化

自动化测试覆盖二进制链接、颜色/透明度、几何宽度、PDF 字节一致性和
页面索引、缩略图规格及封包哈希。关键设备验证使用过一份 171 页笔记，
包含 44,828 条笔迹、48 张图片/贴纸、35 个文本框和 245 条几何记录。

## 关键限制

- 纸胶带对象和音频不会转换。
- 文本可编辑，但字体、换行和行距可能变化。
- 加密 PDF 不受支持；多个 PDF 混合页面尚未完整设备验证。
- 某些特殊笔型、图形或对象可能无法完整保留外观。
- 转换后应在华为笔记中抽查重要页面，并始终保留原始文件。

版本级变更见 [CHANGELOG.md](../CHANGELOG.md)，当前限制的完整说明见
[limitations.md](limitations.md)。历史实现由 Git 提交和标签保存，不再复制到当前源码树。

---

The current implementation has been device-tested with Jnotes 3.2.3.2 and
Huawei Notes 15.0.14.295. Automated tests cover both known Jnotes container
entries, editable ink, geometry, images, text, paper backgrounds, native PDF
attachments, portrait and landscape thumbnails, archive integrity, CLI/GUI
helpers, safe output paths, and redacted reports.

Paper tape and audio are not converted. Text layout can differ, encrypted PDFs
are unsupported, and unusual objects may not preserve their appearance
exactly. Keep the source notebook and verify important pages after import.
