"""
Allegro(R) "third party" netlist format exporter.
"""

from .base import Part, PartInstancePin, Net, Plugin
from .context import *
import collections
from datetime import datetime
import itertools

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

def netlist_generator(context):
	yield "(NETLIST)"
	yield "(CREATED BY PCBDL)"
	yield "(%s)" % (datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
	yield ""

	yield "$PACKAGES"
	grouped_parts = collections.defaultdict(list)
	for part in context.parts_list:
		key = (part.package, part.part_number)
		grouped_parts[key].append(part)
	for (package, part_number), parts_list in grouped_parts.items():
		yield "'%s' ! %s ; %s" % (
			package, part_number,
			" ".join(map(repr, parts_list))
		)
	yield ""

	yield "$NETS"
	for net in context.net_list:
		yield net.plugins[NetlistNet].line

	yield "$END"

def generate_netlist(context=global_context):
	return "\n".join(netlist_generator(context))
