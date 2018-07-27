#!/usr/bin/env python3
from enum import IntEnum
from typing import List, Tuple
import logging
import zmq

log = logging.getLogger(__name__)

PORT = 9998


class MockBus(object):
    context = zmq.Context()
    # The total number of registers

    class Message:
        def __init__(self, data, address: IntEnum, register: int = 0):
            self.data = data
            self.address = address
            self.register = register

        @staticmethod
        def deserialize(data: str) -> Tuple[int, int, List[int]]:
            result = data.split()
            address = int(result.pop(0))
            register = int(result.pop(0))
            return address, register, [int(x) for x in result]

        def __repr__(self):
            return "{} {} {}".format(
                self.address, self.register,
                " ".join([str(x) for x in self.data]) if hasattr(self.data, "__iter__") else self.data
            )

    def __init__(self, bus: int = None):
        self.bus = bus
        # Set up server for sending data
        self.zmq_pub = self.context.socket(zmq.PUB)
        # self.zmq_pub.bind("tcp://*:{}".format(PORT))

        # Set up server for reading data
        self.zmq_sub = self.context.socket(zmq.SUB)
        self.zmq_sub.connect("tcp://localhost:{}".format(PORT))
        self.buffer = dict()

    def read_byte(self, address: IntEnum) -> int:
        self.zmq_sub.setsockopt_string(zmq.SUBSCRIBE, str(address))
        try:
            _, register, value = self.zmq_sub.recv_serialized(self.Message.deserialize, flags=zmq.NOBLOCK)
            self.buffer["{} {}".format(address, register)] = value
        except zmq.Again:
            log.debug("No data waiting for {} on register {}".format(address, register))
            return self.buffer.get("{} {}".format(address, register), 0)
        self.zmq_sub.setsockopt_string(zmq.UNSUBSCRIBE, str(address))
        log.debug("Read Byte: DEVICE: {} Register: {} Value: {}".format(address.name, register, value[0]))
        return value[0]

    def write_byte(self, address: IntEnum, byte: int):
        log.debug("Write Byte: DEVICE: {} Value: {}".format(address.name, byte))
        self.zmq_pub.send_string(str(self.Message(byte, address=address)))

    def read_byte_data(self, address: IntEnum, register: int) -> int:
        self.zmq_sub.setsockopt_string(zmq.SUBSCRIBE, str(address) + " " + str(register))
        try:
            _, _, value = self.zmq_sub.recv_serialized(self.Message.deserialize, flags=zmq.NOBLOCK)
            self.buffer["{} {}".format(address, register)] = value
        except zmq.Again:
            log.debug("No data waiting for {} on register {}".format(address, register))
            return self.buffer.get("{} {}".format(address, register), 0)
        self.zmq_sub.setsockopt_string(zmq.UNSUBSCRIBE, str(address))
        log.debug("Read Byte Data: DEVICE: {} Register: {} Value: {}".format(address.name, register, value[0]))
        return value[0]

    def write_byte_data(self, address: IntEnum, register: int, value: int):
        """Write a single word to a designated register."""
        log.debug("Write Byte Data: DEVICE: {} Register: {} Value: {}".format(address.name, register, value))
        self.zmq_pub.send_string(str(self.Message(value, address=address, register=register)))

    def read_i2c_block_data(self, address: IntEnum, start_register: int, buffer: int) -> bytearray:
        self.zmq_sub.setsockopt_string(zmq.SUBSCRIBE, str(address) + " " + str(start_register))
        try:
            _, _, result = self.zmq_sub.recv_serialized(self.Message.deserialize, flags=zmq.NOBLOCK)
            self.buffer["{} {}".format(address, start_register)] = result
        except zmq.Again:
            log.debug("No data waiting for {} on register {}".format(address, start_register))
            return self.buffer.get("{} {}".format(address, start_register), bytearray([0] * (start_register + buffer)))
        self.zmq_sub.setsockopt_string(zmq.UNSUBSCRIBE, str(address))
        while len(result) < start_register + buffer:
            result.append(0)
        log.debug("Read Block Data: DEVICE: {} Register: {} Value: {}".format(address.name, start_register, result))
        return bytearray(result)

    def write_i2c_block_data(self, address: IntEnum, start_register: int, data: List[ord]):
        log.debug("Write Block Data: DEVICE: {} Register: {} Value: {}".format(address.name, start_register, data))
        self.zmq_pub.send_string(str(self.Message(data, address=address, register=start_register)))


if __name__ == "__main__":
    from multiprocessing import Process
    from time import sleep

    logging.basicConfig(level=logging.DEBUG)

    master = 1
    length = 5


    def write_i2c_thread():
        for i, x in enumerate(range(length)):
            MockBus().write_byte_data(address=master, register=i, value=0xf)
            print(MockBus().read_i2c_block_data(master, 0x0, length))


    Process(target=write_i2c_thread).start()

    sleep(.1)

    print(MockBus().read_i2c_block_data(master, 0, length))
