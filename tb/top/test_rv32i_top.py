import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly
import os
import sys
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

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

    if elf_file and not os.path.exists(elf_file):
        candidate = PROJ_ROOT / elf_file
        if candidate.exists():
            elf_file = str(candidate)

    if hex_file and not os.path.exists(hex_file):
        candidate = PROJ_ROOT / hex_file
        if candidate.exists():
            hex_file = str(candidate)

    if elf_file and os.path.exists(elf_file):
        symbols = load_elf(dut, elf_file)
    elif hex_file and os.path.exists(hex_file):
        load_hex(dut, hex_file)
    else:
        dut._log.info("No PROG_ELF or PROG_HEX set. Running with default empty memory.")

    # Initialize architectural registers to zero to avoid 'x' propagation
    for r in range(32):
        dut.core_inst.reg_file_inst.registers[r].value = 0
    
    # 4. Monitor execution to detect program completion
    tohost_addr = symbols.get("tohost", None)
    tohost_set = {0x80001000, 0x00001000}
    if tohost_addr is not None:
        tohost_set.add(tohost_addr)

    enable_cosim = os.getenv("ENABLE_COSIM", "0") == "1"
    trace_file = os.getenv("COSIM_TRACE", "")
    inject_fault_cycle = int(os.getenv("COSIM_INJECT_FAULT", "-1"))
    cosim_engine = None
    if enable_cosim:
        from tb.cosim.cosim_engine import CoSimEngine
        cosim_engine = CoSimEngine(trace_file=trace_file if trace_file else None)
        if elf_file:
            cosim_engine.preload_elf(elf_file)
        elif hex_file:
            cosim_engine.preload_hex(hex_file)

    enable_coverage = os.getenv("ENABLE_COVERAGE", "0") == "1"
    func_collector = None
    struct_monitor = None
    if enable_coverage:
        from tb.coverage.rv32i_functional_coverage import FunctionalCoverageCollector
        from tb.coverage.structural_coverage import StructuralCoverageMonitor
        func_collector = FunctionalCoverageCollector()
        struct_monitor = StructuralCoverageMonitor()

    # 3. Assert reset for 5 clock cycles, then deassert it
    dut.rst.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    MAX_CYCLES = 100000
    cycles = 0

    def cleanup():
        if enable_coverage:
            cov_yaml = os.getenv("COV_YAML", "")
            if cov_yaml:
                from cocotb_coverage.coverage import coverage_db
                coverage_db.export_to_yaml(cov_yaml)
            cov_struct = os.getenv("COV_STRUCT_JSON", "")
            if cov_struct and struct_monitor:
                struct_monitor.save_json(cov_struct)
        if cosim_engine:
            cosim_engine.close()

    while cycles < MAX_CYCLES:
        try:
            pc = int(dut.core_inst.pc_out.value)
            pc_next = int(dut.core_inst.next_pc.value)
            instruction = int(dut.core_inst.instruction.value)
            reg_write = bool(int(dut.core_inst.reg_write.value))
            rd = (instruction >> 7) & 0x1F
            write_data = int(dut.core_inst.write_data.value)
            mem_we = int(dut.core_inst.data_we.value)
            mem_addr = int(dut.core_inst.data_addr.value)
            mem_wdata = int(dut.core_inst.data_wdata.value)
        except ValueError:
            pc = 0
            pc_next = 4
            instruction = 0x13
            reg_write = False
            rd = 0
            write_data = 0
            mem_we = 0
            mem_addr = 0
            mem_wdata = 0

        # Step golden model and verify combinational outputs
        if cosim_engine:
            if inject_fault_cycle >= 0 and cycles == inject_fault_cycle:
                try:
                    cur_val = int(dut.core_inst.reg_file_inst.registers[3].value)
                    dut.core_inst.reg_file_inst.registers[3].value = cur_val ^ 0xDEADBEEF
                except Exception:
                    pass

            cosim_engine.verify_step(
                dut_pc=pc,
                dut_next_pc=pc_next,
                dut_instr=instruction,
                dut_reg_we=reg_write,
                dut_rd=rd,
                dut_wdata=write_data,
                dut_mem_we=mem_we,
                dut_mem_addr=mem_addr,
                dut_mem_wdata=mem_wdata
            )

        if enable_coverage:
            try:
                imm_val = int(dut.core_inst.imm_data.value)
                mem_rdata_val = int(dut.core_inst.data_rdata.value)
                func_collector.sample(instruction, pc, pc_next, imm_val, mem_addr, mem_rdata_val)
                struct_monitor.sample_cycle(dut)
            except ValueError:
                pass

        await RisingEdge(dut.clk)
        await ReadOnly()

        # Verify register file state committed from this instruction
        if cosim_engine:
            dut_regs = [0] * 32
            for r in range(32):
                try:
                    dut_regs[r] = int(dut.core_inst.reg_file_inst.registers[r].value)
                except ValueError:
                    dut_regs[r] = 0
            cosim_engine.verify_registers(dut_regs)

        if mem_we != 0 and mem_addr in tohost_set:
            status = mem_wdata
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
                        
            cleanup()
            if cosim_engine:
                dut._log.info(f"CO-SIMULATION PASSED: {cosim_engine.instruction_count} instructions verified in lockstep!")
            if status == 1:
                dut._log.info("Test Passed! (tohost == 1)")
            else:
                assert False, f"Test Failed! tohost status = {status} (Expected 1)"
            return
            
        # Check for infinite loop (spin lock)
        if pc == pc_next:
            dut._log.info(f"Program completed via infinite loop at PC = 0x{pc:08X}")
            cleanup()
            if cosim_engine:
                dut._log.info(f"CO-SIMULATION PASSED: {cosim_engine.instruction_count} instructions verified in lockstep!")
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
        
    cleanup()
    assert False, f"Timeout! Program did not complete within {MAX_CYCLES} cycles."
