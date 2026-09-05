import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock
import random

NUM_TESTS = 1000

@cocotb.test()
async def test_x0_hardwired(dut):
    """Exhaustive test ensuring x0 is completely immutable"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Initialize
    dut.rs1.value = 0
    dut.rs2.value = 0
    dut.rd.value = 0
    dut.write_data.value = 0
    dut.write_enable.value = 0
    await RisingEdge(dut.clk)
    
    for _ in range(NUM_TESTS):
        # Attempt to write random data to x0
        dut.rd.value = 0
        dut.write_data.value = random.randint(0, 0xFFFFFFFF)
        dut.write_enable.value = 1
        await RisingEdge(dut.clk)
        dut.write_enable.value = 0
        
        # Read x0 on both ports
        dut.rs1.value = 0
        dut.rs2.value = 0
        await Timer(1, unit="ns")
        
        assert int(dut.read_data1.value) == 0, f"x0 was corrupted on port 1!"
        assert int(dut.read_data2.value) == 0, f"x0 was corrupted on port 2!"

@cocotb.test()
async def test_read_write_random(dut):
    """Exhaustive test for random register writes and reads"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    dut.rs1.value = 0
    dut.rs2.value = 0
    dut.rd.value = 0
    dut.write_data.value = 0
    dut.write_enable.value = 0
    await RisingEdge(dut.clk)
    
    # Initialize all registers to 0 (since there is no HW reset)
    for i in range(1, 32):
        dut.rd.value = i
        dut.write_data.value = 0
        dut.write_enable.value = 1
        await RisingEdge(dut.clk)
    dut.write_enable.value = 0
    
    # Maintain a Python shadow register file
    shadow_regs = [0] * 32
    
    for _ in range(NUM_TESTS):
        # 1. Random Write
        write_reg = random.randint(1, 31) # don't write 0
        write_val = random.randint(0, 0xFFFFFFFF)
        
        dut.rd.value = write_reg
        dut.write_data.value = write_val
        dut.write_enable.value = 1
        
        await RisingEdge(dut.clk)
        shadow_regs[write_reg] = write_val
        dut.write_enable.value = 0
        
        # 2. Random Read
        read_reg1 = random.randint(0, 31)
        read_reg2 = random.randint(0, 31)
        
        dut.rs1.value = read_reg1
        dut.rs2.value = read_reg2
        
        await Timer(1, unit="ns")
        
        assert int(dut.read_data1.value) == shadow_regs[read_reg1], f"Mismatch on rs1! Expected {shadow_regs[read_reg1]}, got {int(dut.read_data1.value)}"
        assert int(dut.read_data2.value) == shadow_regs[read_reg2], f"Mismatch on rs2! Expected {shadow_regs[read_reg2]}, got {int(dut.read_data2.value)}"

@cocotb.test()
async def test_write_disable(dut):
    """Exhaustive test to ensure write_enable = 0 prevents writes"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    dut.rs1.value = 0
    dut.rs2.value = 0
    dut.rd.value = 0
    dut.write_data.value = 0
    dut.write_enable.value = 0
    await RisingEdge(dut.clk)
    
    for i in range(1, 32):
        dut.rd.value = i
        dut.write_data.value = 0
        dut.write_enable.value = 1
        await RisingEdge(dut.clk)
    dut.write_enable.value = 0
    
    shadow_regs = [0] * 32
    
    for _ in range(NUM_TESTS):
        write_reg = random.randint(1, 31)
        write_val = random.randint(0, 0xFFFFFFFF)
        
        dut.rd.value = write_reg
        dut.write_data.value = write_val
        dut.write_enable.value = 0 # Disabled!
        
        await RisingEdge(dut.clk)
        
        dut.rs1.value = write_reg
        await Timer(1, unit="ns")
        
        # Ensure the value did NOT change
        assert int(dut.read_data1.value) == shadow_regs[write_reg], "Write occurred while write_enable was 0!"
