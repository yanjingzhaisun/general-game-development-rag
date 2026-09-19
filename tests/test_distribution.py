"""The reusable skill must leave each project independent of the distributor."""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "skills/project-code-memory/assets/runtime"


def bootstrap(root):
    script = ROOT / "skills/project-code-memory/scripts/bootstrap.py"
    spec = importlib.util.spec_from_file_location("bootstrap_skill", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.bootstrap(root)


def test_bundle_matches_current_implementation():
    for source in (ROOT / "src/general_game_development_rag").glob("*.py"):
        assert (
            source.read_bytes()
            == (BUNDLE / "src/general_game_development_rag" / source.name).read_bytes()
        )


def test_bootstrap_idempotent_and_preserves_local_adaptations(tmp_path):
    assert bootstrap(tmp_path)
    assert bootstrap(tmp_path) == []
    local = tmp_path / "ForAI/rag/manage.py"
    local.write_text("# project-specific change\n", encoding="utf-8")
    with pytest.raises(ValueError, match="merge explicitly"):
        bootstrap(tmp_path)
    assert local.read_text(encoding="utf-8") == "# project-specific change\n"


def installer():
    spec = importlib.util.spec_from_file_location(
        "install_project", ROOT / "tools/install_project.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_install_preserves_instructions_and_is_idempotent(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Existing project rules\n", encoding="utf-8")
    module = installer()
    assert module.install(tmp_path)["copied_files"] > 0
    assert module.install(tmp_path)["copied_files"] == 0
    instructions = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert instructions.startswith("# Existing project rules")
    assert instructions.count(module.MARKER) == 1
    assert (tmp_path / ".agents/skills/project-code-memory/SKILL.md").is_file()
    assert (tmp_path / "ForAI/rag/install.json").is_file()
    assert not (tmp_path / "ForAI/modules/runtime.md").exists()  # Never copy distributor knowledge.


def test_install_conflicts_are_checked_before_writing(tmp_path):
    local = tmp_path / "ForAI/rag/manage.py"
    local.parent.mkdir(parents=True)
    local.write_text("# local adaptation\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Local file differs"):
        installer().install(tmp_path)
    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / "AGENTS.md").exists()


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv required for local-runtime integration")
def test_two_projects_use_separate_runtime_and_database(tmp_path):
    for name in ("game-a", "game-b"):
        project = tmp_path / name
        project.mkdir()
        bootstrap(project)
        runtime = project / "ForAI/rag"
        command = ["uv", "run", "--directory", str(runtime), "python", "manage.py"]
        for action in ("init", "sync"):
            result = subprocess.run(
                [*command, action], cwd=tmp_path, capture_output=True, check=True
            )
            payload = json.loads(result.stdout.decode("utf-8"))
            if action == "init":
                assert payload["root"] == str(project.resolve())
        location = (
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--directory",
                    str(runtime),
                    "python",
                    "-c",
                    "import general_game_development_rag as p; print(p.__file__)",
                ],
                cwd=tmp_path,
                capture_output=True,
                check=True,
            )
            .stdout.decode()
            .strip()
        )
        assert Path(location).is_relative_to(runtime)
        assert (runtime / ".venv").is_dir()
        assert (runtime / ".cache/graph.sqlite3").is_file()
    a_entry = tmp_path / "game-a/ForAI/index.md"
    a_entry.write_text(a_entry.read_text(encoding="utf-8") + "\nOnly game A\n", encoding="utf-8")
    assert "Only game A" not in (tmp_path / "game-b/ForAI/index.md").read_text(encoding="utf-8")
