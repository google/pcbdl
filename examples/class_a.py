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

"""
Simple Class A amplifier example.

https://www.electronics-tutorials.ws/amplifier/amp_5.html
"""

from pcbdl import *

ac_coupling_value = "1000u"

vcc, gnd = Net("vcc"), Net("gnd")

q = BJT("2n3904")

C = C_POL

q.BASE << (
    C(ac_coupling_value, to=Net("vin")),
    R("1k", to=vcc),
    R("1k", to=gnd),
)

q.COLLECTOR << (
    C(ac_coupling_value, to=Net("vout")),
    R("100", to=vcc),
)

q.EMITTER << (
    R("100", "Rc", to=gnd),
    C("1u", "C10", to=gnd),
)
