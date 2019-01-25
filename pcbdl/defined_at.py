from .base import *

__all__ = []

@plugin
class DefinedAt(Net, Part, PinFragment):
	def init(self):
		stack_trace = inspect.stack()

		# Escape from this function
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

		defined_at_frame = stack_trace[0]
		self.defined_at = '%s:%d' % (defined_at_frame.filename, defined_at_frame.lineno)
