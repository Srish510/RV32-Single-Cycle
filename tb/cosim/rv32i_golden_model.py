"""
RV32I Golden Reference Model (Instruction Set Simulator - ISS)
Implements an instruction-accurate, unprivileged RISC-V RV32I architectural model
used for lockstep co-simulation against RTL implementations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict


def to_signed_32(val: int) -> int:
    val = val & 0xFFFFFFFF
    return val if val < 0x80000000 else val - 0x100000000


def to_unsigned_32(val: int) -> int:
    return val & 0xFFFFFFFF


def sign_extend(val: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    return (val & (sign_bit - 1)) - (val & sign_bit)


@dataclass
class CommitPacket:
    cycle: int
    pc: int
    instruction: int
    mnemonic: str
    reg_write: bool = False
    rd: int = 0
    wdata: int = 0
    mem_read: bool = False
    mem_raddr: int = 0
    mem_rdata: int = 0
    mem_write: bool = False
    mem_waddr: int = 0
    mem_wdata: int = 0
    mem_we_mask: int = 0
    next_pc: int = 0
    regs_after: List[int] = field(default_factory=list)

    def to_spike_log(self) -> str:
        """Formats commit packet in standard Spike / Whisper commit log format."""
        if self.reg_write and self.rd != 0:
            return f"core   0: 0x{self.pc:08x} (0x{self.instruction:08x}) x{self.rd:<2} 0x{self.wdata:08x}"
        elif self.mem_write:
            return f"core   0: 0x{self.pc:08x} (0x{self.instruction:08x}) mem 0x{self.mem_waddr:08x} 0x{self.mem_wdata:08x}"
        else:
            return f"core   0: 0x{self.pc:08x} (0x{self.instruction:08x})"


class RV32IGoldenModel:
    """Architectural Golden Reference Model for RV32I Base Integer ISA."""

    MEM_SIZE = 2 * 1024 * 1024  # 2MB matching MEM_ADDR_WIDTH=19
    MEM_MASK = MEM_SIZE - 1

    def __init__(self, mem_size: int = MEM_SIZE):
        self.mem_size = mem_size
        self.mem_mask = mem_size - 1
        self.mem = bytearray(self.mem_size)
        self.regs = [0] * 32
        self.pc = 0
        self.cycle_count = 0
        self.instruction_count = 0
        self.halted = False

    def reset(self, initial_pc: int = 0):
        self.regs = [0] * 32
        self.pc = initial_pc & 0xFFFFFFFF
        self.cycle_count = 0
        self.instruction_count = 0
        self.halted = False

    def load_bytes(self, addr: int, data: bytes):
        for offset, byte in enumerate(data):
            phys_addr = (addr + offset) & self.mem_mask
            self.mem[phys_addr] = byte

    def read_mem_byte(self, addr: int) -> int:
        return self.mem[addr & self.mem_mask]

    def read_mem_word(self, addr: int) -> int:
        p = addr & self.mem_mask
        return (
            self.mem[p]
            | (self.mem[(p + 1) & self.mem_mask] << 8)
            | (self.mem[(p + 2) & self.mem_mask] << 16)
            | (self.mem[(p + 3) & self.mem_mask] << 24)
        )

    def write_mem_byte(self, addr: int, val: int):
        self.mem[addr & self.mem_mask] = val & 0xFF

    def write_mem_halfword(self, addr: int, val: int):
        p = addr & self.mem_mask
        self.mem[p] = val & 0xFF
        self.mem[(p + 1) & self.mem_mask] = (val >> 8) & 0xFF

    def write_mem_word(self, addr: int, val: int):
        p = addr & self.mem_mask
        self.mem[p] = val & 0xFF
        self.mem[(p + 1) & self.mem_mask] = (val >> 8) & 0xFF
        self.mem[(p + 2) & self.mem_mask] = (val >> 16) & 0xFF
        self.mem[(p + 3) & self.mem_mask] = (val >> 24) & 0xFF

    def disassemble(self, instr: int) -> str:
        """Disassembles 32-bit RV32I instruction into human-readable assembly."""
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x07
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F

        imm_i = to_signed_32(sign_extend((instr >> 20) & 0xFFF, 12))
        imm_s = to_signed_32(sign_extend(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12))
        imm_b = to_signed_32(sign_extend(
            (((instr >> 31) & 0x1) << 12)
            | (((instr >> 7) & 0x1) << 11)
            | (((instr >> 25) & 0x3F) << 5)
            | (((instr >> 8) & 0xF) << 1),
            13
        ))
        imm_u = instr & 0xFFFFF000
        imm_j = to_signed_32(sign_extend(
            (((instr >> 31) & 0x1) << 20)
            | (((instr >> 12) & 0xFF) << 12)
            | (((instr >> 20) & 0x1) << 11)
            | (((instr >> 21) & 0x3FF) << 1),
            21
        ))

        if opcode == 0x37:
            return f"lui x{rd}, 0x{imm_u >> 12:x}"
        elif opcode == 0x17:
            return f"auipc x{rd}, 0x{imm_u >> 12:x}"
        elif opcode == 0x6F:
            return f"jal x{rd}, {imm_j}"
        elif opcode == 0x67:
            return f"jalr x{rd}, {imm_i}(x{rs1})"
        elif opcode == 0x63:
            b_names = {0: "beq", 1: "bne", 4: "blt", 5: "bge", 6: "bltu", 7: "bgeu"}
            name = b_names.get(funct3, "b_unknown")
            return f"{name} x{rs1}, x{rs2}, {imm_b}"
        elif opcode == 0x03:
            l_names = {0: "lb", 1: "lh", 2: "lw", 4: "lbu", 5: "lhu"}
            name = l_names.get(funct3, "l_unknown")
            return f"{name} x{rd}, {imm_i}(x{rs1})"
        elif opcode == 0x23:
            s_names = {0: "sb", 1: "sh", 2: "sw"}
            name = s_names.get(funct3, "s_unknown")
            return f"{name} x{rs2}, {imm_s}(x{rs1})"
        elif opcode == 0x13:
            if funct3 == 0:
                if rs1 == 0 and imm_i == 0 and rd == 0:
                    return "nop"
                return f"addi x{rd}, x{rs1}, {imm_i}"
            elif funct3 == 1:
                return f"slli x{rd}, x{rs1}, {imm_i & 0x1F}"
            elif funct3 == 2:
                return f"slti x{rd}, x{rs1}, {imm_i}"
            elif funct3 == 3:
                return f"sltiu x{rd}, x{rs1}, {imm_i & 0xFFFFFFFF}"
            elif funct3 == 4:
                return f"xori x{rd}, x{rs1}, {imm_i}"
            elif funct3 == 5:
                shamt = imm_i & 0x1F
                return f"{'srai' if (funct7 & 0x20) else 'srli'} x{rd}, x{rs1}, {shamt}"
            elif funct3 == 6:
                return f"ori x{rd}, x{rs1}, {imm_i}"
            elif funct3 == 7:
                return f"andi x{rd}, x{rs1}, {imm_i}"
        elif opcode == 0x33:
            r_names = {
                (0, 0x00): "add", (0, 0x20): "sub",
                (1, 0x00): "sll",
                (2, 0x00): "slt",
                (3, 0x00): "sltu",
                (4, 0x00): "xor",
                (5, 0x00): "srl", (5, 0x20): "sra",
                (6, 0x00): "or",
                (7, 0x00): "and"
            }
            name = r_names.get((funct3, funct7), "r_unknown")
            return f"{name} x{rd}, x{rs1}, x{rs2}"
        return f"unknown (0x{instr:08x})"

    def step(self, override_instr: Optional[int] = None) -> CommitPacket:
        """Executes one instruction from current PC and returns the commit packet."""
        current_pc = self.pc
        instr = override_instr if override_instr is not None else self.read_mem_word(current_pc)
        mnemonic = self.disassemble(instr)

        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x07
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F

        imm_i = to_signed_32(sign_extend((instr >> 20) & 0xFFF, 12))
        imm_s = to_signed_32(sign_extend(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12))
        imm_b = to_signed_32(sign_extend(
            (((instr >> 31) & 0x1) << 12)
            | (((instr >> 7) & 0x1) << 11)
            | (((instr >> 25) & 0x3F) << 5)
            | (((instr >> 8) & 0xF) << 1),
            13
        ))
        imm_u = instr & 0xFFFFF000
        imm_j = to_signed_32(sign_extend(
            (((instr >> 31) & 0x1) << 20)
            | (((instr >> 12) & 0xFF) << 12)
            | (((instr >> 20) & 0x1) << 11)
            | (((instr >> 21) & 0x3FF) << 1),
            21
        ))

        reg_write = False
        wdata = 0
        mem_read = False
        mem_raddr = 0
        mem_rdata = 0
        mem_write = False
        mem_waddr = 0
        mem_wdata = 0
        mem_we_mask = 0
        next_pc = (current_pc + 4) & 0xFFFFFFFF

        r1_val = self.regs[rs1]
        r2_val = self.regs[rs2]

        # 1. LUI
        if opcode == 0x37:
            reg_write = True
            wdata = imm_u & 0xFFFFFFFF

        # 2. AUIPC
        elif opcode == 0x17:
            reg_write = True
            wdata = (current_pc + imm_u) & 0xFFFFFFFF

        # 3. JAL
        elif opcode == 0x6F:
            reg_write = True
            wdata = (current_pc + 4) & 0xFFFFFFFF
            next_pc = (current_pc + imm_j) & 0xFFFFFFFF

        # 4. JALR
        elif opcode == 0x67:
            reg_write = True
            wdata = (current_pc + 4) & 0xFFFFFFFF
            target = (r1_val + imm_i) & 0xFFFFFFFF
            next_pc = target & ~1  # Clear bit 0 per RISC-V ISA spec

        # 5. Branch Operations
        elif opcode == 0x63:
            taken = False
            s_r1 = to_signed_32(r1_val)
            s_r2 = to_signed_32(r2_val)
            u_r1 = to_unsigned_32(r1_val)
            u_r2 = to_unsigned_32(r2_val)

            if funct3 == 0:    # BEQ
                taken = (u_r1 == u_r2)
            elif funct3 == 1:  # BNE
                taken = (u_r1 != u_r2)
            elif funct3 == 4:  # BLT
                taken = (s_r1 < s_r2)
            elif funct3 == 5:  # BGE
                taken = (s_r1 >= s_r2)
            elif funct3 == 6:  # BLTU
                taken = (u_r1 < u_r2)
            elif funct3 == 7:  # BGEU
                taken = (u_r1 >= u_r2)

            if taken:
                next_pc = (current_pc + imm_b) & 0xFFFFFFFF

        # 6. Load Operations
        elif opcode == 0x03:
            mem_read = True
            mem_raddr = (r1_val + imm_i) & 0xFFFFFFFF
            reg_write = True

            # Hardware wraps inside memory space
            byte_offset = mem_raddr & 0x3
            hw_offset = mem_raddr & 0x2
            base_word_addr = mem_raddr & ~0x3
            word_val = self.read_mem_word(base_word_addr)

            if funct3 == 0:    # LB (signed byte)
                raw_b = (word_val >> (byte_offset * 8)) & 0xFF
                wdata = to_unsigned_32(sign_extend(raw_b, 8))
            elif funct3 == 1:  # LH (signed halfword)
                raw_h = (word_val >> (hw_offset * 8)) & 0xFFFF
                wdata = to_unsigned_32(sign_extend(raw_h, 16))
            elif funct3 == 2:  # LW (word)
                wdata = word_val
            elif funct3 == 4:  # LBU (unsigned byte)
                wdata = (word_val >> (byte_offset * 8)) & 0xFF
            elif funct3 == 5:  # LHU (unsigned halfword)
                wdata = (word_val >> (hw_offset * 8)) & 0xFFFF

            mem_rdata = wdata

        # 7. Store Operations
        elif opcode == 0x23:
            mem_write = True
            mem_waddr = (r1_val + imm_s) & 0xFFFFFFFF
            byte_offset = mem_waddr & 0x3
            hw_offset = mem_waddr & 0x2

            if funct3 == 0:    # SB
                b = r2_val & 0xFF
                mem_we_mask = 1 << byte_offset
                mem_wdata = b | (b << 8) | (b << 16) | (b << 24)
                self.write_mem_byte(mem_waddr, b)
            elif funct3 == 1:  # SH
                h = r2_val & 0xFFFF
                mem_we_mask = 0x3 << hw_offset
                mem_wdata = h | (h << 16)
                self.write_mem_halfword((mem_waddr & ~3) | hw_offset, h)
            elif funct3 == 2:  # SW
                mem_we_mask = 0xF
                mem_wdata = r2_val & 0xFFFFFFFF
                self.write_mem_word(mem_waddr & ~3, r2_val & 0xFFFFFFFF)

        # 8. Immediate ALU Operations
        elif opcode == 0x13:
            reg_write = True
            s_r1 = to_signed_32(r1_val)
            shamt = imm_i & 0x1F

            if funct3 == 0:    # ADDI
                wdata = (r1_val + imm_i) & 0xFFFFFFFF
            elif funct3 == 1:  # SLLI
                wdata = (r1_val << shamt) & 0xFFFFFFFF
            elif funct3 == 2:  # SLTI
                wdata = 1 if s_r1 < imm_i else 0
            elif funct3 == 3:  # SLTIU
                wdata = 1 if to_unsigned_32(r1_val) < to_unsigned_32(imm_i) else 0
            elif funct3 == 4:  # XORI
                wdata = (r1_val ^ imm_i) & 0xFFFFFFFF
            elif funct3 == 5:  # SRLI / SRAI
                if funct7 & 0x20:
                    wdata = to_unsigned_32(s_r1 >> shamt)
                else:
                    wdata = (to_unsigned_32(r1_val) >> shamt) & 0xFFFFFFFF
            elif funct3 == 6:  # ORI
                wdata = (r1_val | imm_i) & 0xFFFFFFFF
            elif funct3 == 7:  # ANDI
                wdata = (r1_val & imm_i) & 0xFFFFFFFF

        # 9. Register-Register ALU Operations
        elif opcode == 0x33:
            reg_write = True
            s_r1 = to_signed_32(r1_val)
            s_r2 = to_signed_32(r2_val)
            u_r1 = to_unsigned_32(r1_val)
            u_r2 = to_unsigned_32(r2_val)
            shamt = u_r2 & 0x1F

            if funct3 == 0:
                if funct7 & 0x20:  # SUB
                    wdata = (u_r1 - u_r2) & 0xFFFFFFFF
                else:              # ADD
                    wdata = (u_r1 + u_r2) & 0xFFFFFFFF
            elif funct3 == 1:      # SLL
                wdata = (u_r1 << shamt) & 0xFFFFFFFF
            elif funct3 == 2:      # SLT
                wdata = 1 if s_r1 < s_r2 else 0
            elif funct3 == 3:      # SLTU
                wdata = 1 if u_r1 < u_r2 else 0
            elif funct3 == 4:      # XOR
                wdata = (u_r1 ^ u_r2) & 0xFFFFFFFF
            elif funct3 == 5:
                if funct7 & 0x20:  # SRA
                    wdata = to_unsigned_32(s_r1 >> shamt)
                else:              # SRL
                    wdata = (u_r1 >> shamt) & 0xFFFFFFFF
            elif funct3 == 6:      # OR
                wdata = (u_r1 | u_r2) & 0xFFFFFFFF
            elif funct3 == 7:      # AND
                wdata = (u_r1 & u_r2) & 0xFFFFFFFF

        # Commit register write (x0 is hardwired to 0)
        if reg_write and rd != 0:
            self.regs[rd] = wdata & 0xFFFFFFFF
        self.regs[0] = 0

        # Commit PC
        self.pc = next_pc
        self.cycle_count += 1
        self.instruction_count += 1

        packet = CommitPacket(
            cycle=self.cycle_count,
            pc=current_pc,
            instruction=instr,
            mnemonic=mnemonic,
            reg_write=reg_write,
            rd=rd,
            wdata=wdata if rd != 0 else 0,
            mem_read=mem_read,
            mem_raddr=mem_raddr,
            mem_rdata=mem_rdata,
            mem_write=mem_write,
            mem_waddr=mem_waddr,
            mem_wdata=mem_wdata,
            mem_we_mask=mem_we_mask,
            next_pc=next_pc,
            regs_after=list(self.regs)
        )
        return packet
