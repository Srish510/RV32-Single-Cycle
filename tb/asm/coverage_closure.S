# See LICENSE_RISCV for license details.
#
# Coverage Closure Directed Test for RV32I Core
# Systematically exercises all edge cases, corner cases, register aliasing,
# immediate boundaries, and LSU alignment to achieve 100% functional coverage.

#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV32I")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN
    # -------------------------------------------------------------------------
    # 1. Register Exhaustion: Write and Read all registers x1..x31
    # -------------------------------------------------------------------------
    addi x1,  x0, 1
    addi x2,  x0, 2
    addi x3,  x0, 3
    addi x4,  x0, 4
    addi x5,  x0, 5
    addi x6,  x0, 6
    addi x7,  x0, 7
    addi x8,  x0, 8
    addi x9,  x0, 9
    addi x10, x0, 10
    addi x11, x0, 11
    addi x12, x0, 12
    addi x13, x0, 13
    addi x14, x0, 14
    addi x15, x0, 15
    addi x16, x0, 16
    addi x17, x0, 17
    addi x18, x0, 18
    addi x19, x0, 19
    addi x20, x0, 20
    addi x21, x0, 21
    addi x22, x0, 22
    addi x23, x0, 23
    addi x24, x0, 24
    addi x25, x0, 25
    addi x26, x0, 26
    addi x27, x0, 27
    addi x28, x0, 28
    addi x29, x0, 29
    addi x30, x0, 30
    addi x31, x0, 31

    # -------------------------------------------------------------------------
    # 2. Hardwired Zero Register (x0) Discard Writes
    # -------------------------------------------------------------------------
    addi x0, x0, 1
    add  x0, x1, x2
    sub  x0, x3, x4
    sll  x0, x5, x6
    slt  x0, x7, x8
    sltu x0, x9, x10
    xor  x0, x11, x12
    srl  x0, x13, x14
    sra  x0, x15, x16
    or   x0, x17, x18
    and  x0, x19, x20
    slli x0, x21, 1
    srli x0, x22, 1
    srai x0, x23, 1
    slti x0, x24, 1
    sltiu x0, x25, 1
    xori x0, x26, 1
    ori  x0, x27, 1
    andi x0, x28, 1
    lui  x0, 0x12345
    auipc x0, 0x12345

    # -------------------------------------------------------------------------
    # 3. Register Aliasing Corner Cases
    # -------------------------------------------------------------------------
    # rs1 == rs2
    sub  x1, x2, x2
    xor  x1, x3, x3
    beq  x4, x4, aliasing_next1
    j fail

aliasing_next1:
    # rd == rs1
    addi x5, x5, 1
    # rd == rs2
    add  x6, x0, x6
    # rd == rs1 == rs2
    add  x7, x7, x7

    # -------------------------------------------------------------------------
    # 4. Immediate Value Boundary Extremes
    # -------------------------------------------------------------------------
    addi x1, x0, 0          # ZERO
    addi x1, x0, 2047       # POS_MAX_12BIT (+2047)
    addi x1, x0, -2048      # NEG_MAX_12BIT (-2048)
    addi x1, x0, -1         # MINUS_ONE_12BIT (-1)

    # Shift amounts 0..31
    slli x1, x1, 0
    slli x1, x1, 1
    slli x1, x1, 7
    slli x1, x1, 15
    slli x1, x1, 30
    slli x1, x1, 31
    srli x1, x1, 0
    srli x1, x1, 1
    srli x1, x1, 31
    srai x1, x1, 0
    srai x1, x1, 1
    srai x1, x1, 31

    # Upper immediate extremes
    lui x1, 0x80000         # MSB = 1
    lui x1, 0x7FFFF         # MSB = 0
    auipc x1, 0x80000       # MSB = 1
    auipc x1, 0x00001       # MSB = 0

    # -------------------------------------------------------------------------
    # 5. Branch Dynamics: All 6 types, Taken and Not-Taken, Forward and Backward
    # -------------------------------------------------------------------------
    addi x10, x0, 10
    addi x20, x0, 20
    addi x21, x0, -1

    # BEQ
    beq  x10, x10, beq_fwd_taken
    j fail
beq_fwd_taken:
    beq  x10, x20, fail     # BEQ not taken

    # BNE
    bne  x10, x20, bne_fwd_taken
    j fail
bne_fwd_taken:
    bne  x10, x10, fail     # BNE not taken

    # BLT
    blt  x10, x20, blt_fwd_taken
    j fail
blt_fwd_taken:
    blt  x20, x10, fail     # BLT not taken

    # BGE
    bge  x20, x10, bge_fwd_taken
    j fail
bge_fwd_taken:
    bge  x10, x20, fail     # BGE not taken

    # BLTU & BGEU
    # x21 (-1 as 0xFFFFFFFF) is greater unsigned than x20
    bltu x20, x21, bltu_fwd_taken
    j fail
