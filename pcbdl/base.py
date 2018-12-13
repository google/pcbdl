import collections
import enum
import inspect

__all__ = [
	"_get_defined_at", "_maybe_single",
	"PinType", "ConnectDirection",
	"Net", "Part", "Pin",
	"Context", "global_context",
]

def _get_defined_at():
	stack_trace = inspect.stack()
	while stack_trace.pop(0):
		if stack_trace[0].filename == "<stdin>":
			break # pragma: no cover, hard to test stdin

		if stack_trace[0].filename == "<string>":
			# probably in an eval/exec
			continue # pragma: no cover

		# Escape all the inheritances
		if "super()" in stack_trace[0].code_context[0]:
			continue

		# Escape from this function
		if "_get_defined_at" in stack_trace[0].code_context[0]:
			continue

		# Make sure it's not a pin implicit anonymous net
		if "ParticularPin._create_anonymous_net" in stack_trace[0].code_context[0]:
			continue

		break
	interesting_frame = stack_trace[0]
	defined_at = '%s:%d' % (interesting_frame.filename, interesting_frame.lineno)
	return defined_at

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

class Context(object):
	def __init__(self, name = ""):
		self.name = name

		self.net_list = []
		self.named_nets = collections.OrderedDict()

		self.refdes_counters = collections.defaultdict(lambda:1)

	def new_net(self, net):
		assert(net not in self.net_list)
		self.net_list.append(net)

		if net.name is not None:
			# Add to the net list
			self.named_nets[net.name] = net

	@property
	def parts_list(self):
		parts_list = []
		for net in self.net_list:
			for pin in net.connections:
				part = pin.part
				if part not in parts_list:
					parts_list.append(part)
		return parts_list

	def fill_refdes(self):
		self.named_parts = {}
		for part in self.parts_list:
			original_name = part.refdes
			prefix = part.REFDES_PREFIX
			if original_name.startswith(prefix):
				number = original_name[len(prefix):]

				if number.startswith("?"):
					while True:
						part.refdes = "%s%d" % (prefix, self.refdes_counters[prefix])
						self.refdes_counters[prefix] += 1
						if part.refdes not in self.named_parts:
							break
					#print ("Renaming %s -> %s" % (original_name, part.refdes))
				else:
					try:
						number=int(number)
					except ValueError:
						continue
					self.refdes_counters[prefix] = number
					#print ("Skipping ahead to %s%d+1" % (prefix, self.refdes_counters[prefix]))
					self.refdes_counters[prefix] += 1
				self.named_parts[part.refdes] = part

global_context = Context()
nets = global_context.named_nets

class Net(object):
	def __init__(self, name=None, context = global_context):
		if name is not None:
			name = name.upper()
		self.name = name
		self._connections = collections.OrderedDict()

		context.new_net(self)

		self.defined_at = _get_defined_at()

	def connect(self, others, direction=ConnectDirection.UNKNOWN, pin_type=PinType.PRIMARY):
		for other in _maybe_single(others):
			pin = None

			if isinstance(other, Part):
				pin = other.get_pin_to_connect(pin_type)

			if isinstance(other, ParticularPin):
				pin = other

			if isinstance(other, Net):
				raise NotImplementedError("Can't connect nets together yet.")

			if pin is None:
				raise TypeError("Don't know how to get %s pin from %r." % (pin_type.name, other))

			self._connections[pin] = direction
			pin.net = self

	def __lshift__(self, others):
		self.connect(others, ConnectDirection.IN, PinType.PRIMARY)
		return self

	def __rshift__(self, others):
		self.connect(others, ConnectDirection.OUT, PinType.PRIMARY)
		return self

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
		if self.name is None:
			return "AnonymousNet"
		return "%s" % self.name

	@property
	def connections(self):
		return tuple(self._connections.keys())

