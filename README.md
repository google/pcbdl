# PCB Design Language
A programming way to design schematics.

[Sphinx Documentation](https://google.github.io/pcbdl/doc/_build/html/)

## Installing

[![PyPI version](https://badge.fury.io/py/pcbdl.svg)](https://pypi.org/project/pcbdl/)

    sudo apt-get install python3 python3-pip python3-pygments

    sudo pip3 install pcbdl

## Interactive terminal

A good way to try various features without having to write a file separately.

    python3 -i -c "from pcbdl import *"

## Language

PCBDL's goal is to allow designing schematics via Code. Similar to how VHDL or Verilog are ways to represent Logic Diagrams in code form, PCBDL the analogous of that but for EDA schematics.

To start one should define a couple of nets:

    >>> vcc, gnd = Net("vcc"), Net("gnd")
    >>> vin = Net("vin")
    >>> base = Net("base")

We then can connect various components between those nets with the `<<` operator and the `to=` argument (for the other side):

    >>> base << C("1000u", to=vin)
    >>> base << (
        R("1k", to=vcc),
        R("1k", to=gnd),
    )

2 pin devices (aka JellyBean in pcbdl) like capacitors and resistors are one of the easiest things to connect. Internally they have a primary (connected with `>>`) and secondary, other side, pin (connected with `to=`).

Let's try to get more complicated by defining a transistor and connect some of its pins.

    >>> class Transistor(Part):
        REFDES_PREFIX = "Q"
        PINS = ["B", "C", "E"]
    ...
    >>> q = Transistor()
    >>> base << q.B

Nets can also be created anonymously if started from a part's pins:

    >>> q.E << (
        R("100", to=gnd),
        C("1u", to=gnd),
    )

Let's finish our class A amplifier (note how we created the "vout" net in place, and how we gave a name ("Rc") to one of our resistors):

    >>> q.C << (
        C("100u", to=Net("vout")),
        R("100", "Rc", to=vcc),
    )

Note: One can find a completed version of this amplifier in `examples/class_a.py`:

    python3 -i examples/class_a.py


One can now give automatic consecutive reference designators to components that haven't been named manually already:

    >>> global_context.autoname()

Then one can explore the circuit:

    >>> global_context.parts_list
    [R1, R2, R3, Rc, C10, C11, Q1, C12]

    >>> global_context.parts_list[0].refdes
    'R1'
    >>> global_context.parts_list[0].value
    '1kΩ'
    >>> global_context.parts_list[0].pins
    (R1.P1, R1.P2)
    >>> global_context.parts_list[0].pins[1].net
    VCC(connected to R1.P2, R2.P2)

    >>> nets
    OrderedDict([('VCC', VCC(connected to R1.P2, R2.P2)), ('GND', GND(connected to R3.P2, Rc.P2, C10.-)), ('VIN', VIN(connected to C11.-)), ('VOUT', VOUT(connected to C12.-))])

    >>> nets["GND"]
    GND(connected to R3.P2, Rc.P2, C10.-)

## Examples

Found in the `examples/` folder. Another way to make sure the environment is sane.
One can just "run" any example schematic with python, add -i to do more analysis operations on the schematic.

* `voltage_divider.py`: Very simple voltage divider
* `class_a.py`: Class A transistor amplifier, a good example to how a complicatedish analog circuit would look like.
* `servo_micro.py`: **Servo micro schematics**, reimplementation in pcbdl, [originally an 8 page pdf schematic](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/refs/heads/master/docs/servo_micro.md#overview).

## Exporting

### Netlists

The main goal of this language is to aid in creating PCBs. The intermediate file format that layout programs (where one designs physical boards) is called a netlist. We must support outputting to that (or several of such formats).

We have a an exporter for the Cadence Allegro Third Party netlists (found in `netlist.py`):

    >>> generate_netlist("/tmp/some_export_location")

### HTML

This produces a standalone html page with everything cross-linked:

* List of nets with links to the parts and pins on each
* List of parts with the part properties and a list of pins linking to the nets connected
* Highlighted source code, with every variable and object linked to the previous 2 lists

Here's an example of such a [html output for servo micro](https://google.github.io/pcbdl/examples/servo_micro.html).

### Schematics / Graphical representation of the circuit

In order for schematics to be more easily parsable, we want to graphically display them. The [netlistsvg](https://github.com/nturley/netlistsvg) project has been proven to be an excellent tool to solve the hard problems of this. See `pcbdl/netlistsvg.py` for the implementation.

1. Convert a pcbdl schematic back into a traditional schematic

    `generate_svg('svg_filename')`

    Here's the [svg output for the servo_micro example](https://google.github.io/pcbdl/examples/servo_micro.svg).

2. Isolated schematics for how a particular thing is hooked up:
    * I2C map, ([servo_micro's](https://google.github.io/pcbdl/examples/servo_micro.i2c.svg))

    `generate_svg('svg_filename', net_regex='.*(SDA|SCL).*', airwires=0)`

    * Power connections ([servo_micro's](https://google.github.io/pcbdl/examples/servo_micro.power.svg))

    `generate_svg('svg_filename', net_regex='.*(PP|GND|VIN|VBUS).*')`

3. Block diagrams of the overall system
    * This depends on how the schematics is declared, if it's not hierarchical enough, it won't have many "blocks" to display
    * This task is dependent on allowing hierarchies in pcbdl

### BOM

Bill of Materials would be a trivial thing to implement in pcbdl.

## ERC

Electrical Rule Checking. How to unit test a schematic?

This is a big **TODO** item. The basic idea is that the pins will get annotated more heavily than normal EDA software.

Pins will have beyond just simple input/output/open drain/power properties, but will go into detail with things like:
* Power well for both inputs and outputs
* ViH, ViL
* Output voltages

With this information it should be possible to make isolated spice circuits to check for current leaks.
For every net, for every combination of output pins on that net, are all the input pins receiving proper voltages?

## Importing from traditional EDA schematics

Given that graphical exporting might be impossible, and in lieu of the language being slightly more unreadable than normal schematics, perhaps we should just use pcbdl as an intermediate data format or a library.

The way one would use it would be to import a kicad schematic, annotate it with a few more classes (for BOM and ERC purposes, unless we can find a way to put all metadata in the kicad schematics). Then all exporting and analysis features of pcbdl can still be used.

A kicad importer should be pretty trivial to implement. **TODO**

## Support

This is not an officially supported Google product.

The language itself is still in flux, things might change. A lot of the syntax was added as a demo of what could be possible, might still need polishing. Please don't use this language without expecting some tinkering to keep your schematics up to date to the language.

## Credits / Thanks

* [CBOLD](http://cbold.com/) for the idea
* [netlistsvg](https://github.com/nturley/netlistsvg) for svg output support
* Chrome OS Hardware Design Team for feedback
