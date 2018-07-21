#!/usr/bin/env python3
from multiprocessing import Manager, Process
from typing import List
import logging

from game.constants import I2C

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

manager = Manager()
shared_dict = manager.dict()


class MockBus(object):
    # The total number of registers
    REGISTERS = 64

    def __init__(self, bus: int = None):
        self.bus = bus
        self.messages = shared_dict

    def read_byte(self, address: I2C) -> int:
        result = self.messages.get(address, 0)
        logging.debug("DEVICE: {} Value: {}".format(address, result))
        return result

    def write_byte(self, address: I2C, byte: int):
        logging.debug("DEVICE: {} Value: {}".format(address, byte))
        self.messages[address] = byte

    def read_byte_data(self, address: I2C, register: int) -> int:
        """Read a single word from a designated register."""
        self._create_reg_if_not_exists(address)
        if isinstance(self.messages[address], int):
            result = self.messages[address]
        else:
            result = self.messages[address][register]
        logging.debug("DEVICE: {} Register: {} Value: {}".format(address, register, result))
        return result

    def write_byte_data(self, address: I2C, register: int, value: int):
        """Write a single byte to a designated register."""
        logging.debug("DEVICE: {} Register: {} Value: {}".format(address, register, value))
        self._create_reg_if_not_exists(address)
        self.messages[address][register] = value

    def read_i2c_block_data(self, address: I2C, start_register: int, buffer: int) -> bytearray:
        self._create_reg_if_not_exists(address)
        result = bytearray(self.messages[address][start_register: start_register + buffer])
        logging.debug("DEVICE: {} Register: {} Value: {}".format(address, start_register, result))
        return result

    def write_i2c_block_data(self, address: I2C, start_register: int, data: List[ord]):
        logging.debug("DEVICE: {} Register: {} Value: {}".format(address, start_register, data))
        data = manager.list([0] * start_register).extend(data)
        self.messages[address] = data

    def _create_reg_if_not_exists(self, address: I2C):
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
