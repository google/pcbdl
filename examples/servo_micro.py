#!/usr/bin/env python3
"""
Full reimplementation of servo micro in pcbdl.

Servo Micro's information page (including pdf schematics made in orthodox tools) can be found at:
https://www.chromium.org/chromium-os/servo/servomicro
"""

from pcbdl import *

class Connector(Part):
	REFDES_PREFIX = "CN"

class UsbConnector(Connector):
	package = "USB_MICRO_FLUSH"
	part_number = "USB_MICRO_9001"
	PINS = [
		"VBUS",
		("DM", "D-"),
		("DP", "D+"),
		"ID",
		"GND",
		"G", # Mechanical
	]

class Regulator(Part):
	REFDES_PREFIX = "U"
	package = "SOTwhatever"
	PINS = [
		"IN",
		"OUT",
		"EN",
		"GND",
		"PAD",
	]

class UsbEsdDiode(Part):
	REFDES_PREFIX = "D"
	package = "SOTwhatever"
	part_number = "esddiode9001"
	PINS = [
		"VCC",
		"GND",
		"P1",
		"P2",
		"NC",
	]

class DoubleDiode(Part):
	REFDES_PREFIX = "D"
	package = "SOTwhatever"
	part_number = "240-800MV"
	PINS = ["A1", "A2", "K"]
class ServoConnector(Connector):
	pin_names_match_nets = True
	pin_names_match_nets_prefix = "DUT_"
	PINS = [
		("P1",  "GND1"),
		("P2",  "SPI2_CLK", "SPI2_SK"),
		("P3",  "SPI2_CS"),
		("P4",  "SPI2_MOSI", "SPI2_DI"),
		("P5",  "SPI2_MISO", "SPI2_DO"),
		("P6",  "SPI2_VREF"),
		("P7",  "SPI2_HOLD_L"),
		("P8",  "GND2"),
		("P9",  "SPI1_CLK", "SPI1_SK"),
		("P10", "SPI1_CS"),
		("P11", "SPI1_MOSI", "SPI1_DI"),
		("P12", "SPI1_MISO", "SPI1_DO"),
		("P13", "SPI1_VREF"),
		("P14", "EC_RESET_L", "COLD_RESET_L"),
		("P15", "GND3"),
		("P16", "UART2_SERVO_DUT_TX", "UART2_RXD"),
		("P17", "UART2_DUT_SERVO_TX", "UART2_TXD"),
		("P18", "UART2_VREF"),
		("P19", "SD_DETECT_L"),
		("P20", "GND4"),
		("P21", "JTAG_TCK"),
		("P22", "PWR_BUTTON"),
		("P23", "JTAG_TMS"),
		("P24", "JTAG_TDI"),
		("P25", "JTAG_TDO"),
		("P26", "JTAG_RTCK"),
		("P27", "JTAG_TRST_L"),
		("P28", "JTAG_SRST_L", "WARM_RESET_L"),
		("P29", "JTAG_VREF"),
		("P30", "REC_MODE_L"),
		("P31", "GND5"),
		("P32", "UART1_SERVO_DUT_TX", "UART1_RXD"),
		("P33", "UART1_DUT_SERVO_TX", "UART1_TXD"),
		("P34", "UART1_VREF"),
		("P35", "I2C_3.3V"),
		("P36", "GND6"),
		("P37", "I2C_SDA"),
		("P38", "I2C_SCL"),
		("P39", "HPD"),
		("P40", "FW_WP"),
		("P41", "PROC_HOT_L", "FW_UPDATE_L"),
		("P42", "GND7"),
		("P43", "DEV_MODE"),
		("P44", "LID_OPEN"),
		("P45", "PCB_DISABLE_L", "CPU_NMI"),
		("P46", "KBD_COL1"),
		("P47", "KBD_COL2"),
		("P48", "KBD_ROW1"),
		("P49", "KBD_ROW2"),
		("P50", "KBD_ROW3"),
	]

	# swap the order of the names so the pretty names are first
	PINS = [names[1:] + (names[0],) for names in PINS]

