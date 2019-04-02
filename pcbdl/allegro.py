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

"""
Allegro(R) "third party" netlist format exporter.
"""

from .base import Part, PartInstancePin, Net, Plugin
from .context import *

import collections
from datetime import datetime
import itertools
import os
import shutil
import pprint

"""Allegro "third party" format"""
__all__ = ["generate_netlist"]
def join_across_lines(iterator, count=10):
	iterator = tuple(iterator)
	grouped_generator = (iterator[i:i + count] for i in range(0, len(iterator), count))
	return ',\n'.join(' '.join(line) for line in grouped_generator)

@Plugin.register(Net)
class NetlistNet(Plugin):
	@property
	def line(self):
		net = self.instance
		name = net.name
		if name is None:
			#TODO: figure out how to name nets automatically
			name = "TODO_NAME_THIS_NET_BETTER_IN_CODE"
		return "%s ; %s" % (
			name,
			join_across_lines(pin.plugins[NetlistPin].name for pin in net.connections)
		)

@Plugin.register(PartInstancePin)
class NetlistPin(Plugin):
	@property
	def name(self):
		pin = self.instance
		return join_across_lines("%r.%s" % (pin.part, number) for number in pin.numbers)

def netlist_generator(context, grouped_parts):
	yield "(NETLIST)"
	yield "(CREATED BY PCBDL)"
	yield "(%s)" % (datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
	yield ""

	yield "$PACKAGES"
	for (package, part_number), parts_list in grouped_parts.items():
		yield "'%s' ! '%s' ; %s" % (
			package, part_number,
			" ".join(map(repr, parts_list))
		)
	yield ""

	yield "$NETS"
	for net in context.net_list:
		yield net.plugins[NetlistNet].line

	yield "$END"

def generate_device_file_contents(part):
	hardware_pins = []
	for pin in part.pins:
		all_name = pin.name
		numbers = pin.numbers

		for i, number in enumerate(numbers):
			if len(numbers) == 1:
				name = all_name
			else:
				# in case there's more than 1 pin, add numbers after every one of them
				name = "%s%d" % (all_name, i)
			hardware_pins.append((name, number))

	pin_count = len(hardware_pins)
	pin_names, pin_numbers = zip(*hardware_pins)

	contents="""(PCBDL generated stub device file)
PACKAGE %s
PINCOUNT %d

PINORDER 'MAIN' %s
FUNCTION G1 'MAIN' %s

END
""" % (part.package, pin_count, ' '.join(pin_names), ' '.join(pin_numbers))

	return contents

def generate_netlist(output_location, context=global_context):
	output_location += ".allegro_third_party"

	# Clear it and make a new one
	try:
		shutil.rmtree(output_location)
	except FileNotFoundError:
		pass
	os.mkdir(output_location)

	grouped_parts = collections.defaultdict(list)
	for part in context.parts_list:
		key = (part.package, part.part_number)
		grouped_parts[key].append(part)

	netlist_contents = "\n".join(netlist_generator(context, grouped_parts))

	netlist_filename = os.path.join(output_location, "frompcbdl.netlist.txt")
	with open(netlist_filename, "w") as f:
		f.write(netlist_contents)

	# Generate device files
	device_location = os.path.join(output_location, "devices")
	os.mkdir(device_location)
	for parts in grouped_parts.values():
		# Not sure if this is ok
		# we're assuming that parts with the same package and part
		# number have the same part class yielding in the same
		# ammount of pin_count
		part = parts[0]

		device_file_contents = generate_device_file_contents(part)

		device_filename = os.path.join(device_location, part.part_number + ".txt")
		with open(device_filename, "w") as f:
			f.write(device_file_contents)
