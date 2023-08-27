import re
from pathlib import Path


class CColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def cprint(text: str, color: CColors):
    print(f"{color}{text}{CColors.ENDC}")


"""
Find templates extended, capturing the filename 
{% extends "template_name.html" %}
"""
extends_re = re.compile(r'{% extends "(.*)" %}', re.DOTALL)
"""
Find blocks, capturing block variable name and block inner content
{% block title %}
    <title>{{ title }}</title>
{% endblock title %}
"""
blocks_re = re.compile(r"{% block (.\S+) %}(.*?){% endblock (.\S+) %}", re.DOTALL)
"""
Find and capture variables
{{ variable }}
"""
variables_re = re.compile(r"{{\s?(\S+)\s?}}", re.DOTALL)


def render_template(template_path: Path, dest_path: Path = None, **kwargs) -> str:
    with template_path.open("r") as f:
        template = f.read()

    extends = extends_re.search(
        template,
    )

    print(extends)
    if extends:
        parent_path = template_path.parent / extends.groups()[0]
        parent_rendered = render_template(parent_path, **kwargs)

    return ""
