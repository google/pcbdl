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

from .base import Net, Part, Plugin
from .defined_at import grab_nearby_lines
import collections
import csv
import hashlib

__all__ = [
    "Context",
    "global_context", "nets",
]

class RefdesRememberer:
    """
    Remembers refdeses from old executions of the schematic. This tries to guarantee that as the schematic
    evolves, automatically generated refdefs are deterministic. It does this by storing the refdefs in a
    file (.refdes_mapping), in part definition order, together with some information about the part (called
    anchors). Even partial matches of the anchors will be enough to remember the name.

    .. warning:: This class is very stateful, successful matches consume the entries from the internal state.
    """

    anchor_names = ("code", "nets", "variable_name", "class", "value", "part_number")

    """[(refdes, {anchor_name: anchor})]"""
    _mapping = []

    csv.register_dialect("pcbdl", delimiter="\t", lineterminator="\n", strict=True) #TODO: strict=False

    class MatchNotFound(Exception):
        pass

    def __init__(self, filename):
        self.filename = filename
        self.read()

    def read(self):
        """
        Read in the existing .refdes_mapping file and populate the internal state
        """
        self._mapping = []
        try:
            with open(self.filename, "r") as f:
                reader = csv.DictReader(f, dialect="pcbdl")
                for row in reader:
                    refdes = row.pop("refdes")
                    self._mapping.append((refdes, row))
        except FileNotFoundError:
            pass # We'll start fresh!

    def find_match(self, part, score_threshold=0.6, debug=False):
        """
        Given a part, finds a match in the older mapping based on the current values of the anchors.

        If most of them match (given the score) with an older entry the refdes of that entry is returned and the entry
        is removed from the matches so it's not matched in the future with another part.
        """
        current_anchors = self.get_part_anchors(part)
        max_score = len(self.anchor_names)

        if not self._mapping:
            raise self.MatchNotFound("Empty state.")

        scored_others = [] # score, (refdes, anchors)
        for refdes, older_anchors in self._mapping:
            score = 0

            for anchor_name in current_anchors.keys():
                if anchor_name not in older_anchors:
                    continue # change of schema?

                if current_anchors[anchor_name] == older_anchors[anchor_name]:
                    score += 1

            scored_others.append((score, (refdes, older_anchors)))

        scored_others.sort(key=(lambda other: other[0]), reverse=True)
        first_match = scored_others[0]
        score, row = first_match
        if score < max_score * score_threshold:
            raise self.MatchNotFound("Score %d/%d too low." % (score, max_score))

        refdes, older_anchors = row

        # some logging if it's inexact
        if debug and (score != max_score):
            print(f"RefdesRememberer: Inexact match ({score}/{max_score}) for {part}:")
            for anchor_name in current_anchors.keys():
                if anchor_name not in older_anchors:
                    print(" [%r] %r not found" % (anchor_name, current_anchors[anchor_name]))
                    continue # change of schema?
                if current_anchors[anchor_name] != older_anchors[anchor_name]:
                    print(" [%r] %r!=%r" % (anchor_name, current_anchors[anchor_name], older_anchors[anchor_name]))

        #make sure nobody else matches with this row again, since we already found the instance matching it
        self._mapping.remove(row)

        return refdes

    def get_part_anchors(self, part):
        """
        Generates a dict of anchors (keys being anchor_names) for a given part.
        """
        anchors = {}
        anchors["code"] = part.plugins[PartContext]._anchor_code
        anchors["nets"] = part.plugins[PartContext]._anchor_nets
        try:
            anchors["variable_name"] = part.variable_name
        except AttributeError:
            anchors["variable_name"] = ""
        anchors["class"] = repr(part.__class__)
        anchors["value"] = part.value
        anchors["part_number"] = part.part_number

        assert(set(anchors.keys()) == set(self.anchor_names))
        return anchors

    def overwrite(self, context):
        """
        Writes the context (all the refdeses and new computed anchors) to a file,
        ready to read for next time.
        """
        with open(self.filename, "w") as f:
            writer = csv.DictWriter(f, dialect="pcbdl", fieldnames=("refdes",) + self.anchor_names)
            writer.writeheader()
            for refdes, part in context.named_parts.items():
                row = self.get_part_anchors(part)
                row["refdes"] = refdes
                writer.writerow(row)

