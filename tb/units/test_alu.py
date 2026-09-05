import cocotb
from cocotb.triggers import Timer
import random

# ALU Opcodes
ALU_ADD  = 0b0000
ALU_SUB  = 0b1000
ALU_SLL  = 0b0001
ALU_SLT  = 0b0010
ALU_SLTU = 0b0011
ALU_XOR  = 0b0100
ALU_SRL  = 0b0101
ALU_OR   = 0b0110
ALU_AND  = 0b0111
ALU_SRA  = 0b1101

def to_signed(val, bits=32):            
    val = val & ((1 << bits) - 1)
    if val & (1 << (bits - 1)):
        return val - (1 << bits)
    return val

def to_unsigned(val, bits=32):
    return val & ((1 << bits) - 1)

EDGE_CASES = [
    0x00000000, 
    0x00000001, 
    0xFFFFFFFF, # -1
    0x7FFFFFFF, # Max positive
    0x80000000, # Max negative
    0x55555555, # Alternating 01
    0xAAAAAAAA, # Alternating 10
]

def get_test_pairs(num_random=1000):
    pairs = []

    ''' Generate edge case pairs'''
    for a in EDGE_CASES:            
        for b in EDGE_CASES:
            pairs.append((a, b))
    
    ''' Generate random pairs'''
    for _ in range(num_random):
        pairs.append((random.randint(0, 0xFFFFFFFF), random.randint(0, 0xFFFFFFFF)))
        
    return pairs

@cocotb.test()
async def test_alu_add(dut):
    """Exhaustive test for ALU ADD"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_ADD
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        await Timer(1, unit="ns")
        assert int(dut.alu_result.value) == to_unsigned(a + b)

@cocotb.test()
async def test_alu_sub(dut):
    """Exhaustive test for ALU SUB and ZERO flag"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_SUB
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        await Timer(1, unit="ns")
        assert int(dut.alu_result.value) == to_unsigned(a - b)
        # Check Zero Flag
        if to_unsigned(a - b) == 0:
            assert int(dut.zero.value) == 1
        else:
            assert int(dut.zero.value) == 0

@cocotb.test()
async def test_alu_and(dut):
    """Exhaustive test for ALU AND"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_AND
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        await Timer(1, unit="ns")
        assert int(dut.alu_result.value) == (a & b)

@cocotb.test()
async def test_alu_or(dut):
    """Exhaustive test for ALU OR"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_OR
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        await Timer(1, unit="ns")
        assert int(dut.alu_result.value) == (a | b)

@cocotb.test()
async def test_alu_xor(dut):
    """Exhaustive test for ALU XOR"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_XOR
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        await Timer(1, unit="ns")
        assert int(dut.alu_result.value) == (a ^ b)

@cocotb.test()
async def test_alu_sll(dut):
    """Exhaustive test for ALU SLL"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_SLL
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        shamt = b & 0x1F
        await Timer(1, unit="ns")
        assert int(dut.alu_result.value) == to_unsigned(a << shamt)

@cocotb.test()
async def test_alu_srl(dut):
    """Exhaustive test for ALU SRL"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_SRL
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        shamt = b & 0x1F
        await Timer(1, unit="ns")
        assert int(dut.alu_result.value) == (a >> shamt)

@cocotb.test()
async def test_alu_sra(dut):
    """Exhaustive test for ALU SRA"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_SRA
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        shamt = b & 0x1F
        await Timer(1, unit="ns")
        expected_sra = to_unsigned(to_signed(a) >> shamt)
        assert int(dut.alu_result.value) == expected_sra

@cocotb.test()
async def test_alu_slt(dut):
    """Exhaustive test for ALU SLT"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_SLT
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        await Timer(1, unit="ns")
        expected_slt = 1 if to_signed(a) < to_signed(b) else 0
        assert int(dut.alu_result.value) == expected_slt

@cocotb.test()
async def test_alu_sltu(dut):
    """Exhaustive test for ALU SLTU"""
    pairs = get_test_pairs()
    dut.alu_op.value = ALU_SLTU
    for a, b in pairs:
        dut.a.value = a
        dut.b.value = b
        await Timer(1, unit="ns")
        expected_sltu = 1 if a < b else 0
        assert int(dut.alu_result.value) == expected_sltu
