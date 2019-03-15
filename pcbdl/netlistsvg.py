from .base import Part, PartInstancePin, Net, Plugin
from .context import *
from .small_parts import C, R, JellyBean
import collections
import json

"""Outputs an input file for netlistsvg (a javascript project) which eventually
   renders our circuit into svg."""
__all__ = ["generate_netlistsvg_json"]

@Plugin.register(Net)
class SVGNet(Plugin):
	current_node_number = -1

	@classmethod
	def get_next_node_number(cls):
		cls.current_node_number += 1
		return cls.current_node_number

	@property
	def node_number(self):
		try:
			return self._node_number
		except AttributeError:
			node_number = self.get_next_node_number()
			self._node_number = node_number
			return node_number

@Plugin.register(Part)
class SVGPart(Plugin):
	@staticmethod
	def create_power_symbol(parts_dict, net, type_name):
		net_node_number = net.plugins[SVGNet].get_next_node_number()
		name = "%s%d" % (net.name, net_node_number)

		parts_dict[name] = {
			"connections": {"A": [ net_node_number ]},
			"port_directions": {"A": "input"},
			"type": type_name
		}

		return net_node_number

	def add_parts(self, parts_dict):
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

			net_node_number = pin.net.plugins[SVGNet].node_number
			if pin.net.is_gnd:
				net_node_number = self.create_power_symbol(parts_dict, pin.net, "gnd")
			if pin.net.is_power:
				net_node_number = self.create_power_symbol(parts_dict, pin.net, "vcc")

			connections[name] = [net_node_number]

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


		svg_type = "%s (%s)" % (part.refdes, part.value)
		# apply particular skins
		if isinstance(part, C):
			svg_type = "c_"
		if isinstance(part, R):
			svg_type = "r_"
		if isinstance(part, (R, C)):
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
			if swap_pins:
				connections = {
					"A": connections["B"],
					"B": connections["A"],
				}
			svg_type += suffix

		parts_dict[part.refdes] = {
			"connections": connections,
			"port_directions": port_directions,
			"type": svg_type
		}

def generate_netlistsvg_json(context=global_context):
	parts_dict = {}

	for part in context.parts_list:
		part.plugins[SVGPart].add_parts(parts_dict)

	big_dict = {"modules": {"SVG Output": {
		"cells": parts_dict,
		"ports": {}
	}}}
	return json.dumps(big_dict, indent="\t")
