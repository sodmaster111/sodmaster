# Render deploy failure: unsupported Python runtime

- **Service**: `sodmaster-c-unit`
- **Render service ID**: `srv-d3rvqhe3jp1c73ei54n0`
- **Detected on**: 2025-10-25
- **Status**: Fixed via PR (pending merge)

## Summary
Recent deployments failed during the build phase with `build_failed`. The Render build
image does not yet ship Python 3.12, but `runtime.txt` requested `python-3.12.3`.
This forced the build to abort before installing dependencies.

## Fix
Pin `runtime.txt` to `python-3.11.9`, the most recent patch release supported by Render.
A regression test (`tests/test_runtime_version.py`) ensures the runtime stays on a
supported 3.11 build until Render upgrades their stack.

## Follow-up
- Monitor the Render changelog for Python 3.12 support.
- Once available, update `runtime.txt` and adjust the runtime test accordingly.
