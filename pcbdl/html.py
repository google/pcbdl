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

from .base import Part, PartInstancePin, Net, Plugin
from .context import *
from .netlistsvg import NetlistSVG

import collections
from datetime import datetime
import html
import textwrap
import itertools

import pygments
import pygments.lexers
import pygments.formatters

"""HTML output format"""
__all__ = ["generate_html"]

@Plugin.register((Net, Part))
class HTMLDefinedAt(Plugin):
	@property
	def href_line(self):
		defined_at = self.instance.defined_at

		file, line = defined_at.split(":")
		line = int(line)
		self.code_manager.instanced_here(self.instance, file, line)

		return "<p>Defined at: %s<a href=\"#line-%d\">:%d</a></p>" % (file, line, line)

@Plugin.register(Part)
class HTMLPart(Plugin):
	@property
	def class_list(self):
		l = self.instance.__class__.__mro__
		s = repr(l[:l.index(Part) + 1])
		s = s.strip("(),")
		return s

	@property
	def part_li(self):
		part = self.instance

		class_str = ""
		if not part.populated:
			class_str = " class=\"not-populated\""

		yield "<li%s><h2 id=\"part-%s\">%s</h2>" % (class_str, part.refdes, part.refdes)

		yield part.plugins[HTMLDefinedAt].href_line
		yield "<p>%s</p>" % html.escape(self.class_list)
		try:
			yield "<p>Variable Name: %s</p>" % part.variable_name
		except AttributeError:
			pass

		if part.__doc__:
			yield "<pre>%s</pre>" % textwrap.dedent(part.__doc__.rstrip())

		if hasattr(self, "netlistsvg"):
			yield "<p><a href=\"#cell_%s\">See in SVG</a></p>" % self.netlistsvg.part_helpers[self.instance].cell_name

		yield "<p>Value: %s</p>" % part.value
		yield "<p>Part Number: %s</p>" % part.part_number
		if not part.populated:
			yield "<p>Do Not Populate!</p>"
		try:
			yield "<p>Package: %s</p>" % part.package
		except AttributeError:
			yield "Package not defined"

		real_pin_count = len({number for pin in part.pins for number in pin.numbers})
		yield "<p>%d logical pins (%d real pins):</p><ul>" % (len(part.pins), real_pin_count)
		for pin in part.pins:
			yield "<li id=\"pin-%s.%s\">%s (%s)" % (pin.part.refdes, pin.name, " / ".join(pin.names), ', '.join(pin.numbers))

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

		yield "<li><h2 id=\"net-%s\">%s</h2>" % (name, name)
		yield net.plugins[HTMLDefinedAt].href_line

		try:
			yield "<p>Variable Name: %s</p>" % net.variable_name
		except AttributeError:
			pass

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

class Code(object):
	# {filename: {line: [instance]}}
	file_database = collections.defaultdict(lambda: collections.defaultdict(set))
	_instances = set()

	class CodeHtmlFormatter(pygments.formatters.HtmlFormatter):
		def _wrap_linespans(self, inner):
			s = self.linespans
			line_no = self.linenostart - 1
			for t, line in inner:
				if t:
					line_no += 1
					variables = self.fill_variables_for_line(line_no)
					line = line.rstrip("\n")
					yield 1, '<span id="%s-%d">%s%s\n</span>' % (s, line_no, line, variables)
				else:
					yield 0, line

	def __init__(self):
		self.lexer = pygments.lexers.PythonLexer()
		self.formatter = self.CodeHtmlFormatter(
			linenos=True,
			linespans="line",

			anchorlinenos = True,
			lineanchors="line",

			cssclass="code",
		)
		self.formatter.fill_variables_for_line = self.fill_variables_for_line

	def fill_variables_for_line(self, line_no):

		file = tuple(self.file_database.values())[0] #TODO: fix this to work for multiple files
		variables_on_this_line = file[line_no]

		if not variables_on_this_line:
			return ""

		links = []
		for variable in variables_on_this_line:
			if isinstance(variable, Net):
				net_name = variable.name
				links.append("<a href=\"#net-%s\">%s</a>" % (net_name, net_name))
				continue

			if isinstance(variable, Part):
				part = variable
				links.append("<a href=\"#part-%s\">%s</a>" % (part.refdes, part.refdes))
				continue

			raise Exception("No idea how to make link for %r of type %r" % (variable, type(variable)))

		return "<span class=\"uv\"># %s</span>" % ", ".join(links)

	def instanced_here(self, instance, file, line):
		self.file_database[file][line].add(instance)
		self._instances.add(instance)

	def css_generator(self):
		yield self.formatter.get_style_defs()

	def code_generator(self):
		file_list = self.file_database.keys()
		for file_name in file_list:
			yield "<h2>%s</h2>" % file_name

			with open(file_name) as file:
				source_code = file.read()

			result = pygments.highlight(source_code, self.lexer, self.formatter)

			for instance in self._instances:
				try:
					variable_name = instance.variable_name
				except AttributeError:
					continue

				if isinstance(instance, Net):
					net = instance
					href = "#net-%s" % net.name
					title = "Net %s" % net

				if isinstance(instance, Part):
					part = instance
					href = "#part-%s" % part.refdes
					title = "Part %s" % part

				original_span = "<span class=\"n\">%s</span>" % variable_name
				modified_span = "<span class=\"n lv\"><a href=\"%s\" title=\"%s\"><span>%s</span></a></span>" % (href, title, variable_name)

				if isinstance(instance, Part):
					# Linkify all the pins too
					for pin in part.pins:
						for name in pin.names:
							prepend = original_span + "<span class=\"o\">.</span>"
							original_pin_span = prepend + "<span class=\"n\">%s</span>" % name

							title = repr(pin)
							href = "#pin-%s.%s" % (pin.part.refdes, pin.name)
							modified_pin_span = prepend + "<span class=\"n lv\"><a href=\"%s\" title=\"%s\"><span>%s</span></a></span>" % (href, title, name)
							result = result.replace(original_pin_span, modified_pin_span)

				result = result.replace(original_span, modified_span)

			yield result