class Pin(object):
	well_name = None
	"""Generic Pin instance of a Part class, but no particular Part instance.
	   Contains general information about the pin (but it could be for any part of that type), nothing specific to a specific part."""
	def __init__(self, names, numbers=None, type=PinType.UNKNOWN, well=None):
		if isinstance(names, str):
			names = (names,)
		self.names = tuple(name.upper() for name in names)
		self.numbers = numbers
		self.type = type
		self.well_name = well

		self.defined_at = _get_defined_at()

	@property
	def name(self):
		return self.names[0]

	@property
	def number(self):
		return self.numbers[0]

	def __str__(self):
		return "Pin %s" % (self.name)
	__repr__ = __str__

class ParticularPin(Pin):
	"""A pin from an actual instance of a Part, might be connected to nets. Each Part instance has different ParticularPin instances."""
	_create_anonymous_net = Net
	_net = None

	def __init__(self, part_instance, part_pin_instance, number=None):
		# copy state of the Pin to be inherited, then continue as if the parent class always existed that way
		self.__dict__.update(part_pin_instance.__dict__.copy())
		# no need to call Pin.__init__
		self._part_pin_instance = part_pin_instance

		# save arguments
		self.part = part_instance

		if number is not None:
			self.numbers = (number,)
		assert self.numbers is not None, "this Pin really should have had real pin numbers assigned by now"

		well_name = self._part_pin_instance.well_name
		if well_name is not None:
			try:
				self.well = self.part.pins[well_name]
			except KeyError:
				raise KeyError("Couldn't find voltage well pin %s on part %r" % (well_name, part_instance))
			if self.well.type not in (PinType.POWER_INPUT, PinType.POWER_OUTPUT):
				raise ValueError("The chosen well pin %s is not a power pin (but is %s)" % (self.well, self.well.type))

	@property
	def net(self):
		if self._net is None:
			fresh_net = ParticularPin._create_anonymous_net()
			fresh_net.connect(self, direction=ConnectDirection.UNKNOWN) # This indirectly sets self.net
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
		if self._net is None:
			# don't let the net property create a new one,
			# we want to dictate the direction to that Net
			ParticularPin._create_anonymous_net() >> self
		return self.net << others

	def __rshift__(self, others):
		if self._net is None:
			# don't let the net property create a new one,
			# we want to dictate the direction to that Net
			ParticularPin._create_anonymous_net() << self
		return self.net >> others

	def __str__(self):
		return "%r.%s" % (self.part, self.name)
	__repr__ = __str__

class Part(object):
	PINS = []
	REFDES_PREFIX = "UNK"
	value = ""

	def __init__(self, value=None, refdes=None, package=None, populated=True):
		if value is None:
			value = self.value
		self.value = value
		self._refdes = refdes

		if package is not None:
			self.package = package
		self.populated = populated

		self._generate_pin_instances(self.PINS)

		self.defined_at = _get_defined_at()

	def _generate_pin_instances(self, pin_names):
		# syntactic sugar, .PIN list might have only names instead of the long form Pin instances
		for i, maybenames in enumerate(self.PINS):
			if not isinstance(maybenames, Pin):
				self.PINS[i] = Pin(maybenames)

		self.pins = _PinList()
		for i, part_class_pin in enumerate(self.PINS):
			# if we don't have an assigned pin number, generate one
			pin_number = str(i) if part_class_pin.numbers is None else None

			pin = ParticularPin(self, part_class_pin, pin_number)
			self.pins[pin.name] = pin

			# save the pin as an attr for this part too
			for name in pin.names:
				self.__dict__[name] = pin

	@property
	def refdes(self):
		if self._refdes is None:
			return "%s?%05x" % (self.REFDES_PREFIX, id(self) // 32 & 0xfffff)
		return self._refdes
	@refdes.setter
	def refdes(self, new_value):
		self._refdes = new_value.upper()

	def __repr__(self):
		return self.refdes

	def __str__(self):
		return "%s - %s%s" % (self.refdes, self.value, " DNS" if not self.populated else "")

	def get_pin_to_connect(self, pin_type): # pragma: no cover
		assert isinstance(pin_type, PinType)
		raise NotImplementedError("Don't know how to get %s pin from %r" % (pin_type.name, self))
