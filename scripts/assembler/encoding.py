
from .opcodes import OP_R_TYPE, OP_STORE, OP_BRANCH, OP_JAL
from .utils import to_unsigned

def encode_r_type(rd: int, rs1: int, rs2: int, funct3: int, funct7: int) -> int:
    """Encode an R-type instruction."""
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | OP_R_TYPE

def encode_i_type(rd: int, rs1: int, imm: int, funct3: int, opcode: int) -> int:
    """Encode an I-type instruction."""
    imm = to_unsigned(imm, 12)
    return (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

def encode_s_type(rs1: int, rs2: int, imm: int, funct3: int) -> int:
    """Encode an S-type (store) instruction."""
    imm = to_unsigned(imm, 12)
    imm_11_5 = (imm >> 5) & 0x7F
    imm_4_0 = imm & 0x1F
    return (imm_11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_4_0 << 7) | OP_STORE

def encode_b_type(rs1: int, rs2: int, imm: int, funct3: int) -> int:
    """Encode a B-type (branch) instruction."""
    imm = to_unsigned(imm, 13)
    imm_12   = (imm >> 12) & 0x1
    imm_11   = (imm >> 11) & 0x1
    imm_10_5 = (imm >> 5)  & 0x3F
    imm_4_1  = (imm >> 1)  & 0xF
    return ((imm_12 << 31) | (imm_10_5 << 25) | (rs2 << 20) | (rs1 << 15) |
            (funct3 << 12) | (imm_4_1 << 8) | (imm_11 << 7) | OP_BRANCH)

def encode_u_type(rd: int, imm: int, opcode: int) -> int:
    """Encode a U-type (LUI / AUIPC) instruction."""
    imm = to_unsigned(imm, 20)
    return (imm << 12) | (rd << 7) | opcode

def encode_j_type(rd: int, imm: int) -> int:
    """Encode a J-type (JAL) instruction."""
    imm = to_unsigned(imm, 21)
    imm_20   = (imm >> 20) & 0x1
    imm_19_12 = (imm >> 12) & 0xFF
    imm_11   = (imm >> 11) & 0x1
    imm_10_1 = (imm >> 1)  & 0x3FF
    return ((imm_20 << 31) | (imm_10_1 << 21) | (imm_11 << 20) |
            (imm_19_12 << 12) | (rd << 7) | OP_JAL)
