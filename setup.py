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

import setuptools

with open("README.md", "r") as readme_file:
	long_description = readme_file.read()

setuptools.setup(
	name="pcbdl",
	version="0.1.0",
	author="Google LLC",
	description="A programming way to design schematics.",
	long_description=long_description,
	long_description_content_type="text/markdown",
	license="Apache-2.0",
	url="https://github.com/google/pcbdl",
	packages=setuptools.find_packages(),
	keywords=["eda", "hdl", "electronics", "netlist", "hardware", "schematics"],
	install_requires=["pygments"],
	classifiers=[
		"Intended Audience :: Developers",
		"License :: OSI Approved :: Apache Software License",
		"Operating System :: OS Independent",
		"Programming Language :: Python :: 3",
		"Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
		"Topic :: System :: Hardware",
	],
)
