from pathlib import Path
import tomllib


PYPROJECT_PATH = Path(__file__).parents[1] / "pyproject.toml"


def test_pyproject_declares_pytest_and_integration() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]

    assert any(
        dependency.startswith("pytest")
        for dependency in project["optional-dependencies"]["dev"]
    )
    assert "integration" in project["keywords"]
    assert any(dependency.startswith("uvicorn") for dependency in project["dependencies"])
