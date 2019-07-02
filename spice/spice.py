from pcbdl import *
import collections
import subprocess
import tempfile

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
pp3300 << po.OUT >> R("100", to=s2)
s2 >> pi.IN

f1 = OutputChip(refdes="FIGHTCHIP1")
pp3300 >> f1.VCC
f2 = OutputChip(refdes="FIGHTCHIP2")
pp1800 >> f2.VCC

fightnet = Net("Fightnet")
fightnet << f1.OUT << f2.OUT


class SpiceError(Exception):
	pass


OUTPUT_PIN_IMPEDANCE = "5ohm"
OUTPUT_PIN_CURRENT_LIMIT = 0.1
CLAMP_DIODE_MODEL = "Default"

def r_spice_helpler(self, pin):
	other_pins = list(set(self.pins) - set((pin,)))
	spice_contents = f"R{self.refdes} net_{self.P1.net} net_{self.P2.net} {self.value}"
	return spice_contents, other_pins
R.spice_helpler = r_spice_helpler

#elif isinstance(part, R):
			#other_pin, = set(part.pins) - set((pin,))
			#other_net = other_pin.net
			#yield f"R{part.refdes} net_{net.name} net_{other_net.name} {part.value}"
			#yield from scan_net(other_net, watches, other_pin)

def check_output_overcurrent(current, pin, net, all_probes):
	if abs(current) > OUTPUT_PIN_CURRENT_LIMIT:
		output_voltage = all_probes[f"pinnode_{pin}".lower()]
		raise SpiceError(f"Overcurrent({-current}A) on pin {pin} when outputting {output_voltage}V toward net {net.name}.")

def check_input_overvoltage(diode_current, pin, net, all_probes):
	if diode_current > 0:
		net_voltage = all_probes[f"net_{net.name}".lower()]
		raise SpiceError(f"Overvoltage({net_voltage}V) on pin {pin}(well={pin.well.net}) from net {net.name}")

def scan_net(net, watches, start_pin=None):
	"""Yields virtual components for each pin on a net, ignoring start_pin."""

	yield f"* Net: {net!r}"
	if start_pin is not None:
		yield f"* Ignoring pin {start_pin} that got us here."
	watches.append((f"net_{net.name}", None, None))

	for pin in net.connections:
		if pin is start_pin:
			# just ignore so we don't go backwards
			continue

		part = pin.part

		if hasattr(part, "spice_helpler"):
			spice_contents, other_pins = part.spice_helpler(pin)
			yield spice_contents
			for other_pin in other_pins:
				other_net = other_pin.net
				if other_net.is_gnd or other_net.is_power:
					continue
				yield from scan_net(other_net, watches, other_pin)
		else:
			yield "* Pin: %r" % pin

			if pin.type == PinType.OUTPUT:
				output_voltage = pin.well.net.spice_voltage
				yield f"V_{pin} pinnode_{pin} 0 {output_voltage}"
				yield f"R{pin} pinnode_{pin} net_{net.name} {OUTPUT_PIN_IMPEDANCE}" # TODO(variable resistor, CCVS)

				watches.append((f"pinnode_{pin}", None, None))
				watches.append((f"I(V_{pin})", pin, check_output_overcurrent))

			elif pin.type == PinType.INPUT:
				yield f"Vwell_{pin} wellnode_{pin} 0 {pin.well.net.spice_voltage}"
				yield f"Dclamp_{pin} net_{net.name} wellnode_{pin} {CLAMP_DIODE_MODEL}"

				watches.append((f"I(Vwell_{pin})", pin, check_input_overvoltage))
			else:
				raise SpiceError(f"Cannot add pin {pin} into the SPICE simulation, unknown type {pin.type}.")

			yield ""

	yield f"* End net {net.name}"

def spice_generator(net, watches):
	"""Yields the whole spice .cir starting from net."""
	yield f"PCBDL Analysis starting at net {net!r}"

	yield from scan_net(net, watches)

	yield ".control"
	yield "op"
	for watch in watches:
		probe, *_ = watch
		yield f"print {probe}"
	yield "quit"
	yield ".endc"

	yield ".end"

def spice_runner(net):
	watches = [] # [(probe, pin, checker_function(probe_value, pin, net, all_probes)), ...]
	cir_contents = '\n'.join(spice_generator(net, watches))

	print(cir_contents)

	with tempfile.NamedTemporaryFile() as input_file:
		input_file.write(cir_contents.encode("utf-8"))
		input_file.flush()

		spice_output = subprocess.check_output([
			"ngspice",
			input_file.name, # input
		]).decode("utf-8")

	probes = {}
	for line in spice_output.split("\n")[:-2][-len(watches):]:
		probe_name, probe_value = line.split(" = ")
		probes[probe_name] = float(probe_value)

	#print(spice_output)

	found_problem = False
	for probe, pin, checker_function in watches:
		if checker_function is not None:
			net = pin.net
			try:
				checker_function(probes[probe.lower()], pin, net, probes)
			except SpiceError as e:
				print(repr(e))
				found_problem = True

	if found_problem:
		print(probes)

for n in global_context.net_list:
	if n.is_gnd or n.is_power:
		continue
	if not n.connections:
		continue
	spice_runner(n)
