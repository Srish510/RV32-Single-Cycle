"""
RV32I Lockstep Co-Simulation Engine
Executes RTL DUT and Golden Reference Model in strict cycle-by-cycle lockstep,
validating Program Counter, Instruction Word, Register Writeback, Memory Access,
and Full 32-Register Architectural State on every retired instruction.
"""

import sys
from typing import List, Optional, Dict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from tb.cosim.rv32i_golden_model import RV32IGoldenModel, CommitPacket, to_signed_32


class CoSimDivergenceError(Exception):
    """Raised when the RTL DUT deviates from the Golden Reference Model."""
    pass


class CoSimEngine:
    """Manages lockstep co-simulation between RTL DUT and Golden Model."""

    def __init__(self, trace_file: Optional[str] = None):
        self.golden = RV32IGoldenModel()
        self.trace_file = trace_file
        self.trace_fp = None
        if self.trace_file:
            self.trace_fp = open(self.trace_file, "w", encoding="utf-8")

        self.instruction_count = 0
        self.branch_count = 0
        self.load_count = 0
        self.store_count = 0
        self.reg_write_count = 0

        self.history: List[Dict] = []
        self.max_history = 10

    def close(self):
        if self.trace_fp:
            self.trace_fp.close()
            self.trace_fp = None

    def preload_elf(self, elf_path: str) -> Dict[str, int]:
        """Preloads an ELF binary into the golden memory space and returns symbols."""
        from elftools.elf.elffile import ELFFile
        symbols = {}
        with open(elf_path, "rb") as f:
            elf = ELFFile(f)
            symtab = elf.get_section_by_name(".symtab")
            if symtab:
                for sym in symtab.iter_symbols():
                    symbols[sym.name] = sym["st_value"]

            for segment in elf.iter_segments():
                if segment["p_type"] == "PT_LOAD":
                    vaddr = segment["p_vaddr"]
                    data = segment.data()
                    self.golden.load_bytes(vaddr, data)
        return symbols

    def preload_hex(self, hex_path: str):
        """Preloads a Verilog @address hex file into golden memory."""
        with open(hex_path, "r") as f:
            current_addr = 0
            for line in f:
                line = line.strip()
                if not line or line.startswith(("//", "#")):
                    continue
                if line.startswith("@"):
                    current_addr = int(line[1:], 16)
                else:
                    for byte_str in line.split():
                        try:
                            val = int(byte_str, 16)
                            self.golden.write_mem_byte(current_addr, val)
                            current_addr += 1
                        except ValueError:
                            pass

    def verify_step(
        self,
        dut_pc: int,
        dut_next_pc: int,
        dut_instr: int,
        dut_reg_we: bool,
        dut_rd: int,
        dut_wdata: int,
        dut_mem_we: int,
        dut_mem_addr: int,
        dut_mem_wdata: int,
        dut_regs: Optional[List[int]] = None
    ) -> CommitPacket:
        """
        Executes one step on the Golden Model and compares all architectural signals
        against the RTL DUT. Raises CoSimDivergenceError on any discrepancy.
        """
        # Step golden model with current instruction
        golden_pkt = self.golden.step(override_instr=dut_instr)
        self.instruction_count += 1

        # Track statistics
        if golden_pkt.mem_read:
            self.load_count += 1
        if golden_pkt.mem_write:
            self.store_count += 1
        if golden_pkt.reg_write and golden_pkt.rd != 0:
            self.reg_write_count += 1
        if golden_pkt.instruction & 0x7F == 0x63:
            self.branch_count += 1

        # Check for discrepancies
        divergence_reason = None
        expected_str = ""
        actual_str = ""

        # 1. PC check
        if dut_pc != golden_pkt.pc:
            divergence_reason = "Program Counter (PC) Mismatch!"
            expected_str = f"0x{golden_pkt.pc:08x}"
            actual_str = f"0x{dut_pc:08x}"

        # 2. Next PC / Branch Target check
        elif dut_next_pc != golden_pkt.next_pc:
            divergence_reason = "Next PC / Branch Target Mismatch!"
            expected_str = f"0x{golden_pkt.next_pc:08x}"
            actual_str = f"0x{dut_next_pc:08x}"

        # 3. Register writeback check
        elif golden_pkt.reg_write and golden_pkt.rd != 0:
            if not dut_reg_we:
                divergence_reason = f"Register Write Enable Missing for x{golden_pkt.rd}!"
                expected_str = f"reg_we = 1, rd = x{golden_pkt.rd}, wdata = 0x{golden_pkt.wdata:08x}"
                actual_str = f"reg_we = 0, rd = x{dut_rd}"
            elif dut_rd != golden_pkt.rd:
                divergence_reason = "Destination Register (rd) Mismatch!"
                expected_str = f"x{golden_pkt.rd}"
                actual_str = f"x{dut_rd}"
            elif dut_wdata != golden_pkt.wdata:
                diff_mask = dut_wdata ^ golden_pkt.wdata
                divergence_reason = f"Writeback Value Mismatch for Register x{golden_pkt.rd}! (Bit Diff: 0x{diff_mask:08x})"
                expected_str = f"0x{golden_pkt.wdata:08x}"
                actual_str = f"0x{dut_wdata:08x}"

        # If golden model does not write register, DUT must not write non-zero register
        elif (not golden_pkt.reg_write) and dut_reg_we and dut_rd != 0:
            divergence_reason = f"Spurious Register Write to x{dut_rd} by DUT!"
            expected_str = "reg_we = 0"
            actual_str = f"reg_we = 1, rd = x{dut_rd}, wdata = 0x{dut_wdata:08x}"

        # 4. Memory store check
        elif golden_pkt.mem_write:
            active_mask = 0
            if golden_pkt.mem_we_mask & 0x1: active_mask |= 0x000000FF
            if golden_pkt.mem_we_mask & 0x2: active_mask |= 0x0000FF00
            if golden_pkt.mem_we_mask & 0x4: active_mask |= 0x00FF0000
            if golden_pkt.mem_we_mask & 0x8: active_mask |= 0xFF000000

            if dut_mem_we != golden_pkt.mem_we_mask:
                divergence_reason = f"Memory Write Enable Mismatch for Store to 0x{golden_pkt.mem_waddr:08x}!"
                expected_str = f"mem_we = 0x{golden_pkt.mem_we_mask:x}"
                actual_str = f"mem_we = 0x{dut_mem_we:x}"
            elif (dut_mem_addr & ~0x3) != (golden_pkt.mem_waddr & ~0x3):
                divergence_reason = "Memory Store Word Address Mismatch!"
                expected_str = f"0x{golden_pkt.mem_waddr & ~0x3:08x}"
                actual_str = f"0x{dut_mem_addr & ~0x3:08x}"
            elif (dut_mem_wdata & active_mask) != (golden_pkt.mem_wdata & active_mask):
                divergence_reason = "Memory Store Data Mismatch!"
                expected_str = f"0x{golden_pkt.mem_wdata & active_mask:08x}"
                actual_str = f"0x{dut_mem_wdata & active_mask:08x}"

        elif (not golden_pkt.mem_write) and dut_mem_we != 0:
            divergence_reason = f"Spurious Memory Write to 0x{dut_mem_addr:08x} by DUT!"
            expected_str = "mem_we = 0"
            actual_str = f"mem_we = 0x{dut_mem_we:x}, addr = 0x{dut_mem_addr:08x}, data = 0x{dut_mem_wdata:08x}"

        # 5. Full Register File State Check (if provided)
        if not divergence_reason and dut_regs is not None:
            for r in range(1, 32):
                expected_reg = self.golden.regs[r]
                actual_reg = dut_regs[r] & 0xFFFFFFFF
                if actual_reg != expected_reg:
                    diff_mask = actual_reg ^ expected_reg
                    divergence_reason = f"Architectural Register State Drift at x{r}! (Bit Diff: 0x{diff_mask:08x})"
                    expected_str = f"x{r} = 0x{expected_reg:08x}"
                    actual_str = f"x{r} = 0x{actual_reg:08x}"
                    break

        # Log trace entry
        if self.trace_fp:
            self.trace_fp.write(golden_pkt.to_spike_log() + "\n")

        # Record history
        record = {
            "instr_num": self.instruction_count,
            "pc": dut_pc,
            "instruction": dut_instr,
            "mnemonic": golden_pkt.mnemonic,
            "golden_pkt": golden_pkt,
            "dut_regs": list(dut_regs) if dut_regs is not None else list(self.golden.regs)
        }
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Handle Divergence Error
        if divergence_reason:
            banner = self._format_divergence_report(
                divergence_reason,
                expected_str,
                actual_str,
                dut_pc,
                dut_instr,
                golden_pkt.mnemonic,
                dut_regs if dut_regs is not None else list(self.golden.regs)
            )
            raise CoSimDivergenceError(banner)

        return golden_pkt

    def verify_registers(self, dut_regs: List[int]):
        """Verifies full 32-register architectural state after sequential commit."""
        for r in range(1, 32):
            expected_reg = self.golden.regs[r]
            actual_reg = dut_regs[r] & 0xFFFFFFFF
            if actual_reg != expected_reg:
                diff_mask = actual_reg ^ expected_reg
                reason = f"Architectural Register State Drift at x{r}! (Bit Diff: 0x{diff_mask:08x})"
                expected_str = f"x{r} = 0x{expected_reg:08x}"
                actual_str = f"x{r} = 0x{actual_reg:08x}"
                last = self.history[-1] if self.history else {
                    "pc": 0, "instruction": 0, "mnemonic": "N/A"
                }
                banner = self._format_divergence_report(
                    reason,
                    expected_str,
                    actual_str,
                    last["pc"],
                    last["instruction"],
                    last["mnemonic"],
                    dut_regs
                )
                raise CoSimDivergenceError(banner)

    def _format_divergence_report(
        self,
        reason: str,
        expected: str,
        actual: str,
        pc: int,
        instr: int,
        mnemonic: str,
        dut_regs: List[int]
    ) -> str:
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("     [!] CO-SIMULATION DIVERGENCE DETECTED (DUT vs GOLDEN REFERENCE) [!]")
        lines.append("=" * 80)
        lines.append(f"  Failure At Instruction #{self.instruction_count}")
        lines.append(f"  Program Counter (PC):  0x{pc:08x}")
        lines.append(f"  Raw Machine Code:      0x{instr:08x}")
        lines.append(f"  Disassembled:          {mnemonic}")
        lines.append("-" * 80)
        lines.append(f"  DIVERGENCE ROOT CAUSE: {reason}")
        lines.append(f"    Expected (Golden Model): {expected}")
        lines.append(f"    Actual   (RTL DUT):      {actual}")
        lines.append("-" * 80)

        # Print recent execution history
        lines.append("  RECENT INSTRUCTION HISTORY (Leading up to divergence):")
        for h in self.history[-5:]:
            lines.append(f"    #{h['instr_num']:<5} PC: 0x{h['pc']:08x}  [{h['mnemonic']:<28}]  (0x{h['instruction']:08x})")

        # Register Dump Comparison for non-zero registers
        lines.append("-" * 80)
        lines.append("  REGISTER FILE COMPARISON (Mismatched registers marked with '>>'):")
        lines.append(f"  {'Reg':<6} {'Expected (Golden)':<20} {'Actual (DUT)':<20} {'Match':<8}")
        lines.append("  " + "-" * 56)
        for r in range(32):
            g_val = self.golden.regs[r]
            d_val = dut_regs[r] & 0xFFFFFFFF
            match = (g_val == d_val)
            marker = "  " if match else ">>"
            match_str = "OK" if match else "MISMATCH"
            if g_val != 0 or d_val != 0 or not match:
                lines.append(f"  {marker} x{r:<3} 0x{g_val:08x}           0x{d_val:08x}           {match_str}")

        lines.append("=" * 80 + "\n")
        return "\n".join(lines)

    def get_summary(self) -> Dict:
        return {
            "instructions_verified": self.instruction_count,
            "branches_verified": self.branch_count,
            "loads_verified": self.load_count,
            "stores_verified": self.store_count,
            "reg_writes_verified": self.reg_write_count,
            "divergences": 0
        }
