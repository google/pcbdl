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

class JellyBeanTest(unittest.TestCase):
	def test_value(self):
		class WeirdPart(JellyBean):
			UNITS = "furlong"

		p = WeirdPart("100u")
		self.assertIn("100", p.value, "where's the value we gave it?")
		self.assertIn("furlong", p.value, "where's the units?")

		p = WeirdPart("100kfurlong")
		self.assertNotIn("furlongfurlong", p.value, "unit should not show twice")

	def test_connections(self):
		class TestPart(JellyBean):
			PINS = ["PRIMARY", "SECONDARY"]

		primary_net = Net("PRIMARY_NET")
		secondary_net = Net("SECONDARY_NET")

		p = TestPart(to=secondary_net)
		primary_net << p

		self.assertIs(p.PRIMARY.net, primary_net, "<< failed")
		self.assertIs(p.SECONDARY.net, secondary_net, "to= failed")

	def test_reverse_polarized(self):
		"""Can we reverse bias a diode and still connect it right?"""
		vcc, gnd = Net("VCC"), Net("GND")

		dn = D(to=gnd)
		dr = D(to=gnd, reversed=True)
		vcc << (dn, dr)

		self.assertIs(dn.A.net, vcc)
		self.assertIs(dn.K.net, gnd)
		self.assertIs(dr.A.net, gnd)
		self.assertIs(dr.K.net, vcc)

class OnePinPartTest(unittest.TestCase):
	def test_connections(self):
		n = Net()

		tp = OnePinPart()
		n << tp
		self.assertIs(tp.net, n)

		self.assertIs(OnePinPart(to=n).net, n)

		tp = OnePinPart()
		tp.net = n
		self.assertIs(tp.net, n)

if __name__ == "__main__":
	unittest.main()
