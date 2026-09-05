import cocotb
from cocotb.triggers import Timer
import random

# Control Signals Constants matching rv32i_defs.vh
BRANCH_NONE = 0
BRANCH_BEQ  = 1
BRANCH_BNE  = 2
BRANCH_BLT  = 3
BRANCH_BGE  = 4

def to_unsigned(val, bits=32):
    return val & ((1 << bits) - 1)

EDGE_CASES = [
    0x00000000, 
    0x00000004, 
    0xFFFFFFFC, # near max
    0xFFFFFFFF, # max
    0x7FFFFFFC,
    0x80000000,
]

def get_test_pairs(num_random=1000):
    pairs = []
    # All combinations of corner/edge cases
    for pc in EDGE_CASES:
        for offset in EDGE_CASES:
            pairs.append((pc, offset))
    
    # Random fuzzing cases
    for _ in range(num_random):
        pairs.append((random.randint(0, 0xFFFFFFFF), random.randint(0, 0xFFFFFFFF)))
        
    return pairs

@cocotb.test()
async def test_branch_none(dut):
    """Exhaustive test for BRANCH_NONE (Fallback / Normal execution)"""
    pairs = get_test_pairs()
    dut.branch_op.value = BRANCH_NONE
    for pc, offset in pairs:
        for eq in [0, 1]:
            for lt in [0, 1]:
                dut.pc_prev.value = pc
                dut.offset.value = offset
                dut.eq_flag.value = eq
                dut.lt_flag.value = lt
                await Timer(1, unit="ns")
                assert int(dut.pc_next.value) == to_unsigned(pc + 4)

@cocotb.test()
async def test_branch_beq(dut):
    """Exhaustive test for BRANCH_BEQ (Branch if Equal)"""
    pairs = get_test_pairs()
    dut.branch_op.value = BRANCH_BEQ
    for pc, offset in pairs:
        for eq in [0, 1]:
            for lt in [0, 1]:
                dut.pc_prev.value = pc
                dut.offset.value = offset
                dut.eq_flag.value = eq
                dut.lt_flag.value = lt
                await Timer(1, unit="ns")
                expected = to_unsigned(pc + offset) if eq == 1 else to_unsigned(pc + 4)
                assert int(dut.pc_next.value) == expected

@cocotb.test()
async def test_branch_bne(dut):
    """Exhaustive test for BRANCH_BNE (Branch if Not Equal)"""
    pairs = get_test_pairs()
    dut.branch_op.value = BRANCH_BNE
    for pc, offset in pairs:
        for eq in [0, 1]:
            for lt in [0, 1]:
                dut.pc_prev.value = pc
                dut.offset.value = offset
                dut.eq_flag.value = eq
                dut.lt_flag.value = lt
                await Timer(1, unit="ns")
                expected = to_unsigned(pc + offset) if eq == 0 else to_unsigned(pc + 4)
                assert int(dut.pc_next.value) == expected

@cocotb.test()
async def test_branch_blt(dut):
    """Exhaustive test for BRANCH_BLT (Branch if Less Than)"""
    pairs = get_test_pairs()
    dut.branch_op.value = BRANCH_BLT
    for pc, offset in pairs:
        for eq in [0, 1]:
            for lt in [0, 1]:
                dut.pc_prev.value = pc
                dut.offset.value = offset
                dut.eq_flag.value = eq
                dut.lt_flag.value = lt
                await Timer(1, unit="ns")
                expected = to_unsigned(pc + offset) if lt == 1 else to_unsigned(pc + 4)
                assert int(dut.pc_next.value) == expected

@cocotb.test()
async def test_branch_bge(dut):
    """Exhaustive test for BRANCH_BGE (Branch if Greater or Equal)"""
    pairs = get_test_pairs()
    dut.branch_op.value = BRANCH_BGE
    for pc, offset in pairs:
        for eq in [0, 1]:
            for lt in [0, 1]:
                dut.pc_prev.value = pc
                dut.offset.value = offset
                dut.eq_flag.value = eq
                dut.lt_flag.value = lt
                await Timer(1, unit="ns")
                expected = to_unsigned(pc + offset) if lt == 0 else to_unsigned(pc + 4)
                assert int(dut.pc_next.value) == expected
