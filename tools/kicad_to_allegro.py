#!/usr/bin/env python3

from pcbdl import *
import sys

try:
    kicad_sch_filename, allegro_output = sys.argv[1:]
except ValueError:
    sys.exit(f"Usage: {sys.argv[0]} kicad_sch_filename allegro_output")

read_kicad_sch(open(kicad_sch_filename))
generate_netlist(allegro_output)
