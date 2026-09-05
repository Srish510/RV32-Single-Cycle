import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly
import os

def load_hex(dut, filename):
    """Loads a hex file into the instruction memory."""
    if not os.path.exists(filename):
        dut._log.warning(f"Hex file '{filename}' not found. Skipping memory preload.")
        return
        
    dut._log.info(f"Preloading instruction memory with '{filename}'")
    with open(filename, 'r') as f:
        idx = 0
        for line in f:
            line = line.strip()
            # Ignore comments and empty lines
            if line and not line.startswith(("//", "#")):
                # Support standard Verilog memory hex format (@address)
                if line.startswith('@'):
                    # Addresses in Verilog hex files are usually word addresses or byte addresses.
                    # Assuming byte addresses for RISC-V, we convert to word index.
                    addr = int(line[1:], 16)
                    idx = addr // 4
                else:
                    for word in line.split():
                        try:
                            dut.imem_inst.memory[idx].value = int(word, 16)
                            idx += 1
                        except ValueError:
                            pass # Skip non-hex words just in case

@cocotb.test()
async def test_full_core(dut):
    """Full-Core Simulation running compiled machine code."""
    # 1. Generate the free-running system clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # 2. Preload instr_mem with compiled machine code (if provided via environment variable)
    #    You can pass this during invocation: PROG_HEX="my_program.hex" make
    hex_file = os.getenv("PROG_HEX", "")
    if hex_file:
        load_hex(dut, hex_file)
    else:
        dut._log.info("No PROG_HEX environment variable set. Running with default empty memory.")
    
    # 3. Assert reset for 5 clock cycles, then deassert it
    dut.rst.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    
    # 4. Monitor execution to detect program completion
    # We will detect completion in two ways:
    # A) A memory write to a specific 'tohost' address
    # B) A tight infinite loop (PC doesn't change)
    
    # Typical address used by RISC-V tests for communication
    TOHOST_ADDR = 0x80001000 
    MAX_CYCLES = 100000
    cycles = 0
    
    while cycles < MAX_CYCLES:
        await RisingEdge(dut.clk)
        
        # Read signals after the clock edge has propagated
        await ReadOnly()
        
        try:
            pc = int(dut.core_inst.pc_out.value)
            pc_next = int(dut.core_inst.next_pc.value)
        except ValueError:
            pc = 0
            pc_next = 4
        
        try:
            mem_we = int(dut.core_inst.data_we.value)
            mem_addr = int(dut.core_inst.data_addr.value)
        except ValueError:
            # If signals are uninitialized (e.g. instruction memory is empty), they contain 'X'
            mem_we = 0
            mem_addr = 0

        
        if mem_we != 0 and mem_addr == TOHOST_ADDR:
            status = int(dut.core_inst.data_wdata.value)
            dut._log.info(f"Program completed via tohost write to 0x{mem_addr:08X} with status: {status}")
            
            # Usually, writing 1 to tohost indicates success, and >1 indicates failure code
            if status == 1:
                dut._log.info("Test Passed! (tohost == 1)")
            else:
                assert False, f"Test Failed! tohost status = {status} (Expected 1)"
            return
            
        # Check for infinite loop (spin lock)
        # Since exceptions are not implemented, a spin loop (JMP 0, or BEQ x0, x0, 0) 
        # means the program has intentionally halted.
        if pc == pc_next:
            dut._log.info(f"Program completed via infinite loop at PC = 0x{pc:08X}")
            
            # In many riscv-tests, register x3 (gp) holds the test status at the end
            try:
                gp_status = int(dut.core_inst.reg_file_inst.registers[3].value)
            except ValueError:
                gp_status = 0
            if gp_status == 1:
                dut._log.info("Test Passed! gp (x3) == 1")
            elif gp_status > 1:
                assert False, f"Test Failed! gp (x3) == {gp_status} (Expected 1)"
            else:
                dut._log.info(f"Test ended via infinite loop. gp (x3) = {gp_status}")
            return
            
        cycles += 1
        
    assert False, f"Timeout! Program did not complete within {MAX_CYCLES} cycles."
