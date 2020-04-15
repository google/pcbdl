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

import importlib
import pathlib
import os
import sys

def run(example_name):
    examples_dir = pathlib.Path(__file__).absolute().parent.parent.parent / "examples"
    sys.path.insert(0, str(examples_dir))
    saved_cwd = os.getcwd()
    try:
        os.chdir(examples_dir) # so the refdes_mapping file is in the right spot
        return importlib.import_module(example_name)
    finally:
        os.chdir(saved_cwd)
