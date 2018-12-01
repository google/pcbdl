#!/usr/bin/env python3

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
			PIN_NAMES = ("PRIMARY", "SECONDARY")

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
