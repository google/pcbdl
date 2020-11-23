import unittest
import os
import glob

from pcbdl import *

class SVGTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ac_coupling_value = "1000u"
        cls.subcircuit_id = 0
        cls.vcc, cls.gnd = Net("vcc"), Net("gnd")

    def _add_sub_circuit(self):
        """Adds a simple sub-circuit to the schematic, naming local subnets
        with a convention based on an incrementing id.
        """
        transistor = BJT("2n3904")

        C = C_POL

        transistor.BASE << (
            C(self.ac_coupling_value, to=Net(f"vin_{self.subcircuit_id}")),
            R("1k", to=self.vcc),
            R("1k", to=self.gnd),
        )

        transistor.COLLECTOR << (
            C(self.ac_coupling_value, to=Net(f"vout_{self.subcircuit_id}")),
            R("100", to=self.vcc),
        )

        transistor.EMITTER << (
            R("100",  to=self.gnd),
            C("1u",  to=self.gnd),
        )

        SVGTest.subcircuit_id += 1


    def test_empty_page_write(self):
        """Ensure that an AssertionError is created when no objects exist
        to write to an SVG
        """
        self.assertRaises(AssertionError, generate_svg, "test")

    def test_single_page_write(self):
        """Ensure a SVG is generated when a sub circuit is added, and then
        delete the SVG file.
        """
        # TODO: Ensure that this works on Windows which doesn't have a tmp
        # directory
        self._add_sub_circuit()
        file_name = "/tmp/test"
        generate_svg(file_name)
        gen_filename = file_name + ".svg"
        self.assertTrue(os.path.isfile(gen_filename), "SVG was not generated")
        os.remove(gen_filename)

    def test_multi_page_write(self):
        """Generates a large circuit and tests whether multiple SVG pages are
        created.
        """
        # Should be enough sub-circuits to trigger multi-page writing.
        for _ in range(100):
            self._add_sub_circuit()

        file_name = "/tmp/test"
        multi_filename_ending = "_{0}"
        generate_svg(file_name, multi_filename_ending=multi_filename_ending)
        gen_filename = file_name + multi_filename_ending.format(0) + ".svg"
        self.assertTrue(os.path.isfile(gen_filename), 
            "Multiple SVGs were not generated.")

        rem_files = glob.glob(file_name + "*.svg", recursive=True)
        # Remove all generated files
        for rem_file in rem_files:
            os.remove(rem_file)

    
if __name__ == "__main__":
    unittest.main()