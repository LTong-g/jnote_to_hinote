# Push this folder to GitHub

After extracting the ZIP, open a terminal in the `Jnotes2Hinote` directory.

If you already created an empty GitHub repository:

```bash
git init
git branch -M main
git add .
git commit -m "Initial release v1.0.0"
git tag -a v1.0.0 -m "Device-tested Jnotes2Hinote v1.0.0"
git remote add origin https://github.com/YOUR_USERNAME/Jnotes2Hinote.git
git push -u origin main --tags
```

If the local folder is already inside a Git repository, skip `git init` and configure the remote as appropriate.

## Recommended GitHub repository settings

- Repository name: `Jnotes2Hinote`
- Description: `Convert Jideos Jnotes (.Jnotes) to Huawei Notes (.hinote) with native editable handwriting.`
- License: already included (MIT)
- Do not upload real personal `.Jnotes` or `.hinote` fixtures.
