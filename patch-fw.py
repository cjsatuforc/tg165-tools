#!/usr/bin/env python3
#
# Quick, hackish scripts to FLIR firmware images with custom functionality
#

import io
import sys
import crc16

PAGE_SIZE = 1024
CRC_SIZE = 2
PAD_SIZE = 2


# Shellcode to load our alternate firmware.:
#   0:	4c02      	ldr	r4, [pc, #8]	; (c <_start+0xc>)
#   2:	4d03      	ldr	r5, [pc, #12]	; (10 <_start+0x10>)
#   4:	6820      	ldr	r0, [r4, #0]
#   6:	6829      	ldr	r1, [r5, #0]
#   8:	4685      	mov	sp, r0
#   a:	468f      	mov	pc, r1
#   c:	00804000 	.word	0x00804000
#  10:	00804004 	.word	0x00804004
SHELLCODE = b"\x4c\x02\x4d\x03\x68\x20\x68\x29\x46\x85\x46\x8f\x00\x00\x04\x08\x04\x00\x04\x08"
SHELLCODE_LOCATION = 0x8C30


def read_file(filename):
    with open(filename, 'rb') as f:
        return f.read()

def write_file(filename, data):
    with open(filename, 'wb') as f:
        return f.write(data)

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
    print("usage: {} <Upgrade.bin> <additional_firmware> <output>".format(sys.argv[0]))


def patch(unpatched):
    unpatched = bytearray(unpatched)
    unpatched[SHELLCODE_LOCATION:SHELLCODE_LOCATION + len(SHELLCODE)] = SHELLCODE
    return bytes(unpatched)


# If our args are wrong, print the usage.
if len(sys.argv) != 4:
    usage()
    sys.exit(0)

# Read in the original firmware and unpack it into a raw binary.
packed_orig = read_file(sys.argv[1])
original = unpack(packed_orig)

# Apply our patch...
patched = patch(original)
assert len(patched) == len(original)

# TODO: add in our additional binary

# Finally, output our patched file.
packed_patched = pack(patched)
write_file(sys.argv[3], packed_patched)
