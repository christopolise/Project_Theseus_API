from smbus2 import SMBus
from bitarray import bitarray
from Project_Theseus_API.i2c.i2c_module import I2CModule


class LaserControl(I2CModule):
    LASER_COUNT = 6

    def __init__(self, bus: SMBus, addr=0x3a):
        super().__init__(bus, addr)
        self._state = bitarray([False]*self.LASER_COUNT, endian='little')
        self._update()

    def __getitem__(self, pos):
        return self._state.__getitem__(pos)

    def __setitem__(self, pos, value):
        self._state.__setitem__(pos, value)
        self._update()

    @property
    def state(self):
        return self._state.tobytes()[0]

    @state.setter
    def state(self, byte):
        self._state = bitarray(endian='little')
        self._state.frombytes(byte.to_bytes(1, byteorder='little'))
        self._update()

    @state.setter
    def state(self, number: int):
        # You passed an integer, write that integer to the lasers
        i = 0
        # Iterate through binary but skip 0b at beginning
        for c in bin(int(number) % (2**self.LASER_COUNT))[2:].zfill(self.LASER_COUNT):
            self[i] = (c == '1')
            i += 1

    def _update(self):
        buf = bitarray(self._state)
        buf.invert()
        buf[4], buf[5] = buf[5], buf[4]
        self.write_byte(buf.tobytes()[0])

    def reset(self):
        self[:] = False


from time import sleep
if __name__ == '__main__':
    from sys import argv

    master = SMBus(1)
    lasers = LaserControl(master)
    lasers[:] = False
    option = argv[1]
    if option == "cycle":
        i = 0
        j = -1
        k = -2
        while True:
            k = j
            j = i
            i += 1
            if i >= lasers.LASER_COUNT:
                i = 0
            lasers[i] = True
            lasers[k] = False

            sleep(.1)
    else:
        try:
            lasers.state = option
            # If they passed a number, write it to the lasers
            print("Binary Written: {}".format(bin(int(option))))

        except ValueError:
            print("{} is not a recognized argument. Please input either 'cycle', or a decimal number".format(option))
