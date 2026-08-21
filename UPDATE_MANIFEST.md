# v1.1.0 更新文件清单

以下路径均相对于仓库根目录。

## 新增

- `src/jnotes2hinote/converter_v1_1_0.py`
- `docs/validation-v1.1.0.md`
- `tests/test_self_contained_pencilengine.py`

## 替换

- `CITATION.cff`
- `src/jnotes2hinote/__init__.py`
- `src/jnotes2hinote/cli.py`
- `pyproject.toml`
- `README.md`
- `README.en.md`
- `CHANGELOG.md`
- `docs/compatibility.md`
- `docs/frozen-core.md`
- `docs/limitations.md`
- `docs/mapping.md`
- `docs/reference-files.md`（保留为 v1.0.0 旧版文档）
- `tests/test_version.py`
- `tests/test_geometry_rules.py`
- `tests/test_mapping.py`
- `tests/test_color_highlighter.py`
- `tests/test_jnotes_parser.py`

## 不要修改

- `src/jnotes2hinote/converter_v1_0_0.py`：冻结的 v1.0.0 核心
- `CORE_SHA256.txt`：继续记录冻结的 v1.0.0 核心哈希

## 删除

v1.1.0 功能文件不需要删除。

如果 GitHub 仓库中仍有初次上传时误创建的顶层 `Jnotes2Hinote/` 目录（其中包含重复的 LICENSE），请另行删除。该目录不属于项目布局。

仓库已经创建后，也可以删除 `GITHUB_SETUP.md`，但这只是可选的整理工作，不是 v1.1.0 的必要步骤。
