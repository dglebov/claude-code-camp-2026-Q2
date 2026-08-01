"""Minimal `.env` loader.

Ruby's side uses the `dotenv` gem. Rather than add `python-dotenv` we hand-roll the small
subset we need, keeping PyYAML as the only third-party runtime dependency.

Mirrors `Dotenv.load` semantics: variables already present in the environment are NOT
overwritten.

Supported: `KEY=value`, `export KEY=value`, single/double quoted values, `#` comment lines and
blank lines. Not supported: inline trailing comments, multi-line values, variable interpolation.
"""

import os

_EXPORT_PREFIX = "export "
_QUOTES = ("'", '"')


def load_env_file(path):
    """Load `KEY=value` pairs from `path` into ``os.environ`` without overriding existing vars."""
    with open(path, encoding="utf-8") as handle:
        for raw_line in handle:
            key, value = _parse_line(raw_line)
            if key is not None and key not in os.environ:
                os.environ[key] = value


def _parse_line(raw_line):
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None, None

    if line.startswith(_EXPORT_PREFIX):
        line = line[len(_EXPORT_PREFIX) :].lstrip()

    key, separator, value = line.partition("=")
    if not separator:
        return None, None

    key = key.strip()
    if not key:
        return None, None

    return key, _unquote(value.strip())


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in _QUOTES:
        return value[1:-1]
    return value
