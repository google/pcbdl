"""
Allegro(R) "third party" netlist format exporter.
"""

from .base import *
from .context import *
from datetime import datetime

__all__ = ["generate_netlist"]

def netlist_generator(context):
	yield "!CREATED-BY-PCBDL! DESIGN DATABASE ASCII FILE 1.0"
	yield "!%s!" % (datetime.now().strftime("%a %b %d %H:%M:%S %Y"))

	yield "*PART*"
	for part in context.parts_list:
		yield part.netlist_part_line

	yield "*NET*"
	for net in context.net_list:
		yield net.netlist_line

	yield "*MISC*"
	yield "ATTRIBUTE VALUES\n{"
	for part in context.parts_list:
		yield part.netlist_attribute_line
	yield "}"

	yield "*END*"


def generate_netlist(context=global_context):
	return "\n".join(netlist_generator(context))

@plugin
class NetNetlist(Net):
	netlist_counter = 1
	@property
	def netlist_line(self):
		name = self.name
		if name is None:
			#TODO: figure out how to name nets automatically
			name = "TODO_NAME_THIS_BETTER_IN_CODE"
		return "*SIGNAL* %s\n%s" % (
			name,
			" ".join(pin.netlist_name for pin in self.connections)
		)

@plugin
class NetlistPin(PartInstancePin):
	def init(self):
		pass

	@property
	def netlist_name(self):
		return repr(self)

@plugin
class NetlistPart(Part):
	@property
	def netlist_part_line(self):
		try:
			package = self.package
		except AttributeError:
			package = ""
		return "%s %s" % (self.refdes, package)

	@property
	def netlist_attribute_line(self):
		return 'PART %s\n{\n"Value" %s\n}' % (self.refdes, self.value)
