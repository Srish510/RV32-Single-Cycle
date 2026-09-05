import cocotb
from cocotb.triggers import Timer
import random

# Opcodes (lower 7 bits of instruction)
OPCODE_LOAD   = 0b0000011
OPCODE_OP_IMM = 0b0010011
OPCODE_STORE  = 0b0100011
OPCODE_BRANCH = 0b1100011
OPCODE_LUI    = 0b0110111
OPCODE_AUIPC  = 0b0010111
OPCODE_JAL    = 0b1101111
OPCODE_JALR   = 0b1100111

def to_unsigned(val, bits=32):
    return val & ((1 << bits) - 1)

def sign_extend(val, bits):
    """Sign extend a 'bits'-bit number to 32 bits"""
    if val & (1 << (bits - 1)):
        return val | (~((1 << bits) - 1) & 0xFFFFFFFF)
    return val

NUM_TESTS = 1000

@cocotb.test()
async def test_imm_i_type(dut):
    """Exhaustive test for I-type immediate generation"""
    for _ in range(NUM_TESTS):
        imm = random.randint(0, 0xFFF)
        expected = sign_extend(imm, 12)
        instr = (imm << 20) | OPCODE_OP_IMM
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        assert int(dut.imm_out.value) == expected

@cocotb.test()
async def test_imm_s_type(dut):
    """Exhaustive test for S-type immediate generation"""
    for _ in range(NUM_TESTS):
        imm = random.randint(0, 0xFFF)
        expected = sign_extend(imm, 12)
        imm_11_5 = (imm >> 5) & 0x7F
        imm_4_0 = imm & 0x1F
        instr = (imm_11_5 << 25) | (imm_4_0 << 7) | OPCODE_STORE
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        assert int(dut.imm_out.value) == expected

@cocotb.test()
async def test_imm_b_type(dut):
    """Exhaustive test for B-type immediate generation"""
    for _ in range(NUM_TESTS):
        # 13-bit immediate, LSB is implicitly 0
        imm = random.randint(0, 0xFFF) << 1 
        expected = sign_extend(imm, 13)
        imm_12 = (imm >> 12) & 1
        imm_11 = (imm >> 11) & 1
        imm_10_5 = (imm >> 5) & 0x3F
        imm_4_1 = (imm >> 1) & 0xF
        instr = (imm_12 << 31) | (imm_10_5 << 25) | (imm_4_1 << 8) | (imm_11 << 7) | OPCODE_BRANCH
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        assert int(dut.imm_out.value) == expected

@cocotb.test()
async def test_imm_u_type(dut):
    """Exhaustive test for U-type immediate generation"""
    for _ in range(NUM_TESTS):
        # 20-bit immediate, mapped to upper 20 bits
        imm_20 = random.randint(0, 0xFFFFF)
        expected = imm_20 << 12
        instr = (imm_20 << 12) | OPCODE_LUI
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        assert int(dut.imm_out.value) == expected

@cocotb.test()
async def test_imm_j_type(dut):
    """Exhaustive test for J-type immediate generation"""
    for _ in range(NUM_TESTS):
        # 21-bit immediate, LSB is implicitly 0
        imm = random.randint(0, 0xFFFFF) << 1
        expected = sign_extend(imm, 21)
        imm_20 = (imm >> 20) & 1
        imm_19_12 = (imm >> 12) & 0xFF
        imm_11 = (imm >> 11) & 1
        imm_10_1 = (imm >> 1) & 0x3FF
        instr = (imm_20 << 31) | (imm_10_1 << 21) | (imm_11 << 20) | (imm_19_12 << 12) | OPCODE_JAL
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        assert int(dut.imm_out.value) == expected
