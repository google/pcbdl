#!/usr/bin/env python3

from pcbdl import *

#parts = list(read_kicad_lib(open("/usr/share/kicad/demos/interf_u/interf_u-cache.lib")))
#for part in parts:
	#p = part()

read_kicad_sch(open("/usr/share/kicad/demos/test_xil_95108/carte_test.sch"))

global_context.autoname()
