import enum
from pprint import pprint

import yaml

import data_reader as dr

yaml_data = """
- name: abspath
  description: Small utility to convert relative to absolute paths
  link: https://github.com/foo/bar
  runs-on: [server]
  contributors: [PersonA]
  maintained: false
  languages: [python]

- name: collection/
  description: Collection of scripts
  link: null
  runs-on: []
  contributors: [SomeDude]
  maintained: true
  languages: [python]
"""

data = yaml.safe_load(yaml_data)


class Language(str, enum.Enum):
    PYTHON = "python"
    BASH = "bash"
    PERL = "perl"
    ELM = "elm"
    JAVASCRIPT = "javascript"
    C = "c"

    def __repr__(self):
        return str(self)


schema = dr.List(
    dr.UserClass["Entry"](
        name=dr.Str.restrict(max_len=20),
        description=dr.Str.restrict(max_len=200),
        link=dr.Str.restrict(regex="https?://.+") | None,
        usage=dr.Str | None,
        runs_on=dr.List(
            dr.UserEnum["RunsOn"]("server", "local", "web")
        ),
        contributors=dr.List(dr.Str),
        maintained=dr.Bool,
        notes=dr.Str | None,
        languages=dr.List(
            dr.UserEnum["Language"](
                "python", "bash", "perl", "elm", "javascript", "c"
            )
        ),
        tags=dr.List(dr.Str),
        obsolete=dr.Bool,
    ).defaults(usage=None, notes=None, languages=list, tags=list, obsolete=False)
)

parsed = dr.parse_data(schema, data)
pprint(parsed)
# [Entry(name='abspath',
#        description='Small utility to convert relative to absolute paths',
#        link='https://github.com/foo/bar',
#        usage=None,
#        runs_on=[RunsOn.SERVER],
#        contributors=['PersonA'],
#        maintained=False,
#        notes=None,
#        languages=[Language.PYTHON],
#        tags=[],
#        obsolete=False),
#  Entry(name='collection/',
#        description='Collection of scripts',
#        link=None,
#        usage=None,
#        runs_on=[],
#        contributors=['SomeDude'],
#        maintained=True,
#        notes=None,
#        languages=[Language.PYTHON],
#        tags=[],
#        obsolete=False)]
