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
                    addr = int(line[1:], 16)
                    idx = (addr & 0x0003FFFF) // 4
                else:
                    for word in line.split():
                        try:
                            if idx < len(dut.imem_inst.memory):
                                dut.imem_inst.memory[idx].value = int(word, 16)
                            idx += 1
                        except ValueError:
                            pass

def load_elf(dut, filename):
    """Loads an ELF file into both instruction and data memories."""
    from elftools.elf.elffile import ELFFile
    if not os.path.exists(filename):
        dut._log.warning(f"ELF file '{filename}' not found.")
        return {}

    dut._log.info(f"Loading ELF '{filename}' into imem and dmem")
    symbols = {}
    with open(filename, 'rb') as f:
        elf = ELFFile(f)
        
        symtab = elf.get_section_by_name('.symtab')
        if symtab:
            for sym in symtab.iter_symbols():
                symbols[sym.name] = sym['st_value']
                
        imem_len = len(dut.imem_inst.memory)
        dmem_len = len(dut.dmem_inst.memory)
        
        for segment in elf.iter_segments():
            if segment['p_type'] == 'PT_LOAD':
                vaddr = segment['p_vaddr']
                data = segment.data()
                for offset in range(0, len(data), 4):
                    chunk = data[offset:offset+4]
                    if len(chunk) < 4:
                        chunk = chunk.ljust(4, b'\x00')
                    word = int.from_bytes(chunk, byteorder='little')
                    addr = vaddr + offset
                    word_idx = (addr & 0x0003FFFF) // 4
                    if word_idx < imem_len:
                        dut.imem_inst.memory[word_idx].value = word
                    if word_idx < dmem_len:
                        dut.dmem_inst.memory[word_idx].value = word
                        
    return symbols

@cocotb.test()
async def test_full_core(dut):
    """Full-Core Simulation running compiled machine code."""
    # 1. Generate the free-running system clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    symbols = {}
    elf_file = os.getenv("PROG_ELF", "")
    hex_file = os.getenv("PROG_HEX", "")
    
    if elf_file:
        symbols = load_elf(dut, elf_file)
    elif hex_file:
        load_hex(dut, hex_file)
    else:
        dut._log.info("No PROG_ELF or PROG_HEX set. Running with default empty memory.")
    
    # 3. Assert reset for 5 clock cycles, then deassert it
    dut.rst.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    
    # 4. Monitor execution to detect program completion
    tohost_addr = symbols.get("tohost", None)
    tohost_set = {0x80001000, 0x00001000}
    if tohost_addr is not None:
        tohost_set.add(tohost_addr)
        
    MAX_CYCLES = 100000
    cycles = 0
    
    while cycles < MAX_CYCLES:
        await RisingEdge(dut.clk)
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
            mem_we = 0
            mem_addr = 0
        
        if mem_we != 0 and mem_addr in tohost_set:
            status = int(dut.core_inst.data_wdata.value)
            dut._log.info(f"Program completed via tohost write to 0x{mem_addr:08X} with status: {status}")
            
            # Dump signature if requested
            sig_file = os.getenv("SIG_FILE", "")
            if sig_file and "begin_signature" in symbols and "end_signature" in symbols:
                begin_sig = symbols["begin_signature"]
                end_sig = symbols["end_signature"]
                dut._log.info(f"Dumping signature from 0x{begin_sig:08X} to 0x{end_sig:08X} into '{sig_file}'")
                with open(sig_file, "w") as sf:
                    for addr in range(begin_sig, end_sig, 4):
                        word_idx = (addr & 0x0003FFFF) // 4
                        try:
                            val = int(dut.dmem_inst.memory[word_idx].value)
                        except ValueError:
                            val = 0
                        sf.write(f"{val:08x}\n")
                        
            if status == 1:
                dut._log.info("Test Passed! (tohost == 1)")
            else:
                assert False, f"Test Failed! tohost status = {status} (Expected 1)"
            return
            
        # Check for infinite loop (spin lock)
        if pc == pc_next:
            dut._log.info(f"Program completed via infinite loop at PC = 0x{pc:08X}")
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
