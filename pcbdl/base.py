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

import collections
import copy
import enum
import itertools
__all__ = [
    "PinType", "ConnectDirection",
    "Net", "Part", "Pin"
]

class Plugin(object):
    def __new__(cls, instance):
        self = super(Plugin,cls).__new__(cls)
        self.instance = instance
        return self

    @staticmethod
    def register(plugin_targets):
        if not isinstance(plugin_targets, collections.abc.Iterable):
            plugin_targets = (plugin_targets,)

        def wrapper(plugin):
            for target_cls in plugin_targets:
                try:
                    target_cls.plugins
                except AttributeError:
                    target_cls.plugins = set()
                target_cls.plugins.add(plugin)
            return plugin

        return wrapper

    @staticmethod
    def init(instance):
        """Init plugins associated with this instance"""
        try:
            factories = instance.plugins
        except AttributeError:
            return
        assert type(instance.plugins) is not dict
        instance.plugins = {plugin: plugin(instance) for plugin in factories}

class ConnectDirection(enum.Enum):
    UNKNOWN = 0
    IN = 1
    OUT = 2

class PinType(enum.Enum):
    UNKNOWN = 0
    PRIMARY = 1
    SECONDARY = 2
    POWER_INPUT = 3
    POWER_OUTPUT = 4
    GROUND = 5
    INPUT = 6
    OUTPUT = 7

def _maybe_single(o):
    if isinstance(o, collections.abc.Iterable):
        yield from o
    else:
        yield o

class _PinList(collections.OrderedDict):
    def __getitem__(self, pin_name):
        if isinstance(pin_name, int):
            return tuple(self.values())[pin_name]
        pin_name = pin_name.upper()
        try:
            return super().__getitem__(pin_name)
        except KeyError:
            # try looking slowly through the other names
            for pin in self.values():
                if pin_name.upper() in pin.names:
                    return pin
            else:
                raise

    def __iter__(self):
        yield from self.values()

    def __repr__(self):
        return repr(tuple(self.values()))

