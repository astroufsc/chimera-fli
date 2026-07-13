# Fli

Chimera plugin for Finger Lakes Instrumentation CCD cameras and filter wheels

This is a plugin for the [Chimera observatory control system](https://github.com/astroufsc/chimera).

## Installation

```bash
pip install -U chimera_fli
```

Or install from source:

```bash
pip install -U git+https://github.com/astroufsc/chimera-fli.git
```

## Configuration Example

Add the following to your `chimera.config` file:


```yaml
instruments:
    - name: fli
      type: FLI
      device: USB
      camera_model: Finger Lakes Instrumentation PL4240
      ccd_model: E2V CCD42-40
```

Requires the FLI SDK library and the [python-FLI](https://github.com/cversek/python-FLI)
bindings installed on the system.




## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/astroufsc/chimera-fli.git
cd chimera-fli

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install --install-hooks
```

### Running Tests

```bash
uv run pytest
```

### Code Quality

This project uses:
- [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- [pre-commit](https://pre-commit.com/) for automated checks

```bash
# Run linter
uv run ruff check

# Run formatter
uv run ruff format

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

## License

GPL-2.0-or-later

## Contact

For more information, contact us on chimera's discussion list:
https://groups.google.com/forum/#!forum/chimera-discuss

Bug reports and patches are welcome and can be sent over our GitHub page:
https://github.com/astroufsc/chimera-fli
