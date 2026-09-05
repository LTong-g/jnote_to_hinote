# 示例

这里不会提交真实的 `.Jnotes` 或 `.hinote` 压缩包，因为导出的笔记可能包含私人数据，华为参考文件也应来自用户自己的安装环境。

典型的转换命令：

```bash
jnotes2hinote MyNotebook.Jnotes MyNotebook.hinote \
  --report reports/MyNotebook.json
```

完整转换前，请先使用 `--pages 5`，再将较小的结果导入华为笔记进行检查。

v1.1.0 及以后的当前转换路径不再需要参考 `.hinote` 文件。需要复现冻结的 v1.0.0 研究路径时，请阅读 [旧版参考文件说明](../docs/reference-files.md)。
