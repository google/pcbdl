#!/usr/bin/env python3
"""
Full reimplementation of servo micro in pcbdl.

Servo Micro's information page (including pdf schematics made in orthodox tools) can be found at:
https://www.chromium.org/chromium-os/servo/servomicro
"""

from pcbdl import *

class Connector(Part):
	REFDES_PREFIX = "CN"

class Regulator(Part):
	REFDES_PREFIX = "U"
	PINS = [
		"IN",
		"OUT",
		"EN",
		"GND",
		"PAD",
	]

class UsbEsdDiode(Part):
	REFDES_PREFIX = "D"
	PINS = [
		"VCC",
		"GND",
		"P1",
		"P2",
		"NC",
	]

class DoubleDiode(Part):
	REFDES_PREFIX = "D"
	PINS = ["A1", "A2", "K"]

class ServoConnector(Connector):
	PINS = [] # TODO

class ProgrammingConnector(Connector):
	PINS = [
		("P1", "GND"),
		("P2", "UART_TX"),
		("P3", "UART_RX"),
		"P4",
		"P5",
		("P6", "NRST"),
		"P7",
		("P8", "BOOT0"),
		"G", # Mechanical
	]

class STM32F072(Part):
	REFDES_PREFIX = "U"
	value = "STM32F072CBU6TR"
	PINS = [
		Pin("VDD", type=PinType.POWER_INPUT),
		"VBAT",
		Pin("VDDA", type=PinType.POWER_INPUT),
		"VDDIO2",

		"VSS",
		"VSSA",
		"PAD",

		"BOOT0",
		"NRST",

		"PC13",
		("PC14", "OSC32_IN"),
		("PC15", "OSC32_OUT"),

		("PF0", "OSC_IN"),
		("PF1", "OSC_OUT"),
	]
	for i in range(16):
		PINS.append(Pin("PA%d" % i, well="VDD"))
	for i in range(16):
		PINS.append(Pin("PB%d" % i, well="VDDA"))

class I2cIoExpander(Part):
	REFDES_PREFIX = "U"
	PINS = [
		"VCCI",
		"VCCP",
		"GND",
		"PAD",

		"SCL",
		"SDA",
		"INT_L",
		"RESET_L",

		"A0",
	]
	for i in range(18):
		PINS.append("P%02d" % i)

class LevelShifter(Part):
	REFDES_PREFIX = "U"
	value = "SN74AVC4T774RSVR"
	PINS = [
		"VCCA",
		"VCCB",
		"GND",
		"OE_L",
	]
	for i in range(1, 5):
		PINS.append("A%d" % i)
		PINS.append("B%d" % i)
		PINS.append("DIR%d" % i)
		# TODO, add these in some kind of bundles, or a list

	def shift(self, i, A_net, B_net, direction_net):
		if A_net is not None:
			A_net << self.pins["A%d" % i]
		if B_net is not None:
			B_net << self.pins["B%d" % i]
		direction_net << self.pins["DIR%d" % i]

	def shift_AB(self, i, A_net, B_net):
		self.shift(i, A_net, B_net, self.VCCA.net)

	def shift_BA(self, i, A_net, B_net):
		self.shift(i, A_net, B_net, self.GND.net)

vbus_in = Net("VBUS_IN")
gnd = Net("GND")
def decoupling(value = "100n"):
	return C(value, to=gnd)

stm32 = STM32F072()

# usb stuff
class UsbConnector(Connector):
	PINS = [
		"VBUS",
		("DM", "D-"),
		("DP", "D+"),
		"ID",
		"GND",
		"G", # Mechanical
	]
usb = UsbConnector()
usb_esd = UsbEsdDiode()
Net("USB_DP") << usb.DP << usb_esd.P1 << stm32.PA11
Net("USB_DM") << usb.DM << usb_esd.P2 << stm32.PA12
vbus_in << usb.VBUS << usb_esd.VCC
gnd << usb.GND << usb.G << usb_esd.GND
# We could make this type-c instead!

# 3300 regulator
pp3300 = Net("PP3300")
reg3300 = Regulator("MIC5504-3.3YMT")
vbus_in << (
	reg3300.IN, decoupling("2.2u"),
	reg3300.EN,
)
gnd << reg3300.GND
pp3300 << (
	reg3300.OUT,
	decoupling("10u"),
	decoupling(),
	decoupling("1000p"),
)

# 1800 regulator
pp1800 = Net("PP1800")
reg1800 = Regulator("TLV70018DSER")
drop_diode = DoubleDiode("240-800MV")
pp3300 << drop_diode.A1 << drop_diode.A2
Net("PP1800_VIN") << (
	drop_diode.K,
	reg1800.IN, decoupling(),
	reg1800.EN
)
gnd << reg1800.GND
pp1800 << reg1800.OUT << decoupling("1u")

# stm32 power
pp3300 << (
	stm32.VBAT, decoupling(),
	stm32.VDD, decoupling(),
	decoupling("4.7u"),
)
Net("PP3300_PD_VDDA") << (
	stm32.VDDA,
	L("600@100MHz", to=pp3300),
	decoupling("1u"),
	decoupling("100p"),
)
pp3300 << (
	stm32.VDDIO2, decoupling(),
	decoupling("4.7u"),
)
gnd << stm32.VSS << stm32.VSSA << stm32.PAD

# stm32 programming/debug
prog = ProgrammingConnector()
gnd << prog.GND << prog.G
Net("PD_NRST_L") << (
	stm32.NRST,
	prog.NRST,
	decoupling(),
)
boot0 = Net("PD_BOOT0")
boot0_q = FET("CSD13381F4")
# Use OTG + A-TO-A cable to go to bootloader mode
Net("USB_ID") << usb.ID << boot0_q.G << R("51.1k", to=vbus_in)
boot0 << boot0_q.D << R("51.1k", to=vbus_in)
gnd << boot0_q.S
Net("EC_UART_TX") << stm32.PA9 << prog.UART_TX
Net("EC_UART_RX") << stm32.PA10 << prog.UART_RX

# TODO: stm32 pins, probably some will be below though

# io expander definition + power
io = I2cIoExpander("TCA6416ARTWR")
pp3300 << io.VCCI << decoupling()
gnd << io.GND << io.PAD
gnd << io.A0 # i2c addr 7'H=0x20
Net("Servo_SDA") << R("4.7k", to=pp3300) << stm32.PB9 << io.SDA
Net("Servo_SCL") << R("4.7k", to=pp3300) << stm32.PB8 << io.SCL
Net("Reset_L") << io.RESET_L << stm32.PC13
pp1800 << io.VCCP << decoupling()
io.P03 << TP()
io.P17 << TP()

# TODO: pins for io expander
# TODO: FTDI_MFG_MODE

# JTAG
vtag_vref = Net("PPDUT_JTAG_VREF")
jtag_shifter_1 = LevelShifter()
pp3300 << jtag_shifter_1.VCCA << decoupling()
vtag_vref << jtag_shifter_1.VCCB << decoupling()
jtag_shifter_1.shift_AB(1, pp3300, None) # spare
jtag_shifter_1.shift_BA(2, Net("SERVO_JTAG_TRST_L"), Net("DUT_JTAG_TRST_L"))
jtag_shifter_1.shift_BA(3, Net("SERVO_JTAG_TMS"),    Net("DUT_JTAG_TMS"))
jtag_shifter_1.shift_BA(4, Net("SERVO_JTAG_TDI"),    Net("DUT_JTAG_TDI"))
