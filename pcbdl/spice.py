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

from pcbdl import *
import collections
import itertools
import subprocess
import tempfile
from .ngspice import NgSpice, SimulationError
ngspice = NgSpice()

class IncompleteSimulationModel(Exception):
	pass

class SchematicProblem(Exception):
	pass

def r_spice_helpler(self, pin):
	other_pins = list(set(self.pins) - set((pin,)))
	spice_contents = f"R{self.refdes} net_{self.P1.net} net_{self.P2.net} {self.value}"
	return spice_contents, other_pins
R.spice_helpler = r_spice_helpler

__all__ = []
def _export(o):
	__all__.append(o.__name__)
	return o

@_export
class Checker(Exception):
	"""Problem with the circuit detected as a result of a SPICE simulation."""
	@staticmethod
	def make_pin_checkers(pin, checker_types):
		for checker_type in checker_types:
			c = checker_type()
			c.pin = pin
			c.net = pin.net
			yield c

	def parse_probes(self, all_probes):
		"""Set the values of all probes of interest as properties to this instance."""
		self.all_probes = all_probes
		for probe_name, spice_probe in self.PROBES.items():
			spice_probe = spice_probe.format(self=self).lower()
			probe_value = all_probes[spice_probe]
			setattr(self, probe_name, probe_value)

	def check(self):
		raise NotImplementedError

	def _error(self, msg):
		SchematicProblem.__init__(self, msg)
		raise self

@_export
class OutputOvercurrent(Checker, SchematicProblem):
	OUTPUT_PIN_IMPEDANCE = "5ohm"
	OUTPUT_PIN_CURRENT_LIMIT = 0.1

	PROBES = {
		"output_voltage": "pinnode_{self.pin}",
		"current":        "V_{self.pin}#branch",
	}

	def check(self):
		if abs(self.current) > self.OUTPUT_PIN_CURRENT_LIMIT:
			self._error(f"{-self.current}A on pin {self.pin} when outputting {self.output_voltage}V toward net {self.net.name}.")

@_export
class InputOverVoltage(Checker, SchematicProblem):
	CLAMP_DIODE_MODEL = "Default"

	"""Detect current leaks into input pins."""
	PROBES = {
		"diode_current": "Vwell_{self.pin}#branch",
		"input_voltage":   "net_{self.net.name}",
	}

	def check(self):
		if self.diode_current > 1e-10:
			self._error(f"{self.input_voltage}V on pin {self.pin}(well={self.pin.well.net}) from net {self.net.name}")

@_export
class InputVoltageWeak(Checker, SchematicProblem):
	"""Make sure input voltage is enough to properly open the pin."""
	PROBES = {
		"input_voltage": "net_{self.net.name}",
		"well_voltage":  "wellnode_{self.pin}"
	}

	def check(self):
		if self.well_voltage * 0.3 < self.input_voltage < self.well_voltage * 0.7:
			self._error(f"{self.input_voltage}V on pin {self.pin}(well={self.pin.well.net}) not between VIL and VIH from net {self.net.name}")

class HizNets(SchematicProblem):
	pass

@_export
class HizNetChecker(Checker):
	EXCITATION_VOLTAGE = "1V"
	EXCITATION_MIN_CURRENT = 100e-9 # 100nA, EXCITATION_VOLTAGE / 10MegOhm

	PROBES = {
		"hiz_current": "Vnethiz_{self.net.name}#branch",
	}

	def check(self):
		if self.triggered:
			self._error(f"Not enough current({self.hiz_current}A) when {self.net.name} pulled to {self.output_voltage}")

	@property
	def triggered(self):
		return abs(self.hiz_current) < self.EXCITATION_MIN_CURRENT

	def spice_helpler(self):
		self.output_voltage = self.EXCITATION_VOLTAGE if self.direction else "0V"

		return [
			f"Vnethiz_{self.net.name} net_{self.net.name} 0 {self.output_voltage}",
			"",
		]

@_export
def scan_net(net, start_pin=None):
	"""Recursively circuit simulation elements starting at a net, ignores start_pin."""

	while hasattr(net, "parent"):
		net = net.parent
	elements = {
		"nets": [net],
		"chip_output_pins": [],
		"chip_input_pins": [],
		"spice_parts": [],
	}

	for pin in net.connections:
		if pin is start_pin:
			# just ignore so we don't go backwards
			continue

		part = pin.part

		if hasattr(part, "spice_helpler"):
			# Then we probably want to recursively scan through this component
			spice_contents, other_pins = part.spice_helpler(pin)
			elements["spice_parts"].append(spice_contents)
			for other_pin in other_pins:
				other_net = other_pin.net
				if other_net.is_gnd or other_net.is_power:
					continue

				more_elements = scan_net(other_net, other_pin)
				for k in more_elements:
					elements[k].extend(more_elements[k])
		else:
			# It's not so easy, we'll have to replace each pin with virtual components and do more detailed checking
			# For now, remember everything we have
			if pin.type == PinType.OUTPUT:
				elements["chip_output_pins"].append(pin)
			elif pin.type == PinType.INPUT:
				elements["chip_input_pins"].append(pin)
			else:
				raise IncompleteSimulationModel(f"Cannot add pin {pin} into the SPICE simulation, unknown type {pin.type}.")

	return elements

