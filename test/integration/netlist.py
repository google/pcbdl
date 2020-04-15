#!/usr/bin/env python3

# Copyright 2020 Google LLC
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


import difflib
import pathlib
import tempfile
import shutil
import unittest

import load_example
import netlist_normalize

class NetlistIntegration(unittest.TestCase):
    def test_netlist(self):
        """Integration test to compare the third party Allegro netlist file that we output vs what the project originally used."""
        servo_micro = load_example.run("servo_micro")
        print(f"Import of examples/servo_micro was successful: {servo_micro.ec}")

        tmp_dir = pathlib.Path(tempfile.mkdtemp("_netlist.test"))
        try:
            print(f"Temporary dir {tmp_dir!r}")
            netlist_dir = tmp_dir / "allegro_third_party"

            servo_micro.generate_netlist(netlist_dir)

            with open(netlist_dir / "frompcbdl.netlist.rpt", "r") as f:
                pcbdl_netlist_contents = f.read()
            pcbdl_normalized = netlist_normalize.normalize(
                pcbdl_netlist_contents,
                normalize_header=True,
                normalize_part_props=True,
            )
            pcbdl_normalized_file = tmp_dir / "pcbdl.normalized.rpt"
            with open(pcbdl_normalized_file, "w") as f:
                f.write(pcbdl_normalized)

            with open(pathlib.Path(__file__).absolute().parent / "servo_original.rpt", "r") as f:
                original_netlist_contents = f.read()
            original_normalized = netlist_normalize.normalize(
                original_netlist_contents,
                normalize_header=True,
                normalize_part_props=True,
            )
            original_normalized_file = tmp_dir / "original.normalized.rpt"
            with open(original_normalized_file, "w") as f:
                f.write(original_normalized)

            delta = '\n'.join(difflib.unified_diff(
                pcbdl_normalized.splitlines(),
                original_normalized.splitlines(),
                str(pcbdl_normalized_file),
                str(original_normalized_file),
                n=3
            ))
            if delta:
                raise self.failureException(f"Netlists differ:\n{delta}")

            # Delete the tmp_dir if we got so far successfully
            shutil.rmtree(str(tmp_dir))
        except Exception:
            print(f"Not deleting {tmp_dir!r} for further investigations:")
            raise

if __name__ == "__main__":
    unittest.main()