class ProgrammingConnector(Connector):
	package = "flexwhatever"
	part_number = "flexwhatever"
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
	package = "QFNwhatever"
	part_number = "STM32F072CBU6TR"
	pin_names_match_nets = True
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

		Pin(("PA0",  "UART3_TX"), well="VDD"),
		Pin(("PA1",  "UART3_RX"), well="VDD"),
		Pin(("PA2",  "UART1_TX")),
		Pin(("PA3",  "UART1_RX")),
		Pin(("PA4",  "SERVO_JTAG_TMS")),
		Pin(("PA5",  "SPI1_MUX_SEL")),
		Pin(("PA6",  "SERVO_JTAG_TDO_BUFFER_EN")),
		Pin(("PA7",  "SERVO_JTAG_TDI")),

		Pin(("PA8",  "UART1_EN_L")),
		Pin(("PA9",  "EC_UART_TX")),
		Pin(("PA10", "EC_UART_RX")),
		Pin(("PA11", "USB_DM")),
		Pin(("PA12", "USB_DP")),
		Pin(("PA13", "SERVO_JTAG_TRST_L")),
		Pin(("PA14", "SPI1_BUF_EN_L")),
		Pin(("PA15", "SPI2_BUF_EN_L")),

		Pin(("PB0",  "UART2_EN_L")),
		Pin(("PB1",  "SERVO_JTAG_RTCK")),
		Pin(("PB2",  "SPI1_VREF_33")),
		Pin(("PB3",  "SPI1_VREF_18")),
		Pin(("PB4",  "SPI2_VREF_33")),
		Pin(("PB5",  "SPI2_VREF_18")),
		Pin(("PB6",  "SERVO_JTAG_TRST_DIR")),
		Pin(("PB7",  "SERVO_JTAG_TDI_DIR")),

		Pin(("PB8",  "SERVO_SCL")),
		Pin(("PB9",  "SERVO_SDA")),
		Pin(("PB10", "UART2_TX")),
		Pin(("PB11", "UART2_RX")),
		Pin(("PB12", "SERVO_SPI_CS")),
		Pin(("PB13", "SERVO_TO_SPI1_MUX_CLK")),
		Pin(("PB14", "SERVO_TO_SPI1_MUX_MISO")),
		Pin(("PB15", "SERVO_SPI_MOSI")),

		Pin(("PC13", "RESET_L")),
		Pin(("PC14", "SERVO_JTAG_TMS_DIR")),
		Pin(("PC15", "SERVO_JTAG_TDO_SEL")),

		Pin(("PF0", "JTAG_BUFOUT_EN_L", "OSC_IN")),
		Pin(("PF1", "JTAG_BUFIN_EN_L", "OSC_OUT")),
	]

	for pin in PINS:
		if not isinstance(pin, Pin):
			continue

		if pin.names[0].startswith("PA"):
			pin.well_name = "VDD"
		if pin.names[0].startswith("PB"):
			pin.well_name = "VDDA"

		if pin.names[0].startswith("P"):
			# swap the order of the names so the
			# functional names are first
			pin.names = pin.names[1:] + (pin.names[0],)

class I2cIoExpander(Part):
	REFDES_PREFIX = "U"
	part_number = "TCA6416ARTWR"
	package = "SSOPwhatever"
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
	PINS = [
		"VCCA",
		"VCCB",
		"GND",
		"OE_L",
	]

	@property
	def direction_AB(self):
		return self.VCCA.net

	@property
	def direction_BA(self):
		return self.GND.net

class LevelShifter2(LevelShifter):
	part_number = "SN74AVC2T245RSWR"
	package = "SSOP10?"
	PINS = list(LevelShifter.PINS)
	for i in range(1, 3):
		PINS.append("A%d" % i)
		PINS.append("B%d" % i)
		PINS.append("DIR%d" % i)

class LevelShifter4(LevelShifter):
	part_number = "SN74AVC4T774RSVR"
	package = "SSOP16?"
	PINS = list(LevelShifter.PINS)
	for i in range(1, 5):
		PINS.append("A%d" % i)
		PINS.append("B%d" % i)
		PINS.append("DIR%d" % i)
		# TODO, add these in some kind of bundles, or a list

vbus_in = Net("VBUS_IN")
gnd = Net("GND")
def decoupling(value = "100n"):
	return C(value, to=gnd, package="402", part_number="CY" + value) #defined_at: not here

stm32 = STM32F072()

dut = ServoConnector()
gnd << (pin for pin in dut.pins if pin.name.startswith("GND"))

# usb stuff
usb = UsbConnector()
usb_esd = UsbEsdDiode()
Net("USB_DP") << usb.DP << usb_esd.P1 << stm32
Net("USB_DM") << usb.DM << usb_esd.P2 << stm32
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
drop_diode = DoubleDiode()
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
	L("600@100MHz", to=pp3300, package="603"),
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
boot0_q = FET("CSD13381F4", package="sot23")
# Use OTG + A-TO-A cable to go to bootloader mode
Net("USB_ID") << usb.ID << boot0_q.G << R("51.1k", to=vbus_in, package="402", part_number="R51.1k")
boot0 << boot0_q.D << R("51.1k", to=vbus_in, package="402", part_number="R51.1k")
gnd << boot0_q.S
Net("EC_UART_TX") << stm32 << prog.UART_TX
Net("EC_UART_RX") << stm32 << prog.UART_RX

# TODO: stm32 pins, probably some will be below though

# io expander definition + power
io = I2cIoExpander()
pp3300 << io.VCCI << decoupling()
gnd << io.GND << io.PAD
gnd << io.A0 # i2c addr 7'H=0x20
Net("SERVO_SDA") << R("4.7k", to=pp3300, package="402", part_number="R4.7k") << stm32 << io.SDA
Net("SERVO_SCL") << R("4.7k", to=pp3300, package="402", part_number="R4.7k") << stm32 << io.SCL
Net("RESET_L") << io.RESET_L << stm32
pp1800 << io.VCCP << decoupling()
io.P03 << TP()
io.P17 << TP()

# TODO: pins for io expander
# TODO: FTDI_MFG_MODE

# JTAG
jtag_vref = Net("PPDUT_JTAG_VREF")
jtag_vref << dut.JTAG_VREF

