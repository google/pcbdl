#!/usr/bin/env python3
"""
Super trivial voltage divider circuit.
"""

from pcbdl import *

vin, gnd = Net("vin"), Net("gnd")

Net("vout") << (
	R("100k", to=vin),
	R("200k", to=gnd),
)
