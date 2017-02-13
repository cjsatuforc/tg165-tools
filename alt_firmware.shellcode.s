.section .text
.global _start

_start:

    .code   16
    # TODO: relocate VTOR, as well
    ldr r4, =0x0804000  # vector table entry for the new SP
    ldr r5, =0x0804004  # vector table entry for the new PC:
    ldr r0, [r4]
    ldr r1, [r5]
    mov sp, r0
    mov pc, r1

    # shellcode
    #   0:	4c02      	ldr	r4, [pc, #8]	; (c <_start+0xc>)
    #   2:	4d03      	ldr	r5, [pc, #12]	; (10 <_start+0x10>)
    #   4:	6820      	ldr	r0, [r4, #0]
    #   6:	6829      	ldr	r1, [r5, #0]
    #   8:	4685      	mov	sp, r0
    #   a:	468f      	mov	pc, r1
    #   c:	00804000 	.word	0x00804000
    #  10:	00804004 	.word	0x00804004
