# Examples

No real `.Jnotes` or `.hinote` archives are committed here because exported notebooks can contain private data and Huawei reference files should come from the user's own installation.

A typical conversion command is:

```bash
jnotes2hinote MyNotebook.Jnotes MyNotebook.hinote \
  --reference-hinote references/pen-reference.hinote \
  --shape-reference-hinote references/shape-reference.hinote \
  --report reports/MyNotebook.json
```

Before a full conversion, use `--pages 5` and import the small result into Huawei Notes.