def html_generator(context=global_context, include_svg=False):
	code_manager = Code()

	if include_svg:
		svg = NetlistSVG(context=context)
		HTMLPart.netlistsvg = svg
		HTMLNet.netlistsvg = svg

	HTMLDefinedAt.code_manager = code_manager

	# Make sure the code_manager knows about everything already
	_ = [instance.plugins[HTMLDefinedAt].href_line for instance in context.parts_list + context.net_list]

	yield "<!DOCTYPE html>"
	yield "<html>"
	yield "<head>"
	yield "<title>PCBDL %s</title>" % (list(code_manager.file_database.keys())[0])
	yield "<meta charset=\"UTF-8\">"

	yield "<style>"
	yield ":target { background-color: #ffff99; }"
	yield ".not-populated { color: #777777; }"
	yield from code_manager.css_generator()
	yield "svg text {font-weight: normal; font-family: monospace; }"

	yield "svg :target text {font-weight: bold; text-shadow: 0 0 10px #ffff00}"
	yield "svg :target :not(text) { fill: #ffff99; stroke: #000; stroke-width: 3; }"

	# unnamed variables
	yield ".code .uv { color: #b8e0b8; margin: 0 4em; font-style: italic; user-select: none; }"
	yield ".code .uv a { color: #6bc76b; text-decoration: none; }"
	yield ".code .uv a:hover { color: #1d631d; text-decoration: underline; }"

	# linked variables
	yield ".code .lv a { color: #aaaaaa }"
	yield ".code .lv a:hover { color: #000000 }"
	yield ".code .lv a span { color: #000000 }"

	yield ".linenos a { color: #aaaaaa; text-decoration: none; user-select: none; }"
	yield ".linenos a:hover { color: #0000ff; text-decoration: underline; }"

	yield "</style>"
	yield "</head>"
	yield "<body>"

	yield "<h1>PCBDL HTML Output</h1>"
	yield "<h2>Contents</h2><ul>"
	yield "<li><a href=\"#parts\">Parts</a></li>"
	yield "<li><a href=\"#nets\">Nets</a></li>"
	yield "<li><a href=\"#code\">Code</a></li>"
	if include_svg:
		yield "<li><a href=\"#svg\">SVG</a></li>"
	yield "</ul>"
	yield "<p>Generated from:</p><ul>"
	for filename in code_manager.file_database.keys():
		yield "<li>%s</li>" % (filename)
	yield "</ul>"

	yield "<h1 id=\"parts\">Parts</h1><ul>"
	for part in context.parts_list:
		yield from part.plugins[HTMLPart].part_li
	yield "</ul>"

	yield "<h1 id=\"nets\">Nets</h1><ul>"
	for net in context.net_list:
		yield from net.plugins[HTMLNet].net_li
	yield "</ul>"

	yield "<h1 id=\"code\">Code</h1>"
	yield from code_manager.code_generator()

	if include_svg:
		yield "<h1 id=\"svg\">SVG</h1>"
		yield svg.svg

	yield "</body>"
	yield "</html>"

def generate_html(*args, **kwargs):
	return "\n".join(html_generator(*args, **kwargs))
