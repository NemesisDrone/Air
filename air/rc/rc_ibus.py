import struct
from typing import Tuple, Union

import serial


class RcIbus:
    """
    This class is used to read and write iBus packages from/to serial port. Especially for the FlySky i6X.
    """

    IBUS_START = b"\x20"
    IBUS_START_BYTES = [0x20, 0x40]
    IBUS_FORMAT = "<BBHHHHHHHHHHHHHHh"
    IBUS_FORMAT_CALC_CHECKSUM = "<BBHHHHHHHHHHHHHH"

    def __init__(self, serial_port: str, baudrate: int = 115200) -> None:
        """
        Initialize the serial port.
        :param serial_port: The serial port to use. ( eg. /dev/serial0 for pin number 10 / GPIO15 )
        :param baudrate: The baudrate to use.
        """
        self.port = serial_port
        self.baudrate = baudrate
        self.serial = None
        self.connect()

    def connect(self) -> None:
        """
        Connect to the serial port.
        """
        self.serial = serial.Serial(self.port, self.baudrate)

    def read(self) -> Union[Tuple, None]:
        """
        Read iBus data from serial port.
        :return: The iBus data.
        """
        data = self.serial.read(32)

        while not self.validate(data):
            data = self.serial.read(1)

            while data != self.IBUS_START:
                data = self.serial.read(1)

            data += self.serial.read(31)

        if self.validate(data):
            return self.unpack(data)
        else:
            return None

    def validate(self, data: list) -> bool:
        """
        Validate the iBus data by checking the checksum, the start and end bytes.
        :param data: The iBus data.
        :return: True if valid, False if not.
        """
        data = self.unpack(data)

        return data[0] == 32 and data[1] == 64 and data[-1] == self.calc_checksum(data[:-1])

    def write(self, data: list) -> None:
        """
        Write iBus data to serial port.
        :param data: The iBus data.
        """
        if len(data) != 14:
            raise ValueError("Data must be 14 bytes long")

        data.insert(0, self.IBUS_START_BYTES[0])
        data.insert(1, self.IBUS_START_BYTES[1])

        data.append(self.calc_checksum(data[2:]))

        self.serial.write(struct.pack(self.IBUS_FORMAT, *data))

    def unpack(self, data: list) -> tuple:
        """
        Unpack the iBus data.
        :param data: The iBus data, a list of the first 30 bytes.
        :return: The unpacked iBus data.
        """
        if len(data) != 32:
            raise ValueError("Data must be 32 bytes long")

        return struct.unpack(self.IBUS_FORMAT, data)

    def calc_checksum(self, data: list) -> int:
        """
        Calculate the checksum of the iBus data.
        :param data: The iBus data
        :return: The checksum.
        """
        return ((sum(bytearray(struct.pack(self.IBUS_FORMAT_CALC_CHECKSUM, *data)))) * -1) - 1

    def close(self) -> None:
        """
        Close the serial port.
        """
        self.serial.close()
