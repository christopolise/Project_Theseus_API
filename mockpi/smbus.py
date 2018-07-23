#!/usr/bin/env python3
from enum import IntEnum
from multiprocessing import Manager, Process
from typing import List
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

manager = Manager()
shared_dict = manager.dict()


class MockBus(object):
    # The total number of registers
    REGISTERS = 64

    def __init__(self, bus: int = None):
        self.bus = bus
        self.messages = shared_dict

    def read_byte(self, address: IntEnum) -> int:
        result = self.read_byte_data(address, 0)
        logger.debug("Read Byte: DEVICE: {} Value: {}".format(address.name, result))
        return result

    def write_byte(self, address: IntEnum, byte: int):
        logger.debug("Write Byte: DEVICE: {} Value: {}".format(address.name, byte))
        self.write_byte_data(address, 0, byte)

    def read_byte_data(self, address: IntEnum, register: int) -> int:
        """Read a single word from a designated register."""
        self._create_reg_if_not_exists(address)
        if isinstance(self.messages[address], int):
            result = self.messages[address]
        else:
            result = self.messages[address][register]
        logger.debug("Read Byte Data: DEVICE: {} Register: {} Value: {}".format(address.name, register, result))
        return result

    def write_byte_data(self, address: IntEnum, register: int, value: int):
        """Write a single byte to a designated register."""
        logger.debug("Write Byte Data: DEVICE: {} Register: {} Value: {}".format(address.name, register, value))
        self._create_reg_if_not_exists(address)
        self.messages[address][register] = value

    def read_i2c_block_data(self, address: IntEnum, start_register: int, buffer: int) -> bytearray:
        self._create_reg_if_not_exists(address)
        result = self.messages[address][start_register: start_register + buffer]
        logger.debug("Read Block Data: DEVICE: {} Register: {} Value: {}".format(address.name, start_register, result))
        return result

    def write_i2c_block_data(self, address: IntEnum, start_register: int, data: List[ord]):
        self._create_reg_if_not_exists(address)
        logger.debug("Write Block Data: DEVICE: {} Register: {} Value: {}".format(address.name, start_register, data))
        for i, d in enumerate(data):
            self.messages[address][start_register + i] = d

    def _create_reg_if_not_exists(self, address: IntEnum):
        if self.messages.get(address, None) is None:
            self.messages[address] = manager.list(bytearray(self.REGISTERS))


if __name__ == "__main__":
    from time import sleep

    master = 1
    length = 5


    def write_i2c_thread():
        for i, x in enumerate(range(length)):
            MockBus().write_byte_data(address=master, register=i, value=0xf)
            print(MockBus().read_i2c_block_data(master, 0x0, length))


    Process(target=write_i2c_thread).start()

    sleep(.1)

    print(MockBus().read_i2c_block_data(master, 0, length))
