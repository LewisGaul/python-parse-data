import enum

import pytest as pytest

import data_reader as dr


class TestParseSuccess:
    def test_parse_none(self):
        assert dr.parse_node(None, None) is None

    def test_parse_int(self):
        assert dr.parse_node(dr.Int, 1) == 1

    def test_parse_float(self):
        assert dr.parse_node(dr.Float, 1.1) == 1.1

    def test_parse_bool(self):
        assert dr.parse_node(dr.Bool, True) is True

    def test_parse_str(self):
        assert dr.parse_node(dr.Str, "hello") == "hello"

    def test_parse_str_restrict(self):
        schema = dr.Str.restrict(min_len=5, max_len=5, regex="he.*")
        assert dr.parse_node(schema, "hello") == "hello"

    def test_parse_list(self):
        assert dr.parse_node(dr.List(dr.Int), [1, 2, 3]) == [1, 2, 3]

    def test_parse_dict(self):
        schema = dr.Dict(foo=dr.Int, bar_baz=dr.Bool)
        in_data = {"foo": 1, "bar-baz": False, "extra": "ignored"}
        assert dr.parse_node(schema, in_data) == {"foo": 1, "bar_baz": False}

    def test_parse_dict_defaults(self):
        schema = dr.Dict(foo=dr.Int, bar_baz=dr.Bool).defaults(foo=0)
        in_data = {"bar-baz": False}
        assert dr.parse_node(schema, in_data) == {"foo": 0, "bar_baz": False}

    def test_parse_union(self):
        schema = dr.List(dr.Union(dr.Int, dr.Str, None))
        in_data = [0, None, "n", "no", "none"]
        assert dr.parse_node(schema, in_data) == [0, None, "n", "no", "none"]

    def test_parse_user_class(self):
        schema = dr.UserClass["Cls"](foo=dr.Int, bar_baz=dr.Bool)
        in_data = {"foo": 1, "bar-baz": False, "extra": "ignored"}
        assert dr.parse_node(schema, in_data) == schema.cls(foo=1, bar_baz=False)

    def test_parse_enum(self):
        class MyEnum(enum.Enum):
            A = "a"
            B = "b"

        assert dr.parse_node(MyEnum, "a") == MyEnum.A


class TestParseError:
    def test_parse_none(self):
        with pytest.raises(dr.ParseError):
            dr.parse_node(None, "")

    def test_parse_int(self):
        with pytest.raises(dr.ParseError):
            dr.parse_node(dr.Int, "")

    def test_parse_float(self):
        with pytest.raises(dr.ParseError):
            dr.parse_node(dr.Float, "")

    def test_parse_bool(self):
        with pytest.raises(dr.ParseError):
            dr.parse_node(dr.Bool, "")

    def test_parse_str(self):
        with pytest.raises(dr.ParseError):
            dr.parse_node(dr.Str, 1)

    def test_parse_str_restrict(self):
        for schema in [
            dr.Str.restrict(min_len=6),
            dr.Str.restrict(max_len=4),
            dr.Str.restrict(regex="ello"),
        ]:
            with pytest.raises(dr.ParseError):
                dr.parse_node(schema, "hello")

    def test_parse_list(self):
        with pytest.raises(dr.ParseError):
            dr.parse_node(dr.List(dr.Int), [1, ""])

    def test_parse_dict(self):
        # Missing field
        with pytest.raises(dr.ParseError):
            dr.parse_node(dr.Dict(foo=dr.Int), {})
        # Wrong type
        with pytest.raises(dr.ParseError):
            dr.parse_node(dr.Dict(foo=dr.Int), [])

    def test_parse_union(self):
        schema = dr.List(dr.Union(dr.Int, dr.Str, None))
        in_data = [0, None, "n", "no", "none", False]
        with pytest.raises(dr.ParseError):
            dr.parse_node(schema, in_data)

    def test_parse_enum(self):
        class MyEnum(enum.Enum):
            A = "a"
            B = "b"

        with pytest.raises(dr.ParseError):
            dr.parse_node(MyEnum, "A")
