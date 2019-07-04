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
from .ngspice import NgSpice
ngspice = NgSpice()

class CannotStartSimulation(Exception):
	pass

class SpiceError(Exception):
	"""Problem with the circuit detected as a result of a SPICE simulation."""

OUTPUT_PIN_IMPEDANCE = "5ohm"
OUTPUT_PIN_CURRENT_LIMIT = 0.1
CLAMP_DIODE_MODEL = "Default"

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
class PinChecker(SpiceError):
	def __init__(self, pin, simulation_inputs):
		self.pin = pin
		self.net = pin.net
		self.simulation_inputs = simulation_inputs

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
		SpiceError.__init__(self, msg)
		raise self

@_export
class OutputOvercurrent(PinChecker):
	PROBES = {
		"output_voltage": "pinnode_{self.pin}",
		"current":        "V_{self.pin}#branch",
	}

	def check(self):
		if abs(self.current) > OUTPUT_PIN_CURRENT_LIMIT:
			self._error(f"{-self.current}A on pin {self.pin} when outputting {self.output_voltage}V toward net {self.net.name}.")

@_export
class InputOverVoltage(PinChecker):
	"""Detect current leaks into input pins."""
	PROBES = {
		"diode_current": "Vwell_{self.pin}#branch",
		"input_voltage":   "net_{self.net.name}",
	}

	def check(self):
		if self.diode_current > 0:
			self._error(f"{self.input_voltage}V on pin {self.pin}(well={self.pin.well.net}) from net {self.net.name}")

@_export
class InputVoltageWeak(PinChecker):
	"""Make sure input voltage is enough to properly open the pin."""
	PROBES = {
		"input_voltage": "net_{self.net.name}",
		"well_voltage":  "wellnode_{self.pin}"
	}

	def check(self):
		if self.well_voltage * 0.3 < self.input_voltage < self.well_voltage * 0.7:
			self._error(f"{self.input_voltage}V on pin {self.pin}(well={self.pin.well.net}) not between VIL and VIH from net {self.net.name}")

@_export
class HiZ(SpiceError):
	pass

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
				raise CannotStartSimulation(f"Cannot add pin {pin} into the SPICE simulation, unknown type {pin.type}.")

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
	HIZ_NET_STATES = ["normal"] + ["tryhigh", "trylow"] # TODO
	for output_values in itertools.product(OUTPUT_PIN_STATES, repeat=len(elements["chip_output_pins"])):
		output_values = dict(zip(elements["chip_output_pins"], output_values))

		for net_state in itertools.product(HIZ_NET_STATES, repeat=len(elements["nets"])):
			net_state = dict(zip(elements["nets"], net_state))

			#print(f" Outputs {output_values}")
			#print(" Net HiZ testers " + repr({net.name: state for net, state in net_state.items()}))
			errors = do_circuit_state_simulation(elements, output_values, net_state)
			if errors and raise_errors:
				raise errors[0]
			#print("")

def do_circuit_state_simulation(elements, output_values, net_state):
	simulation_inputs = locals().copy()
	checkers = []
	cir = [f"PCBDL Analysis for nets {elements['nets']}"]
	cir.append("")

	cir.append("* Real parts from the original schematics:")
	for active in elements["spice_parts"]:
		cir.append(active)
	cir.append("")

	for pin in elements["chip_output_pins"]:
		cir.append("* Output Pin: %r" % pin)
		net = pin.net
		output_voltage = pin.well.net.spice_voltage if output_values[pin] else "0"
		cir.append(f"V_{pin} pinnode_{pin} 0 {output_voltage}")
		cir.append(f"R{pin} pinnode_{pin} net_{net.name} {OUTPUT_PIN_IMPEDANCE}") # TODO(variable resistor, CCVS)

		for checker in (OutputOvercurrent,):
			checkers.append(checker(pin, simulation_inputs))

		cir.append("")

	for pin in elements["chip_input_pins"]:
		cir.append("* Input Pin: %r" % pin)
		net = pin.net
		cir.append(f"Vwell_{pin} wellnode_{pin} 0 {pin.well.net.spice_voltage}")
		cir.append(f"Dclamp_{pin} net_{net.name} wellnode_{pin} {CLAMP_DIODE_MODEL}")

		for checker in (InputOverVoltage, InputVoltageWeak):
			checkers.append(checker(pin, simulation_inputs))

		cir.append("")

	cir.append(".control")
	cir.append("op")
	cir.append(".endc")

	cir.append(".end")

	#print('\n'.join(cir))
	probes = ngspice.circ(cir)

	errors = []
	for checker in checkers:
		try:
			checker.parse_probes(probes)
			checker.check()
		except PinChecker as e:
			#print(f"  {e!r}")
			errors.append(e)
	#print(f"  f{probes}")

	return errors
