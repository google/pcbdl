#!/usr/bin/env python3

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

import unittest
from pcbdl import *
import pcbdl.spice as spice

class OutputChip(Part):
	PINS = [
		Pin("VCC", type=PinType.POWER_INPUT),
		Pin("OUT", type=PinType.OUTPUT, well="VCC")
	]

class InputChip(Part):
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

class IncompletePartTest(unittest.TestCase):
	def test(self):
		class IncompletePart(Part):
			PINS = ["IDKPIN"]

		idknet = Net("IDKNET") << IncompletePart().IDKPIN
		with self.assertRaisesRegex(spice.CannotStartSimulation, "unknown type PinType"):
			spice.do_circuit_simulation(spice.scan_net(idknet))

class CurrentLeakTest(unittest.TestCase):
	def test(self):
		# Define a circuit that causes a current leak
		po = OutputChip(refdes="OUTCHIP")
		pp3300 >> po.VCC

		pi = InputChip(refdes="INCHIP")
		pp1800 >> pi.VCC

		s1 = Net("CURRENT_LEAK")
		s2 = Net("CURRENT_LEAK_R")
		s1 << po.OUT >> R("100k", to=s2)
		s2 >> pi.IN

		#Make sure we catch it
		with self.assertRaises(spice.InputOverVoltage) as cm:
			spice.do_circuit_simulation(spice.scan_net(s1))
		print(cm.exception)

		# Make sure we caught the right pin
		checker = cm.exception
		self.assertIs(checker.pin, pi.IN)

class DriveFightTest(unittest.TestCase):
	def test(self):
		f1 = OutputChip(refdes="FIGHTCHIP1")
		pp3300 >> f1.VCC
		f2 = OutputChip(refdes="FIGHTCHIP2")
		pp1800 >> f2.VCC

		fightnet = Net("Fightnet")
		fightnet << f1.OUT << f2.OUT

		with self.assertRaises(spice.OutputOvercurrent) as cm:
			spice.do_circuit_simulation(spice.scan_net(fightnet))
		print(cm.exception)

class InputVoltageWeakTest(unittest.TestCase):
	def test(self):
		"""Make sure VIH and VIL work."""
		po = OutputChip(refdes="WEAKOUTCHIP")
		pp1800 >> po.VCC
		pi = InputChip(refdes="VILCHIP")
		pp3300 >> pi.VCC

		weaknet = Net("WEAKNET") << po.OUT >> pi.IN

		with self.assertRaises(spice.InputVoltageWeak) as cm:
			spice.do_circuit_simulation(spice.scan_net(weaknet))
		print(cm.exception)

class HizTest(unittest.TestCase):
	def test(self):
		"""Do we catch undriven inputs?"""
		pi = InputChip(refdes="HIZCHIP")
		pp3300 >> pi.VCC

		hiznet = Net("HIZNET") >> pi.IN

		with self.assertRaises(spice.HiZ) as cm:
			spice.do_circuit_simulation(spice.scan_net(hiznet))
		print(cm.exception)

class PerformanceTest(unittest.TestCase):
	def test(self):
		"""Simulating 1000 nets."""
		po1 = OutputChip(refdes="PERFCHIPO1")
		po2 = OutputChip(refdes="PERFCHIPO2")
		pp3300 >> po1.VCC
		pp3300 >> po2.VCC

		pi1 = InputChip(refdes="PERFCHIPI1")
		pi2 = InputChip(refdes="PERFCHIPI2")
		pp1800 >> pi1.VCC
		pp1800 >> pi2.VCC

		n = Net("PERFNET")
		n << po1.OUT << po2.OUT >> pi1.IN >> pi2.IN

		for i in range(1000):
			spice.do_circuit_simulation(spice.scan_net(n), raise_errors=False)

if __name__ == "__main__":
	unittest.main()
