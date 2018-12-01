from .base import *

class JellyBean(Part):
	"""2 pin Jelly Bean components.

	The main attraction to subclass this is because of the to= argument, it's very easy to chain connections
	with such a part because its pins are pretty flexible therefore easy tochoose automatically.
	"""
	PIN_NAMES = (
		("P1", "1"),
		("P2", "2"),
	)

	UNITS = ""

	def __init__(self, value=None, refdes=None, package="", populated=True, reversed=False, to=None):
		if value is None:
			value = self.value
		if not value.endswith(self.UNITS):
			value = value + self.UNITS
		super().__init__(value, refdes, package, populated)

		self._connect_pins_reversed = reversed

		if to is not None:
			to.connect(self, ConnectDirection.OUT, pin_type=PinType.SECONDARY)

	def get_pin_to_connect(self, pin_type):
		assert isinstance(pin_type, PinType)

		mapping = [0, 1]
		if self._connect_pins_reversed:
			mapping.reverse()

		if pin_type == PinType.PRIMARY:
			return self.pins[mapping[0]]
		elif pin_type == PinType.SECONDARY:
			return self.pins[mapping[1]]
		else: # pragma: no cover
			raise ValueError("Don't know how to get %s pin from %r" % (pin_type.name, self))

class OnePinPart(Part):
	PIN_NAMES = (("PIN", "P"),)

	def __init__(self, value="", refdes=None, package="", populated=True, to=None):
		super().__init__(value, refdes, package, populated)
		if to is not None:
			to.connect(self, ConnectDirection.OUT, pin_type=PinType.PRIMARY)

	def get_pin_to_connect(self, pin_type):
		if pin_type == PinType.PRIMARY:
			return self.PIN
		else: # pragma: no cover
			assert isinstance(pin_type, PinType)
			raise ValueError("Don't know how to get %s pin from %r" % (pin_type.name, self))

	@property
	def net(self):
		return self.PIN.net
	@net.setter
	def net(self, value):
		self.PIN.net = value

class TP(OnePinPart):
	"""Test Point"""
	REFDES_PREFIX = "TP"

PIN_NAMES_PLUS_MINUS = (
	("+", "P", "PLUS"),
	("-", "M", "MINUS"),
)

PIN_NAMES_BJT = (
	("B", "BASE"),
	("E", "EMITTER"),
	("C", "COLLECTOR"),
)

PIN_NAMES_FET = (
	("G", "GATE"),
	("S", "SOURCE"),
	("D", "DRAIN"),
)

class R(JellyBean):
	"""Resistor"""
	REFDES_PREFIX = "R"
	UNITS = u"\u03A9"

class C(JellyBean):
	"""Capacitor"""
	REFDES_PREFIX = "C"
	UNITS = "F"

class C_POL(C):
	"""Polarized Capacitor"""
	PIN_NAMES = PIN_NAMES_PLUS_MINUS

class L(JellyBean):
	"""Inductor"""
	REFDES_PREFIX = "L"
	UNITS = "H"

class D(JellyBean):
	"""Diode"""
	REFDES_PREFIX = "D"
	PIN_NAMES = (
		("A", "ANODE", "+"),
		("K", "CATHODE", "KATHODE", "-"),
	)

class LED(D):
	"""Light Emitting Diode"""
	REFDES_PREFIX = "LED"

class BJT(Part):
	"""BJT Transistor"""
	REFDES_PREFIX = "Q"
	PIN_NAMES = PIN_NAMES_BJT

class FET(Part):
	"""FET Transistor"""
	REFDES_PREFIX = "Q"
	PIN_NAMES = PIN_NAMES_FET
