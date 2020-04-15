#!/usr/bin/env python3

# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Normalizes a third party Allegro netlist file so it's easier to diff."""

import re

def _sort_lines_and_components(lines):
    lines = lines.split("\n") # split lines
    lines = [line.rsplit(";", 1) for line in lines] # look at the components
    for line in lines: # split and sort components
        components = line[1].strip().split()
        components.sort()
        line[1] = ' '.join(components)
    lines.sort()
    return '\n'.join('; '.join(line) for line in lines)

def _normalize_nets(netlist):
    # normalizes jelly bean components: removes pin numbers
    netlist = re.sub(r"(([RLC]|FB)\d+\w*)\.\w+", r"\1", netlist)

    # unnamed nets
    netlist = re.sub(r"UNNAMED\w+\s*;", "ZZZUNNAMED ;", netlist) # google style
    netlist = re.sub(r"N\d{5,}\s*;", "ZZZUNNAMED ;", netlist) # odm style
    netlist = re.sub(r"ANON_NET\w+\s*;", "ZZZUNNAMED ;", netlist) # pcbdl style

    return _sort_lines_and_components(netlist)

def _add_quote(s):
    """Add quotes on a package unless already quoted."""
    s = re.sub("'(.*)'",r"\1", s)
    return f"'{s}'"

def _normalize_packages(packages, normalize_props):
    packages = [package.split(";") for package in packages.split("\n")]
    for package in packages:
        props = package[0].split("!")
        props = [_add_quote(prop.strip()) for prop in props]
        if normalize_props:
            # cut the rest (part number, values?, tolerance?)
            props = props[:1]
        package[0] = ' ! '.join(props)
    packages = '\n'.join(' ; '.join(package) for package in packages)
    return _sort_lines_and_components(packages)

def normalize(contents, normalize_header=False, normalize_part_props=False):
    # unwordwrap
    contents = re.sub(r",\n?\s*", r"", contents)

    header, packages, netlist = [group.strip() for group in
        re.match(r"(.*)\$PACKAGES*(.*)\$NETS(.*)\$END.*", contents, flags=re.DOTALL).groups()
    ]

    if normalize_header:
        header = "(NETLIST)\n(normalized header)"
    netlist = _normalize_nets(netlist)
    packages = _normalize_packages(packages, normalize_part_props)

    return f"{header}\n\n$PACKAGES\n{packages}\n\n$NETS\n{netlist}\n$END."

if __name__=="__main__":
    import sys
    contents = open(sys.argv[1], "r").read()
    print(normalize(contents))
