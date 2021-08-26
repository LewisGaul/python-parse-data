import enum
from pprint import pprint

import yaml

from data_reader import *

yaml_data = """
        - name: abspath
          description: Small utility to convert relative to absolute paths
          link: https://github.com/foo/bar
          runs-on: [server]
          contributors: [PersonA]
          maintained: false
          languages: [python3]
        
        - name: collection/
          description: Collection of scripts
          link: None
          runs- on: []
          contributors: [SomeDude]
          maintained: true
          languages: [python3]
    """

data = yaml.safe_load(yaml_data)

class RunsOn(enum.Enum):
    SERVER = "server"
    LOCAL = "local"
    WEB = "web"

class Language(enum.Enum):
    PYTHON = "python"
    BASH = "bash"
    PERL = "perl"
    ELM = "elm"
    JAVASCRIPT = "javascript"
    C = "c"


schema = List(
    UserClass["Entry"](
        name=Str.restrict(max_len=20),
        description=Str.restrict(max_len=200),
        link=Str.restrict(regex="https?://.+") | None,
        usage=Str | None,
        # runs_on=List(RunsOn),
        contributors=List(Str),
        maintained=Bool,
        notes=Str | None,
        # languages=List(Language),
        tags=List(Str),
        obsolete=Bool,
    ).defaults(usage=None, notes=None, languages=list, tags=list, obsolete=False)
)

parsed = parse_node(schema, data)
pprint(parsed)
# [Entry(name='abspath',
#        description='Small utility to convert relative to absolute paths',
#        link='https://github.com/foo/bar',
#        usage=None,
#        contributors=['PersonA'],
#        maintained=False,
#        notes=None,
#        tags=[],
#        obsolete=False),
#  Entry(name='collection/',
#        description='Collection of scripts',
#        link='None',
#        usage=None,
#        contributors=['SomeDude'],
#        maintained=True,
#        notes=None,
#        tags=[],
#        obsolete=False)]
