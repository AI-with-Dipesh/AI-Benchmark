from __future__ import annotations



from aibenchmark.app.validation import (
    validate_json_schema,
    validate_model_name,
    validate_path_safety,
)


def test_validate_model_name_rejects_invalid_chars():
    report = validate_model_name("bad name!")
    assert report.valid is False


def test_validate_model_name_accepts_valid():
    report = validate_model_name("valid-name.v2")
    assert report.valid is True


def test_validate_path_safety_rejects_traversal(tmp_path):
    report = validate_path_safety("/etc/passwd", base_dir=tmp_path)
    assert report.valid is False
    assert report.issues


def test_validate_path_safety_invalid_exception(tmp_path):
    very_long = "a" * 500
    report = validate_path_safety(very_long, base_dir=tmp_path)
    assert report.valid is False


def test_validate_json_schema_non_dict_returns_early():
    report = validate_json_schema("not-a-dict", {"type": "object"}, label="test")
    assert report.valid is False
    assert report.issues


def test_validate_json_schema_array_type_mismatch():
    report = validate_json_schema("not-a-list", {"type": "array"}, label="test")
    assert report.valid is False
    assert report.issues


def test_validate_json_schema_minimum_violation():
    report = validate_json_schema(5, {"type": "integer", "minimum": 10}, label="test")
    assert report.valid is False
    assert any("minimum" in str(i.message) for i in report.issues)


def test_validate_json_schema_maximum_violation():
    report = validate_json_schema(15, {"type": "integer", "maximum": 10}, label="test")
    assert report.valid is False
    assert any("maximum" in str(i.message) for i in report.issues)


def test_validate_json_schema_enum_mismatch():
    report = validate_json_schema("c", {"type": "string", "enum": ["a", "b"]}, label="test")
    assert report.valid is False
    assert any("enum" in str(i.message) for i in report.issues)


def test_validate_json_schema_valid_value():
    report = validate_json_schema("a", {"type": "string", "enum": ["a", "b"]}, label="test")
    assert report.valid is True


def test_validate_json_schema_object_required_missing():
    report = validate_json_schema({"a": 1}, {"type": "object", "required": ["a", "b"]}, label="test")
    assert report.valid is False
    assert report.issues
