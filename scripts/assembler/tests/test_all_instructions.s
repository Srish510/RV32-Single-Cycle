# RV32I Assembler Verification Test
# This assembly program exercises all supported RV32I instructions

.text

_start:
    # --- R-Type Instructions ---
    add   x1, x2, x3       # x1 = x2 + x3
    sub   x4, x5, x6       # x4 = x5 - x6
    and   x7, x8, x9       # x7 = x8 & x9
    or    x10, x11, x12    # x10 = x11 | x12
    xor   x13, x14, x15    # x13 = x14 ^ x15
    sll   x16, x17, x18    # x16 = x17 << x18
    srl   x19, x20, x21    # x19 = x20 >> x21 (logical)
    sra   x22, x23, x24    # x22 = x23 >> x24 (arithmetic)
    slt   x25, x26, x27    # x25 = (x26 < x27) ? 1 : 0 (signed)
    sltu  x28, x29, x30    # x28 = (x29 < x30) ? 1 : 0 (unsigned)

    # --- I-Type ALU Instructions ---
    addi  x1, x0, 42       # x1 = 42
    addi  x2, x0, -1       # x2 = -1 (0xFFFFFFFF)
    slti  x3, x1, 100      # x3 = (42 < 100) ? 1 : 0
    sltiu x4, x1, 100      # x4 = unsigned comparison
    xori  x5, x1, 0xFF     # x5 = x1 ^ 0xFF
    ori   x6, x0, 0x0F     # x6 = 0x0F
    andi  x7, x5, 0xFF     # x7 = x5 & 0xFF
    slli  x8, x1, 4        # x8 = x1 << 4
    srli  x9, x8, 4        # x9 = x8 >> 4 (logical)
    srai  x10, x2, 4       # x10 = x2 >> 4 (arithmetic, sign extends)

    # --- Load Instructions ---
    lb    x1, 0(x2)
    lh    x3, 4(x4)
    lw    x5, 8(x6)
    lbu   x7, 12(x8)
    lhu   x9, 16(x10)

    # --- Store Instructions ---
    sb    x1, 0(x2)
    sh    x3, 4(x4)
    sw    x5, 8(x6)

    # --- U-Type Instructions ---
    lui   x1, 0x12345       # x1 = 0x12345000
    auipc x2, 0x00001       # x2 = PC + 0x1000

    # --- Branch Instructions ---
    beq   x1, x2, branch_target
    bne   x3, x4, branch_target
    blt   x5, x6, branch_target
    bge   x7, x8, branch_target
    bltu  x9, x10, branch_target
    bgeu  x11, x12, branch_target

branch_target:
    # --- JAL / JALR Instructions ---
    jal   x1, jump_target
    
jump_target:
    jalr  x1, x2, 0

    # --- Pseudo-instructions ---
    nop                     # addi x0, x0, 0
    mv    x1, x2            # addi x1, x2, 0
    not   x3, x4            # xori x3, x4, -1
    neg   x5, x6            # sub  x5, x0, x6
    seqz  x7, x8            # sltiu x7, x8, 1
    snez  x9, x10           # sltu x9, x0, x10
    j     loop              # jal x0, loop
    jr    x1                # jalr x0, x1, 0
    ret                     # jalr x0, x1, 0

loop:
    beqz  x1, loop          # beq x1, x0, loop
    bnez  x2, loop          # bne x2, x0, loop

    # --- LI Pseudo-instruction ---
    li    x1, 42            # Small immediate: addi x1, x0, 42
    li    x2, 0x12345678    # Large immediate: lui + addi

    # End: infinite loop
end:
    j     end
