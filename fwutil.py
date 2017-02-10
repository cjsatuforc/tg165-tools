#!/usr/bin/env python3
#
# Quick, hackish scripts to pack/unpack TG165 upgrade binaries
#

import sys
import crc16

PAGE_SIZE = 1024
CRC_SIZE = 2
PAD_SIZE = 2

def unpack(from_filename, to_filename):
    """
        Unpacks a FLIR TG165 image into a raw binary.
    """
    source = open(from_filename, mode='rb')
    target = open(to_filename, mode='wb')

    while True:
        chunk = source.read(CRC_SIZE + PAD_SIZE + PAGE_SIZE)

        if not chunk:
            break

        checksum = chunk[0:2]
        padding  = chunk[2:4]
        data     = chunk[4:]

        # Check to make sure our padding are always zeroes.
        if padding != b"\x00\x00":
            issue = repr(padding)
            sys.stderr.write("Data format error! Expected 0x0000, got {}\n".format(issue))

        # Check to make sure the CRCs are valid.
        data_crc = crc16.crc16xmodem(data).to_bytes(2, byteorder='little')
        if checksum != data_crc:
            expected = repr(checksum)
            actual = repr(data_crc)
            sys.stderr.write("CRC mismatch! Expected {}, got {}\n".format(expected, actual))

        target.write(data)

    source.close()
    target.close()


def pack(from_filename, to_filename):
    """
        Packs a raw binary into a TG165 image.
    """
    source = open(from_filename, mode='rb')
    target = open(to_filename, mode='wb')

    while True:
        data = source.read(PAGE_SIZE)

        if not data:
            break

        # Compute the CRC of the chunk.
        data_crc = crc16.crc16xmodem(data).to_bytes(2, byteorder='little')

        # Write the chunk with checksum in the FLIR-expected format.
        target.write(data_crc)
        target.write(b"\x00\x00")
        target.write(data)

    source.close()
    target.close()


def usage():
    print("usage: {} [command] <input> <output>".format(sys.argv[0]))
    print("  command can be:")
    print("   pack - packs a raw binary into an upgrade binary")
    print("   unpack - unpacks an upgrade binary into a raw binary")

# If our args are wrong, print the usage.
if len(sys.argv) != 3:
    usage()

# Handle the relevant command.
if sys.argv[1] == "pack":
    pack(sys.argv[2], sys.argv[3])
elif sys.argv[1] == "unpack":
    unpack(sys.argv[2], sys.argv[3])
else:
    usage()


