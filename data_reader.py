__all__ = (
    "Bool",
    "Float",
    "Int",
    "List",
    "Dict",
    "Str",
    "UserClass",
    "UserEnum",
    "parse_data",
    "ParseError",
)

import dataclasses as dc
import enum
import re


class _SchemaTypeMeta(type):
    def __or__(cls, other):
        types = [cls]
        if type(other) is Union:
            types.extend(other.types)
        else:
            types.append(other)
        return Union(*types)

    def __getitem__(cls, item):
        if hasattr(cls, "named_cls"):
            if not isinstance(item, str):
                raise TypeError(f"{cls.__name__} name must be a string")
            return cls.named_cls(item)
        else:
            raise TypeError(f"'{cls}' is not subscriptable")


class _SchemaType(metaclass=_SchemaTypeMeta):
    def __or__(self, other):
        types = [self]
        if type(other) is Union:
            types.extend(other.types)
        else:
            types.append(other)
        return Union(*types)


class Any(_SchemaType):

    def __init__(self):
        raise TypeError(f"Cannot instantiate schema type {type(self)}")


class Bool(_SchemaType):

    type = bool

    def __init__(self):
        raise TypeError(f"Cannot instantiate schema type {type(self)}")


class Int(_SchemaType):

    type = int

    def __init__(self):
        raise TypeError(f"Cannot instantiate schema type {type(self)}")


class Float(_SchemaType):

    type = float

    def __init__(self):
        raise TypeError(f"Cannot instantiate schema type {type(self)}")


class Str(_SchemaType):

    type = str

    def __init__(self, *, _min_len=None, _max_len=None, _regex=None):
        """Not recommended to instantiate - cleaner to use '.restrict()'."""
        self.min_len = _min_len
        self.max_len = _max_len
        self.regex = _regex

    @classmethod
    def restrict(cls, *, min_len=None, max_len=None, regex=None):
        return cls(_min_len=min_len, _max_len=max_len, _regex=regex)


class List(_SchemaType):

    type = list

    def __init__(self, inner_type):
        self.inner_type = inner_type


class Dict(_SchemaType):

    type = dict

    def __init__(self, **fields):
        self.fields = fields
        self._defaults = {}

    def defaults(self, **fields):
        self._defaults = fields
        return self


class Union(_SchemaType):
    def __init__(self, *types):
        self.types = types


class _NamedUserClass(_SchemaType):
    def __init__(self, name: str):
        self.name = name
        self.fields = {}
        self._defaults = {}
        self.cls = None

    def __call__(self, **fields):
        self.fields = fields
        self.cls = dc.make_dataclass(self.name, fields.keys())
        return self

    def defaults(self, **fields):
        self._defaults = fields
        for f in dc.fields(self.cls):
            if f.name in self._defaults:
                dflt = self._defaults[f.name]
                if callable(dflt):
                    f.default_factory = dflt
                else:
                    f.default = dflt
        return self


class UserClass(_SchemaType):

    named_cls = _NamedUserClass

    def __init__(self):
        raise TypeError(f"Cannot instantiate {type(self)}")


class _NamedUserEnum(_SchemaType):
    def __init__(self, name: str):
        self.name = name
        self.fields = {}
        self._defaults = {}
        self.cls = None

    def __call__(self, *fields):
        self.fields = [f.upper().replace("-", "_") for f in fields]
        self.cls = enum.Enum(self.name, self.fields)
        self.cls.__repr__ = self.cls.__str__
        return self


class UserEnum(_SchemaType):

    named_cls = _NamedUserEnum

    def __init__(self):
        raise TypeError(f"Cannot instantiate {type(self)}")


class ParseError(Exception):
    pass


def parse_data(schema, node):
    match schema:
        case None:
            if node is not None:
                raise ParseError(f"Expected 'None', got {type(node)}")
            return node
        case Str(min_len=min_len, max_len=max_len, regex=regex):
            if type(node) != str:
                raise ParseError(f"Expected str, got {type(node)}")
            if min_len is not None and len(node) < min_len:
                raise ParseError(f"String {node!r} exceeds min len of {min_len}")
            if max_len is not None and len(node) > max_len:
                raise ParseError(f"String {node!r} exceeds max len of {max_len}")
            if regex is not None and not re.fullmatch(regex, node):
                raise ParseError(f"String {node!r} failed to match regex {regex!r}")
            return node
        case List(inner_type=inner_type):
            if type(node) != list:
                raise ParseError(f"Expected list, got {type(node)}")
            result = []
            for item in node:
                try:
                    result.append(parse_data(inner_type, item))
                except ParseError as e:
                    raise ParseError(f"Error in list item {len(result)}") from e
            return result
        case Dict(fields=fields, _defaults=defaults):
            if type(node) != dict:
                raise ParseError(f"Expected dict, got {type(node)}")
            node = {k.replace("-", "_"): v for k, v in node.items()}
            d = {}
            for f, t in fields.items():
                try:
                    node_field = node[f]
                except KeyError:
                    if f in defaults:
                        dflt = defaults[f]
                        if callable(dflt):
                            dflt = dflt()
                        d[f] = dflt
                    else:
                        raise ParseError(f"Missing field {f!r}") from None
                else:
                    try:
                        d[f] = parse_data(t, node_field)
                    except ParseError as e:
                        raise ParseError(f"Error parsing field {f!r}") from e
            return d
        case Union(types=types):
            for t in types:
                try:
                    return parse_data(t, node)
                except ParseError:
                    pass
            raise ParseError(f"Failed to parse {type(node)} into union of {types}")
        case _NamedUserClass(name=name, fields=fields, _defaults=defaults, cls=cls):
            d = parse_data(Dict(**fields).defaults(**defaults), node)
            return cls(**d)
        case _NamedUserEnum(name=name, cls=cls):
            enum_name = node.upper().replace("-", "_")
            if enum_name in cls.__members__:
                return getattr(cls, enum_name)
            raise ParseError(f"Failed to parse '{node}' into enum '{cls.__name__}'")
        case _SchemaTypeMeta():
            if schema is not Any and type(node) != schema.type:
                raise ParseError(f"Expected type {schema.type!r}, got {type(node)}")
            return node
        case enum.EnumMeta():
            enum_values = {x.value: x for x in schema}
            if node in enum_values:
                return enum_values[node]
            else:
                raise ParseError(
                    f"Expected value from enum {schema.__name__!r}, got '{node}'"
                )
        case _:
            raise ParseError(f"Unsupported match pattern: {schema}")
