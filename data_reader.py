__all__ = ("Bool", "Int", "List", "Dict", "Str", "UserClass", "parse_node")

import dataclasses as dc
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
        if cls is UserClass:
            if not isinstance(item, str):
                raise TypeError("UserClass name must be a string")
            return _NamedUserClass(item)
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


class Bool(_SchemaType):

    type = bool

    def __init__(self):
        raise TypeError(f"Cannot instantiate schema type {type(self)}")


class Int(_SchemaType):

    type = int

    def __init__(self):
        raise TypeError(f"Cannot instantiate schema type {type(self)}")


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


class Str(_SchemaType):

    type = str

    def __init__(self, *, _min_len=None, _max_len=None, _regex=None):
        """Not recommended to instantiate - cleaner to use '.restrict()'."""
        self.min_len = None
        self.max_len = None
        self.regex = None

    @classmethod
    def restrict(cls, *, min_len=None, max_len=None, regex=None):
        return cls(_min_len=min_len, _max_len=max_len, _regex=regex)


class Union(_SchemaType):
    def __init__(self, *types):
        self.types = types


class UserClass(_SchemaType):
    def __init__(self):
        raise TypeError(f"Cannot instantiate {type(self)}")


class _NamedUserClass(_SchemaType):
    def __init__(self, name: str):
        self.name = name
        self.fields = {}
        self._defaults = {}

    def __call__(self, **fields):
        self.fields = fields
        return self

    def defaults(self, **fields):
        self._defaults = fields
        return self


def parse_node(schema, node):
    match schema:
        case None:
            if node is not None:
                raise ValueError("Expected 'None'")
            return node
        case Bool():
            if type(node) != bool:
                raise ValueError("Expected bool")
            return node
        case Int():
            if type(node) != int:
                raise ValueError("Expected int")
            return node
        case Str(min_len=min_len, max_len=max_len, regex=regex):
            if type(node) != str:
                raise ValueError("Expected str")
            if min_len is not None and len(node) < min_len:
                raise ValueError(f"String exceeds min len of {min_len}")
            if max_len is not None and len(node) > max_len:
                raise ValueError(f"String exceeds max len of {max_len}")
            if regex is not None and not re.fullmatch(regex, node):
                raise ValueError(f"String failed to match regex {regex!r}")
            return node
        case List(inner_type=inner_type):
            if type(node) != list:
                raise ValueError("Expected list")
            result = []
            for item in node:
                try:
                    result.append(parse_node(inner_type, item))
                except ValueError as e:
                    raise ValueError(f"Error in list item {len(result)}") from e
            return result
        case Dict(fields=fields, _defaults=defaults):
            if type(node) != dict:
                raise ValueError("Expected dict")
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
                        raise ValueError(f"Missing field {f!r}") from None
                else:
                    try:
                        d[f] = parse_node(t, node_field)
                    except ValueError as e:
                        raise ValueError(f"Error parsing field {f!r}") from e
            return d
        case Union(types=types):
            for t in types:
                try:
                    return parse_node(t, node)
                except ValueError:
                    pass
            raise ValueError(f"Failed to parse into union of {types}")
        case _NamedUserClass(name=name, fields=fields, _defaults=defaults):
            d = parse_node(Dict(**fields).defaults(**defaults), node)
            return dc.make_dataclass(name, fields.keys())(**d)
        case _SchemaTypeMeta():
            if type(node) != schema.type:
                raise ValueError(f"Expected type {schema.type!r}")
            return node
        case _:
            raise RuntimeError(f"Unsupported match pattern: {schema}")
