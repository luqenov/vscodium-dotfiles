"""Validate JSONC and edit a root property without rewriting unrelated comments."""

import json
import re
from dataclasses import dataclass


_TOKEN = re.compile(
    r'(?P<space>\s+)|(?P<line>//[^\r\n]*)|(?P<block>/\*[\s\S]*?\*/)|'
    r'(?P<string>"(?:[^"\\\x00-\x1f]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*")|'
    r'(?P<number>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)|'
    r'(?P<literal>true|false|null)|(?P<punct>[{}\[\]:,])'
)


@dataclass(frozen=True)
class Token:
    value: str
    start: int
    end: int


def tokens(text):
    result = []
    offset = 0
    while offset < len(text):
        match = _TOKEN.match(text, offset)
        if match is None:
            raise ValueError(f'Invalid JSONC at character {offset + 1}')
        if match.lastgroup not in ('space', 'line', 'block'):
            result.append(Token(match.group(), offset, match.end()))
        offset = match.end()
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def loads(text):
    items = tokens(text)
    normalized = ' '.join(
        token.value for index, token in enumerate(items)
        if not (token.value == ',' and 0 < index < len(items) - 1
                and items[index - 1].value not in ('{', '[', ',', ':')
                and items[index + 1].value in (']', '}'))
    )
    return json.loads(normalized, object_pairs_hook=_unique_object)


def require_type(text, expected):
    value = loads(text)
    if not isinstance(value, expected):
        raise ValueError(f'Expected a JSONC {expected.__name__}')
    return value

