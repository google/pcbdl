# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS"BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Kicad Library part importer / exporter.
"""

__all__ = ["KicadPart", "read_kicad_lib", "read_kicad_sch"]

from .base import Part, Pin, Net
from .context import *
from .small_parts import *

import collections
import os
import pprint
import re
import shlex

LIB_PART_RE = re.compile("(DEF.*?ENDDEF)", flags=(re.MULTILINE | re.DOTALL))
REFDES_RE = re.compile("[^0-9]+")
PIN_SPLITTER_RE = re.compile("[^\(\)/\s,]+")

F_MAPPING = {
    0: "refdes",
    1: "value",
    2: "footprint",
    3: "datasheet",
}

DEF_KEYS = "name", "reference", "unused", "text_offset", "draw_pinnumber", "draw_pinname", "unit_count", "units_locked", "option_flag"
PIN_KEYS = "name", "num", "posx", "posy", "length", "direction", "name_text_size", "num_text_size", "unit", "convert", "electrical_type", "pin_type"

SCH_HEADER_RE = re.compile("(EESchema Schematic File Version ?(?P<version>[^\n]*)\n(?P<fields>.*)\$EndDescr)", flags=(re.MULTILINE | re.DOTALL))
SCH_PART_RE = re.compile("(\$Comp.*?\$EndComp)", flags=(re.MULTILINE | re.DOTALL))
SCH_LABEL = re.compile("Text Label (.+)\n(.+)\n")
SCH_JUNCTION = re.compile("Connection (.+)\n")
SCH_WIRE = re.compile("Wire Wire Line\n(.+)\n")

class PartNotFoundException(KeyError):
    pass

class PowerSymbolException(Exception):
    pass

class KicadPart(Part):
    pass

def finditer_with_line_numbers(file_contents, match_re):
    line_number = 1
    prev_start_character = 0

    for match in match_re.finditer(file_contents):
        start_character = match.span()[0]
        line_number += file_contents.count("\n", prev_start_character, start_character)
        yield match, line_number
        prev_start_character = start_character

def tokenize(line):
    s = shlex.shlex(line)
    s.whitespace_split = True
    s.commenters = ''
    s.quotes = '"'
    return tuple(s)

def read_kicad_lib_part(part_match, filename, line_number):
    lines = part_match.group(1).split("\n")

    fields = {}
    pins = []

    for line in lines:
        tokens = tokenize(line)
        if not tokens:
            continue
        name, *args = tokens

        # take stuff out of quotes
        for i,arg in enumerate(args):
            if arg[0] == '"' and arg[-1] == '"':
                args[i] = arg[1:-1]

        if name == "DEF":
            definition = {k:v for k, v in zip(DEF_KEYS, args)}
        elif name.startswith("F"):
            if name != "F":
                args = [name[1:]] + args
                name = "F"

            f_number, text, *rest, field_name = args
            f_number = int(f_number)

            if text:
                if f_number < 4:
                    fields[F_MAPPING[f_number]] = text
                else:
                    fields[field_name] = text
        elif name == "X":
            pin = {k:v for k, v in zip(PIN_KEYS, args)}

            if pin["name"] == "~":
                pin["name"] = "P%s"% pin["num"]
            pin["posx"] = int(pin["posx"])
            pin["posy"] = int(pin["posy"])

            pins.append(pin)
        else:
            #print("Unknown line %r"% line)
            pass

    pins.sort(key=lambda pin: (pin["posx"], -pin["posy"]))

    pcbdl_pins = []
    for pin in pins:
        pin_names = PIN_SPLITTER_RE.findall(pin["name"])
        pin_numbers = PIN_SPLITTER_RE.findall(pin["num"])
        pcbdl_pin = Pin(tuple(pin_numbers), tuple(pin_names))
        pcbdl_pin._kicad_pin = pin
        pcbdl_pins.append(pcbdl_pin)

    refdes_prefix = REFDES_RE.match(fields.pop("refdes")).group(0)

    class_dict = {
        "REFDES_PREFIX": refdes_prefix,
        "value": fields.pop("value", ""),
        "package": fields.pop("footprint", ""),
        "PINS": pcbdl_pins,
        #"fields": fields, # TODO: insert this when ready
    }

    class_dict["__doc__"] = '\n'.join((
        "Part imported from Kicad:",
        "%s:%s" % (filename, line_number),
        "",
        '\n'.join(("%s: %s"% (k, v) for k, v in fields.items())),
    ))

    class_dict["_kicad_definition"] = definition
    class_dict["_kicad_re_match"] = part_match
    class_dict["_kicad_filename"] = filename
    class_dict["_kicad_line_number"] = line_number

    parent_classes = (KicadPart,)
    if refdes_prefix == "R":
        parent_classes += (R,)
    if refdes_prefix == "C":
        parent_classes += (C,)

    return type(definition["name"], parent_classes, class_dict)

def read_kicad_lib(file):
    for match, line_number in finditer_with_line_numbers(file.read(), LIB_PART_RE):
        yield read_kicad_lib_part(match, file.name, line_number)

def apply_orientation(orientation_matrix, coord):
    ox, oy = coord
    x1, y1, x2, y2 = orientation_matrix
    return (
        ox * x1 + oy * x2,
        ox * y1 + oy * y2,
    )

def within(p, e1, e2):
    return e1 <= p <= e2 or e2 <= p <= e1

def point_on_segment(point, line):
    xp, yp = point
    (x1, y1), *_middle_points, (x2, y2) = line

    dxp = x1 - xp
    dyp = y1 - yp
    dxl = x1 - x2
    dyl = y1 - y2

    cross = dxp*dyl - dyp*dxl
    if cross != 0:
        return False

    if xp != x1:
        return within(xp, x1, x2)
    else:
        return within(yp, y1, y2)

def read_kicad_sch_part(part_match, lib_parts, filename, line_number):
    lines = part_match.group(1).split("\n")

    fields = {}

    for line in lines:
        tokens = tokenize(line)
        if not tokens:
            continue
        name, *args = tokens

        # take stuff out of quotes
        for i,arg in enumerate(args):
            if arg[0] == '"' and arg[-1] == '"':
                args[i] = arg[1:-1]

        if name == "F":
            f_number, text, *rest, field_name = args
            f_number = int(f_number)

            if text:
                if f_number < 4:
                    fields[F_MAPPING[f_number]] = text
                else:
                    fields[field_name] = text
        if name == "L":
            part_name, _refdes = args
        if name == "P":
            part_x, part_y = map(int, args)
        else:
            #print("Unknown line %r"% line)
            pass

    orientation_matrix = tuple(map(int, tokenize(lines[-2])))

    try:
        part_class, = [part for part in lib_parts if part._kicad_definition["name"] == part_name]
    except ValueError:
        raise PartNotFoundException(part_name)

    if part_class._kicad_definition["option_flag"] == "P":
        # We shouldn't just plop it down, convert to label instead
        kicad_pin = part_class.PINS[0]._kicad_pin
        rx, ry = apply_orientation(orientation_matrix, (kicad_pin["posx"], kicad_pin["posy"]))
        label_coord = part_x + rx, part_y + ry
        label = label_coord, fields["value"], line_number
        raise PowerSymbolException(label, part_class)

    try:
        instance = part_class(refdes=fields["refdes"], value=fields["value"])
    except Exception:
        raise PartNotFoundException(part_name)
    instance.defined_at = "%s:%d" % (filename, line_number)
    try:
        instance.package = fields["footprint"]
    except KeyError:
        pass

    instance._kicad_pos = (part_x, part_y)
    instance._kicad_orientation_matrix = orientation_matrix

    # Calculate absolute pin positions
    for pin in instance.pins:
        pin._kicad_pos = []
        for fragment in pin._part_class_pin._fragments:
            try:
                kicad_pin = fragment._kicad_pin
            except AttributeError:
                continue
            rx, ry = apply_orientation(orientation_matrix, (kicad_pin["posx"], kicad_pin["posy"]))
            pin._kicad_pos.append((part_x + rx, part_y + ry))

    return instance

def read_kicad_sch(file):
    file_contents = file.read()

    # Parse Header
    header_match = SCH_HEADER_RE.match(file_contents).groupdict()
    header = {"version": header_match["version"], "LIBS": []}
    for line in header_match["fields"].split("\n"):
        if line.startswith("LIBS"):
            header["LIBS"].append(line.split(":", 1)[1])
            continue

        if not line:
            continue

        key, value = line.split(" ", maxsplit=1)
        if value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        header[key] = value
    print(header)

    # Load libraries
    lib_parts = []
    for lib_name in header["LIBS"][-1:]:
        lib_path = os.path.join(os.path.dirname(file.name), lib_name + ".lib")
        lib_file = open(lib_path)
        print("Using lib %s" % lib_path)
        for part in read_kicad_lib(lib_file):
            lib_parts.append(part)

    # Net labels
    net_labels = [] # [((posx, posy), text, line_number), ...]
    for match, line_number in finditer_with_line_numbers(file_contents, SCH_LABEL):
        args, text = match.groups()
        posx, posy, *_ = tokenize(args)
        posx = int(posx)
        posy = int(posy)
        net_labels.append(((posx, posy), text, line_number))

    # Populate parts
    sch_parts = []
    for match, line_number in finditer_with_line_numbers(file_contents, SCH_PART_RE):
        try:
            part_instance = read_kicad_sch_part(match, lib_parts, file.name, line_number)
            sch_parts.append(part_instance)
        except PartNotFoundException:
            pass
        except PowerSymbolException as e:
            label, part = e.args
            net_labels.append(label)
            print("Converting %s to net %r." % (part, label[1]))

    # Net wires
    net_junctions = [] # [(posx, posy), ...]
    for match in SCH_JUNCTION.finditer(file_contents):
        posx, posy = map(int, tokenize(match.groups()[0])[1:])
        net_junctions.append((posx, posy))

    def maybe_split(*line):
        """Return endpoints of the line. In case junctions are on the line, return them too."""
        points = [line[0]]
        for junction in net_junctions:
            if point_on_segment(junction, line):
                points.append(junction)
        points.extend(line[1:])
        return tuple(points)

    net_lines = [] # [((startx, starty), [optional (middlex, middley), ...] (endx, endy))]
    for match in SCH_WIRE.finditer(file_contents):
        startx, starty, endx, endy = map(int, tokenize(match.groups()[0]))
        net_lines.append(maybe_split((startx, starty), (endx, endy)))

    net_bundles = [] # [(net_lines, net_points(#just line endpoints)), ...]
    while net_lines:
        starting_line = net_lines.pop()
        current_net_lines = set((starting_line,))
        current_net_points = set(starting_line)
        net_bundles.append((current_net_lines, current_net_points))

        while True:
            found_others = False
            for point in tuple(current_net_points):
                for other_line in net_lines:
                    if point_on_segment(point, other_line):
                        net_lines.remove(other_line)
                        current_net_lines.add(other_line)
                        current_net_points.update(other_line)
                        found_others = True
            if not found_others:
                break

    # See what pins and labels are on each bundle
    grouped_nets = {} # net_name: (line_number, [pin_group1, pin_group2])
    for net_lines, net_points in net_bundles:
        # do we have a name for this
        name = None
        line_number = None
        for line in net_lines:
            for label in net_labels:
                label_pos, _, _ = label
                if point_on_segment(label_pos, line):
                    _, name, line_number = label
                    break
            if name:
                break

        # gather pins
        pins = set()
        for net_point in net_points:
            for part in sch_parts:
                for pcbdl_pin in part.pins:
                    for kicad_pin_pos in pcbdl_pin._kicad_pos:
                        if kicad_pin_pos == net_point:
                            pins.add(pcbdl_pin)
                            break

        if name in grouped_nets:
            grouped_nets[name][1].append(pins)
        else:
            grouped_nets[name] = (line_number, [pins])

    pprint.pprint(grouped_nets)

    # Actually create Net instances
    sch_nets = set()
    for name, (line_number, pin_groups) in grouped_nets.items():
        if name is None:
            # We need a new net for each
            for pin_group in pin_groups:
                n = Net()
                n.defined_at = "%s:%d" % (file.name, 0)
                n_group = n
                for pin in pin_group:
                    if pin._net:
                        #assert pin._net == n
                        pass #TODO: this is bad
                    else:
                        n_group = n_group << pin
                sch_nets.add(n)
            continue
        else:
            # One big net for everything named the same
            n = Net(name)
            n.defined_at = "%s:%d" % (file.name, line_number)
            for pin_group in pin_groups:
                n_group = n
                for pin in pin_group:
                    if pin._net:
                        #assert pin._net == n
                        pass  #TODO: this is bad
                    else:
                        n_group = n_group << pin
            sch_nets.add(n)

