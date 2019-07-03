from pcbdl import *
import collections
import itertools
import subprocess
import tempfile

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

class SpiceChecker(SpiceError):
	def __init__(self, pin, simulation_inputs):
		self.pin = pin
		self.net = pin.net
		self.simulation_inputs = simulation_inputs

	def watches(self):
		"""Returns spice prints for this checker."""
		for spice_probe in self.PROBES.values():
			spice_probe = spice_probe.format(self=self)
			yield f"print {spice_probe}"

	def parse_probes(self, all_probes):
		self.all_probes = all_probes
		for probe_name, spice_probe in self.PROBES.items():
			spice_probe = spice_probe.format(self=self)
			probe_value = all_probes[spice_probe.lower()]
			setattr(self, probe_name, probe_value)

	def check(self):
		raise NotImplementedError

	def error(self, msg):
		SpiceError.__init__(self, msg)
		raise self

class OutputOvercurrent(SpiceChecker):
	PROBES = {
		"output_voltage": "pinnode_{self.pin}",
		"current":        "I(V_{self.pin})",
	}

	def check(self):
		if abs(self.current) > OUTPUT_PIN_CURRENT_LIMIT:
			self.error(f"{-self.current}A on pin {self.pin} when outputting {self.output_voltage}V toward net {self.net.name}.")

class InputOverVoltage(SpiceChecker):
	"""Detect current leaks into input pins."""
	PROBES = {
		"diode_current": "I(Vwell_{self.pin})",
		"input_voltage":   "net_{self.net.name}",
	}

	def check(self):
		if self.diode_current > 0:
			self.error(f"{self.input_voltage}V on pin {self.pin}(well={self.pin.well.net}) from net {self.net.name}")

class InputVoltage(SpiceChecker):
	"""Make sure input voltage is enough to properly open the pin."""
	PROBES = {
		"input_voltage": "net_{self.net.name}",
		"well_voltage":  "wellnode_{self.pin}"
	}

	def check(self):
		if self.well_voltage * 0.3 < self.input_voltage < self.well_voltage * 0.7:
			self.error(f"{self.input_voltage}V on pin {self.pin}(well={self.pin.well.net}) not between VIL and VIH from net {self.net.name}")

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

def do_circuit_simulation(elements):
	OUTPUT_PIN_STATES = [0, 1]
	HIZ_NET_STATES = ["normal"] #+ ["tryhigh", "trylow"]
	for output_values in itertools.product(OUTPUT_PIN_STATES, repeat=len(elements["chip_output_pins"])):
		output_values = dict(zip(elements["chip_output_pins"], output_values))

		for net_state in itertools.product(HIZ_NET_STATES, repeat=len(elements["nets"])):
			net_state = dict(zip(elements["nets"], net_state))

			print(f" Outputs {output_values}")
			print(" Net HiZ testers " + repr({net.name: state for net, state in net_state.items()}))
			do_circuit_state_simulation(elements, output_values, net_state)
			print("")

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
		output_voltage = pin.well.net.spice_voltage * output_values[pin]
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

		for checker in (InputOverVoltage, InputVoltage):
			checkers.append(checker(pin, simulation_inputs))

		cir.append("")

	cir.append(".control")
	cir.append("op")
	watches = set()
	for checker in checkers:
		watches.update(checker.watches())
	cir.extend(watches)
	cir.append("quit")
	cir.append(".endc")

	cir.append(".end")

	cir = '\n'.join(cir)
	#print(cir)

	with tempfile.NamedTemporaryFile() as input_file:
		input_file.write(cir.encode("utf-8"))
		input_file.flush()

		spice_output = subprocess.check_output([
			"ngspice",
			input_file.name, # input
		], stderr=subprocess.STDOUT).decode("utf-8")

	probes = {}
	for line in spice_output.split("\n")[:-2][-len(watches):]:
		probe_name, probe_value = line.split(" = ")
		probes[probe_name] = float(probe_value)

	#print(spice_output)

	found_problem = False
	for checker in checkers:
		try:
			checker.parse_probes(probes)
			checker.check()
		except SpiceChecker as e:
			print(f"  {e!r}")
			found_problem = True
			#raise
	if not found_problem:
		print("  Combination good!")
	print(f"  f{probes}")

class Chip(Part):
	pass

class OutputChip(Chip):
	PINS = [
		Pin("VCC", type=PinType.POWER_INPUT),
		Pin("OUT", type=PinType.OUTPUT, well="VCC")
	]

class InputChip(Chip):
	PINS = [
		Pin("VCC", type=PinType.POWER_INPUT),
		Pin("IN", type=PinType.INPUT, well="VCC")
	]

#class ODChip(Part):
	#PINS = [
		#Pin("VCC", type=PinType.POWER_INPUT),
		#Pin("OD", type=PinType.OUTPUT, well="VCC")
	#]

pp3300 = Net("PP3300")
pp1800 = Net("PP1800")
gnd = Net("GND")
pp3300.spice_voltage = "3.3"
pp1800.spice_voltage = "1.8"

po = OutputChip(refdes="OUTCHIP")
pp3300 >> po.VCC

pi = InputChip(refdes="INCHIP")
pp1800 >> pi.VCC

s1 = Net("SIGNAL")
s2 = Net("SIGNAL_R")
s1 << po.OUT >> R("1", to=s2)
s2 >> pi.IN

f1 = OutputChip(refdes="FIGHTCHIP1")
pp3300 >> f1.VCC
f2 = OutputChip(refdes="FIGHTCHIP2")
pp1800 >> f2.VCC

fightnet = Net("Fightnet")
fightnet << f1.OUT << f2.OUT

#for i in range(200):
for elements in scan_nets(global_context.net_list):
	do_circuit_simulation(elements)
#do_circuit_simulation(scan_net(fightnet))
