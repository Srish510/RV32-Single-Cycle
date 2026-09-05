import cocotb
from cocotb.triggers import Timer
import random

# Opcode constants
OPCODE_R_TYPE  = 0x33
OPCODE_OP_IMM  = 0x13
OPCODE_LOAD    = 0x03
OPCODE_STORE   = 0x23
OPCODE_BRANCH  = 0x63
OPCODE_JAL     = 0x6F
OPCODE_JALR    = 0x67
OPCODE_LUI     = 0x37
OPCODE_AUIPC   = 0x17

# Control Signal Constants
PC_SEL_INC    = 0
PC_SEL_BRANCH = 1
PC_SEL_JAL    = 2
PC_SEL_JALR   = 3

WB_SEL_REG     = 0
WB_SEL_MEM     = 1
WB_SEL_UPP_IMM = 2
WB_SEL_PC_NEXT = 3

ALU_SRC_REG = 0
ALU_SRC_IMM = 1

NUM_TESTS = 1000

@cocotb.test()
async def test_decoder_rtype(dut):
    """Exhaustive test for R-Type instructions"""
    for _ in range(NUM_TESTS):
        rs2 = random.randint(0, 31)
        rs1 = random.randint(0, 31)
        rd = random.randint(0, 31)
        funct3 = random.randint(0, 7)
        funct7 = random.randint(0, 127)
        instr = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | OPCODE_R_TYPE
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.alu_src.value) == ALU_SRC_REG
        assert int(dut.reg_write.value) == 1
        assert int(dut.reg_src.value) == WB_SEL_REG
        assert int(dut.next_pc_src.value) == PC_SEL_INC
        assert int(dut.lsu_op.value) == 0

@cocotb.test()
async def test_decoder_itype(dut):
    """Exhaustive test for I-Type ALU instructions"""
    for _ in range(NUM_TESTS):
        imm = random.randint(0, 0xFFF)
        rs1 = random.randint(0, 31)
        rd = random.randint(0, 31)
        funct3 = random.randint(0, 7)
        instr = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | OPCODE_OP_IMM
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.alu_src.value) == ALU_SRC_IMM
        assert int(dut.reg_write.value) == 1
        assert int(dut.reg_src.value) == WB_SEL_REG
        assert int(dut.next_pc_src.value) == PC_SEL_INC
        assert int(dut.lsu_op.value) == 0

@cocotb.test()
async def test_decoder_load(dut):
    """Exhaustive test for I-Type Load instructions"""
    for _ in range(NUM_TESTS):
        imm = random.randint(0, 0xFFF)
        rs1 = random.randint(0, 31)
        rd = random.randint(0, 31)
        # Valid funct3 for loads: 0, 1, 2, 4, 5
        funct3 = random.choice([0, 1, 2, 4, 5])
        instr = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | OPCODE_LOAD
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.alu_src.value) == ALU_SRC_IMM
        assert int(dut.reg_write.value) == 1
        assert int(dut.reg_src.value) == WB_SEL_MEM
        assert int(dut.next_pc_src.value) == PC_SEL_INC
        assert int(dut.lsu_op.value) != 0

@cocotb.test()
async def test_decoder_store(dut):
    """Exhaustive test for S-Type Store instructions"""
    for _ in range(NUM_TESTS):
        imm_11_5 = random.randint(0, 0x7F)
        rs2 = random.randint(0, 31)
        rs1 = random.randint(0, 31)
        # Valid funct3 for stores: 0, 1, 2
        funct3 = random.choice([0, 1, 2])
        imm_4_0 = random.randint(0, 0x1F)
        instr = (imm_11_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_4_0 << 7) | OPCODE_STORE
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.alu_src.value) == ALU_SRC_IMM
        assert int(dut.reg_write.value) == 0
        assert int(dut.next_pc_src.value) == PC_SEL_INC
        assert int(dut.lsu_op.value) != 0

@cocotb.test()
async def test_decoder_branch(dut):
    """Exhaustive test for B-Type Branch instructions"""
    for _ in range(NUM_TESTS):
        imm_12 = random.randint(0, 1)
        imm_10_5 = random.randint(0, 0x3F)
        rs2 = random.randint(0, 31)
        rs1 = random.randint(0, 31)
        funct3 = random.choice([0, 1, 4, 5, 6, 7])
        imm_4_1 = random.randint(0, 0xF)
        imm_11 = random.randint(0, 1)
        instr = (imm_12 << 31) | (imm_10_5 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (imm_4_1 << 8) | (imm_11 << 7) | OPCODE_BRANCH
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.alu_src.value) == ALU_SRC_REG
        assert int(dut.reg_write.value) == 0
        assert int(dut.next_pc_src.value) == PC_SEL_BRANCH
        assert int(dut.branch_op.value) != 0

@cocotb.test()
async def test_decoder_jal(dut):
    """Exhaustive test for J-Type JAL instructions"""
    for _ in range(NUM_TESTS):
        imm = random.randint(0, 0xFFFFF)
        rd = random.randint(0, 31)
        instr = (imm << 12) | (rd << 7) | OPCODE_JAL
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.reg_write.value) == 1
        assert int(dut.reg_src.value) == WB_SEL_PC_NEXT
        assert int(dut.next_pc_src.value) == PC_SEL_JAL

@cocotb.test()
async def test_decoder_jalr(dut):
    """Exhaustive test for I-Type JALR instructions"""
    for _ in range(NUM_TESTS):
        imm = random.randint(0, 0xFFF)
        rs1 = random.randint(0, 31)
        rd = random.randint(0, 31)
        instr = (imm << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | OPCODE_JALR
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.reg_write.value) == 1
        assert int(dut.reg_src.value) == WB_SEL_PC_NEXT
        assert int(dut.next_pc_src.value) == PC_SEL_JALR
        assert int(dut.alu_src.value) == ALU_SRC_IMM

@cocotb.test()
async def test_decoder_lui(dut):
    """Exhaustive test for U-Type LUI instructions"""
    for _ in range(NUM_TESTS):
        imm = random.randint(0, 0xFFFFF)
        rd = random.randint(0, 31)
        instr = (imm << 12) | (rd << 7) | OPCODE_LUI
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.reg_write.value) == 1
        assert int(dut.reg_src.value) == WB_SEL_UPP_IMM

@cocotb.test()
async def test_decoder_auipc(dut):
    """Exhaustive test for U-Type AUIPC instructions"""
    for _ in range(NUM_TESTS):
        imm = random.randint(0, 0xFFFFF)
        rd = random.randint(0, 31)
        instr = (imm << 12) | (rd << 7) | OPCODE_AUIPC
        dut.instruction.value = instr
        await Timer(1, unit="ns")
        
        assert int(dut.reg_write.value) == 1
        assert int(dut.reg_src.value) == WB_SEL_PC_NEXT
        assert int(dut.pc_writeback_src.value) == 1 
