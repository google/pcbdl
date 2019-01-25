from .base import *

__all__ = [
	"Context",
	"global_context", "nets",
]

class Context(object):
	def __init__(self, name = ""):
		self.name = name

		self.net_list = []
		self.named_nets = collections.OrderedDict()

		self.refdes_counters = collections.defaultdict(lambda:1)

	def new_net(self, net):
		#assert(net not in self.net_list)
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

@plugin
class NetContext(Net):
	def init(self):
		global_context.new_net(self)

global_context = Context()
nets = global_context.named_nets
