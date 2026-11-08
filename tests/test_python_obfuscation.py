import random
import subprocess
import sys

import pytest

from api import index


@pytest.fixture(autouse=True)
def deterministic_names(monkeypatch):
    monkeypatch.setattr(index, "random", random.Random(0))


def assert_preserves_output(source, level, anti_hooking=False):
    generated = index.obfuscate_python(source, level, anti_hooking)
    compile(generated, "<obfuscated>", "exec")
    result = subprocess.run(
        [sys.executable, "-I", "-c", generated],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "result 42\n"
    assert result.stderr == ""


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
    pytest.param(14, marks=pytest.mark.xfail(
        strict=True, raises=SyntaxError,
        reason="Chunk declarations embed unescaped quotes in generated Python",
    )),
    pytest.param(15, marks=pytest.mark.xfail(
        strict=True, raises=SyntaxError,
        reason="Chunk declarations embed unescaped quotes in generated Python",
    )),
])
def test_python_output_executes_at_each_level(level):
    assert_preserves_output('value = 6\nprint("result", value * 7)\n', level)


@pytest.mark.parametrize("level", [
    pytest.param(1, marks=pytest.mark.xfail(
        strict=True, raises=SyntaxError,
        reason="Anti-hook prelude lacks a newline before the original code",
    )),
    10,
])
def test_python_anti_hooking_preserves_normal_execution(level):
    assert_preserves_output('value = 6\nprint("result", value * 7)\n', level, True)


def test_python_preserves_indentation_and_removes_comments():
    source = '# heading\nif True:\n    value = 6  # inline comment\n    print("result", value * 7)\n'
    assert_preserves_output(source, 2)


@pytest.mark.xfail(
    strict=True, raises=SyntaxError,
    reason="Regex comment removal treats a hash inside a string as a comment",
)
def test_python_comment_removal_preserves_string_literals():
    assert_preserves_output('value = "#not a comment"\nprint("result", 42)\n', 2)
