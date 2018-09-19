class Packet:
    def __init__(self, *args):
        """
        Initialize a packet
        :param args: if args is nothing, initialize without data
                    if len(args) is 1, initialise this packet with given bytearray
                    if len(args) is more than 1, initialize this packet with data that corresponds to (number of bits, number, scale)
        """
        self.phase = 0
        self.payload = None
        self.length = 0
        self.crc = 0
        self.goodpacket = None

        self.index = 0
        if len(args) == 0:
            self.message = bytearray()
        elif len(args) == 1:
            self.message = args[0]
        else:
            self.message = bytearray()
            for x in range(0, len(args), 3):
                if args[x] == 8:
                    self.append_number_8(args[x + 1], args[x + 2])
                elif args[x] == 16:
                    self.append_number_16(args[x + 1], args[x + 2])
                elif args[x] == 32:
                    self.append_number_32(args[x + 1], args[x + 2])

    def process_buffer(self, buffer):
        """
        This function processes the given buffer (bytearray). When a packet is received, the function calls the process_packet fucntion
        :param buffer: The given bytearray to proces
        :return: None
        """

        """
        This is an integer that indicates the state the message reading is in.
        0: Starting a package read
        1: Reading payload length - long version
        2: Reading payload length - both versions
        3: Reading payload
        4: Reading CRC checksum - first byte
        5: Reading CRC checksum - second byte
        6: Checking checksum
        """

        for x in range(len(buffer)):

            curr_byte = buffer[x]
            if self.phase == 0:
                self.payload = bytearray()
                self.length = 0
                self.crc = 0
                if curr_byte == 2:
                    self.phase += 2
                elif curr_byte == 3:
                    self.phase += 1
            elif self.phase == 1:
                self.length = curr_byte << 8
                self.phase += 1
            elif self.phase == 2:
                self.length |= curr_byte
                self.phase += 1
            elif self.phase == 3:
                self.payload.append(curr_byte)
                if len(self.payload) == self.length:
                    self.phase += 1
            elif self.phase == 4:
                self.crc = curr_byte << 8
                self.phase += 1
            elif self.phase == 5:
                self.crc |= curr_byte
                self.phase += 1
            elif self.phase == 6:
                self.phase = 0
                if curr_byte == 3 and calc_crc(self.payload) == self.crc:
                    self.goodpacket = Packet(self.payload)
                    return True
                else:
                    return False
            else:
                self.phase = 0

    def get_message(self):
        return self.message

    def get_next_number_8(self, scale, proceed):
        if len(self.message) < 1:
            raise Exception("Error unpacking message: message not long enough")
        if proceed:
            self.index += 1
        return self.message[self.index - 1] / scale

    def get_next_number_16(self, scale, proceed):
        if len(self.message) < 2:
            raise Exception("Error unpacking message: message not long enough")
        if proceed:
            self.index += 2
        return (self.message[self.index - 2] << 8 | self.message[self.index - 1]) / scale

    def get_next_number_32(self, scale, proceed):
        if len(self.message) < 4:
            raise Exception("Error unpacking message: message not long enough")
        if proceed:
            self.index += 4
        return (self.message[self.index - 4] << 24 | self.message[self.index - 3] << 16 | self.message[self.index - 2] << 8 | self.message[self.index - 1]) / scale

    def get_next_number(self, bits, scale, proceed=True):
        if bits == 8:
            return self.get_next_number_8(int(scale), proceed)
        elif bits == 16:
            return self.get_next_number_16(int(scale), proceed)
        elif bits == 32:
            return self.get_next_number_32(int(scale), proceed)

    def length_left(self):
        return len(self.message[self.index:])

    def append_number_8(self, number, scale):
        res = int(number * scale)
        self.message.append(res)

    def append_number_16(self, number, scale):
        res = int(number * scale)
        self.message.append((res >> 8) & 0xFF)
        self.message.append(res & 0xFF)

    def append_number_32(self, number, scale):
        res = int(number * scale)
        self.message.append((res >> 24) & 0xFF)
        self.message.append((res >> 16) & 0xFF)
        self.message.append((res >> 8) & 0xFF)
        self.message.append(res & 0xFF)

    def send(self, vesc_usb):
        to_send = bytearray()
        len_tot = len(self.get_message())
        if len_tot <= 256:
            to_send.append(2)
            to_send.append(len_tot)
        else:
            to_send.append(3)
            to_send.append(len_tot >> 8)
            to_send.append(len_tot & 0xFF)
        crc = calc_crc(self.get_message())
        to_send += self.get_message()
        to_send.append(crc >> 8)
        to_send.append(crc & 0xFF)
        to_send.append(3)
        vesc_usb.write(to_send)


crc16_tab = [0x0000, 0x1021, 0x2042, 0x3063, 0x4084,
             0x50a5, 0x60c6, 0x70e7, 0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad,
             0xe1ce, 0xf1ef, 0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7,
             0x62d6, 0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
             0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485, 0xa56a,
             0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d, 0x3653, 0x2672,
             0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4, 0xb75b, 0xa77a, 0x9719,
             0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc, 0x48c4, 0x58e5, 0x6886, 0x78a7,
             0x0840, 0x1861, 0x2802, 0x3823, 0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948,
             0x9969, 0xa90a, 0xb92b, 0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50,
             0x3a33, 0x2a12, 0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b,
             0xab1a, 0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
             0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49, 0x7e97,
             0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70, 0xff9f, 0xefbe,
             0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78, 0x9188, 0x81a9, 0xb1ca,
             0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f, 0x1080, 0x00a1, 0x30c2, 0x20e3,
             0x5004, 0x4025, 0x7046, 0x6067, 0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d,
             0xd31c, 0xe37f, 0xf35e, 0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214,
             0x6277, 0x7256, 0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c,
             0xc50d, 0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
             0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c, 0x26d3,
             0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634, 0xd94c, 0xc96d,
             0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab, 0x5844, 0x4865, 0x7806,
             0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3, 0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e,
             0x8bf9, 0x9bd8, 0xabbb, 0xbb9a, 0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1,
             0x1ad0, 0x2ab3, 0x3a92, 0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b,
             0x9de8, 0x8dc9, 0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0,
             0x0cc1, 0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
             0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0]


def calc_crc(buf):
    cksum = 0
    for byte in buf:
        # Intricate computation: The change in comparison with the cpp file is the fact that C++ automatically cuts of the last bits when the number is too large.
        # With python, no types are declared, so you have to do this manually
        cksum = crc16_tab[(((cksum >> 8) ^ byte) & 0xFF)] ^ (cksum << 8) & (1 << (17 - 1)) - 1
    return cksum
