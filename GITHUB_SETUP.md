# 将此文件夹推送到 GitHub

解压 ZIP 后，在 `Jnotes2Hinote` 目录中打开终端。

如果你已经创建了空的 GitHub 仓库：

```bash
git init
git branch -M main
git add .
git commit -m "初始发布 v1.0.0"
git tag -a v1.0.0 -m "经过设备验证的 Jnotes2Hinote v1.0.0"
git remote add origin https://github.com/YOUR_USERNAME/Jnotes2Hinote.git
git push -u origin main --tags
```

如果本地文件夹已经位于 Git 仓库中，请跳过 `git init`，并按需配置远程仓库。

## 推荐的 GitHub 仓库设置

- 仓库名称：`Jnotes2Hinote`
- 仓库描述：`将 Jideos 云记（.Jnotes）转换为华为笔记（.hinote），并保留原生可编辑笔迹。`
- 许可证：已包含（MIT）
- 不要上传真实的个人 `.Jnotes` 或 `.hinote` 测试文件。
