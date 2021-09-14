import enum
import logging
import pathlib
from pprint import pprint
from typing import Optional, Tuple

import yaml

import data_reader as dr

YAML_PATH = pathlib.Path(__file__).parent / "cli.yaml"

with open(YAML_PATH) as f:
    data = yaml.safe_load(f)


class ArgType(str, enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    FLAG = "flag"
    TEXT = "text"

    def __repr__(self):
        return str(self)


arg_schema = dr.UserClass["Arg"](
    name=dr.Str.restrict(regex=r"[\w-]+"),
    help=dr.Str,
    default=dr.Any,
    type=ArgType,
    enum=dr.List(dr.Str.restrict(regex=r"\w+")) | None,
    positional=dr.Bool,
).defaults(default=None, type=ArgType.STRING, enum=None, positional=False)

node_schema = dr.UserClass["Node"](
    keyword=dr.Str.restrict(regex=r"[\w-]+"),
    help=dr.Str,
    command=dr.Str | None,
    args=dr.List(arg_schema),
    subtree=None,  # circular - set after
).defaults(command=None, args=list, subtree=None)

SubtreeSchema = dr.List(node_schema)
node_schema.fields["subtree"] = SubtreeSchema | None

schema = dr.UserClass["RootNode"](
    welcome=dr.Str | None,
    subtree=SubtreeSchema,
).defaults(welcome=None)


Arg = arg_schema.cls
Node = node_schema.cls
RootNode = schema.cls


def get_next_node(node: Node, kw: str) -> Optional[Node]:
    if node.subtree is None:
        return None
    return {n.keyword: n for n in node.subtree}.get(kw)


def get_final_node(root_node: RootNode, command: str) -> Tuple[Node, str, str]:
    node = root_node
    full_kws = []
    rem_command = command.split()
    while node.subtree and rem_command:
        kw = rem_command[0]
        next_node = get_next_node(node, kw)
        if next_node:
            node = next_node
            full_kws.append(node.keyword)
            rem_command.pop(0)
        else:
            break
    return node, " ".join(full_kws), " ".join(rem_command)


def fmt_arg(arg: Arg) -> str:
    match arg.type:
        case ArgType.INTEGER:
            qual = "int"
        case ArgType.FLOAT:
            qual = "float"
        case ArgType.STRING:
            qual = "str"
        case ArgType.TEXT:
            qual = "text"
        case _:
            qual = None
    inner = arg.name
    if qual:
        inner += f":{qual}"
    if arg.default:
        inner += f"={arg.default}"
    if arg.positional:
        return f"<{inner}>"
    else:
        return f"[{inner}]"


def node_help(node: Node):
    if node.subtree:
        for subnode in node.subtree:
            print(f"{subnode.keyword:<15s} {subnode.help}")
    if getattr(node, "command", None):
        arg_strs = [fmt_arg(a) for a in node.args]
        print(" ".join(arg_strs + ["<CR>"]))


def node_help_long(node: Node):
    print(node.help)
    print()
    if node.subtree:
        for subnode in node.subtree:
            print(f"{subnode.keyword:<15s} {subnode.help}")
        print()
    if getattr(node, "command", None):
        print(f"Command: {node.command!r}")
        for arg in node.args:
            print(f"{fmt_arg(arg):<15s} {arg.help}")
        print()


parsed = dr.parse_node(schema, data)
# pprint(parsed)

# Mainloop
if parsed.welcome:
    print(parsed.welcome)
while True:
    try:
        cmd = input("(cli)# ")
        logging.debug("Got cmd: %r", cmd)
        end_node, matched_cmd, rem_cmd = get_final_node(parsed, cmd)
        logging.debug("Matched: %r", matched_cmd)
        logging.debug("Remaining: %r", rem_cmd)
        if rem_cmd == "?":
            node_help(end_node)
        if rem_cmd == "??":
            node_help_long(end_node)
    except Exception:
        print("Don't know how to handle that command!")
