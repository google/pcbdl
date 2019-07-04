#!/usr/bin/env python3

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

from cffi import FFI
import ctypes.util
import signal
import warnings

ffi = FFI()
ffi.cdef("""
struct ngcomplex {
    double cx_real;
    double cx_imag;
};

typedef struct ngcomplex ngcomplex_t;

typedef struct vector_info {
    char *v_name;		/* Same as so_vname. */
    int v_type;			/* Same as so_vtype. */
    short v_flags;		/* Flags (a combination of VF_*). */
    double *v_realdata;		/* Real data. */
    ngcomplex_t *v_compdata;	/* Complex data. */
    int v_length;		/* Length of the vector. */
} vector_info, *pvector_info;

typedef struct vecvalues {
    char* name;        /* name of a specific vector */
    double creal;      /* actual data value */
    double cimag;      /* actual data value */
    bool is_scale;     /* if 'name' is the scale vector */
    bool is_complex;   /* if the data are complex numbers */
} vecvalues, *pvecvalues;

typedef struct vecvaluesall {
    int veccount;      /* number of vectors in plot */
    int vecindex;      /* index of actual set of vectors. i.e. the number of accepted data points */
    pvecvalues *vecsa; /* values of actual set of vectors, indexed from 0 to veccount - 1 */
} vecvaluesall, *pvecvaluesall;

typedef struct vecinfo
{
    int number;     /* number of vector, as postion in the linked list of vectors, starts with 0 */
    char *vecname;  /* name of the actual vector */
    bool is_real;   /* TRUE if the actual vector has real data */
    void *pdvec;    /* a void pointer to struct dvec *d, the actual vector */
    void *pdvecscale; /* a void pointer to struct dvec *ds, the scale vector */
} vecinfo, *pvecinfo;

typedef struct vecinfoall
{
    /* the plot */
    char *name;
    char *title;
    char *date;
    char *type;
    int veccount;

    /* the data as an array of vecinfo with length equal to the number of vectors in the plot */
    pvecinfo *vecs;

} vecinfoall, *pvecinfoall;

typedef int (SendChar)(char*, int, void*);
typedef int (SendStat)(char*, int, void*);
typedef int (ControlledExit)(int, bool, bool, int, void*);
typedef int (SendData)(pvecvaluesall, int, int, void*);
typedef int (SendInitData)(pvecinfoall, int, void*);
typedef int (BGThreadRunning)(bool, int, void*);
int ngSpice_Init(SendChar* printfcn, SendStat* statfcn, ControlledExit* ngexit, SendData* sdata, SendInitData* sinitdata, BGThreadRunning* bgtrun, void* userData);
int ngSpice_Command(char* command);
int ngSpice_Circ(char** circarray);
char* ngSpice_CurPlot(void);
char** ngSpice_AllVecs(char* plotname);
pvector_info ngGet_Vec_Info(char* vecname);
""")
lib = ffi.dlopen(ctypes.util.find_library("ngspice"))

class NgSpiceError(Exception):
	pass

class SimulationError(NgSpiceError):
	errors = ""

class NgSpice():
	_keepalives = []
	stderr = []

	def _callback(self, cdecl, method):
		function_ptr = ffi.callback(cdecl, method)
		self._keepalives.append(function_ptr)
		return function_ptr

	def __init__(self):
		original_sigint_handler = signal.getsignal(signal.SIGINT)

		lib.ngSpice_Init(
			self._callback("SendChar",        self.send_char),
			ffi.NULL, #self._callback("SendStat",        self.send_stat),
			self._callback("ControlledExit",  self.controlled_exit),
			ffi.NULL, #self._callback("SendData",        self.send_data),
			ffi.NULL, #self._callback("SendInitData",    self.send_init_data),
			ffi.NULL, # self._callback("BGThreadRunning", self.bg_thread_running),
			ffi.NULL, # we don't need this void* to be set to `self` since we're already wrapping everything
		)

		signal.signal(signal.SIGINT, original_sigint_handler)

	def command(self, command):
		ret = lib.ngSpice_Command(command.encode("utf-8"))
		if ret:
			raise NgSpiceError(f"ngSpice_Command error: {command}")

	def circ(self, circ):
		self.reset_simulator()

		lines = [ffi.from_buffer(line.encode("utf-8")) for line in circ]
		lines.append(ffi.NULL)
		lib.ngSpice_Circ(lines)

		self.check_errors()

		return self.vectors

	def reset_simulator(self):
		# Make sure we clean everything before so we don't memory leak
		self.command("remcirc")
		self.command("destroy all")
		# TODO: https://sourceforge.net/p/ngspice/discussion/133842/thread/d29f4768/#1218
		# "The memory leak is related to ngGet_Vec_Info -> newvec = vec_get(vecname);"

		self.stderr = []

	def check_errors(self):
		if not self.stderr:
			return

		errors = "\n".join(self.stderr)
		if "op simulation(s) aborted" in errors:
			for line in self.stderr:
				if "stderr Warning:":
					warning_line = line.split(" ", 2)[2]
					e = SimulationError(f"Simulation Aborted, first warning: {warning_line}")
					break
			else:
				e = SimulationError(f"Simulation aborted with no warning.")
			e.full_text = errors
			raise e
		else:
			warnings.warn(errors, RuntimeWarning)

	@property
	def vectors(self):
		cur_plot = lib.ngSpice_CurPlot()
		raw_vectors = lib.ngSpice_AllVecs(cur_plot)
		assert(raw_vectors)
		vectors = {}
		i = 0
		while raw_vectors[i]:
			raw_name = raw_vectors[i]
			name = ffi.string(raw_name).decode("utf-8")
			vector_info = lib.ngGet_Vec_Info(raw_vectors[i])
			assert(vector_info.v_length == 1)
			vectors[name] = vector_info.v_realdata[0]
			i+=1
		return vectors

	def send_char(self, string, _ident, _void):
		line = ffi.string(string).decode("utf-8")
		if line.startswith("stderr"):
			self.stderr.append(line)
		else:
			#print(line)
			pass
		return 0

	def controlled_exit(self, status, immediate, normal, _ident, _void):
		raise NgSpiceError(f"We don't really want ngspice to close on us. {locals()}")
		return 0

if __name__ == "__main__":
	self = NgSpice()
	v = self.circ(list(open("test.cir").readlines()))
