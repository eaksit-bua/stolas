"""Mypy typing-fixture harness for the stolas mypy plugin and stubs.

This runs ``mypy`` as a SUBPROCESS over small deterministic fixture files in
``tests/typing/fixtures/`` and asserts on its output -- ``reveal_type(...)``
notes and expected error codes/messages. It is the regression guard for the
mypy plugin (``src/stolas/mypy_plugin.py``), which is excluded from line
coverage; its behaviour is validated here instead.

Harness design
--------------
* Invocation: ``sys.executable -m mypy <fixture-copy>.py --config-file
  <repo>/pyproject.toml --cache-dir <tmp> --strict``, run with ``cwd`` = repo
  root so that ``mypy_path = ["src"]`` and the file-path plugin entry
  ``src/stolas/mypy_plugin.py`` (both resolved relative to the config dir / cwd)
  apply. Running from elsewhere fails to find ``stolas`` AND fails to load the
  plugin, so cwd is pinned.
* Isolation: each run gets its own per-test ``--cache-dir`` in a pytest
  ``tmp_path``, so no stale incremental cache leaks between cases or from the
  developer's own ``.mypy_cache``.
* Deterministic module names: each fixture is COPIED into the tmp dir before
  invocation. Run directly from ``tests/typing/fixtures/`` the module name would
  be package-qualified (``tests.typing.fixtures.<name>``) because ``tests`` is a
  package; copying to a bare tmp dir makes ``reveal_type`` report ``<name>.Point``.
* Plugin-on vs plugin-off: ``run_mypy`` uses the project ``pyproject.toml``
  (plugin active). ``run_mypy_plugin_off`` writes a tmp config with ``mypy_path``
  but no ``plugins=`` -- the same fixtures then fail, which proves the plugin is
  what makes them pass (registration proof).

The mypy subprocess is slow, so fixtures are kept few and each is checked once.
"""

import os
import re
import shutil
import subprocess  # nosec B404 - invoking the project's own mypy on fixtures
import sys

import pytest

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

_PYPROJECT = os.path.join(_REPO_ROOT, "pyproject.toml")
_FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

_REVEAL_RE = re.compile(r'Revealed type is "(?P<type>.*)"')
_ERROR_RE = re.compile(r"error: (?P<msg>.*?)\s+\[(?P<code>[a-z-]+)\]\s*$", re.MULTILINE)


def _fixture_path(name: str) -> str:
    """Absolute path to a committed fixture .py file."""
    path = os.path.join(_FIXTURE_DIR, name)
    assert os.path.isfile(path), f"missing fixture: {path}"
    return path


def _copy_fixture(name: str, dest_dir: str) -> str:
    """Copy a fixture into ``dest_dir`` so its module name is the bare stem."""
    dest = os.path.join(dest_dir, name)
    shutil.copyfile(_fixture_path(name), dest)
    return dest


