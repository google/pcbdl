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
	"Part", "Pin"
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

	def connect(self, others, direction=ConnectDirection.UNKNOWN, pin_type=PinType.PRIMARY, connection_group=None):
		if connection_group is None:
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

		# Return a copy that acts just like us, but already knows the group
		grouped_net = copy.copy(self)
		grouped_net.parent = self
		grouped_net.group = self._last_connection_group
		grouped_net._shift = grouped_net._shift_already_grouped
		return grouped_net

	def _shift_already_grouped(self, direction, others):
		self.connect(others, direction, PinType.PRIMARY, self.group)
		return self

	def __lshift__(self, others):
		return self._shift(ConnectDirection.IN, others)

	def __rshift__(self, others):
		return self._shift(ConnectDirection.OUT, others)

	MAX_REPR_CONNECTIONS = 10
	def __repr__(self):
		connected = self.connections
		if len(connected) >= self.MAX_REPR_CONNECTIONS:
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
	def grouped_connections(self):
		return tuple(tuple(group.keys()) for group in self._connections)

	@property
	def connections(self):
		return sum(self.grouped_connections, ())

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
	"""Saves everything it's given, resolves later"""
	def __init__(self, names, number=None, numbers=(), *args, **kwargs):
		if isinstance(names, str):
			names = (names,)
		self.names = tuple(name.upper() for name in names)

		self.numbers = numbers
		if number is not None:
			if isinstance(number, str):
				self.numbers = (number,) + self.numbers
			else:
				self.numbers = number + self.numbers

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

		return PartClassPin(deduplicated_names, pin_numbers, *args, **kwargs)
Pin = PinFragment

class PartClassPin(object):
	"""Pin of a Part, but no particular Part instance.
	   Contains general information about the pin (but it could be for any part of that type), nothing related to a specific part instance."""
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

	def __lshift__(self, others):
		net = self._net
		if net is None:
			# don't let the net property create a new one,
			# we want to dictate the direction to that Net
			net = Net() #defined_at: not here
			net >>= self
		return net << others

	def __lshift__(self, others):
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

class Part(object):
	PINS = []
	REFDES_PREFIX = "UNK"
	pin_names_match_nets = False
	pin_names_match_nets_prefix = ""

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

		self._generate_pin_instances(self.PINS)

		Plugin.init(self)

	def _generate_pin_instances(self, pin_names):
		cls_list = list(PinFragment.part_superclasses(self))

		for cls in cls_list:
			# syntactic sugar, .PIN list might have only names instead of the long form Pin instances
			for i, maybenames in enumerate(cls.PINS):
				if not isinstance(maybenames, Pin):
					cls.PINS[i] = PinFragment(maybenames)

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

	def _generate_refdes_from_context(self):
		if not hasattr(self, "defined_at"):
			self._context_ref_value = None
			raise Exception("No defined_at")

		if self.defined_at.startswith("<stdin>"):
			self._context_ref_value = None
			raise Exception("Can't get context from stdin")

		from .defined_at import grab_nearby_lines
		import hashlib

		tohash = repr((
			grab_nearby_lines(self.defined_at, 3), # nearby source lines
			#tuple(pin.net.name for pin in self.pins), # net names connected to this part
		))

		h = hashlib.md5(tohash.encode("utf8")).hexdigest()

		ret = "%s?h%s" % (self.REFDES_PREFIX, h[:7])
		self._context_ref_value = ret
		return ret

	@property
	def _refdes_from_context(self):
		try:
			return self._refdes_from_context_value
		except AttributeError:
			pass

		self._refdes_from_context_value = None
		self._refdes_from_context_value = self._generate_refdes_from_context()
		return self._refdes_from_context_value

	@property
	def _refdes_from_memory_address(self):
		return "%s?m%05x" % (self.REFDES_PREFIX, id(self) // 32 & 0xfffff)

	@property
	def refdes(self):
		if self._refdes is not None:
			return self._refdes

		#if self._refdes_from_context: # TODO: clean this up, it currently breaks tests
			#return self._refdes_from_context

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
