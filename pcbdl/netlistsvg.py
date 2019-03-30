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
from .small_parts import C, R, JellyBean
import collections
import json
import os
import re
import subprocess
import tempfile

"""Renders our circuit into svg with the help of netlistsvg."""
__all__ = ["generate_svg"]

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
			self.grouped_connections.append(group)

			if self.schematic_page.airwires < 2:
				continue

			first_big_part = None
			for pin in original_group:
				if len(pin.part.pins) <= 4:
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

	def get_node_number(self, pin):
		if not hasattr(self, "node_numbers"):
			self.categorize_groups()

		for i, group in enumerate(self.grouped_connections):
			if pin in group:
				group_idx = i
				break
		else:
			raise ValueError("Can't find pin %s on %s" % (pin, self.instance))

		if self.schematic_page.airwires == 0:
			return self.node_numbers[0]
		return self.node_numbers[group_idx]

class SVGPart(object):
	def __init__(self, instance, schematic_page):
		self.instance = instance
		self.schematic_page = schematic_page

	def attach_airwire(self, net, net_node_number, direction):
		self.schematic_page.ports_dict[net.name + str(net_node_number)] = {
			"bits": [net_node_number],
			"direction": direction
		}

	def attach_power_symbol(self, net, net_node_number):
		name = "%s%d" % (net.name, net_node_number)

		name_attribute = net.name
		if len(name_attribute) > 10:
			name_attribute = name_attribute.replace("PP","")
			name_attribute = name_attribute.replace("_VREF","")

		power_symbol = {
			"connections": {"A": [net_node_number]},
			"port_directions": {"A": "input"},
			"attributes": {"value": name_attribute},
		}
		if net.is_gnd:
			power_symbol["type"] = "gnd"
		if net.is_power:
			power_symbol["type"] = "vcc"

		self.schematic_page.parts_dict[name] = power_symbol

	def add_parts(self):
		# Every real part might yield multiple smaller parts (eg: airwires, gnd/vcc connections)
		part = self.instance

		connections = {}
		port_directions = {}

		pin_count = len(part.pins)
		for i, pin in enumerate(part.pins):
			name = "%s (%s)" % (pin.name, ", ".join(pin.numbers))
			if isinstance(part, JellyBean):
				# we need to match pin names for the skin file in netlistsvg
				name = "AB"[i]

			DIRECTIONS = ["output", "input"] # aka right, left
			port_directions[name] = DIRECTIONS[i < pin_count/2]

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

				#if len(pin_net_helper.grouped_connections) > 1 and not (pin.net.is_gnd or pin.net.is_power):
					#self.attach_airwire(pin.net, net_node_number, port_directions[name])
			else:
				# Make up a new disposable connection
				connections[name] = [SVGNet.get_next_node_number()]


			skip_drawing_pin = False
			if not self.schematic_page.net_regex.match(str(pin.net.name)):
				skip_drawing_pin = True

			if pin in self.schematic_page.pins_to_skip:
				skip_drawing_pin = True

			if skip_drawing_pin:
				del connections[name]
				continue

			self.schematic_page.pins_drawn.append(pin)
			self.schematic_page.pin_count += 1

			if pin.net.is_gnd or pin.net.is_power:
				self.attach_power_symbol(pin.net, net_node_number)

		if not connections:
			return

		svg_type = "%s (%s)" % (part.refdes, part.value)
		# apply particular skins
		if isinstance(part, C):
			svg_type = "c_"
		if isinstance(part, R):
			svg_type = "r_"
		if isinstance(part, (R, C)):
			suffix = "h"

			#for pin in port_directions.keys():
				#port_directions[pin] = "input"

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
			if swap_pins:
				mapping = {"A": "B", "B": "A"}
				connections = {mapping[name]:v
					for name, v in connections.items()}
				port_directions = {mapping[name]:v
					for name, v in port_directions.items()}

			svg_type += suffix

		self.schematic_page.parts_dict["%s(%s)" % (part.refdes, part.value)] = {
			"connections": connections,
			"port_directions": port_directions,
			"type": svg_type
		}

class NetlistSVG(object):
	"""Represents single .svg file"""

	NETLISTSVG_LOCATION = os.path.expanduser("~/netlistsvg")

	def __init__(self, net_regex=".*", airwires=2, pins_to_skip=[], max_pin_count=None, context=global_context):
		self.net_regex = re.compile(net_regex)
		self.airwires = airwires
		self.context = context

		self.max_pin_count = max_pin_count
		self.pin_count = 0

		self.pins_to_skip = pins_to_skip
		self.pins_drawn = []

	@property
	def json(self):
		self.parts_dict = {}
		self.ports_dict = {}

		# start helper classes
		self.net_helpers = {}
		for net in self.context.net_list:
			self.net_helpers[net] = SVGNet(net, self)

		self.part_helpers = {}
		for part in self.context.parts_list:
			if self.max_pin_count and self.pin_count > self.max_pin_count:
				# stop drawing, this page is too cluttered
				self.net_regex = re.compile(".^")

			part_helper = SVGPart(part, self)
			self.part_helpers[part] = part_helper
			part_helper.add_parts()

		big_dict = {"modules": {"SVG Output": {
			"cells": self.parts_dict,
			"ports": self.ports_dict,
		}}}

		return json.dumps(big_dict, indent="\t")

	@property
	def svg(self):
		with tempfile.NamedTemporaryFile("r") as f:
			json = self.json
			with open("out.json", "w") as f2:
				f2.write(json)
			subprocess.check_output([
				"nodejs",
				os.path.join(self.NETLISTSVG_LOCATION, "bin", "netlistsvg.js"),

				"--skin",
				os.path.join(self.NETLISTSVG_LOCATION, "lib", "analog.svg"),

				"/dev/stdin", # input

				"-o",
				f.name
			], input=json.encode("utf-8"))

			return f.read()


def generate_svg(filename, pins_to_skip=[], *args, **kwargs):
	i = 0
	while True:
		for attempt in range(10):
			print(i)
			n = NetlistSVG(*args, **kwargs, pins_to_skip=pins_to_skip)
			svg_contents = n.svg
			if svg_contents != "undefined":
				break

			kwargs["max_pin_count"] -= 1
		if len(svg_contents)>700:
			with open("%s%d.svg" % (filename, i), "w") as f:
				f.write(svg_contents)
		pins_to_skip += n.pins_drawn

		i+=1
		if not n.pins_drawn:
			break

