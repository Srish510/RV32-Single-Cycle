import cocotb
from cocotb.triggers import Timer
import random

# LSU Opcodes matching rv32i_defs.vh
LSU_NONE= 0b0000
LSU_LB  = 0b0001
LSU_LH  = 0b0010
LSU_LW  = 0b0011
LSU_LBU = 0b0100
LSU_LHU = 0b0101
LSU_SB  = 0b1001
LSU_SH  = 0b1010
LSU_SW  = 0b1011

NUM_TESTS = 1000

def to_unsigned(val, bits=32):
    return val & ((1 << bits) - 1)

def sign_extend(val, bits):
    if val & (1 << (bits - 1)):
        return val | (~((1 << bits) - 1) & 0xFFFFFFFF)
    return val

@cocotb.test()
async def test_lsu_store_word(dut):
    """Exhaustive test for Store Word (SW)"""
    dut.lsu_op.value = LSU_SW
    for _ in range(NUM_TESTS):
        addr = random.randint(0, 0xFFFFFFFF) & 0xFFFFFFFC # word aligned
        val = random.randint(0, 0xFFFFFFFF)
        
        dut.addr_in.value = addr
        dut.reg_read_data.value = val
        await Timer(1, unit="ns")
        
        assert int(dut.mem_we.value) == 0b1111
        assert int(dut.mem_write_data.value) == val

@cocotb.test()
async def test_lsu_store_halfword(dut):
    """Exhaustive test for Store Halfword (SH)"""
    dut.lsu_op.value = LSU_SH
    for _ in range(NUM_TESTS):
        addr = random.randint(0, 0xFFFFFFFF) & 0xFFFFFFFE # halfword aligned
        val = random.randint(0, 0xFFFFFFFF)
        
        dut.addr_in.value = addr
        dut.reg_read_data.value = val
        await Timer(1, unit="ns")
        
        offset = addr & 0b10
        if offset == 0:
            assert int(dut.mem_we.value) == 0b0011
        else:
            assert int(dut.mem_we.value) == 0b1100
            
        # The lower 16 bits should be replicated
        hw = val & 0xFFFF
        expected_wdata = (hw << 16) | hw
        assert int(dut.mem_write_data.value) == expected_wdata

@cocotb.test()
async def test_lsu_store_byte(dut):
    """Exhaustive test for Store Byte (SB)"""
    dut.lsu_op.value = LSU_SB
    for _ in range(NUM_TESTS):
        addr = random.randint(0, 0xFFFFFFFF)
        val = random.randint(0, 0xFFFFFFFF)
        
        dut.addr_in.value = addr
        dut.reg_read_data.value = val
        await Timer(1, unit="ns")
        
        offset = addr & 0b11
        assert int(dut.mem_we.value) == (1 << offset)
            
        # The lower 8 bits should be replicated across all 4 bytes
        b = val & 0xFF
        expected_wdata = (b << 24) | (b << 16) | (b << 8) | b
        assert int(dut.mem_write_data.value) == expected_wdata

@cocotb.test()
async def test_lsu_load_word(dut):
    """Exhaustive test for Load Word (LW)"""
    dut.lsu_op.value = LSU_LW
    for _ in range(NUM_TESTS):
        addr = random.randint(0, 0xFFFFFFFF) & 0xFFFFFFFC
        mem_val = random.randint(0, 0xFFFFFFFF)
        
        dut.addr_in.value = addr
        dut.mem_read_data.value = mem_val
        await Timer(1, unit="ns")
        
        assert int(dut.mem_re.value) == 1
        assert int(dut.reg_write_data.value) == mem_val

@cocotb.test()
async def test_lsu_load_halfword(dut):
    """Exhaustive test for Load Halfword (LH, LHU)"""
    for _ in range(NUM_TESTS):
        addr = random.randint(0, 0xFFFFFFFF) & 0xFFFFFFFE
        mem_val = random.randint(0, 0xFFFFFFFF)
        
        dut.addr_in.value = addr
        dut.mem_read_data.value = mem_val
        
        offset = addr & 0b10
        hw = (mem_val >> (offset * 8)) & 0xFFFF
        
        # Signed (LH)
        dut.lsu_op.value = LSU_LH
        await Timer(1, unit="ns")
        assert int(dut.mem_re.value) == 1
        assert int(dut.reg_write_data.value) == sign_extend(hw, 16)
        
        # Unsigned (LHU)
        dut.lsu_op.value = LSU_LHU
        await Timer(1, unit="ns")
        assert int(dut.mem_re.value) == 1
        assert int(dut.reg_write_data.value) == hw

@cocotb.test()
async def test_lsu_load_byte(dut):
    """Exhaustive test for Load Byte (LB, LBU)"""
    for _ in range(NUM_TESTS):
        addr = random.randint(0, 0xFFFFFFFF)
        mem_val = random.randint(0, 0xFFFFFFFF)
        
        dut.addr_in.value = addr
        dut.mem_read_data.value = mem_val
        
        offset = addr & 0b11
        b = (mem_val >> (offset * 8)) & 0xFF
        
        # Signed (LB)
        dut.lsu_op.value = LSU_LB
        await Timer(1, unit="ns")
        assert int(dut.mem_re.value) == 1
        assert int(dut.reg_write_data.value) == sign_extend(b, 8)
        
        # Unsigned (LBU)
        dut.lsu_op.value = LSU_LBU
        await Timer(1, unit="ns")
        assert int(dut.mem_re.value) == 1
        assert int(dut.reg_write_data.value) == b