shifter1 = LevelShifter4()
pp3300 >> shifter1.VCCA << decoupling()
jtag_vref >> shifter1.VCCB << decoupling()
gnd >> shifter1.GND

shifter2 = LevelShifter4()
pp3300 >> shifter2.VCCA << decoupling()
jtag_vref >> shifter2.VCCB << decoupling()
gnd >> shifter2.GND

Net("JTAG_BUFOUT_EN_L") << stm32 >> shifter1.OE_L
Net("JTAG_BUFIN_EN_L")  << stm32  >> shifter2.OE_L

# spare
pp3300 >> shifter1.A1
shifter1.direction_AB >> shifter1.DIR1
shifter1.B1

Net("SERVO_JTAG_TRST_L") << stm32 << shifter1.A2
Net("SERVO_JTAG_TRST_DIR") << stm32 >> shifter1.DIR2
Net("DUT_JTAG_TRST_L") << dut << shifter1.B2

Net("SERVO_JTAG_TMS") << stm32 << shifter1.A3
Net("SERVO_JTAG_TRST_DIR") >> shifter1.DIR3
Net("DUT_JTAG_TMS") >> dut << shifter1.B3

Net("SERVO_JTAG_TDI") << stm32 << shifter1.A4
Net("SERVO_JTAG_TDI_DIR") << stm32 >> shifter1.DIR4
Net("DUT_JTAG_TDI") << dut << shifter1.B4 >> shifter2.B3
shifter2.direction_BA >> shifter2.DIR3
Net("SERVO_JTAG_SWDIO") << shifter2.A3 # >> mux.IN1

Net("DUT_JTAG_TDO") << dut >> shifter2.B1
shifter2.direction_BA >> shifter2.DIR1
Net("SERVO_JTAG_TDO") << shifter2.A1 # >> mux.IN0

Net("DUT_JTAG_RTCK") << dut >> shifter2.B2
shifter2.direction_BA >> shifter2.DIR2
Net("SERVO_JTAG_RTCK") >> stm32 << shifter2.A2

Net("DUT_JTAG_TCK") << dut >> shifter2.B4
shifter2.direction_AB >> shifter2.DIR4
Net("DUT_JTAG_TCK") >> stm32.UART3_TX << shifter2.A4

# TODO SERVO_TO_SPI1_MUX_CLK
# TODO jtag mux output buffer

# SPI1 & 2
servo_spi_mosi = Net("SERVO_SPI_MOSI") << stm32
servo_spi_cs = Net("SERVO_SPI_CS") << stm32

# Since the circuits look so similar, we'll just have a loop
spi_shifters = {i: LevelShifter4() for i in (1, 2)}
for i, s in spi_shifters.items():
	# Power supply
	# TODO add part
	Net("SPI%d_VREF_33" % i) << stm32
	Net("SPI%d_VREF_18" % i) << stm32
	vref = Net("PPDUT_SPI%d_VREF" % i)
	vref << dut.pins["SPI%d_VREF" % i]

	# Level shifter setup
	pp3300 >> s.VCCA << decoupling()
	vref >> s.VCCB << decoupling()
	gnd >> s.GND
	Net("SPI%d_BUF_EN_L" % i) << stm32 >> s.OE_L

	# MISO
	Net("DUT_SPI%d_MISO" % i) << dut >> s.B1
	s.direction_BA >> s.DIR1
	# A side connected after this loop

	# MOSI
	servo_spi_mosi >> s.A2
	s.direction_AB >> s.DIR2
	Net("DUT_SPI%d_MOSI" % i) << dut >> s.B2

	# CS
	servo_spi_cs >> s.A3
	s.direction_AB >> s.DIR3
	Net("DUT_SPI%d_CS" % i) << dut >> s.B3

	# CLK
	# A side connected after this loop
	s.direction_AB >> s.DIR4
	Net("DUT_SPI%d_CLK" % i) << dut >> s.B4

#Net("SPI_MUX_TO_DUT_SPI%d_MISO" % i) << shifter.A1 #>> com1
#Net("SPI_MUX_TO_DUT_SPI%d_CLK" % i) >> shifter.A4 #<< com2

# UART 1 & 2
uart_shifters = {i: LevelShifter2() for i in (1, 2)}
for i, s in uart_shifters.items():
	vref = Net("PPDUT_UART%d_VREF" % i)
	vref << dut.pins["UART%d_VREF" % i]

	# Power off to VCCA or VCCB provides isolation
	pp3300 >> s.VCCA << decoupling()
	vref >> s.VCCB << decoupling()
	gnd >> s.GND
	Net("UART%d_EN_L" % i) << stm32 >> s.OE_L

	Net("UART%d_TX" % i) << stm32 >> s.A1
	s.direction_AB >> s.DIR1
	Net("UART%d_SERVO_DUT_TX" % i) >> dut << s.B1

	Net("UART%d_DUT_SERVO_TX" % i) << dut >> s.B2
	s.direction_BA >> s.DIR2
	Net("UART%d_RX" % i) >> stm32 << s.A2

global_context.fill_refdes()
