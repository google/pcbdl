from .base import Part, PartInstancePin, Net, Plugin
from .context import *
import collections
from datetime import datetime
import itertools

"""HTML output format"""
__all__ = ["generate_html"]

files = set()
@Plugin.register((Net, Part))
class HTMLDefinedAt(Plugin):
	@property
	def href_line(self):
		defined_at = self.instance.defined_at

		file, line = defined_at.split(":")
		line = int(line)
		files.add(file)

		return "<p>Defined at: %s<a href=\"#line-%d\">:%d</a></p>" % (file, line, line)

@Plugin.register(Part)
class HTMLPart(Plugin):
	@property
	def part_li(self):
		part = self.instance
		yield "<li>"
		yield "<h2 id=\"part-%s\">%s</h2>" % (part.refdes, part.refdes)
		yield part.plugins[HTMLDefinedAt].href_line
		yield "<p>Value: %s</p>" % part.value
		yield "<p>Part Number: %s</p>" % part.part_number
		yield "<p>%d pins:</p><ul>" % len(part.pins)
		for pin in part.pins:
			yield "<li id=\"pin-%s.%s\">%s (%s)" % (pin.part.refdes, pin.name, "/".join(pin.names), ', '.join(pin.numbers))
			try:
				net_name = pin._net.name
				yield "net: <a href=\"#net-%s\">%s</a>" % (net_name, net_name)
			except AttributeError:
				pass
			try:
				yield "well: %s" % (pin.well.plugins[HTMLPin].short_anchor)
			except AttributeError:
				pass
			yield "</li>"
		yield "</ul>"
		yield "</li>"

@Plugin.register(Net)
class HTMLNet(Plugin):
	@property
	def net_li(self):
		net = self.instance
		name = net.name
		if name is None:
			#TODO: figure out how to name nets automatically
			name = "TODO_NAME_THIS_NET_BETTER_IN_CODE"

		yield "<li>"
		yield "<h2 id=\"net-%s\">%s</h2>" % (name,name)
		yield net.plugins[HTMLDefinedAt].href_line
		yield "<p>%d connections:</p><ul>" % len(net.connections)
		for pin in net.connections:
			yield "<li>%s</li>" % (pin.plugins[HTMLPin].full_anchor)
		yield "</ul>"
		yield "</li>"

@Plugin.register(PartInstancePin)
class HTMLPin(Plugin):
	@property
	def short_anchor(self):
		pin = self.instance
		return "<a href=\"#pin-%s.%s\">%s</a>" % (pin.part.refdes, pin.name, pin.name)

	@property
	def full_anchor(self):
		pin = self.instance
		part_anchor = "<a href=\"#part-%s\">%s</a>." % (pin.part.refdes, pin.part.refdes)
		return part_anchor + self.short_anchor

def html_generator(context):
	yield "<html>"
	yield "<style>"
	yield ":target {background-color: yellow;}"
	yield "</style>"
	yield "<body>"

	yield "<h1>Parts</h1><ul>"
	for part in context.parts_list:
		yield from part.plugins[HTMLPart].part_li
	yield "</ul>"

	yield "<h1>Nets</h1><ul>"
	for net in context.net_list:
		yield from net.plugins[HTMLNet].net_li
	yield "</ul>"

	yield "<h1>Code</h1>"
	for file_name in files:
		yield "<h2>%s</h2>" % file_name

		yield "<pre>"
		with open(file_name) as file:
			for line_no, line in enumerate(file):
				line_no += 1 # they start at 1
				line = line[:-1] # kill the end '\n'
				yield "<a name=\"line-%d\">%s</a>" % (line_no, line)
		yield "</pre>"

	yield "</body>"
	yield "</html>"

def generate_html(context=global_context):
	return "\n".join(html_generator(context))
