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

from pcbdl import *

import collections
import json

j = json.load(open("arbitrage.json"))

class ArbitragePart(Part):
    pass

def parse_part(part):
    name = part["name"]

    if "pin_names" in part:
        pcbdl_pins = []
        for pin_number, pin_name in part["pin_names"].items():
            #pin_name = pin_name.split("'")[0] # trim out bussed pin numbers
            pcbdl_pins.append(Pin(pin_name, pin_number))
    else:
        # TODO(in Arbitrage): always have pin names
        # Come up with some automatically generated pin names based on pin numbers of the first instance that uses this part
        first_instance = [chip for chip in j["chips"].values() if chip["part_id"]==name][0]
        pcbdl_pins = [Pin(number, number) for number in first_instance["pins"].keys()]

    class_dict = {
        "value": name,
        "package": name,
        "PINS": pcbdl_pins,
        #"fields": fields, # TODO: insert this when ready
    }

    parent_classes = (ArbitragePart,)
    if part["type"] == "RESISTOR":
        parent_classes += (R,)
    if part["type"] == "CAPACITOR":
        parent_classes += (C,)

    return type(name, parent_classes, class_dict)

pcbdl_part_classes = {part_key: parse_part(arb_part) for part_key, arb_part in j["parts"].items()}

arb_nets = collections.defaultdict(list) # net_name: [pin, ...]
for refdes, arb_chip in j["chips"].items():
    part_class = [pcbdl_part_classes[arb_chip["part_id"]]][0]
    instance = part_class(refdes=refdes)
    for arb_pin_number, arb_pin in arb_chip["pins"].items():
        net_name = arb_pin["name"]

        # find a pcbdl pin to assign it to
        for pcbdl_pin in instance.pins:
            if arb_pin_number in pcbdl_pin.numbers:
                arb_nets[net_name].append(pcbdl_pin)
                break
        else:
            #raise KeyError("Couldn't find pin %s in %s." % (arb_pin_number, instance))
            pass

for net_name, pins in arb_nets.items():
    n = Net(net_name)
    for pin in pins:
        n << pin

global_context.autoname()
