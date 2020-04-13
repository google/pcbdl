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

from .base import *

class JellyBean(Part):
    """2 pin Jelly Bean components (this includes :class:`Resistors<pcbdl.small_parts.R>`
    and :class:`Capacitors<pcbdl.small_parts.C>`).

    The main attraction to subclass this is because of the ``to=`` argument, it's very easy to chain connections
    with such a part because its pins are pretty flexible therefore easy tochoose automatically.
    The use of this class is to allow quick connections of 2 pin devices (both pins at the same time).

    One way to do this is the ``to=`` argument, allows to connect the SECONDARY pin (usually in the same expression)
    easily without having to save the JellyBean part to a variable first::

        supply >> IC.VCC << C("100nF", to=gnd) # note how decoupling cap is fully connected

    The other way these types of parts are cool and unique is the
    :meth:`^ operator<pcbdl.small_parts.JellyBean.__rxor__>`; it allows us to describe series connections
    through Jellybean components. Here's an example with a resistor divider::

        some_net ^ R("1k") ^ attenuated_net ^ R("1k") ^ gnd
    """
    PINS = [
        ("P1", "1"),
        ("P2", "2"),
    ]

    UNITS = ""

    def __init__(self, value=None, refdes=None, package=None, part_number=None, populated=True, reversed=False, to=None):
        if value is not None:
            self.value = value
        try:
            if not value.endswith(self.UNITS):
                value += self.UNITS
        except AttributeError:
            pass # whatever, we don't even have a value

        super().__init__(value, refdes, package, part_number, populated)

        self._connect_pins_reversed = reversed

        if to is not None:
            to.connect(self, ConnectDirection.OUT, pin_type=PinType.SECONDARY)

    def get_pin_to_connect(self, pin_type, net=None):
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

    def __rxor__(self, left_net):
        """
        Implements ``left_net ^ jellybean``. Connects the left_net to the PRIMARY pin,
        then returns the JellyBean part so it can keep chaining.

        .. note:: This is similar to :meth:`left_net \<\< JellyBean()<pcbdl.Net.__lshift__>`, but
                  with the slight difference in how it can chain.
        """
        assert isinstance(left_net, Net)
        left_net << self.get_pin_to_connect(PinType.PRIMARY)
        return self

    def __xor__(self, right_net):
        """
        Implements ``jellybean ^ right_net``. Connects the right_net to the SECONDARY pin,
        then returns the JellyBean part so it can keep chaining.

        .. note:: This is similar to ``JellyBean(to=right_net)`` but a little cleaner looking.
        """
        assert isinstance(right_net, Net)
        grouped_right_net = right_net << self.get_pin_to_connect(PinType.SECONDARY)
        return grouped_right_net


class OnePinPart(Part):
    PINS = [("PIN", "P")]

    def __init__(self, value=None, refdes=None, package=None, part_number=None, populated=True, to=None):
        super().__init__(value, refdes, package, part_number, populated)
        if to is not None:
            to.connect(self, ConnectDirection.OUT, pin_type=PinType.PRIMARY)

    def get_pin_to_connect(self, pin_type, net=None):
        if pin_type == PinType.PRIMARY:
            # Perhaps we can name ourselves too after the net
            if net is not None and net._name is not None:
                if self.value == self.part_number:
                    self.value = net.name

            return self.PIN
        else: # pragma: no cover
            assert isinstance(pin_type, PinType)
            raise ValueError("Don't know how to get %s pin from %r" % (pin_type.name, self))

    @property
    def net(self):
        return self.PIN.net #defined_at: not here
    @net.setter
    def net(self, new_net):
        self.PIN.net = new_net

class TP(OnePinPart):
    """Test Point"""
    REFDES_PREFIX = "TP"
    package = "TP"
    part_number = "TP"

PINS_PLUS_MINUS = [
    ("+", "P", "PLUS", "P2"),
    ("-", "M", "MINUS", "P1"),
]

PINS_BJT = [
    ("B", "BASE"),
    ("E", "EMITTER"),
    ("C", "COLLECTOR"),
]

PINS_FET = [
    ("G", "GATE"),
    ("S", "SOURCE"),
    ("D", "DRAIN"),
]

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
    PINS = PINS_PLUS_MINUS

class L(JellyBean):
    """Inductor"""
    REFDES_PREFIX = "L"
    UNITS = "H"

class D(JellyBean):
    """Diode"""
    REFDES_PREFIX = "D"
    PINS = [
        ("A", "ANODE", "P1"),
        ("K", "CATHODE", "KATHODE", "P2"),
    ]

class LED(D):
    """Light Emitting Diode"""
    REFDES_PREFIX = "LED"
    PINS = [
        ("A", "+"),
        ("K", "-"),
    ]

class BJT(Part):
    """BJT Transistor"""
    REFDES_PREFIX = "Q"
    PINS = PINS_BJT

class FET(Part):
    """FET Transistor"""
    REFDES_PREFIX = "Q"
    PINS = PINS_FET
