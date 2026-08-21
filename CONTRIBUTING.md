# Contributing

Contributions are welcome, especially reproducible format findings and compatibility reports.

## Rules for format research

1. Do not commit private notebooks, exported personal notes, account data, or proprietary app assets.
2. Prefer minimal synthetic samples made specifically for testing.
3. For a new binary-field claim, include:
   - source/target app versions;
   - a controlled experiment;
   - byte offsets / observed values;
   - whether the result was device-tested.
4. Keep `src/jnotes2hinote/converter_v1_0_0.py` frozen. New conversion behavior belongs in a new versioned core module.

## Development

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
