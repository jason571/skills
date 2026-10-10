"""Read saved plan data without guessing missing structure or changing values."""
import json
import math


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key; resolve the conflicting field explicitly")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("plan JSON must not contain NaN or Infinity")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("plan JSON number exceeds the finite numeric range")
    return number


def load_plan_json(raw):
    if len(raw) > 512 * 1024:
        raise ValueError("plan JSON exceeds 512 KiB")
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    options = {"object_pairs_hook": unique_object, "parse_constant": reject_constant,
               "parse_float": finite_float}
    try:
        return json.loads(text, **options), False
    except json.JSONDecodeError as error:
        if not error.msg.startswith("Invalid control character"):
            raise ValueError(f"plan JSON syntax error at line {error.lineno}, column {error.colno}: {error.msg}; correct this location or use edit_workspace.json_files with native JSON") from error
        # Accept only raw line breaks/tabs in strings. No quote/comma/key repair,
        # eval, replacement of prose, or relaxation of content validation.
        if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
            raise ValueError("plan JSON contains unsupported raw control characters") from error
        try:
            return json.loads(text, strict=False, **options), True
        except json.JSONDecodeError as invalid:
            raise ValueError(f"plan JSON syntax error at line {invalid.lineno}, column {invalid.colno}: {invalid.msg}; input was not changed") from invalid