class Net(object):
    _name = None
    has_name = False

    def __init__(self, name=None):
        if name is not None:
            self.name = name.upper()
        self._connections = []

        Plugin.init(self)

    def connect(self, others, direction=ConnectDirection.UNKNOWN, pin_type=PinType.PRIMARY):
        try:
            connection_group = self.group
        except AttributeError:
            connection_group = collections.OrderedDict()
            self._connections.append(connection_group)

        for other in _maybe_single(others):
            pin = None

            if isinstance(other, Part):
                pin = other.get_pin_to_connect(pin_type, self)

            if isinstance(other, PartInstancePin):
                pin = other

            if isinstance(other, Net):
                raise NotImplementedError("Can't connect nets together yet.")

            if pin is None:
                raise TypeError("Don't know how to get %s pin from %r." % (pin_type.name, other))

            connection_group[pin] = direction
            pin.net = self

        self._last_connection_group = connection_group

    def _shift(self, direction, others):
        self.connect(others, direction, PinType.PRIMARY)

        if hasattr(self, "group"):
            return self

        # Return a copy that acts just like us, but already knows the group
        grouped_net = copy.copy(self)
        grouped_net.parent = self
        grouped_net.group = self._last_connection_group
        return grouped_net

    def __lshift__(self, others):
        return self._shift(ConnectDirection.IN, others)

    def __rshift__(self, others):
        return self._shift(ConnectDirection.OUT, others)

    _MAX_REPR_CONNECTIONS = 10
    def __repr__(self):
        connected = self.connections
        if len(connected) >= self._MAX_REPR_CONNECTIONS:
            inside_str = "%d connections" % (len(connected))
        elif len(connected) == 0:
            inside_str = "unconnected"
        elif len(connected) == 1:
            inside_str = "connected to " + repr(connected[0])
        else:
            inside_str = "connected to " + repr(connected)[1:-1]
        return "%s(%s)" % (self, inside_str)

    def __str__(self):
        return self.name

    @property
    def name(self):
        if hasattr(self, "parent"):
            return self.parent.name

        if not self.has_name:
            # This path should be rare, only if the user really wants trouble
            return "ANON_NET?m%05x" % (id(self) // 32 & 0xfffff)

        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name.upper()
        self.has_name = True

    @property
    def connections(self):
        """
        A :class:`tuple` of pins connected to this net.

        Useful in the interpreter and/or when you want to inspect your schematic::

            >>> gnd.connections
            (U1.GND, VREG1.GND, U2.GND, VREG2.GND)

        """
        return sum(self.grouped_connections, ())

    @property
    def grouped_connections(self):
        """
        Similar to :attr:`connections`, but this time pins that were connected together stay in groups::

            >>> pp1800.grouped_connections
            ((U1.GND, VREG1.GND), (U2.GND, VREG2.GND))
        """
        return tuple(tuple(group.keys()) for group in self._connections)

    def is_net_of_class(self, keywords):
        for keyword in keywords:
            if keyword in self.name:
                return True

    @property
    def is_power(self):
        return self.is_net_of_class(("VCC", "PP", "VBUS"))

    @property
    def is_gnd(self):
        return self.is_net_of_class(("GND",))

class PinFragment(object):
    """
    This is the fully featured (as opposed to just a tuple of parameters)
    element of :attr:`PINS<pcbdl.Part.PINS>` at the time of writing
    a :class:`Part<pcbdl.Part>`. Saves all parameters it's given,
    merges later once the Part is fully defined.

    .. warning:: Just like the name implies this is just a fragment of the
        information we need for the pin. It's possible the Part needs to be
        overlayed on top of its parents before we can have a complete picture.
        Ex: this could be the pin labeled "PA2" of a microcontroller, but until
        the part is told what package it is, we don't really know the pin
        number.
    """
    def __init__(self, names_or_numbers=(), names_if_numbers=None, *args, **kwargs):
        # Check if short form for the positional arguments
        if names_if_numbers is None:
            names, numbers = names_or_numbers, ()
        else:
            names, numbers = names_if_numbers, names_or_numbers

        if isinstance(names, str):
            names = (names,)
        names += kwargs.pop("names", ())
        try:
            names += (kwargs.pop("name"),)
        except KeyError:
            pass
        names = tuple(name.upper() for name in names)
        self.names = names

        if isinstance(numbers, (str, int)):
            numbers = (numbers,)
        numbers += kwargs.pop("numbers", ())
        try:
            numbers += (kwargs.pop("number"),)
        except KeyError:
            pass
        numbers = tuple(str(maybe_int) for maybe_int in numbers)
        self.numbers = numbers

        self.args = args
        self.kwargs = kwargs

        Plugin.init(self)

    def __repr__(self):
        def arguments():
            yield repr(self.names)
            if self.numbers:
                yield "numbers=" + repr(self.numbers)
            for arg in self.args:
                yield repr(arg)
            for name, value in self.kwargs.items():
                yield "%s=%r" % (name, value)
        return "PinFragment(%s)" % (", ".join(arguments()))

    def __eq__(self, other):
        """If any names match between two fragments, we're talking about the same pin. This is associative, so it chains through other fragments."""
        for my_name in self.names:
            if my_name in other.names:
                return True
        return False

    @staticmethod
    def part_superclasses(part):
        for cls in type(part).__mro__:
            if cls is Part:
                return
            yield cls

    @staticmethod
    def gather_fragments(cls_list):
        all_fragments = [pin for cls in cls_list for pin in cls.PINS]
        while len(all_fragments) > 0:
            same_pin_fragments = []
            same_pin_fragments.append(all_fragments.pop(0))
            pin_index = 0
            while True:
                try:
                    i = all_fragments.index(same_pin_fragments[pin_index])
                    same_pin_fragments.append(all_fragments.pop(i))
                except ValueError:
                    pin_index += 1 # try following the chain of names, maybe there's another one we need to search by
                except IndexError:
                    break # probably no more fragments for this pin
            yield same_pin_fragments

    @staticmethod
    def resolve(fragments):
        # union the names, keep order
        name_generator = (n for f in fragments for n in f.names)
        seen_names = set()
        deduplicated_names = [n for n in name_generator if not (n in seen_names or seen_names.add(n))]

        pin_numbers = [number for fragment in fragments for number in fragment.numbers]

        # union the args and kwargs, stuff near the front has priority to override
        args = []
        kwargs = {}
        for fragment in reversed(fragments):
            args[:len(fragment.args)] = fragment.args
            kwargs.update(fragment.kwargs)

        part_class_pin = PartClassPin(deduplicated_names, pin_numbers, *args, **kwargs)
        part_class_pin._fragments = fragments
        return part_class_pin

    @staticmethod
    def second_name_important(pin):
        """
        Swap the order of the pin names so the functional (second) name is first.

        Used as a :func:`Part._postprocess_pin filter<pcbdl.Part._postprocess_pin>`.
        """
        pin.names = pin.names[1:] + (pin.names[0],)
Pin = PinFragment

class PartClassPin(object):
    """
    Pin of a Part, but no particular Part instance.
    Contains general information about the pin (but it could be for any
    part of that type), nothing related to a specific part instance.
    """
    well_name = None

    def __init__(self, names, numbers, type=PinType.UNKNOWN, well=None):
        self.names = names
        self.numbers = numbers
        self.type = type
        self.well_name = well

        Plugin.init(self)

    @property
    def name(self):
        return self.names[0]

    @property
    def number(self):
        return self.numbers[0]

    def __str__(self):
        return "Pin %s" % (self.name)
    __repr__ = __str__

class PartInstancePin(PartClassPin):
    """Particular pin of a particular part instance. Can connect to nets. Knows the refdes of its part."""
    _net = None

    def __init__(self, part_instance, part_class_pin, inject_number=None):
        # copy state of the Pin to be inherited, then continue as if the parent class always existed that way
        self.__dict__.update(part_class_pin.__dict__.copy())
        # no need to call PartClassPin.__init__

        self._part_class_pin = part_class_pin

        # save arguments
        self.part = part_instance

        if inject_number is not None:
            self.numbers = (inject_number,)
        assert self.numbers is not None, "this Pin really should have had real pin numbers assigned by now"

        well_name = self.well_name
        if well_name is not None:
            try:
                self.well = self.part.pins[well_name]
            except KeyError:
                raise KeyError("Couldn't find voltage well pin %s on part %r" % (well_name, part_instance))
            if self.well.type not in (PinType.POWER_INPUT, PinType.POWER_OUTPUT):
                raise ValueError("The chosen well pin %s is not a power pin (but is %s)" % (self.well, self.well.type))

        Plugin.init(self)

    @property
    def net(self):
        """
        The :class:`Net<pcbdl.Net>` that this pin is connected to.

        If it's not connected to anything yet, we'll get a fresh net.
        """
        if self._net is None:
            fresh_net = Net() #defined_at: not here
            return fresh_net << self
            #fresh_net.connect(self, direction=ConnectDirection.UNKNOWN) # This indirectly sets self.netf
        return self._net
    @net.setter
    def net(self, new_net):
        if self._net is not None:
            # TODO: Maybe just unify the existing net and the new
            # net and allow this.
            raise ValueError("%s pin is already connected to a net (%s). Can't connect to %s too." %
                (self, self._net, new_net))

        self._net = new_net

    def connect(self, *args, **kwargs):
        self.net.connect(*args, **kwargs)

    def __lshift__(self, others):
        net = self._net
        if net is None:
            # don't let the net property create a new one,
            # we want to dictate the direction to that Net
            net = Net() #defined_at: not here
            net >>= self
        return net << others

    def __rshift__(self, others):
        net = self._net
        if net is None:
            # don't let the net property create a new one,
            # we want to dictate the direction to that Net
            net = Net() #defined_at: not here
            net <<= self
        return net >> others

    def __str__(self):
        return "%r.%s" % (self.part, self.name)
    __repr__ = __str__

class PinFragmentList(list):
    """Used as a marker that we have visited Part.PINS and converted all the elements to PinFragment."""
    def __init__(self, part_cls):
        self.part_cls = part_cls
        list.__init__(self, part_cls.PINS)
        for i, maybenames in enumerate(self):
            # syntactic sugar, .PIN list might have only names instead of the long form Pin instances
            if not isinstance(maybenames, Pin):
                self[i] = PinFragment(maybenames)

        if part_cls._postprocess_pin.__code__ == Part._postprocess_pin.__code__:
            # Let's not waste our time with a noop
            return
        for i, _ in enumerate(self):
            # do user's postprocessing
            part_cls._postprocess_pin(self[i])

class Part(object):
    """
    This is the :ref:`base class<python:tut-inheritance>` for any new Part the writer of a schematic or a part librarian has to make. ::

        class Transistor(Part):
            REFDES_PREFIX = "Q"
            PINS = ["B", "C", "E"]
    """

    PINS = []
    """
    This is how the pins of a part are defined, as a :class:`list` of pins.

    Each pin entry can be one of:

    * :class:`Pin`
    * :class:`tuple` of names which will automatically be turned into a :class:`Pin`
    * just one :class:`string<str>`, representing a pin name, if one cares about nothing else.

    So these are all valid ways to define a pin (in decreasing order of detail), and mean about the same thing::

        PINS = [
            Pin("1", ("GND", "GROUND"), type=PinType.POWER_INPUT),
            ("GND", "GROUND"),
            "GND",
        ]

    See the :class:`Pins Section<Pin>` for the types of properties that can be
    defined on each Pin entry.
    """

    pins = _PinList()
    """
    Once the Part is instanced (aka populated on the schematic), our pins become real too (they turn into :class:`PartInstancePins<pcbdl.base.PartInstancePin>`).
    This is a :class:`dict` like object where the pins are stored. One can look up pins by any of its names::

        somechip.pins["VCC"]

    Though most pins are also directly populated as a attributes to the part, so this is equivalent::

        somechip.VCC

    The pins list can still be used to view all of the pins at once, like on the console:

        >>> diode.pins
        (D1.VCC, D1.NC, D1.P1, D1.GND, D1.P2)
    """

    REFDES_PREFIX = "UNK"
    """
    The prefix that every reference designator of this part will have.

    Example: :attr:`"R"<pcbdl.small_parts.R.REFDES_PREFIX>` for resistors,
    :attr:`"C"<pcbdl.small_parts.C.REFDES_PREFIX>` for capacitors.

    The auto namer system will eventually put numbers after the prefix to get the complete :attr:`refdes`.
    """

    pin_names_match_nets = False
    """
    Sometimes when connecting nets to a part, the pin names become very redundant::

        Net("GND") >> somepart.GND
        Net("VCC") >> somepart.VCC
        Net("RESET") >> somepart.RESET

    We can use this variable tells the part to pick the right pin depending on
    the variable name, at that point the part itself can be used in lieu of
    the pin::

        Net("GND") >> somepart
        Net("VCC") >> somepart
        Net("RESET") >> somepart
    """

    pin_names_match_nets_prefix = ""
    """
    When :attr:`pin_names_match_nets` is active, it strips a
    little bit of the net name in case it's part of a bigger net group::

        class SPIFlash(Part):
            pin_names_match_nets = True
            pin_names_match_nets_prefix = "SPI1"
            PINS = ["MOSI", "MISO", "SCK", "CS", ...]
        ...
        Net("SPI1_MOSI") >> spi_flash # autoconnects to the pin called only "MOSI"
        Net("SPI1_MISO") << spi_flash # "MISO"
        Net("SPI1_SCK")  >> spi_flash # "SCK"
        Net("SPI1_CS")   >> spi_flash # "CS"
    """

    def __init__(self, value=None, refdes=None, package=None, part_number=None, populated=True):
        if part_number is not None:
            self.part_number = part_number
        if value is not None:
            self.value = value

        # if we don't have a value xor a package, use one of them for both
        if not hasattr(self, "value") and hasattr(self, "part_number"):
            self.value = self.part_number
        if not hasattr(self, "part_number") and hasattr(self, "value"):
            self.part_number = self.value
        # if we don't have either, then there's not much we can do
        if not hasattr(self, "value") and not hasattr(self, "part_number"):
            self.value = ""
            self.part_number = ""

        self._refdes = refdes
        if package is not None:
            self.package = package
        self.populated = populated

        self._generate_pin_instances()

        Plugin.init(self)

    def _generate_pin_instances(self):
        cls_list = list(PinFragment.part_superclasses(self))

        # process the pin lists a little bit
        for cls in cls_list:
            # but only if we didn't already do it
            if isinstance(cls.PINS, PinFragmentList):
                continue
            cls.PINS = PinFragmentList(cls)

        self.__class__.pins = [PinFragment.resolve(f) for f in PinFragment.gather_fragments(cls_list)]

        self.pins = _PinList()
        for i, part_class_pin in enumerate(self.__class__.pins):
            # if we don't have an assigned pin number, generate one
            inject_pin_number = str(i + 1) if not part_class_pin.numbers else None

            pin = PartInstancePin(self, part_class_pin, inject_pin_number)
            self.pins[pin.name] = pin

            # save the pin as an attr for this part too
            for name in pin.names:
                self.__dict__[name] = pin

    @property
    def _refdes_from_memory_address(self):
        return "%s?m%05x" % (self.REFDES_PREFIX, id(self) // 32 & 0xfffff)

    @property
    def refdes(self):
        """
        Reference designator of the part. Example: R1, R2.

        It's essentially the unique id for the part that will be used to
        refer to it in most output methods.
        """
        if self._refdes is not None:
            return self._refdes

        # make up a refdes based on memory address
        return self._refdes_from_memory_address

    @refdes.setter
    def refdes(self, new_value):
        self._refdes = new_value.upper()

    def __repr__(self):
        return self.refdes

    def __str__(self):
        return "%s - %s%s" % (self.refdes, self.value, " DNS" if not self.populated else "")

    def get_pin_to_connect(self, pin_type, net=None): # pragma: no cover
        assert isinstance(pin_type, PinType)

        if self.pin_names_match_nets and net is not None:
            prefix = self.pin_names_match_nets_prefix
            net_name = net.name
            for pin in self.pins:
                for pin_name in pin.names:
                    if pin_name == net_name:
                        return pin
                    if prefix + pin_name == net_name:
                        return pin
            raise ValueError("Couldn't find a matching named pin on %r to connect the net %s" % (self, net_name))

        raise NotImplementedError("Don't know how to get %s pin from %r" % (pin_type.name, self))

    @classmethod
    def _postprocess_pin(cls, pin):
        """
        It's sometimes useful to process the pins from the source code before the part gets placed down.
        This method will be called for each pin by each subclass of a Part.

        Good uses for this:

        *  :func:`Raise the importance of the second name<pcbdl.base.PinFragment.second_name_important>` in a connector, so the more semantic name is the primary name, not the pin number::

            PINS = [
                ("P1", "Nicer name"),
            ]
            _postprocess_pin = Pin.second_name_important

        * Populate alternate functions of a pin if they follow an easy pattern.
        * A simple programmatic alias on pin names without subclassing the part itself.
        """
        raise TypeError("This particular implementation of _postprocess_pin should be skipped by PinFragmentList()")
