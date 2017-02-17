#!/usr/bin/env python3
#
# Quick, hackish scripts to extend FLIR firmware images with custom functionality
#

import io
import sys
import crc16

PAGE_SIZE = 1024
CRC_SIZE = 2
PAD_SIZE = 2

SELECTOR_LOCATION_ABSOLUTE = b"\x01\x00\x05\x08"
SELECTOR_LOCATION_RELATIVE = 0x40000
ALT_FW_LOCATION_RELATIVE   = 0x44000


def read_file(filename):
    with open(filename, 'rb') as f:
        return f.read()

def write_file(filename, data):
    with open(filename, 'wb') as f:
        return f.write(data)


def extend_with_fw(base, new_fw, location):

    # Extend the firmware out, filling any unused space between the
    # base image and the new firmware.
    total_padding = location - len(base)
    padded = base + (b'\xFF' * total_padding)

    return padded + new_fw



def unpack(bytes_in):
    """
        Unpacks a FLIR TG165 image into a raw binary.
    """

    source = io.BytesIO(bytes_in)
    target = io.BytesIO()

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

    return target.getvalue()


def pack(bytes_in):
    """
        Packs a raw binary into a TG165 image.
    """
    source = io.BytesIO(bytes_in)
    target = io.BytesIO()

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

    return target.getvalue()


def usage():
    print("usage: {} <Upgrade.bin> <bootsel_firmware> <additional_firmware> <output>".format(sys.argv[0]))


def patch_vector_table_to_launch_fw(unpatched, new_entry_point):
    unpatched = bytearray(unpatched)
    unpatched[4:8] = new_entry_point
    return bytes(unpatched)


# If our args are wrong, print the usage.
if len(sys.argv) != 5:
    usage()
    sys.exit(0)


SHELLCODE = read_file(sys.argv[2])

# Read in the original firmware and unpack it into a raw binary.
packed_orig = read_file(sys.argv[1])
original = unpack(packed_orig)

# Extend the image with the "boot selector" firmware.
selector = read_file(sys.argv[2])
extended = extend_with_fw(original, selector, SELECTOR_LOCATION_RELATIVE)

# Extend the image with our target firmware.
additional_fw = read_file(sys.argv[3])
extended = extend_with_fw(extended, additional_fw, ALT_FW_LOCATION_RELATIVE)

# Patch the file's vector table to launch the additional firmware.
patched = patch_vector_table_to_launch_fw(extended, SELECTOR_LOCATION_ABSOLUTE)

# Finally, output our patched file.
packed_patched = pack(patched)
write_file(sys.argv[4], packed_patched)
