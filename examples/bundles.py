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

from pcbdl import *

class SPI(Interface):
    SIGNALS = [
        "MOSI",
        "MISO",
        ("CLK", "CK"),
        ("CS", "CS_L"),
    ]


class I2C(Interface):
    SIGNALS = [
        "SDA",
        "SCL"
    ]


class SOC(Part):
    REFDES_PREFIX = "IC"
    part_number = "Google Novem-Core Processor"
    PINS = [
        "VCC",
        "GND",

        ("GPIO0", "SPI1_MOSI"),
        ("GPIO1", "SPI1_MISO"),
        ("GPIO2", "SPI1_CLK"),
        ("GPIO3", "SPI1_CS"),

        ("GPIO4", "SPI2_MOSI", "I2C1_SDA"),
        ("GPIO5", "SPI2_MISO"),
        ("GPIO6", "SPI2_CLK", "I2C1_SCL"),
        ("GPIO7", "SPI2_CS"),
    ]
    PORTS = [
        SPI("(SPI.*)_(.*)"),
        I2C("(I2C.*)_(.*)"),
    ]


class SPIFlash(Part):
    REFDES_PREFIX = "IC"
    part_number = "SPI_FLASH_32MB"
    PINS = [
        "VCC",
        "MOSI",
        "MISO",
        "CK",
        "CS_L",
        "GND",
    ]
    PORTS = [
        SPI("(.*)", name="SPI"),
    ]


class I2CFlash(Part):
    REFDES_PREFIX = "IC"
    part_number = "I2C_FLASH_32MB"
    PINS = [
        "VCC",
        "GND",
        "SDA",
        "SCL",
        "A0",
        "A1",
    ]
    PORTS = [
        I2C("(.*)", name="I2C"),
    ]


spiflash1 = SPIFlash()
spiflash2 = SPIFlash()
i2cflash = I2CFlash()
ap = SOC()

NetBundle(SPI, "SPI1") << ap.SPI1 >> spiflash1
NetBundle(I2C, "I2C1") << ap >> i2cflash
#NetBundle(SPI, "SPI2") << ap.SPI2 >> spiflash2

global_context.autoname("bundles.refdes_mapping")
