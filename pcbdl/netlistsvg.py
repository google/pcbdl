# Copyright 2019 Google LLC
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

from .base import Part, PartInstancePin, Net
from .context import *
import pcbdl.small_parts as small_parts

import collections
import logging
import json
import os
import re
import subprocess
import tempfile

"""Renders our circuit into svg with the help of netlistsvg."""
__all__ = ["generate_svg", "SVGPage"]

NETLISTSVG_LOCATION = os.path.expanduser(
    os.environ.get("NETLISTSVG_LOCATION", "~/netlistsvg"))

NET_REGEX_ALL = ".*"

class SVGNet(object):
    def __init__(self, instance, schematic_page):
        self.instance = instance
        self.schematic_page = schematic_page

    current_node_number = -1
    @classmethod
    def get_next_node_number(cls):
        cls.current_node_number += 1
        return cls.current_node_number

    def categorize_groups(self):
        self.grouped_connections = []

        for original_group in self.instance.grouped_connections:
            group = list(original_group) # make a copy so we can fragment it
            group_pin_count = sum(len(pin.part.pins) for pin in group)
            self.grouped_connections.append(group)

            if self.schematic_page.airwires < 2:
                continue

            #if group_pin_count < 40:
                #continue

            first_big_part = None
            for pin in original_group:
                if len(pin.part.pins) <= 3:
                    # part is too small, probably should stay here
                    continue

                if first_big_part is None:
                    first_big_part = pin.part
                    continue

                if pin.part is not first_big_part:
                    # too many big parts here, move this one out
                    #print("Too many big parts in %s group %r, moving %r out" % (self.instance.name, group, pin))
                    group.remove(pin)
                    self.grouped_connections.append((pin,))


        self.node_numbers = [self.get_next_node_number()
            for group in self.grouped_connections]

    def _find_group(self, pin):
        if not hasattr(self, "node_numbers"):
            self.categorize_groups()

        for i, group in enumerate(self.grouped_connections):
            if pin in group:
                return i, group

        raise ValueError("Can't find pin %s on %s" % (pin, self.instance))

    def get_other_pins_in_group(self, pin):
        _, group = self._find_group(pin)
        return group

    def get_node_number(self, pin):
        group_idx, _ = self._find_group(pin)

        if self.schematic_page.airwires == 0:
            return self.node_numbers[0]
        return self.node_numbers[group_idx]

