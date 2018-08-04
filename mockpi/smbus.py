#!/usr/bin/env python3
from enum import IntEnum
from typing import List, Tuple
import logging
import zmq
log = logging.getLogger(__name__)

CLIENT_PORT = 9998
SERVER_PORT = 9999


# http://learning-0mq-with-pyzmq.readthedocs.io/en/latest/pyzmq/devices/queue.html
class MockBus(object):

    # The total number of registers

    class Message:
        def __init__(self, data, address: IntEnum, register: int = 0):
            self.data = data
            self.address = address
            self.register = register
            self.name = "{}_{}".format(address, register)

        @staticmethod
        def deserialize(data: str) -> Tuple[int, int, List[int]]:
            result = data.split()
            address = int(result.pop(0))
            register = int(result.pop(0))
            return address, register, [int(x) for x in result]

        def __repr__(self):
            return "{}_{} {}".format(
                self.address, self.register,
                " ".join([str(x) for x in self.data]) if hasattr(self.data, "__iter__") else self.data
            )

    def __init__(self, bus: int = None):
        context = zmq.Context().instance()
        self.bus = bus

        # Set up client for reading data
        self.zmq = context.socket(zmq.REQ)
        self.zmq.connect("tcp://localhost:{}".format(CLIENT_PORT))
        self.buffer = dict()

    def read_byte(self, address: IntEnum) -> int:
        register = 0
        self.zmq.setsockopt_string(zmq.SUBSCRIBE, str(address.value) + "_0")
        log.debug("Waiting for {}".format(str(address.value) + "_0"))
        try:
            _, register, value = self.zmq.recv_serialized(self.Message.deserialize, flags=zmq.NOBLOCK)
            self.buffer["{}_{}".format(address, register)] = value
        except zmq.Again:
            log.debug("No data waiting for {} on register {}".format(address.name, register))
            return self.buffer.get("{}_{}".format(address, register), 0)
        self.zmq.setsockopt_string(zmq.UNSUBSCRIBE, str(address) + "_0")
        log.debug("Read Byte: DEVICE: {} Register: {} Value: {}".format(address.name, register, value[0]))
        return value[0]

    def write_byte(self, address: IntEnum, byte: int):
        msg = self.Message(byte, address=address)
        log.debug("Write Byte: DEVICE: {} Value: {}".format(address.name, str(msg)))
        self.zmq.send_string(str(msg))
        self.zmq.recv_string()

    def read_byte_data(self, address: IntEnum, register: int) -> int:
        self.zmq.setsockopt_string(zmq.SUBSCRIBE, str(address) + "_" + str(register))
        try:
            _, _, value = self.zmq.recv_serialized(self.Message.deserialize, flags=zmq.NOBLOCK)
            self.buffer["{}_{}".format(address, register)] = value
        except zmq.Again:
            log.debug("No data waiting for {} on register {}".format(address.name, register))
            return self.buffer.get("{}_{}".format(address, register), 0)
        self.zmq.setsockopt_string(zmq.UNSUBSCRIBE, str(address))
        log.debug("Read Byte Data: DEVICE: {} Register: {} Value: {}".format(address.name, register, value[0]))
        return value[0]

    def write_byte_data(self, address: IntEnum, register: int, value: int):
        """Write a single word to a designated register."""
        log.debug("Write Byte Data: DEVICE: {} Register: {} Value: {}".format(address.name, register, value))
        self.zmq.send_string(str(self.Message(value, address=address, register=register)))
        # TODO buffer the received message
        self.zmq.recv_string()

    def read_i2c_block_data(self, address: IntEnum, start_register: int, buffer: int) -> bytearray:
        self.zmq.subscribe(str(address) + "_" + str(start_register))
        try:
            _, _, result = self.zmq.recv_serialized(self.Message.deserialize, flags=zmq.NOBLOCK)
            self.buffer["{}_{}".format(address, start_register)] = result
        except zmq.Again:
            log.debug("No data waiting for {} on register {}".format(address.name, start_register))
            return self.buffer.get("{}_{}".format(address, start_register), bytearray([0] * (start_register + buffer)))
        self.zmq.setsockopt_string(zmq.UNSUBSCRIBE, str(address))
        while len(result) < start_register + buffer:
            result.append(0)
        log.debug("Read Block Data: DEVICE: {} Register: {} Value: {}".format(address.name, start_register, result))
        return bytearray(result)

    def write_i2c_block_data(self, address: IntEnum, start_register: int, data: List[ord]):
        log.debug("Write Block Data: DEVICE: {} Register: {} Value: {}".format(address.name, start_register, data))
        self.zmq.send_string(str(self.Message(data, address=address, register=start_register)))
        self.zmq.recv_string()


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