def _invoke_mypy(target: str, config_file: str, cache_dir: str) -> str:
    """Run mypy --strict on ``target`` from the repo root; return combined output."""
    result = subprocess.run(  # nosec B603 - fixed argv, project's own mypy
        [
            sys.executable,
            "-m",
            "mypy",
            target,
            "--config-file",
            config_file,
            "--cache-dir",
            cache_dir,
            "--strict",
            "--no-error-summary",
            "--hide-error-context",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + result.stderr


def run_mypy(name: str, tmp_path: object) -> str:
    """Type-check a fixture with the project config (plugin ACTIVE)."""
    work = str(tmp_path)
    target = _copy_fixture(name, work)
    cache = os.path.join(work, "cache")
    return _invoke_mypy(target, _PYPROJECT, cache)


def run_mypy_plugin_off(name: str, tmp_path: object) -> str:
    """Type-check a fixture with mypy_path but NO plugin (plugin INACTIVE)."""
    work = str(tmp_path)
    target = _copy_fixture(name, work)
    cache = os.path.join(work, "cache_off")
    config = os.path.join(work, "mypy_off.ini")
    src_path = os.path.join(_REPO_ROOT, "src")
    with open(config, "w", encoding="utf-8") as handle:
        handle.write(f"[mypy]\nmypy_path = {src_path}\n")
    return _invoke_mypy(target, config, cache)


def reveal_types(output: str) -> list[str]:
    """All revealed types, in source order, from mypy output."""
    return _REVEAL_RE.findall(output)


def error_codes(output: str) -> list[str]:
    """All ``[error-code]`` tokens, in source order, from mypy output."""
    return [match.group("code") for match in _ERROR_RE.finditer(output)]


def is_clean(output: str) -> bool:
    """True when mypy reported zero errors."""
    return "error:" not in output


# --- @struct >> and .replace() reveal types (plugin active, 5.2 / 5.6 / 5.7) ---


def test_struct_pipe_reveals_target_function_return_type(tmp_path: object) -> None:
    output = run_mypy("struct_pipe_replace.py", tmp_path)
    assert reveal_types(output)[0] == "builtins.str"


def test_struct_replace_reveals_the_struct_type(tmp_path: object) -> None:
    output = run_mypy("struct_pipe_replace.py", tmp_path)
    assert reveal_types(output)[1] == "struct_pipe_replace.Point"


def test_struct_pipe_replace_fixture_has_no_type_errors(tmp_path: object) -> None:
    output = run_mypy("struct_pipe_replace.py", tmp_path)
    assert is_clean(output)


# --- @struct(open=True) keeps the plugin firing (Milestone 6.2) ---


def test_open_struct_pipe_reveals_target_function_return_type(
    tmp_path: object,
) -> None:
    output = run_mypy("struct_open.py", tmp_path)
    assert reveal_types(output)[0] == "builtins.str"


def test_open_struct_replace_reveals_the_struct_type(tmp_path: object) -> None:
    output = run_mypy("struct_open.py", tmp_path)
    assert reveal_types(output)[1] == "struct_open.Open"


def test_open_struct_positional_construction_is_rejected_as_kw_only(
    tmp_path: object,
) -> None:
    output = run_mypy("struct_open.py", tmp_path)
    assert "Too many positional arguments" in output


# --- @cases value-variant constructor typing (5.3) ---


def test_cases_value_variant_constructor_reveals_any(tmp_path: object) -> None:
    output = run_mypy("cases_constructor.py", tmp_path)
    assert reveal_types(output)[0] == "Any"


def test_cases_constructor_call_is_accepted(tmp_path: object) -> None:
    output = run_mypy("cases_constructor.py", tmp_path)
    assert is_clean(output)


# --- @trait dispatch reveal types (5.4) ---


def test_trait_decorator_reveals_parametrized_dispatcher(tmp_path: object) -> None:
    output = run_mypy("trait_dispatch.py", tmp_path)
    assert (
        reveal_types(output)[0] == "stolas.struct.trait.TraitDispatcher[builtins.str]"
    )


def test_trait_dispatch_call_reveals_return_type(tmp_path: object) -> None:
    output = run_mypy("trait_dispatch.py", tmp_path)
    assert reveal_types(output)[1] == "builtins.str"


def test_trait_fixture_has_no_type_errors(tmp_path: object) -> None:
    output = run_mypy("trait_dispatch.py", tmp_path)
    assert is_clean(output)


# --- the `_` placeholder stays opaque / Any (north star, 5.6) ---


def test_placeholder_attribute_access_stays_opaque_any(tmp_path: object) -> None:
    output = run_mypy("placeholder_opaque.py", tmp_path)
    assert (
        reveal_types(output)[0]
        == "stolas.logic.placeholder.PlaceholderExpression[Any, Any]"
    )


# --- registration proof: clean WITH plugin, errors WITHOUT it (5.5) ---


def test_plugin_active_proof_is_clean_with_plugin(tmp_path: object) -> None:
    output = run_mypy("plugin_active_proof.py", tmp_path)
    assert is_clean(output)


def test_plugin_active_proof_pipe_fails_without_plugin(tmp_path: object) -> None:
    output = run_mypy_plugin_off("plugin_active_proof.py", tmp_path)
    assert "Unsupported left operand type for >> " in output


def test_plugin_active_proof_replace_fails_without_plugin(tmp_path: object) -> None:
    output = run_mypy_plugin_off("plugin_active_proof.py", tmp_path)
    assert 'has no attribute "replace"' in output


def test_plugin_active_proof_cases_call_fails_without_plugin(
    tmp_path: object,
) -> None:
    output = run_mypy_plugin_off("plugin_active_proof.py", tmp_path)
    assert '"str" not callable' in output


# --- negative / strictness: errors EVEN WITH the plugin (not blanket-Any) ---


def test_piping_struct_into_str_only_function_is_operator_error(
    tmp_path: object,
) -> None:
    output = run_mypy("struct_errors.py", tmp_path)
    assert "operator" in error_codes(output)


def test_replace_result_assigned_to_wrong_type_is_assignment_error(
    tmp_path: object,
) -> None:
    output = run_mypy("struct_errors.py", tmp_path)
    assert "assignment" in error_codes(output)


def test_unexpected_struct_constructor_keyword_is_call_arg_error(
    tmp_path: object,
) -> None:
    output = run_mypy("struct_errors.py", tmp_path)
    assert "call-arg" in error_codes(output)


def test_wrong_typed_struct_field_is_arg_type_error(tmp_path: object) -> None:
    output = run_mypy("struct_errors.py", tmp_path)
    assert "arg-type" in error_codes(output)


@pytest.mark.parametrize(
    "name",
    [
        "struct_pipe_replace.py",
        "struct_open.py",
        "cases_constructor.py",
        "trait_dispatch.py",
        "placeholder_opaque.py",
        "plugin_active_proof.py",
        "struct_errors.py",
    ],
)
def test_every_fixture_file_exists(name: str) -> None:
    assert os.path.isfile(_fixture_path(name))
