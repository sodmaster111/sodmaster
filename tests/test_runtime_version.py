import pathlib

EXPECTED_RUNTIME = "python-3.11.9"


def test_runtime_pin_matches_supported_version():
    runtime_path = pathlib.Path(__file__).resolve().parent.parent / "runtime.txt"
    contents = runtime_path.read_text(encoding="utf-8").strip()
    assert (
        contents == EXPECTED_RUNTIME
    ), (
        "Render uses runtime.txt to select the Python interpreter. "
        "Pin the file to a supported 3.11 release so deployments stay green."
    )