class Context(object):
    def __init__(self, name = ""):
        self.name = name

        self.net_list = []
        self.parts_list = []
        self.named_nets = collections.OrderedDict()

    def new_part(self, part):
        assert(part not in self.parts_list)

        if part.refdes in (other_part.refdes for other_part in self.parts_list):
            raise Exception("Cannot have more than one part with the refdes %s in %s" % (part.refdes, self))

        # Add to the part list
        self.parts_list.append(part)

    def new_net(self, net):
        assert(net not in self.net_list)

        if net.name in self.named_nets:
            raise Exception("Cannot have more than one net called %s in %s" % (net.name, self))

        # Add to the net list
        self.net_list.append(net)
        self.named_nets[net.name] = net

    def autoname(self, mapping_file=None):
        self.named_parts = collections.OrderedDict()
        refdes_rememberer = RefdesRememberer(mapping_file)

        # Do a pass trying to remember it
        for part in self.parts_list:
            original_name = part.refdes
            prefix = part.REFDES_PREFIX
            if original_name.startswith(prefix):
                number = original_name[len(prefix):]

                if number.startswith("?"):
                    try:
                        refdes = refdes_rememberer.find_match(part)
                    except RefdesRememberer.MatchNotFound:
                        continue
                    part.refdes = refdes
                    number = refdes[len(prefix):]
                    #print("Remembering refdes %s -> %s" % (original_name, part.refdes))

                    if part.refdes in (other_part.refdes for other_part in self.parts_list if other_part != part):
                        raise Exception("Cannot have more than one part with the refdes %s in %s" % (part.refdes, self))

        # Another pass by naming things with the autoincrement
        self.refdes_counters = collections.defaultdict(lambda:1)
        for part in self.parts_list:
            original_name = part.refdes
            prefix = part.REFDES_PREFIX
            if original_name.startswith(prefix):
                number = original_name[len(prefix):]

                if number.startswith("?"):
                    while True:
                        part.refdes = "%s%d" % (prefix, self.refdes_counters[prefix])
                        self.refdes_counters[prefix] += 1
                        if part.refdes not in self.named_parts:
                            break
                    print("New refdes %s -> %s" % (original_name, part.refdes))
                else:
                    # Yay, there's a part that's already named
                    # Let's remember the number for it and save it
                    try:
                        number = int(number)
                    except ValueError:
                        pass
                    else:
                        self.refdes_counters[prefix] = number
                        #print("Skipping ahead to %s%d+1" % (prefix, self.refdes_counters[prefix]))
                        self.refdes_counters[prefix] += 1
            self.named_parts[part.refdes] = part

        refdes_rememberer.overwrite(self)
        del refdes_rememberer

        for net in self.net_list:
            # Look only for unnamed nets
            if net.has_name:
                continue

            old_name = net.name
            new_name = "ANON_NET_%s" % str(net.connections[0]).replace(".","_")
            net.name = new_name

            # Update named_nets list with the new name
            if new_name in self.named_nets:
                raise Exception("Cannot have more than one net called %s in %s" % (net.name, self))
            self.named_nets[new_name] = net
            del self.named_nets[old_name]


@Plugin.register(Net)
class NetContext(Plugin):
    def __init__(self, instance):
        global_context.new_net(instance)

@Plugin.register(Part)
class PartContext(Plugin):
    def __init__(self, instance):
        self.instance = instance
        global_context.new_part(instance)

    def _generate_anchor_code(self):
        if not hasattr(self.instance, "defined_at"):
            self._context_ref_value = None
            raise Exception("No defined_at")

        if self.instance.defined_at.startswith("<stdin>"):
            self._context_ref_value = None
            raise Exception("Can't get context from stdin")


        tohash = repr((
            grab_nearby_lines(self.instance.defined_at, 3),
        ))

        h = hashlib.md5(tohash.encode("utf8")).hexdigest()

        ret = "c" + h[:8]
        self._context_ref_value = ret
        return ret

    @property
    def _anchor_code(self):
        try:
            return self._anchor_code_value
        except AttributeError:
            pass

        self._anchor_code_value = self._generate_anchor_code()
        return self._anchor_code_value

    def _generate_anchor_nets(self):
        tohash = repr((
            sorted(pin.net.name for pin in self.instance.pins if (pin._net is not None and "ANON_NET" not in pin.net.name)),
        ))

        h = hashlib.md5(tohash.encode("utf8")).hexdigest()

        ret = "n" + h[:8]
        self._context_ref_value = ret
        return ret

    @property
    def _anchor_nets(self):
        try:
            return self._anchor_nets_value
        except AttributeError:
            pass

        self._anchor_nets_value = self._generate_anchor_nets()
        return self._anchor_nets_value

global_context = Context()
nets = global_context.named_nets