class SVGPart(object):
    SKIN_MAPPING = { # pcbdl_class: (skin_alias_name, pin_names, is_symmetric, is_rotatable)
        # more specific comes first
        small_parts.R:   ("r_", "AB", True, True),
        small_parts.C:   ("c_", "AB", True, True),
        small_parts.L:   ("l_", "AB", True, True),
        small_parts.LED: ("d_led_", "+-", False, True),
        small_parts.D:   ("d_", "+-", False, True),
    }
    SKIN_MAPPING_INSTANCES = tuple(SKIN_MAPPING.keys())

    def __init__(self, part, schematic_page):
        self.part = part
        self.schematic_page = schematic_page

        self.svg_type = part.refdes
        self.is_skinned = False
        self.skin_pin_names = ()
        self.is_symmetric = False
        self.is_rotatable = False

        for possible_class, skin_properties in self.SKIN_MAPPING.items():
            if isinstance(part, possible_class):
                self.is_skinned = True
                self.svg_type, self.skin_pin_names, self.is_symmetric, self.is_rotatable = skin_properties
                break

    def attach_net_name_port(self, net, net_node_number, direction):
        self.schematic_page.ports_dict["%s_node%s" % (net.name, str(net_node_number))] = {
            "bits": [net_node_number],
            "direction": direction
        }

    def attach_net_name(self, net, net_node_number, display=True):
        netname_entry = self.schematic_page.netnames_dict[net.name]
        if net_node_number not in netname_entry["bits"]: # avoid duplicates
            netname_entry["bits"].append(net_node_number)
        if display:
            netname_entry["hide_name"] = 0

    def attach_power_symbol(self, net, net_node_number):
        name = net.name
        if len(name) > 10:
            name = name.replace("PP","")
            name = name.replace("_VREF","")

        power_symbol = {
            "connections": {"A": [net_node_number]},
            "attributes": {"name": name},
            "type": "gnd" if net.is_gnd else "vcc",
        }

        if name == "GND":
            # redundant
            del power_symbol["attributes"]["name"]

        cell_name = "power_symbol_%d" % (net_node_number)
        self.schematic_page.cells_dict[cell_name] = power_symbol

    def should_draw_pin(self, pin):
        if not pin._net:
            # if we don't have a pin name, do it conditionally based on if a regex is set
            return self.schematic_page.net_regex.pattern == NET_REGEX_ALL
        else:
            return self.schematic_page.net_regex.match(str(pin.net.name))

    def add_parts(self, indent_depth=""):
        # Every real part might yield multiple smaller parts (eg: airwires, gnd/vcc connections)
        part = self.part
        self.schematic_page.parts_to_draw.remove(part)

        connections = {}
        port_directions = {}

        parts_to_bring_on_page = []

        pin_count = len(part.pins)
        for i, pin in enumerate(part.pins):
            name = "%s (%s)" % (pin.name, ", ".join(pin.numbers))
            if self.skin_pin_names:
                # if possible we need to match pin names with the skin file in netlistsvg
                name = self.skin_pin_names[i]

            DIRECTIONS = ["output", "input"] # aka right, left
            port_directions[name] = DIRECTIONS[i < pin_count/2]

            # TODO: Make this depend on pin type, instead of such a rough heuristic
            if "OUT" in pin.name:
                port_directions[name] = "output"
            if "IN" in pin.name:
                port_directions[name] = "input"
            if "EN" in pin.name:
                port_directions[name] = "input"

            is_connector = part.refdes.startswith("J") or part.refdes.startswith("CN")
            if is_connector:
                try:
                    pin_number = int(pin.number)
                except ValueError:
                    pass
                else:
                    port_directions[name] = DIRECTIONS[pin_number % 2]

            pin_net = pin._net
            if pin_net:
                if hasattr(pin_net, "parent"):
                    pin_net = pin_net.parent

                pin_net_helper = self.schematic_page.net_helpers[pin_net]

                net_node_number = pin_net_helper.get_node_number(pin)
                connections[name] = [net_node_number]

                for other_pin in pin_net_helper.get_other_pins_in_group(pin):
                    other_part = other_pin.part
                    parts_to_bring_on_page.append(other_part)
            else:
                # Make up a new disposable connection
                connections[name] = [SVGNet.get_next_node_number()]

            skip_drawing_pin = not self.should_draw_pin(pin)

            if self.is_skinned or part.refdes.startswith("Q"):
                # if any other pins good on a small part, we should draw the whole part (all pins)
                for other_pin in set(part.pins) - set((pin,)):
                    if self.should_draw_pin(other_pin):
                        skip_drawing_pin = False

            if pin in self.schematic_page.pins_to_skip:
                skip_drawing_pin = True

            if skip_drawing_pin:
                del connections[name]
                continue

            self.schematic_page.pins_drawn.append(pin)
            self.schematic_page.pin_count += 1

            if pin_net:
                display_net_name = pin.net.has_name
                if pin.net.is_gnd or pin.net.is_power:
                    self.attach_power_symbol(pin.net, net_node_number)
                    display_net_name = False
                self.attach_net_name(pin.net, net_node_number, display=display_net_name)

        if not connections:
            return

        if self.is_rotatable:
            suffix = "h"
            swap_pins = False
            for i, pin in enumerate(part.pins):
                if pin.net.is_power:
                    suffix = "v"
                    if i != 0:
                        swap_pins = True
                if pin.net.is_gnd:
                    suffix = "v"
                    if i != 1:
                        swap_pins = True
                #TODO maybe keep it horizontal if both sides .is_power

            if swap_pins and self.is_symmetric:
                mapping = {"A": "B", "B": "A"}
                connections = {mapping[name]:v
                    for name, v in connections.items()}

            if self.is_rotatable:
                self.svg_type += suffix

        self.schematic_page.cells_dict[self.part.refdes] = {
            "connections": connections,
            "port_directions": port_directions,
            "attributes": {"value": part.value},
            "type": self.svg_type
        }

        logging.debug(f"Added part to SVG: {indent_depth + str(part)}")

        # Make sure the other related parts are squeezed on this page
        for other_part in parts_to_bring_on_page:
            if other_part not in self.schematic_page.parts_to_draw:
                # we already drew it earlier
                continue

            self.schematic_page.part_helpers[other_part].add_parts(indent_depth + " ")

