#!/usr/bin/env python3
"""
Simple Class A amplifier example.

https://www.electronics-tutorials.ws/amplifier/amp_5.html
"""

from pcbdl import *

class Q(Part):
	REFDES_PREFIX="Q"
	PIN_NAMES = PIN_NAMES_BJT


ac_coupling_value = "1000u"

vcc, gnd = Net("vcc"), Net("gnd")

q = Q("2n3904")

C = C_POL

q.BASE << (
	C(ac_coupling_value, to=Net("vin")),
	R("1k", to=vcc),
	R("1k", to=gnd),
)

q.COLLECTOR << (
	C(ac_coupling_value, to=Net("vout")),
	R("100", to=vcc),
)

q.EMITTER << (
	R("100", "Rc", to=gnd),
	C("1u", "C10", to=gnd),
)
