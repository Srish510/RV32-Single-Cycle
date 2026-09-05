
import re
from typing import Dict, List, Tuple

from .registers import parse_reg
from .utils import parse_imm, check_range
from .encoding import (
    encode_r_type, encode_i_type, encode_s_type,
    encode_b_type, encode_u_type, encode_j_type,
)
from .opcodes import (
    OP_I_TYPE, OP_LOAD, OP_JALR, OP_LUI, OP_AUIPC,
    FUNCT3, FUNCT7, FUNCT7_SHIFT,
    R_TYPE_INSTRS, I_TYPE_ALU, I_TYPE_SHIFT,
    LOAD_INSTRS, STORE_INSTRS, BRANCH_INSTRS,
)
from .pseudo import try_pseudo


def parse_mem_operand(operand: str) -> Tuple[str, str]:
    """Parse a memory operand like '0(x1)' into (offset_str, register_str)."""
    match = re.match(r'(-?\w+)\((\w+)\)', operand.strip())
    if match:
        return match.group(1), match.group(2)
    raise ValueError(f"Invalid memory operand: '{operand}'")


def assemble_instruction(mnemonic: str, operands: List[str],
                         labels: Dict[str, int], pc: int) -> List[int]:
    """
    Assemble a single instruction into one or more 32-bit machine code words.
    Tries pseudo-instructions first, then falls through to real instructions.
    """
    mn = mnemonic.lower()

    # --- Pseudo-instructions ---
    result = try_pseudo(mn, operands, labels, pc)
    if result is not None:
        return result

    # --- R-type ---
    if mn in R_TYPE_INSTRS:
        rd  = parse_reg(operands[0])
        rs1 = parse_reg(operands[1])
        rs2 = parse_reg(operands[2])
        return [encode_r_type(rd, rs1, rs2, FUNCT3[mn], FUNCT7[mn])]

    # --- I-type ALU ---
    if mn in I_TYPE_ALU:
        rd  = parse_reg(operands[0])
        rs1 = parse_reg(operands[1])
        imm = parse_imm(operands[2], labels)
        check_range(imm, 12, name="I-type immediate")
        return [encode_i_type(rd, rs1, imm, FUNCT3[mn], OP_I_TYPE)]

    # --- I-type shifts ---
    if mn in I_TYPE_SHIFT:
        rd  = parse_reg(operands[0])
        rs1 = parse_reg(operands[1])
        shamt = parse_imm(operands[2], labels)
        check_range(shamt, 5, signed=False, name="Shift amount")
        imm = (FUNCT7_SHIFT[mn] << 5) | shamt
        return [encode_i_type(rd, rs1, imm, FUNCT3[mn], OP_I_TYPE)]

    # --- Load ---
    if mn in LOAD_INSTRS:
        rd = parse_reg(operands[0])
        offset_str, base_str = parse_mem_operand(operands[1])
        rs1 = parse_reg(base_str)
        imm = parse_imm(offset_str, labels)
        check_range(imm, 12, name="Load offset")
        return [encode_i_type(rd, rs1, imm, FUNCT3[mn], OP_LOAD)]

    # --- Store ---
    if mn in STORE_INSTRS:
        rs2 = parse_reg(operands[0])
        offset_str, base_str = parse_mem_operand(operands[1])
        rs1 = parse_reg(base_str)
        imm = parse_imm(offset_str, labels)
        check_range(imm, 12, name="Store offset")
        return [encode_s_type(rs1, rs2, imm, FUNCT3[mn])]

    # --- Branch ---
    if mn in BRANCH_INSTRS:
        rs1 = parse_reg(operands[0])
        rs2 = parse_reg(operands[1])
        offset = parse_imm(operands[2], labels, pc, relative=True)
        check_range(offset, 13, name="Branch offset")
        return [encode_b_type(rs1, rs2, offset, FUNCT3[mn])]

    # --- JAL ---
    if mn == 'jal':
        if len(operands) == 1:
            rd = 1  # implicit ra
            offset = parse_imm(operands[0], labels, pc, relative=True)
        else:
            rd = parse_reg(operands[0])
            offset = parse_imm(operands[1], labels, pc, relative=True)
        check_range(offset, 21, name="JAL offset")
        return [encode_j_type(rd, offset)]

    # --- JALR ---
    if mn == 'jalr':
        if len(operands) == 1:
            rs1 = parse_reg(operands[0])
            return [encode_i_type(1, rs1, 0, FUNCT3['jalr'], OP_JALR)]
        elif len(operands) == 2:
            rd = parse_reg(operands[0])
            try:
                offset_str, base_str = parse_mem_operand(operands[1])
                rs1 = parse_reg(base_str)
                imm = parse_imm(offset_str, labels)
            except ValueError:
                rs1 = parse_reg(operands[1])
                imm = 0
            check_range(imm, 12, name="JALR offset")
            return [encode_i_type(rd, rs1, imm, FUNCT3['jalr'], OP_JALR)]
        else:
            rd  = parse_reg(operands[0])
            rs1 = parse_reg(operands[1])
            imm = parse_imm(operands[2], labels)
            check_range(imm, 12, name="JALR offset")
            return [encode_i_type(rd, rs1, imm, FUNCT3['jalr'], OP_JALR)]

    # --- LUI ---
    if mn == 'lui':
        rd  = parse_reg(operands[0])
        imm = parse_imm(operands[1], labels)
        check_range(imm, 20, signed=False, name="LUI immediate")
        return [encode_u_type(rd, imm, OP_LUI)]

    # --- AUIPC ---
    if mn == 'auipc':
        rd  = parse_reg(operands[0])
        imm = parse_imm(operands[1], labels)
        check_range(imm, 20, signed=False, name="AUIPC immediate")
        return [encode_u_type(rd, imm, OP_AUIPC)]

    raise ValueError(f"Unknown instruction: '{mnemonic}'")
