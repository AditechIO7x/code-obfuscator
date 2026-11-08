# Focused production tests

Run from the repository root:

```sh
python -m pip install -r requirements-test.txt
python -m pytest -q -rx
```

The API tests cover HTTP validation, all 12 language dispatch targets, level
boundaries, anti-hooking forwarding/defaults, response metadata (including
Unicode), and transform failures. Dispatch tests mock only the transformation;
a separate real request executes the returned Python in an isolated subprocess.

Python tests execute generated code at every supported level, covering encoding,
renaming, compression, XOR and nested wrappers. Subprocesses use only fixed test
fixtures and have a five-second timeout.

Four strict expected failures document three existing production defects:

- Levels 14 and 15 generate chunk strings without escaping their embedded quotes.
- The anti-hooking prelude joins directly to source without a separating newline
  (level 1 reproduces this; level 10 has an existing leading newline and passes).
- Comment removal mistakes `#` within a string for a comment.

These tests require a `SyntaxError` to be expected failures. Unexpected success
fails the suite, so remove the markers when the production defects are fixed.
Production behavior is unchanged. Executable output for other languages is not
covered by this focused suite; their routing is covered, not their semantics.
