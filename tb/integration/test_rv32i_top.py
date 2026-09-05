import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Helper function to get register file contents
def get_reg(dut, reg_num):
    return int(dut.core_inst.reg_file_inst.registers[reg_num].value)

# Assembly functions for generating raw machine code instructions
def asm_addi(rd, rs1, imm):
    # ADDI: opcode = 0x13, funct3 = 000
    imm_11_0 = (imm & 0xFFF)
    return (imm_11_0 << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | 0x13

def asm_add(rd, rs1, rs2):
    # ADD: opcode = 0x33, funct3 = 000, funct7 = 0000000
    return (0 << 25) | (rs2 << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | 0x33

def asm_beq(rs1, rs2, offset):
    # BEQ: opcode = 0x63, funct3 = 000
    offset = offset & 0x1FFE
    imm_12 = (offset >> 12) & 1
    imm_11 = (offset >> 11) & 1
    imm_10_5 = (offset >> 5) & 0x3F
    imm_4_1 = (offset >> 1) & 0xF
    return (imm_12 << 31) | (imm_10_5 << 25) | (rs2 << 20) | (rs1 << 15) | (0 << 12) | (imm_4_1 << 8) | (imm_11 << 7) | 0x63

def asm_jal(rd, offset):
    # JAL: opcode = 0x6F
    # Note offset is 21 bits, LSB is always 0
    offset = offset & 0x1FFFFE
    imm_20 = (offset >> 20) & 1
    imm_19_12 = (offset >> 12) & 0xFF
    imm_11 = (offset >> 11) & 1
    imm_10_1 = (offset >> 1) & 0x3FF
    return (imm_20 << 31) | (imm_10_1 << 21) | (imm_11 << 20) | (imm_19_12 << 12) | (rd << 7) | 0x6F

@cocotb.test()
async def test_single_stepping(dut):
    """Integrations check: Single Instruction Stepping (ADDI, ADD)"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # 1. Start in Reset
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    
    # 2. Write instructions directly to simulation instruction memory (word addressed)
    # pc = 0x00: ADDI x1, x0, 5
    # pc = 0x04: ADDI x2, x0, 10
    # pc = 0x08: ADD x3, x1, x2
    dut.imem_inst.memory[0].value = asm_addi(1, 0, 5)
    dut.imem_inst.memory[1].value = asm_addi(2, 0, 10)
    dut.imem_inst.memory[2].value = asm_add(3, 1, 2)
    
    # Run cycle 1: Fetch ADDI x1, x0, 5 -> Executes and writes to x1 on next rising edge
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert get_reg(dut, 1) == 5, f"x1 should be 5, got {get_reg(dut, 1)}"
    
    # Run cycle 2: Fetch ADDI x2, x0, 10 -> Executes and writes to x2 on next rising edge
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert get_reg(dut, 2) == 10, f"x2 should be 10, got {get_reg(dut, 2)}"
    
    # Run cycle 3: Fetch ADD x3, x1, x2 -> Executes and writes to x3 on next rising edge
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert get_reg(dut, 3) == 15, f"x3 should be 15 (5+10), got {get_reg(dut, 3)}"

@cocotb.test()
async def test_control_flow(dut):
    """Integrations check: Control Flow Checks (BEQ, JAL)"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # 1. Start in Reset
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    
    # Memory Layout / Assembly Program:
    # 0: ADDI x1, x0, 5
    # 4: ADDI x2, x0, 5
    # 8: BEQ x1, x2, +8     (Branch to PC=16 if equal)
    # 12: ADDI x3, x0, 99   (Should be skipped!)
    # 16: JAL x4, -16       (Jump back to PC=0, save return address to x4)
    
    dut.imem_inst.memory[0].value = asm_addi(1, 0, 5)
    dut.imem_inst.memory[1].value = asm_addi(2, 0, 5)
    dut.imem_inst.memory[2].value = asm_beq(1, 2, 8)
    dut.imem_inst.memory[3].value = asm_addi(3, 0, 99)
    dut.imem_inst.memory[4].value = asm_jal(4, -16)
    
    # Cycle 1: PC=0, ADDI x1, 5
    await RisingEdge(dut.clk)
    
    # Cycle 2: PC=4, ADDI x2, 5
    await RisingEdge(dut.clk)
    
    # Cycle 3: PC=8, BEQ x1, x2, +8 (Target = 16)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    # Verify PC becomes 16 on next cycle
    assert int(dut.core_inst.pc_out.value) == 16, f"PC should be 16 after BEQ, got {int(dut.core_inst.pc_out.value)}"
    assert get_reg(dut, 3) != 99, f"x3 should NOT be 99 (instruction skipped), but got {get_reg(dut, 3)}"
    
    # Cycle 4: PC=16, JAL x4, -16 (Target = 0)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    
    # JAL at PC=16 should write return address (PC+4 = 20) into x4
    assert get_reg(dut, 4) == 20, f"JAL should write return address (20) into x4, got {get_reg(dut, 4)}"
    # Verify PC wraps back to 0
    assert int(dut.core_inst.pc_out.value) == 0, f"PC should be 0 after JAL, got {int(dut.core_inst.pc_out.value)}"