class SVGPage(object):
    """Represents single .svg page"""

    def __init__(self, net_regex=NET_REGEX_ALL, airwires=2, pins_to_skip=[], max_pin_count=None, context=global_context):
        self.net_regex = re.compile(net_regex)
        self.airwires = airwires
        self.context = context

        self.max_pin_count = max_pin_count
        self.pin_count = 0

        self.pins_to_skip = pins_to_skip
        self.pins_drawn = []

        self.cells_dict = {}
        self.netnames_dict = collections.defaultdict(lambda: {"bits": [], "hide_name": 1})
        self.ports_dict = {}

        # start helper classes
        self.net_helpers = {}
        for net in self.context.net_list:
            self.net_helpers[net] = SVGNet(net, self)

        self.part_helpers = {}
        for part in self.context.parts_list:
            self.part_helpers[part] = SVGPart(part, self)

    class PageEmpty(Exception):
        pass

    def write_json(self, fp):
        """Generate the json input required for netlistsvg and dumps it to a file."""
        self.parts_to_draw = collections.deque(self.context.parts_list)
        while self.parts_to_draw:

            if self.max_pin_count and self.pin_count > self.max_pin_count:
                # stop drawing, this page is too cluttered
                break

            part = self.parts_to_draw[0]
            self.part_helpers[part].add_parts()

        if not self.pins_drawn:
            raise self.PageEmpty

        big_dict = {"modules": {"SVG Output": {
            "cells": self.cells_dict,
            "netnames": self.netnames_dict,
            "ports": self.ports_dict,
        }}}

        json.dump(big_dict, fp, indent=4)
        fp.flush()

    def generate(self):
        """Calls netlistsvg to generate the page and returns the svg contents as a string."""
        with tempfile.NamedTemporaryFile("w", prefix="netlistsvg_input_", suffix=".json", delete=False) as json_file, \
             tempfile.NamedTemporaryFile("r", prefix="netlistsvg_output_", suffix=".svg", delete=False) as netlistsvg_output:
            self.write_json(json_file)
            netlistsvg_command = [
                "/usr/bin/env", "node",
                os.path.join(NETLISTSVG_LOCATION, "bin", "netlistsvg.js"),

                "--skin",
                os.path.join(NETLISTSVG_LOCATION, "lib", "analog.svg"),

                json_file.name,

                "-o",
                netlistsvg_output.name
            ]
            logging.debug(f"Called SVG with command: {netlistsvg_command}")
            subprocess.call(netlistsvg_command)

            svg_contents = netlistsvg_output.read()

        # When a net appears in a few places (when we have airwires), we need to disambiguage the parts of the net
        # so netlistsvg doesn't think they're actually the same net and should connect them together.
        # Remove the extra decoration:
        svg_contents = re.sub("_node\d+", "", svg_contents)

        return svg_contents


def generate_svg(filename: str, *args, multi_filename_ending: str="_{0}", **kwargs):
    """Generates an SVG or a series of SVG files to a given file. If multiple
    SVG pages are created, then each SVG is named according to the scheme
    'filename'+'multi_filename_ending'.format(i) where i is the page number.

    Args:
        filename: The file name to write the SVG to. If multiple SVGs are written
            then the multi_filename_ending will be concatenated.
        multi_filename_ending: The ending to concatenate to filename in order to
            name multiple generated SVG files sequentially. The ending is
            evaluated like 'multi_filename_ending'.format(i) where i is the page
            number. Defaults to "_{0}".
    """
    # Force SVG file
    if not filename.lower().endswith(('.svg')):
        filename += ".svg"

    svg_arr = []
    pins_to_skip = []
    while True:
        n = SVGPage(*args, **kwargs, pins_to_skip=pins_to_skip)
        try:
            svg_contents = n.generate()
        except SVGPage.PageEmpty:
            break
        pins_to_skip += n.pins_drawn

        svg_arr.append(svg_contents)

    # Write a single file with the SVG name
    assert len(svg_arr) > 0, "No SVG generated, check inputs."
    if len(svg_arr) == 1:
        with open(filename, "w") as svg_file:
            svg_file.write(svg_arr[0])
        logging.info(f"Wrote SVG file: {filename}")
    if len(svg_arr) > 1:
        for i, svg in enumerate(svg_arr):
            svg_filename = filename + multi_filename_ending.format(i)
            with open(svg_filename, "w") as svg_file:
                svg_file.write(svg)
            logging.info(f"Wrote SVG file: {svg_filename}")
