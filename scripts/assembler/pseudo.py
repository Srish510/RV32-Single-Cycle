
from typing import Dict, List

from .registers import parse_reg
from .utils import parse_imm, sign_extend, check_range
from .encoding import (
    encode_r_type, encode_i_type, encode_b_type,
    encode_u_type, encode_j_type,
)
from .opcodes import (
    OP_I_TYPE, OP_JALR, OP_LUI, OP_AUIPC,
    FUNCT3, FUNCT7,
)

# Pseudo-instructions that can expand to 2 words (used for address sizing in pass 1)
EXPANDS_TO_TWO = {'li', 'la', 'call', 'tail'}


def try_pseudo(mn: str, operands: List[str], labels: Dict[str, int], pc: int) -> List[int] | None:
    """
    If 'mn' is a pseudo-instruction, return the list of encoded machine words.
    Otherwise return None so the caller falls through to real-instruction handling.
    """

    if mn == 'nop':                     # No operation
        return [encode_i_type(0, 0, 0, FUNCT3['addi'], OP_I_TYPE)]

    if mn == 'li':                      # Load immediate 
        rd = parse_reg(operands[0])
        imm = parse_imm(operands[1], labels)
        if -2048 <= imm <= 2047:
            return [encode_i_type(rd, 0, imm, FUNCT3['addi'], OP_I_TYPE)]
        upper = (imm >> 12) & 0xFFFFF
        lower = imm & 0xFFF
        if lower & 0x800:
            upper = (upper + 1) & 0xFFFFF
        lower = sign_extend(lower, 12)
        return [
            encode_u_type(rd, upper, OP_LUI),
            encode_i_type(rd, rd, lower, FUNCT3['addi'], OP_I_TYPE),
        ]

    if mn == 'la':                  # Load address (PC-relative)    
        rd = parse_reg(operands[0])
        addr = parse_imm(operands[1], labels)
        offset = addr - pc
        upper = (offset >> 12) & 0xFFFFF
        lower = offset & 0xFFF
        if lower & 0x800:
            upper = (upper + 1) & 0xFFFFF
        lower = sign_extend(lower, 12)
        return [
            encode_u_type(rd, upper, OP_AUIPC),
            encode_i_type(rd, rd, lower, FUNCT3['addi'], OP_I_TYPE),
        ]

    if mn == 'mv':                      # Move register
        rd  = parse_reg(operands[0])
        rs1 = parse_reg(operands[1])
        return [encode_i_type(rd, rs1, 0, FUNCT3['addi'], OP_I_TYPE)]

    if mn == 'not':                     # Bitwise NOT
        rd  = parse_reg(operands[0])
        rs1 = parse_reg(operands[1])
        return [encode_i_type(rd, rs1, -1, FUNCT3['xori'], OP_I_TYPE)]

    if mn == 'neg':                     # Negate
        rd  = parse_reg(operands[0])
        rs2 = parse_reg(operands[1])
        return [encode_r_type(rd, 0, rs2, FUNCT3['sub'], FUNCT7['sub'])]

    if mn == 'seqz':                    # Set if equal to zero
        rd  = parse_reg(operands[0])
        rs1 = parse_reg(operands[1])
        return [encode_i_type(rd, rs1, 1, FUNCT3['sltiu'], OP_I_TYPE)]

    if mn == 'snez':                    # Set if not equal to zero
        rd  = parse_reg(operands[0])
        rs2 = parse_reg(operands[1])
        return [encode_r_type(rd, 0, rs2, FUNCT3['sltu'], FUNCT7['sltu'])]

    if mn == 'sltz':                    # Set if less than zero
        rd  = parse_reg(operands[0])
        rs1 = parse_reg(operands[1])
        return [encode_r_type(rd, rs1, 0, FUNCT3['slt'], FUNCT7['slt'])]

    if mn == 'sgtz':                    # Set if greater than zero  
        rd  = parse_reg(operands[0])
        rs2 = parse_reg(operands[1])
        return [encode_r_type(rd, 0, rs2, FUNCT3['slt'], FUNCT7['slt'])]

    if mn == 'j':                       # Unconditional jump (PC-relative)
        offset = parse_imm(operands[0], labels, pc, relative=True)
        check_range(offset, 21, name="J offset")
        return [encode_j_type(0, offset)]

    if mn == 'jr':                      # Jump register (unconditional)
        rs1 = parse_reg(operands[0])
        return [encode_i_type(0, rs1, 0, FUNCT3['jalr'], OP_JALR)]

    if mn == 'ret':                     # Return from subroutine
        return [encode_i_type(0, 1, 0, FUNCT3['jalr'], OP_JALR)]

    if mn == 'call':                    # Call subroutine (PC-relative)
        offset = parse_imm(operands[0], labels, pc, relative=True)
        upper = (offset >> 12) & 0xFFFFF
        lower = offset & 0xFFF
        if lower & 0x800:
            upper = (upper + 1) & 0xFFFFF
        lower = sign_extend(lower, 12)
        return [
            encode_u_type(1, upper, OP_AUIPC),
            encode_i_type(1, 1, lower, FUNCT3['jalr'], OP_JALR),
        ]

    if mn == 'tail':                    # Tail call (jump to subroutine, PC-relative)
        offset = parse_imm(operands[0], labels, pc, relative=True)
        upper = (offset >> 12) & 0xFFFFF
        lower = offset & 0xFFF
        if lower & 0x800:
            upper = (upper + 1) & 0xFFFFF
        lower = sign_extend(lower, 12)
        return [
            encode_u_type(6, upper, OP_AUIPC),
            encode_i_type(0, 6, lower, FUNCT3['jalr'], OP_JALR),
        ]

    # Branch-zero pseudo-instructions
    _BRANCH_ZERO = {
        'beqz': ('beq', lambda rs1: (rs1, 0)),
        'bnez': ('bne', lambda rs1: (rs1, 0)),
        'blez': ('bge', lambda rs1: (0, rs1)),
        'bgez': ('bge', lambda rs1: (rs1, 0)),
        'bltz': ('blt', lambda rs1: (rs1, 0)),
        'bgtz': ('blt', lambda rs1: (0, rs1)),
    }

    if mn in _BRANCH_ZERO:
        base_mn, reg_fn = _BRANCH_ZERO[mn]
        rs1_val = parse_reg(operands[0])
        r1, r2 = reg_fn(rs1_val)
        offset = parse_imm(operands[1], labels, pc, relative=True)
        check_range(offset, 13, name="Branch offset")
        return [encode_b_type(r1, r2, offset, FUNCT3[base_mn])]

    return None  # Not a pseudo-instruction
