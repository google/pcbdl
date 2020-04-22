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
Full reimplementation of servo micro in pcbdl.

Servo Micro's information page (including pdf schematics made in orthodox tools) can be found at:
https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/refs/heads/master/docs/servo_micro.md
"""

from pcbdl import *

# Start of things that should really be in a generic library
# It's a TODO to make a library. Until then, 300 lines to start a new schematic from scratch with no library is probably not bad.
def make_connector(pin_count):
    class Connector(Part):
        REFDES_PREFIX = "CN"

        PINS = []

    for i in range(pin_count):
        i += 1 # 1 indexed
        pin = Pin(i, "P%d" % i)
        Connector.PINS.append(pin)

    return Connector

class UsbConnector(Part):
    REFDES_PREFIX = "CN"
    part_number = "1981568-1"
    package = "TE_1981568-1"
    PINS = [
        "VBUS",
        ("DM", "D-"),
        ("DP", "D+"),
        "ID",
        "GND",
        Pin("G", numbers=("G1", "G2", "G3", "G4")),
    ]

class FET(Part):
    """FET Transistor"""
    REFDES_PREFIX = "Q"

    PINS = [
        Pin("D", "D"),
        Pin("G", "G"),
        Pin("S", "S"),
    ]

class Regulator(Part):
    REFDES_PREFIX = "U"

    PINS = [
        Pin("IN", type=PinType.POWER_INPUT),
        Pin("OUT", type=PinType.POWER_OUTPUT),
        Pin("GND", type=PinType.POWER_INPUT),
    ]

class MIC5504(Regulator):
    part_number = "MIC5504-3.3YMT"
    package = "SON65P100X100X40-5T48X48N"

    PINS = [
        Pin("4", "IN"),
        Pin("1", "OUT"),
        Pin("3", "EN"),
        Pin(("2", "G1"), ("GND", "PAD")),
    ]

class TLV70018DSER(Regulator):
    part_number = "TLV70018DSER"
    package = "SON50P150X150X80-6L"

    PINS = [
        Pin("1", "IN"),
        Pin("3", "OUT"),
        Pin("6", "EN"),
        Pin("4", "NC1"),
        Pin("5", "NC2"),
        Pin("2", "GND"),
    ]

class UsbEsdDiode(Part):
    REFDES_PREFIX = "D"
    part_number = "TPD2E001DRLR"
    package = "SOP50P170X60-5N"
    PINS = [
        Pin("1", "VCC", type=PinType.POWER_INPUT),
        Pin("4", "GND", type=PinType.POWER_INPUT),
        Pin("3", "P1"),
        Pin("5", "P2"),
        Pin("2", "NC"),
    ]

class DoubleDiode(Part):
    REFDES_PREFIX = "D"
    part_number = "240-800MV"
    package = "SOT95P247X115-3L"
    PINS = ["A1", "A2", "K"]

class STM32F072(Part):
    REFDES_PREFIX = "U"

    part_number = "STM32F072CBU6TR"
    package = "QFN05P_7-1X7-1_0-6_49N"

    PINS = [
        Pin(("24", "48"), "VDD",    type=PinType.POWER_INPUT),
        Pin("1",          "VBAT",   type=PinType.POWER_INPUT),
        Pin("9",          "VDDA",   type=PinType.POWER_INPUT),
        Pin("36",         "VDDIO2", type=PinType.POWER_INPUT),

        Pin(("23", "35", "47"), "VSS"),
        Pin("8",  "VSSA"),
        Pin("49", "PAD"),

        Pin("44", "BOOT0"),
        Pin("7",  "NRST"),
    ]

    for i in range(8):
        PINS.append(Pin(i + 10, "PA%d" % i))

    PINS += [
        Pin("29", "PA8"),
        Pin("30", "PA9"),
        Pin("31", "PA10"),
        Pin("32", "PA11"),
        Pin("33", "PA12"),
        Pin("34", "PA13"),
        Pin("37", "PA14"),
        Pin("38", "PA15"),

        Pin("18", "PB0"),
        Pin("19", "PB1"),
        Pin("20", "PB2"),
        Pin("39", "PB3"),
        Pin("40", "PB4"),
        Pin("41", "PB5"),
        Pin("42", "PB6"),
        Pin("43", "PB7"),

        Pin("45", "PB8"),
        Pin("46", "PB9"),
        Pin("21", "PB10"),
        Pin("22", "PB11"),
        Pin("25", "PB12"),
        Pin("26", "PB13"),
        Pin("27", "PB14"),
        Pin("28", "PB15"),

        Pin("2",  "PC13"),
        Pin("3", ("PC14", "OSC32_IN")),
        Pin("4", ("PC15", "OSC32_OUT")),

        Pin("5", ("PF0", "OSC_IN")),
        Pin("6", ("PF1", "OSC_OUT")),
    ]

    for pin in PINS:
        if pin.names[0].startswith("PA"):
            pin.well_name = "VDD"

        if pin.names[0].startswith("PB"):
            pin.well_name = "VDDA"

        if pin.names[0].startswith("PC"):
            pin.well_name = "VDDA"

        if pin.names[0].startswith("PF"):
            pin.well_name = "VDDA"

class I2cIoExpander(Part):
    REFDES_PREFIX = "U"

    part_number = "TCA6416ARTWR"
    package = "QFN50P400X400X080-25N"

    PINS = [
        Pin("23", "VCCI"),
        Pin("21", "VCCP"),
        Pin("9",  "GND"),
        Pin("25", "PAD"),

        Pin("19", "SCL"),
        Pin("20", "SDA"),
        Pin("22", "INT_L"),
        Pin("24", "RESET_L"),

        Pin("18", "A0"),
    ]

    for i in range(8):
        PINS.append(Pin(i + 1, "P0%d" % i))

    for i in range(8):
        PINS.append(Pin(i + 10, "P1%d" % i))

class Mux(Part):
    REFDES_PREFIX = "U"

    part_number = "313-00929-00"
    package = "SOT65P210X110-6L"

    PINS = [
        Pin("5", "VCC"),
        Pin("2", "GND"),

        Pin("3", ("0", "IN0")),
        Pin("1", ("1", "IN1")),

        Pin("6", ("S0", "SEL")),
        Pin("4", ("Y", "OUT")),
    ]

class OutputBuffer(Part):
    REFDES_PREFIX = "U"

    part_number = "SN74LVC1G126YZPR"
    package = "BGA5C50P3X2_141X91X50L"

    PINS = [
        Pin("A2", "VCC"),
        Pin("C1", "GND"),

        Pin("B1", ("A", "IN")),
        Pin("A1", ("OE", "SEL")),
        Pin("C2", ("Y", "OUT")),
    ]

class LevelShifter(Part):
    """
        Bidirectional Level Shifter

        DIR=0 : B->A
        DIR=1 : A->B
    """
    REFDES_PREFIX = "U"

    PINS = [
        "VCCA",
        "VCCB",
        "GND",
    ]

    @property
    def direction_AB(self):
        return self.VCCA.net

    @property
    def direction_BA(self):
        return self.GND.net

class LevelShifter1(LevelShifter):
    __doc__ = LevelShifter.__doc__
    part_number = "SN74AVC1T45DRLR"
    package = "SOP50P170X60-6N"

    PINS = [
        Pin("1", "VCCA", type=PinType.POWER_INPUT),
        Pin("6", "VCCB", type=PinType.POWER_INPUT),
        Pin("3", "A"),
        Pin("4", "B"),
        Pin("5", "DIR"),
        Pin("2", "GND", type=PinType.POWER_INPUT),
    ]

class LevelShifter2(LevelShifter):
    __doc__ = LevelShifter.__doc__
    part_number = "SN74AVC2T245RSWR"
    package = "QFN40P145X185X55-10N"

    PINS = [
        Pin("7",  "VCCA", type=PinType.POWER_INPUT),
        Pin("6",  "VCCB", type=PinType.POWER_INPUT),
        Pin("2",  "OE_L"),
        Pin("8",  "A1"),
        Pin("9",  "A2"),
        Pin("5",  "B1"),
        Pin("4",  "B2"),
        Pin("10", "DIR1"),
        Pin("1",  "DIR2"),
        Pin("3",  "GND", type=PinType.POWER_INPUT),
    ]

class LevelShifter4(LevelShifter):
    __doc__ = LevelShifter.__doc__
    part_number = "SN74AVC4T774RSVR"
    package = "QFN40P265X185X55-16N"

    PINS = [
        Pin("14", "VCCA", type=PinType.POWER_INPUT),
        Pin("13", "VCCB", type=PinType.POWER_INPUT),
        Pin("7",  "OE_L"),
        Pin("1",  "A1"),
        Pin("2",  "A2"),
        Pin("3",  "A3"),
        Pin("4",  "A4"),
        Pin("12", "B1"),
        Pin("11", "B2"),
        Pin("10", "B3"),
        Pin("9",  "B4"),
        Pin("15", "DIR1"),
        Pin("16", "DIR2"),
        Pin("5",  "DIR3"),
        Pin("6",  "DIR4"),
        Pin("8",  "GND",  type=PinType.POWER_INPUT),
    ]

class AnalogSwitch(Part):
    """
        Dual Analog Switch

        IN   DIRECTION
        L    NC -> COM
        H    NO -> COM
    """
    REFDES_PREFIX = "U"

    part_number = "TS3A24159"
    package = "BGA10C50P4X3_186X136X50L"

    PINS = [
        Pin("D2", ("V+", "VCC")),
        Pin("A2", "GND"),

        Pin("B1", ("IN1", "SEL1")),
        Pin("C1", "COM1"),
        Pin("A1", "NC1"),
        Pin("D1", "NO1"),

        Pin("B3", ("IN2", "SEL2")),
        Pin("C3", "COM2"),
        Pin("A3", "NC2"),
        Pin("D3", "NO2"),
    ]

class PowerSwitch(Part):
    REFDES_PREFIX = "U"

    part_number = "ADP194ACBZ-R7"
    package = "BGA4C40P2X2_80X80X56"

    PINS = [
        Pin("A1", ("IN", "IN1")),
        Pin("A2", ("OUT", "OUT1")),
        Pin("B1", "EN"),
        Pin("B2", "GND"),
    ]
# End of things that should be in a generic library

# Maybe this connector could be in a library too, since it's not too specific to this servo schematic
class ServoConnector(make_connector(pin_count=50)):
    part_number = "AXK850145WG"
    package = "AXK850145WG"

    pin_names_match_nets = True
    pin_names_match_nets_prefix = "DUT_"
    PINS = [
        ("P1",  "GND"),
        ("P2",  "SPI2_CLK", "SPI2_SK"),
        ("P3",  "SPI2_CS"),
        ("P4",  "SPI2_MOSI", "SPI2_DI"),
        ("P5",  "SPI2_MISO", "SPI2_DO"),
        ("P6",  "SPI2_VREF"),
        ("P7",  "SPI2_HOLD_L"),
        ("P8",  "GND"),
        ("P9",  "SPI1_CLK", "SPI1_SK"),
        ("P10", "SPI1_CS"),
        ("P11", "SPI1_MOSI", "SPI1_DI"),
        ("P12", "SPI1_MISO", "SPI1_DO"),
        ("P13", "SPI1_VREF"),
        ("P14", "EC_RESET_L", "COLD_RESET_L"),
        ("P15", "GND"),
        ("P16", "UART2_SERVO_DUT_TX", "UART2_RXD"),
        ("P17", "UART2_DUT_SERVO_TX", "UART2_TXD"),
        ("P18", "UART2_VREF"),
        ("P19", "SD_DETECT_L"),
        ("P20", "GND"),
        ("P21", "JTAG_TCK"),
        ("P22", "PWR_BUTTON"),
        ("P23", "JTAG_TMS"),
        ("P24", "JTAG_TDI"),
        ("P25", "JTAG_TDO"),
        ("P26", "JTAG_RTCK"),
        ("P27", "JTAG_TRST_L"),
        ("P28", "JTAG_SRST_L", "WARM_RESET_L"),
        ("P29", "JTAG_VREF"),
        ("P30", "REC_MODE_L", "GOOG_REC_MODE_L"),
        ("P31", "GND"),
        ("P32", "UART1_SERVO_DUT_TX", "UART1_RXD"),
        ("P33", "UART1_DUT_SERVO_TX", "UART1_TXD"),
        ("P34", "UART1_VREF"),
        ("P35", "I2C_3.3V"),
        ("P36", "GND"),
        ("P37", "I2C_SDA"),
        ("P38", "I2C_SCL"),
        ("P39", "HPD"),
        ("P40", "FW_WP", "MFG_MODE"),
        ("P41", "PROC_HOT_L", "FW_UPDATE_L", "FW_UP_L"),
        ("P42", "GND"),
        ("P43", "DEV_MODE"),
        ("P44", "LID_OPEN"),
        ("P45", "PCH_DISABLE_L", "CPU_NMI"),
        ("P46", "KBD_COL1"),
        ("P47", "KBD_COL2"),
        ("P48", "KBD_ROW1"),
        ("P49", "KBD_ROW2"),
        ("P50", "KBD_ROW3"),
    ]
    _postprocess_pin = Pin.second_name_important

# The following part definitions are only related to this circuit
class ProgrammingConnector(make_connector(8)):
    part_number = "FH34SRJ-8S-0.5SH(50)"
    package = "HRS_FH34SRJ-8S-0-5SH"

    PINS = [
        ("P1", "GND"),
        ("P2", "UART_TX"),
        ("P3", "UART_RX"),
        ("P6", "NRST"),
        ("P8", "BOOT0"),
        Pin("G", numbers=("G1", "G2")),
    ]
    _postprocess_pin = Pin.second_name_important

class JtagConnector(make_connector(10)):
    part_number = "HDR_2X5_50MIL-210-00939-00-SAMTEC_FTSH-105-01"
    package = "SAMTEC_FTSH-105-01-L-DV-K"


    pin_names_match_nets = True
    pin_names_match_nets_prefix = "DUT_JTAG_"
    PINS = [
        ("P1",  "VCC"),
        ("P2",  "TMS", "SWDIO"),
        ("P3",  "GND"),
        ("P4",  "TCK", "SWDCLK"),
        ("P5",  "GND"),
        ("P6",  "TDO", "SWO"),
        ("P7",  "KEY"),
        ("P8",  "TDI"),
        ("P9",  "GNDDetect"),
        ("P10", "RESET"),
    ]
    _postprocess_pin = Pin.second_name_important

class ServoEC(STM32F072):
    pin_names_match_nets = True
    PINS = [
        Pin(("PA0",  "UART3_TX")),
        Pin(("PA1",  "UART3_RX")),
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

        Pin(("PB8",  "MASTER_I2C_SCL")),
        Pin(("PB9",  "MASTER_I2C_SDA")),
        Pin(("PB10", "UART2_TX")),
        Pin(("PB11", "UART2_RX")),
        Pin(("PB12", "SERVO_SPI_CS")),
        Pin(("PB13", "SERVO_TO_SPI1_MUX_CLK")),
        Pin(("PB14", "SERVO_TO_SPI1_MUX_MISO")),
        Pin(("PB15", "SERVO_SPI_MOSI")),

        Pin(("PC13", "RESET_L")),
        Pin(("PC14", "SERVO_JTAG_TMS_DIR")),
        Pin(("PC15", "SERVO_JTAG_TDO_SEL")),

        Pin(("PF0", "JTAG_BUFOUT_EN_L")),
        Pin(("PF1", "JTAG_BUFIN_EN_L")),
    ]
    _postprocess_pin = Pin.second_name_important

# Start of actual schematic
vbus_in = Net("VBUS_IN")
gnd = Net("GND")
def decoupling(value="100n", package=None):
    if package is None:
        package = "CAPC0603X33L"

        if "u" in value:
            package = "CAPC1005X71L"

        if "0u" in value:
            package = "CAPC1608X80L"

    return C(value, to=gnd, package=package, part_number="CY" + value) #defined_at: not here
old_R = R
def R(value, to):
    return old_R(value, package="RESC0603X23L", part_number="R" + value, to=to) #defined_at: not here

# usb stuff
usb = UsbConnector()
usb_esd = UsbEsdDiode()
Net("USB_DP") << usb.DP << usb_esd.P1
Net("USB_DM") << usb.DM << usb_esd.P2 >> usb_esd.NC
vbus_in << usb.VBUS << usb_esd.VCC
gnd << usb.GND << usb.G << usb_esd.GND
# We could make this type-c instead!

# 3300 regulator
pp3300 = Net("PP3300")
reg3300 = MIC5504()
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
reg1800 = TLV70018DSER()
drop_diode = DoubleDiode()
pp3300 << drop_diode.A1 << drop_diode.A2
Net("PP1800_VIN") << (
    drop_diode.K,
    reg1800.IN, decoupling(),
    reg1800.EN
)
gnd << reg1800.GND
pp1800 << reg1800.OUT << decoupling("1u", "CAPC0603X33L")

ec = ServoEC()
usb.DP << ec
usb.DM << ec

# ec power
pp3300 << (
    ec.VBAT, decoupling(),
    ec.VDD, decoupling(),
    decoupling("4.7u"),
)
Net("PP3300_PD_VDDA") << (
    ec.VDDA,
    L("600@100MHz", to=pp3300, package="INDC1005L", part_number="FERRITE_BEAD-185-00019-00"),
    decoupling("1u"),
    decoupling("100p"),
)
pp3300 << (
    ec.VDDIO2, decoupling(),
    decoupling("4.7u"),
)
gnd << ec.VSS << ec.VSSA << ec.PAD

# ec programming/debug
prog = ProgrammingConnector()
gnd << prog.GND << prog.G
Net("PD_NRST_L") << (
    ec.NRST,
    prog.NRST,
    decoupling(),
)
boot0 = Net("PD_BOOT0")
boot0_q = FET("CSD13381F4", package="DFN100X60X35-3L")
# Use OTG + A-TO-A cable to go to bootloader mode
Net("USB_ID") >> boot0_q.G >> R("51.1k", to=vbus_in) << usb.ID
boot0 << boot0_q.D << R("51.1k", to=vbus_in) << ec.BOOT0 << prog.BOOT0
gnd << boot0_q.S
Net("EC_UART_TX") << ec << prog.UART_TX
Net("EC_UART_RX") << ec << prog.UART_RX

ppdut_spi_vrefs = {
    1: Net("PPDUT_SPI1_VREF"),
    2: Net("PPDUT_SPI2_VREF"),
}

jtag_buffer_to_servo_tdo = Net("JTAG_BUFFER_TO_SERVO_TDO") >> ec.UART3_RX  # also Net("UART3_TX")
servo_jtag_tck = Net("SERVO_JTAG_TCK") << ec.UART3_TX # also Net("UART3_TX")

dut = ServoConnector()
gnd << dut.GND
pp3300 >> dut.pins["I2C_3.3V"]

io = I2cIoExpander()
pp3300 << io.VCCI << decoupling()
gnd << io.GND << io.PAD
gnd << io.A0 # i2c addr 7'H=0x20
Net("I2C_REMOTE_ADC_SDA") << R("4.7k", to=pp3300) << ec.MASTER_I2C_SDA << io.SDA << dut.I2C_SDA
Net("I2C_REMOTE_ADC_SCL") << R("4.7k", to=pp3300) << ec.MASTER_I2C_SCL << io.SCL << dut.I2C_SCL
Net("RESET_L") << io.RESET_L << ec
pp1800 << io.VCCP << decoupling()

dut_mfg_mode = Net("DUT_MFG_MODE") << dut
mfg_mode_shifter = LevelShifter1()
gnd << mfg_mode_shifter.GND

Net("FW_WP_EN") << mfg_mode_shifter.VCCA << io.P00 << decoupling() << R("4.7k", to=gnd)
Net("FTDI_MFG_MODE") << io.P01 << mfg_mode_shifter.A
dut_mfg_mode << io.P02
io.P03 << TP(package="TP075") # spare
Net("SPI_HOLD_L") << io.P04 >> dut.SPI2_HOLD_L
Net("DUT_COLD_RESET_L") << io.P05 >> dut
Net("DUT_PWR_BUTTON") << io.P06 >> dut

Net("DUT_GOOG_REC_MODE_L") << io.P10 >> dut
dut_mfg_mode << io.P11
Net("HPD") << io.P12 >> dut
Net("FW_UP_L") << io.P13 >> dut
Net("DUT_LID_OPEN") << io.P14 >> dut
Net("DUT_DEV_MODE") << io.P15 >> dut
Net("PCH_DISABLE_L") << io.P16 >> dut
io.P17 << TP(package="TP075") # spare

mfg_mode_shifter.direction_AB << mfg_mode_shifter.DIR
ppdut_spi_vrefs[2] >> mfg_mode_shifter.VCCB << decoupling()
Net("DUT_MFG_MODE_BUF") << R("0", to=dut_mfg_mode) >> mfg_mode_shifter.B

# JTAG
jtag_connector = JtagConnector()
gnd >> jtag_connector.GND
Net("DUT_WARM_RESET_L") << io.P07 >> dut << jtag_connector.RESET

jtag_vref = Net("PPDUT_JTAG_VREF")
jtag_vref << dut.JTAG_VREF >> jtag_connector.VCC

shifter1 = LevelShifter4()
pp3300 >> shifter1.VCCA << decoupling()
jtag_vref >> shifter1.VCCB << decoupling()
gnd >> shifter1.GND

shifter2 = LevelShifter4()
pp3300 >> shifter2.VCCA << decoupling()
jtag_vref >> shifter2.VCCB << decoupling()
gnd >> shifter2.GND

jtag_mux = Mux()
pp3300 >> jtag_mux.VCC << decoupling()
gnd >> jtag_mux.GND
Net("SERVO_JTAG_TDO_SEL") << ec >> jtag_mux.SEL

jtag_output_buffer = OutputBuffer()
pp3300 >> jtag_output_buffer.VCC << decoupling()
gnd >> jtag_output_buffer.GND
Net("SERVO_JTAG_TDO_BUFFER_EN") << ec >> jtag_output_buffer.OE
Net("SERVO_JTAG_MUX_TDO") << jtag_mux.OUT >> jtag_output_buffer.IN
jtag_buffer_to_servo_tdo << jtag_output_buffer.OUT

Net("JTAG_BUFOUT_EN_L") << ec >> shifter1.OE_L
Net("JTAG_BUFIN_EN_L")  << ec  >> shifter2.OE_L

pp3300 >> shifter1.A1 # spare
Net("SERVO_JTAG_TRST_L") << ec << shifter1.A2
Net("SERVO_JTAG_TMS") << ec << shifter1.A3
Net("SERVO_JTAG_TDI") << ec << shifter1.A4

shifter1.direction_AB >> shifter1.DIR1 # spare
Net("SERVO_JTAG_TRST_DIR") << ec >> shifter1.DIR2
Net("SERVO_JTAG_TMS_DIR") << ec >> shifter1.DIR3
Net("SERVO_JTAG_TDI_DIR") << ec >> shifter1.DIR4

shifter1.B1 # spare
Net("DUT_JTAG_TRST_L") << dut << shifter1.B2
Net("DUT_JTAG_TMS") >> dut << shifter1.B3 << jtag_connector
Net("DUT_JTAG_TDI") << dut << shifter1.B4 >> shifter2.B3 >> jtag_connector

Net("DUT_JTAG_TDO") << dut >> shifter2.B1 >> jtag_connector
Net("DUT_JTAG_RTCK") << dut >> shifter2.B2
Net("DUT_JTAG_TCK") << dut >> shifter2.B4 >> jtag_connector

shifter2.direction_BA >> shifter2.DIR1
shifter2.direction_BA >> shifter2.DIR2
shifter2.direction_BA >> shifter2.DIR3
shifter2.direction_AB >> shifter2.DIR4

Net("SERVO_JTAG_TDO") << shifter2.A1 >> jtag_mux.IN0
Net("SERVO_JTAG_RTCK") >> ec << shifter2.A2
Net("SERVO_JTAG_SWDIO") << shifter2.A3 >> jtag_mux.IN1
servo_jtag_tck << shifter2.A4

# SPI1 & 2
# TODO SERVO_TO_SPI1_MUX_CLK
servo_spi_mosi = Net("SERVO_SPI_MOSI") << ec
servo_spi_cs = Net("SERVO_SPI_CS") << ec

# Since the circuits look so similar, we'll just have a loop
spi_shifters = {
    1: LevelShifter4(),
    2: LevelShifter4(),
}
for i, s in spi_shifters.items():
    # Power supply
    vref = ppdut_spi_vrefs[i]
    vref << dut.pins["SPI%d_VREF" % i]

    power_switches = [
        ("18", pp1800, PowerSwitch()),
        ("33", pp3300, PowerSwitch()),
    ]
    for voltage, input_rail, power_switch in power_switches:
        gnd << power_switch.GND
        Net("SPI%d_VREF_%s" % (i, voltage)) << ec >> power_switch.EN << R("4.7k", to=gnd)
        input_rail << power_switch.IN
        vref << power_switch.OUT

    # Level shifter setup
    pp3300 >> s.VCCA << decoupling()
    vref >> s.VCCB << decoupling()
    gnd >> s.GND
    Net("SPI%d_BUF_EN_L" % i) << ec >> s.OE_L

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

spi1_mux = AnalogSwitch()
pp3300 >> spi1_mux.VCC >> decoupling()
gnd >> spi1_mux.GND
Net("SPI1_MUX_SEL") << ec >> spi1_mux.SEL1 >> spi1_mux.SEL2

Net("SPI_MUX_TODUT_SPI1_MISO") >> spi1_mux.COM1 << spi_shifters[1].A1
Net("SPI_MUX_TO_DUT_SPI1_CLK")  << spi1_mux.COM2 >> spi_shifters[1].A4

Net("SERVO_TO_SPI1_MUX_MISO")  << spi1_mux.NO1 << spi_shifters[2].A1 >> ec
Net("SERVO_TO_SPI1_MUX_CLK")   >> spi1_mux.NO2 >> spi_shifters[2].A4 << ec

jtag_buffer_to_servo_tdo << spi1_mux.NC1
servo_jtag_tck >> spi1_mux.NC2

# UART 1 & 2
uart_shifters = {
    1: LevelShifter2(),
    2: LevelShifter2(),
}
for i, s in uart_shifters.items():
    vref = Net("PPDUT_UART%d_VREF" % i)
    vref << dut.pins["UART%d_VREF" % i]

    # Power off to VCCA or VCCB provides isolation
    pp3300 >> s.VCCA << decoupling()
    vref >> s.VCCB << decoupling()
    gnd >> s.GND
    Net("UART%d_EN_L" % i) << ec >> s.OE_L

    Net("UART%d_TX" % i) << ec >> s.A1
    s.direction_AB >> s.DIR1
    Net("UART%d_SERVO_DUT_TX" % i) >> dut << s.B1

    Net("UART%d_DUT_SERVO_TX" % i) << dut >> s.B2
    s.direction_BA >> s.DIR2
    Net("UART%d_RX" % i) >> ec << s.A2

global_context.autoname("servo_micro.refdes_mapping")
