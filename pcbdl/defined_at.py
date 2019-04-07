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

		# Skip #defined_at: not here code
		while (stack_trace[0].code_context is not None and
		    "#defined_at: not here" in stack_trace[0].code_context[0]):
			stack_trace.pop(0)

		# Escape all the inheritances of that class
		while (stack_trace[0].code_context is not None and
		       "super()" in stack_trace[0].code_context[0]):
			stack_trace.pop(0)

		# Skip #defined_at: not here code again
		while (stack_trace[0].code_context is not None and
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
