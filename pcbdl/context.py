from .base import Net, Part, Plugin
import collections
__all__ = [
	"Context",
	"global_context", "nets",
]

class Context(object):
	def __init__(self, name = ""):
		self.name = name

		self.net_list = []
		self.parts_list = []
		self.named_nets = collections.OrderedDict()

		self.refdes_counters = collections.defaultdict(lambda:1)

	def new_part(self, part):
		self.parts_list.append(part)

	def new_net(self, net):
		assert(net not in self.net_list)
		self.net_list.append(net)

		if net.name is not None:
			# Add to the net list
			self.named_nets[net.name] = net

	def name_part_with_mapping(self, part, mapping):
		try:
			part_context_name = part._refdes_from_context
		except:
			# just give up, we can't get context name for some reason
			return

		for i, (final_name, context_name) in enumerate(mapping):
			if context_name == part_context_name:
				part.refdes = final_name
				break
		else:
			# couldn't find it in the mapping
			return

		# remove from mapping in case there's other parts at the same line that need to be named differently
		mapping.pop(i)

	def fill_refdes(self, mapping_file):
		try:
			with open(mapping_file, "r") as file:
				mapping = [line.strip().split(" ") for line in file.readlines()]
		except:
			mapping = []

		self.named_parts = collections.OrderedDict()
		for part in self.parts_list:
			original_name = part.refdes
			prefix = part.REFDES_PREFIX
			if original_name.startswith(prefix):
				number = original_name[len(prefix):]

				if number.startswith("?"):
					self.name_part_with_mapping(part, mapping)
					number = part.refdes[len(prefix):]
					#print ("Renaming %s -> %s with mapping file" % (original_name, part.refdes))

				if number.startswith("?"):
					while True:
						part.refdes = "%s%d" % (prefix, self.refdes_counters[prefix])
						self.refdes_counters[prefix] += 1
						if part.refdes not in self.named_parts:
							break
					#print ("Renaming %s -> %s" % (original_name, part.refdes))
				else:
					# Yay, there's a part that's already named
					# Let's remember the number for it and save it
					try:
						number = int(number)
					except ValueError:
						pass
					else:
						self.refdes_counters[prefix] = number
						#print ("Skipping ahead to %s%d+1" % (prefix, self.refdes_counters[prefix]))
						self.refdes_counters[prefix] += 1
			self.named_parts[part.refdes] = part

		with open(mapping_file, "w") as file:
			for final_name, part in self.named_parts.items():
				file.write("%s %s\n" % (final_name, part._refdes_from_context))

@Plugin.register(Net)
class NetContext(Plugin):
	def __init__(self, instance):
		global_context.new_net(instance)

@Plugin.register(Part)
class PartContext(Plugin):
	def __init__(self, instance):
		global_context.new_part(instance)

global_context = Context()
nets = global_context.named_nets
