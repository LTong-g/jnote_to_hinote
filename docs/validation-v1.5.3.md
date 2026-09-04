# v1.5.3 横向缩略图与封包验证

v1.5.3 修复 v1.5.2 的横向页元数据和缩略图尺寸。用户提供的 10 份解析失败 PDF Hinote 均被写为 `pageRatio>1`、`pageOrientation=0`，同时其缩略图宽度为 1179–1527 像素。原生横向样本的最后一页证明正确结构是 `pageRatio=0.625`、`pageOrientation=1`和 1080×675 缩略图。

当前规则是：

- 缩略图最长边固定为 1080 像素，另一边按 `pageRatio` 等比计算。
- `pageRatio` 始终表示小于或等于 1 的基础页面比例，横向页通过 `pageOrientation=1` 表示，竖向页为 `0`。
- 竖向页保持与原生样本一致的尺寸，例如 0.706 比例生成 762×1080。
- 横向 4:3 页面生成 1080×810，不再生成 1440×1080。
- JPEG 仍使用质量 100 和 4:2:0 采样，PDF 正文与可编辑覆盖层仍由高分辨率画布合成。
- ZIP 先写入 PDF/outline 等顶层资源，再按页面引用写入页面资源；`custom_md.jhinote` 使用同一顺序。

自动化验证覆盖竖向和横向尺寸、PDF 多页、PDF/普通页混排、JPEG 量化表与采样、ZIP CRC、`fileList` / `detailFileMap` / `custom_md.jhinote` SHA-256 及物理资源顺序。
