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


# Shellcode to load our alternate firmware.:
#   0:	4c04      	ldr	r4, [pc, #16]	; (14 <_start+0x14>)
#   2:	4d05      	ldr	r5, [pc, #20]	; (18 <_start+0x18>)
#   4:	602c      	str	r4, [r5, #0]
#   6:	4c03      	ldr	r4, [pc, #12]	; (14 <_start+0x14>)
#   8:	4d04      	ldr	r5, [pc, #16]	; (1c <_start+0x1c>)
#   a:	6820      	ldr	r0, [r4, #0]
#   c:	6829      	ldr	r1, [r5, #0]
#   e:	4685      	mov	sp, r0
#  10:	468f      	mov	pc, r1
#  12:	0000      	.short	0x0000
#  14:	00804000 	.word	0x00804000
#  18:	e000ed14 	.word	0xe000ed14
#  1c:	00804004 	.word	0x00804004

#SHELLCODE_LOCATION = 0x8C30
SHELLCODE_LOCATION = 0x36B4

SELECTOR_LOCATION = 0x40000
ALT_FW_LOCATION   = 0x40800


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


def patch_vector_table_to_launch_fw(unpatched, additional_fw):
    unpatched = bytearray(unpatched)
    additional_fw = bytearray(additional_fw)
    unpatched[0:8] = additional_fw[0:8]
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
extended = extend_with_fw(original, selector, SELECTOR_LOCATION)

# Extend the image with our target firmware.
additional_fw = read_file(sys.argv[3])
extended = extend_with_fw(extended, additional_fw, ALT_FW_LOCATION)

# Patch the file's vector table to launch the additional firmware.
patched = patch_vector_table_to_launch_fw(extended, selector)

# Finally, output our patched file.
packed_patched = pack(patched)
write_file(sys.argv[4], packed_patched)
