# PCB Design Language
A programming way to design schematics.

# Developing

This command will install the current folder globally and it can easily be imported.

	$ sudo pip3 install -e .

## Interactive terminal

A good way to try various features without having to write a file separately.

	$ python3 -i -c "from pcbdl import *"

## Language

PCBDL's goal is to allow designing schematics via Code. Similar to how VHDL or Verilog are ways to represent Logic Diagrams in code form, PCBDL the analogous of that but for EDA schematics.

To start one should define a couple of nets:

	>>> vcc, gnd = Net("vcc"), Net("gnd")
	>>> vin = Net("vin")
	>>> base = Net("base")

We then can connect varios components between those nets with the `<<` operator and the `to=` argument (for the other side):

	>>> base << C("1000u", to=Net("vin"))
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

Nets can also be created annonymously if started from a part's pins:

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

	$ python3 -i examples/class_a.py


One can now give automatic consecutive reference designators to components that haven't been named manually already:

	>>> global_context.fill_refdes()

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

## Exporting

### Netlists

The main goal of this language is to aid in creating PCBs. The intermediate file format that layout programs (where one designs physical boards) is called a netlist. We must support outputting to that (or several of such formats).

For now we have a **minimum viable example** of an exporter for the Allegro Cadence netlists (found in `netlist.py`):

	>>> print(generate_netlist("/tmp/some_export_location"))

### Schematics / Graphical representation of the circuit

In order for schematics to be more easily parsable, we should research ways to graphically display them. Huge **TODO**, probably infeasible.

Suggestions include:

1. Convert a pcbdl schematic back into a traditional schematic
	* Laying out graphical elements in a schematic without it looking like a spaghetti mess is probably non trivial
2. Block diagrams of the overall system
	* Similar problems to the above point
	* This depends on how the schematics is declared, if it's not hierarchical enough, it won't have many "blocks" to display
3. Isolated schematics for how a particular thing is hooked up:
	* An example of this would be how a reset signal moves though a board.
	* The drawing engine for this would be similar to 1, but the limited scope of the signals might make it look more readable (even though the complete schematics are spaghetti).
	* This might be enough for sharing reference designs?

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
For every net, for every combination of output pins on that net, are all the input pins recieving proper voltages?

## Importing from traditional EDA schematics

Given that graphical exporting might be impossible, and in lieu of the language being slightly more unreadable than normal schematics, perhaps we should just use pcbdl as an intermediate data format or a library.

The way one would use it would be to import a kicad schematic, annotate it with a few more classes (for BOM and ERC purposes, unless we can find a way to put all metadata in the kicad schematics). Then all exporting and analysis features of pcbdl can still be used.

A kicad importer should be pretty trivial to implement. **TODO**

# Examples

Found in the `examples/` folder. Another way to make sure the enviroment is sane.
One can just "run" any example schematic with python, add -i to do more analysis operations on the schematic.

* `voltage_divider.py`: Very simple voltage divider
* `class_a.py`: Class A transistor amplifier, a good example to how a complicatedish analog circuit would look like.
* `servo_micro.py`: Servo micro schematics, reimplementation in pcbdl, [originally an 8 page pdf schematic](https://www.chromium.org/chromium-os/servo/servomicro).

## Tests

To test pcbdl framework functionality (not the schematics themselves), one can run:

	$ make test

If everything passes the code coverage can be seen with:

	$ make show-coverage

## Credits / Thanks

* [CBOLD](http://cbold.com/) for the idea
* Chrome OS Hardware Design Team for feedback
