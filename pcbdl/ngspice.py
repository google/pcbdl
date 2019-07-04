#!/usr/bin/env python3

from cffi import FFI
import ctypes.util

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

class NgSpice():
	_keepalives = []

	def _callback(self, cdecl, method):
		function_ptr = ffi.callback(cdecl, method)
		self._keepalives.append(function_ptr)
		return function_ptr

	def __init__(self):
		lib.ngSpice_Init(
			self._callback("SendChar",        self.send_char),
			ffi.NULL, #self._callback("SendStat",        self.send_stat),
			self._callback("ControlledExit",  self.controlled_exit),
			ffi.NULL, #self._callback("SendData",        self.send_data),
			ffi.NULL, #self._callback("SendInitData",    self.send_init_data),
			ffi.NULL, # self._callback("BGThreadRunning", self.bg_thread_running),
			ffi.NULL, # we don't need this void* to be set to `self` since we're already wrapping everything
		)

	def command(self, command):
		ret = lib.ngSpice_Command(command.encode("utf-8"))
		if ret:
			raise ValueError(f"ngSpice_Command error: {command}")

	def circ(self, circ):
		# Make sure we clean everything before so we don't memory leak
		self.command("remcirc")
		self.command("destroy all")
		# TODO: https://sourceforge.net/p/ngspice/discussion/133842/thread/d29f4768/#1218
		# "The memory leak is related to ngGet_Vec_Info -> newvec = vec_get(vecname);"

		lib.ngSpice_Circ([ffi.from_buffer(line.encode("utf-8")) for line in circ] + [ffi.NULL])
		return self.vectors

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
		input_line = ffi.string(string).decode("utf-8")
		channel, *line_parts = input_line.split(" ")
		line = ' '.join(line_parts)
		if channel == "stderr":
			print(line)
		return 0

	def controlled_exit(self, status, immediate, normal, _ident, _void):
		raise Exception(f"We don't really want ngspice to close on us. {locals()}")
		return 0

if __name__ == "__main__":
	self = NgSpice()
	v = self.circ(list(open("test.cir").readlines()))
