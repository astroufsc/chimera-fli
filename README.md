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
    - name: camera
      type: FLICamera
      device: USB
      camera_model: Finger Lakes Instrumentation PL4240
      ccd_model: E2V CCD42-40

    - name: wheel
      type: FLIFilterWheel
      device: USB          # or a device name/serial number to pin one wheel
      filters: U B V R I
      move_timeout: 30     # optional, seconds to wait for a move to finish
```

The camera and the filter wheel are independent instruments, so deployments
with only one of the two devices can configure just that section.

The filter wheel automatically reconnects (three attempts with increasing
delays) when the USB device drops mid-call (EPIPE), and polls the wheel until
the motor stops, since the FLI SDK documents `FLISetFilterPos` as possibly
returning while the wheel is still moving.

If `libfli.so` lives outside the default linker paths, point the
`FLI_SDK_PATH` environment variable at it. See `docs/summary.md` for the
FLI SDK API reference used by the vendored bindings.

Requires the FLI SDK library (`libfli.so`, packaged as `libfli2` on Debian)
installed on the system. The Python bindings from
[python-FLI](https://github.com/cversek/python-FLI) are vendored into this
package (`chimera_fli.fli`), ported to Python 3.




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
