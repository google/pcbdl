from .base import Net, Part, PinFragment, Plugin

import inspect
__all__ = []

source_code = {}
def grab_nearby_lines(defined_at, range_):
	filename, lineno = defined_at.split(":")
	lineno = int(lineno)

	if filename not in source_code:
		with open(filename) as file:
			source_code[filename] = tuple(file.read().split("\n"))

	range_ = slice(lineno - range_, lineno + range_ - 1)

	return source_code[filename][range_]

@Plugin.register((Net, Part, PinFragment))
class DefinedAt(Plugin):
	def __init__(self, instance):
		stack_trace = inspect.stack()

		# Escape from this function
		stack_trace.pop(0)

		# Escape the plugin architecture
		stack_trace.pop(0)
		stack_trace.pop(0)

		# Escape the caller function (probably the __init__ of the class that has the plugin)
		stack_trace.pop(0)

		# Make sure it's not a pin implicit anonymous net
		if (stack_trace[0].code_context is not None and
		    "PartInstancePin._create_anonymous_net" in stack_trace[0].code_context[0]):
			stack_trace.pop(0)

		# Escape all the inheritances of that class
		while (stack_trace[0].code_context is not None and
		       "super()" in stack_trace[0].code_context[0]):
			stack_trace.pop(0)

		# Skip #defined_at: not here code
		if (stack_trace[0].code_context is not None and
		    "#defined_at: not here" in stack_trace[0].code_context[0]):
			stack_trace.pop(0)

		self.frame = stack_trace[0]

		label_locals_with_variable_names(self.frame.frame.f_locals)

		instance.defined_at = '%s:%d' % (self.frame.filename, self.frame.lineno)

def label_locals_with_variable_names(locals_dict):
	for variable_name, instance in locals_dict.items():
		if not isinstance(instance, (Net, Part)):
			continue

		if hasattr(instance, variable_name):
			continue

		instance.variable_name = variable_name
