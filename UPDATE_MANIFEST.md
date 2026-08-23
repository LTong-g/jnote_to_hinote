# Jnotes2Hinote v1.1.1 更新文件清单

以下路径均相对于仓库根目录。请将本更新覆盖到 v1.1.0 项目中，并替换同名文件。

v1.1.1 是一个修复版本：普通不透明 type 6/type 7 几何图形的 Huawei `style+84` 直接写入 Jnotes `d` 值，与普通笔迹保持一致。经过单独验证的半透明 `type=6,b=12` 荧光笔生成曲线规则保持不变。

## 新增

- `src/jnotes2hinote/converter_v1_1_1.py`：新的当前 v1.1.1 核心。
- `docs/validation-v1.1.1.md`：v1.1.1 修复和回归验证记录。
- `UPDATE_MANIFEST.md`：本文件。
- `SHA256SUMS.txt`：本更新文件的校验和清单。

## 替换

- `src/jnotes2hinote/__init__.py`：默认 API 改为导出 v1.1.1。
- `src/jnotes2hinote/cli.py`：命令行改为调用 v1.1.1。
- `pyproject.toml`：项目版本改为 `1.1.1`。
- `CITATION.cff`：软件版本改为 `1.1.1`。
- `README.md`：当前中文主文档。
- `README.en.md`：当前英文文档。
- `CHANGELOG.md`：增加 v1.1.1 更新记录。
- `docs/compatibility.md`：增加 v1.1.1 兼容性说明。
- `docs/frozen-core.md`：记录历史 v1.1.0 核心和当前 v1.1.1 核心。
- `docs/limitations.md`：更新几何宽度限制说明。
- `docs/mapping.md`：记录直接几何宽度映射。
- `tests/test_color_highlighter.py`：改为测试当前 v1.1.1 核心。
- `tests/test_geometry_rules.py`：测试直接几何宽度和半透明曲线规则。
- `tests/test_jnotes_parser.py`：改为测试当前 v1.1.1 核心。
- `tests/test_mapping.py`：改为测试当前 v1.1.1 核心。
- `tests/test_self_contained_pencilengine.py`：改为测试当前 v1.1.1 核心。
- `tests/test_version.py`：期望版本为 `1.1.1`。

## 保持不变

- `src/jnotes2hinote/converter_v1_0_0.py`：冻结的 v1.0.0 核心。
- `CORE_SHA256.txt`：继续记录冻结核心的哈希。

冻结的 v1.0.0 核心 SHA-256：

`ee551f236053b141f4f6d66425367cdf268a87f6b777c885b2a1c6f2553d7287`

## 删除

无。缓存文件不纳入 `SHA256SUMS.txt`。