bltu_fwd_taken:
    bltu x21, x20, fail    # BLTU not taken

    bgeu x21, x20, bgeu_fwd_taken
    j fail
bgeu_fwd_taken:
    bgeu x20, x21, fail    # BGEU not taken

    # Backward Branches (Loop constructs)
    addi x2, x0, 3
back_loop:
    addi x2, x2, -1
    bne  x2, x0, back_loop  # BNE Backward taken
    bne  x2, x0, fail       # BNE Backward not-taken

    # BLTU Backward
    addi x2, x0, 0
    addi x3, x0, 2
bltu_back:
    addi x2, x2, 1
    bltu x2, x3, bltu_back  # BLTU Backward taken

    # BGEU Backward
    addi x2, x0, 2
    addi x3, x0, 1
bgeu_back:
    addi x2, x2, -1
    bgeu x2, x3, bgeu_back  # BGEU Backward taken

    # Branches to Self (offset = 0) with false conditions to test SELF direction without looping
self_beq:  beq  x10, x20, self_beq   # 10 == 20 false, falls through
self_bne:  bne  x10, x10, self_bne   # 10 != 10 false, falls through
self_blt:  blt  x20, x10, self_blt   # 20 < 10 false, falls through
self_bge:  bge  x10, x20, self_bge   # 10 >= 20 false, falls through
self_bltu: bltu x21, x20, self_bltu  # 0xFFFFFFFF < 20 false, falls through
self_bgeu: bgeu x20, x21, self_bgeu  # 20 >= 0xFFFFFFFF false, falls through

    # -------------------------------------------------------------------------
    # 6. Jump Dynamics: JAL and JALR (Forward, Backward, Alignment Masking)
    # -------------------------------------------------------------------------
    jal  x1, jal_target_fwd
    j fail
jal_target_fwd:
    la   x5, jalr_target
    # Verify bit 0 masking: add 1 to target address, JALR must clear bit 0
    ori  x5, x5, 1
    jalr x1, x5, 0
    j fail

jalr_target:

    # -------------------------------------------------------------------------
    # 7. LSU Memory Operations: All 8 ops, Byte Offsets 0, 1, 2, 3 & Sign Extension
    # -------------------------------------------------------------------------
    la   x6, test_data_area

    # Test SW and LW across all byte offsets: 0, 1, 2, 3
    lui  x7, 0x12345
    ori  x7, x7, 0x678
    sw   x7, 0(x6)
    lw   x8, 0(x6)
    sw   x7, 1(x6)
    lw   x8, 1(x6)
    sw   x7, 2(x6)
    lw   x8, 2(x6)
    sw   x7, 3(x6)
    lw   x8, 3(x6)

    # Test SH and LH / LHU at Offsets 0, 1, 2, 3
    # Store 0x8080 (negative signed 16-bit)
    li   x7, 0x8080
    sh   x7, 0(x6)
    lh   x9, 0(x6)          # Must sign-extend to 0xFFFF8080
    lhu  x10, 0(x6)         # Must zero-extend to 0x00008080

    sh   x7, 1(x6)          # Offset 1
    lh   x9, 1(x6)
    lhu  x10, 1(x6)

    sh   x7, 2(x6)          # Offset 2
    lh   x11, 2(x6)
    lhu  x12, 2(x6)

    sh   x7, 3(x6)          # Offset 3
    lh   x11, 3(x6)
    lhu  x12, 3(x6)

    # Test SB and LB / LBU at Offsets 0, 1, 2, 3
    # Store 0xFE (negative byte)
    addi x7, x0, -2         # 0xFE in low byte
    sb   x7, 0(x6)          # Offset 0
    sb   x7, 1(x6)          # Offset 1
    sb   x7, 2(x6)          # Offset 2
    sb   x7, 3(x6)          # Offset 3

    lb   x13, 0(x6)         # Must sign-extend (negative)
    lbu  x14, 0(x6)         # Must zero-extend
    lb   x15, 1(x6)
    lbu  x16, 1(x6)
    lb   x17, 2(x6)
    lbu  x18, 2(x6)
    lb   x19, 3(x6)
    lbu  x20, 3(x6)

    # Discard memory loads into x0
    lw   x0, 0(x6)
    lh   x0, 0(x6)
    lhu  x0, 0(x6)
    lb   x0, 0(x6)
    lbu  x0, 0(x6)

    # -------------------------------------------------------------------------
    # 8. All Checks Succeeded -> Write 1 to tohost
    # -------------------------------------------------------------------------
    RVMODEL_HALT

fail:
    li x1, 2
fail_loop:
    sw x1, tohost, t5
    j fail_loop

RVTEST_CODE_END

# -----------------------------------------------------------------------------
# Data Section
# -----------------------------------------------------------------------------
RVTEST_DATA_BEGIN
RVMODEL_DATA_BEGIN

.align 4
test_data_area:
    .word 0x00000000
    .word 0x00000000
    .word 0x00000000
    .word 0x00000000

RVMODEL_DATA_END
RVTEST_DATA_END