@_export
def scan_nets(nets):
	"""Yields simulation elements for every circuit in `nets`."""
	nets_todo = set(nets)
	while nets_todo:
		n = nets_todo.pop()
		if n.is_gnd or n.is_power:
			continue
		if not n.connections:
			continue

		# Start a new simulation at this net
		elements = scan_net(n)
		print(f"Found SPICE circuit {elements['nets']}")
		yield elements

		# Make sure we don't repeat this set of nets
		nets_todo.difference_update(elements["nets"])

@_export
def do_circuit_simulation(elements, raise_errors=True):
	OUTPUT_PIN_STATES = [0, 1]
	for output_values in itertools.product(OUTPUT_PIN_STATES, repeat=len(elements["chip_output_pins"])):
		output_values = dict(zip(elements["chip_output_pins"], output_values))

		errors = do_circuit_state_simulation(elements, output_values, {})
		if raise_errors and errors:
			raise errors[0]
		for error in errors:
			if isinstance(error, SimulationError):
				if "singular matrix" in error.full_text:
					new_e = HizNets(f"Singular matrix with nets {elements['nets']}")
					new_e.nets = elements["nets"]
					raise new_e from error
				raise error

		for tested_hiz_net in elements["nets"]:
			triggered = []
			for hiz_net_direction in [0, 1]:
				errors = do_circuit_state_simulation(elements, output_values, {tested_hiz_net: hiz_net_direction})
				if errors and isinstance(errors[0], HizNetChecker):
					triggered.append(errors[0])
			if len(triggered) == 2:
				max_current = max(abs(c.hiz_current) for c in triggered)
				e = HizNets(f"Not enough current(<={max_current}A) when pulling {tested_hiz_net} in both directions.")
				e.nets = elements["nets"]
				e.checkers = triggered
				#print(f" {e!r}")
				if raise_errors:
					raise e


def do_circuit_state_simulation(elements, output_values, try_hiz_nets):
	#print(f" Outputs {output_values}")
	simulation_inputs = locals().copy()
	checkers = []
	cir = [f"PCBDL Analysis for nets {elements['nets']}"]
	cir.append("")

	cir.append("* Real parts from the original schematics:")
	for active in elements["spice_parts"]:
		cir.append(active)
	cir.append("")

	for net_attempt in try_hiz_nets.items():
		c = HizNetChecker()
		c.net, c.direction = net_attempt
		c.nets = elements["nets"]
		cir.extend(c.spice_helpler())
		checkers.append(c)

	for pin in elements["chip_output_pins"]:
		cir.append("* Output Pin: %r" % pin)
		net = pin.net
		output_voltage = pin.well.net.spice_voltage if output_values[pin] else "0"
		cir.append(f"V_{pin} pinnode_{pin} 0 {output_voltage}")
		cir.append(f"R{pin} pinnode_{pin} net_{net.name} {OutputOvercurrent.OUTPUT_PIN_IMPEDANCE}") # TODO(variable resistor, CCVS)

		checkers.extend(Checker.make_pin_checkers(pin, (
			OutputOvercurrent,
		)))

		cir.append("")

	for pin in elements["chip_input_pins"]:
		cir.append("* Input Pin: %r" % pin)
		net = pin.net
		cir.append(f"Vwell_{pin} wellnode_{pin} 0 {pin.well.net.spice_voltage}")
		cir.append(f"Dclamp_{pin} net_{net.name} wellnode_{pin} {InputOverVoltage.CLAMP_DIODE_MODEL}")

		checkers.extend(Checker.make_pin_checkers(pin, (
			InputOverVoltage, InputVoltageWeak,
		)))

		cir.append("")

	cir.append(".control")
	cir.append("op")
	cir.append(".endc")
	cir.append(".op")

	cir.append(".end")

	#print('\n'.join(cir))
	try:
		probes = ngspice.circ(cir)
	except SimulationError as e:
		return [e]

	errors = []
	for checker in checkers:
		try:
			checker.parse_probes(probes)
			checker.simulation_inputs = simulation_inputs
			checker.check()
		except Checker as e:
			#print(f"  {e!r}")
			errors.append(e)
	#print(f"  f{probes}")

	#print("")
	return errors
