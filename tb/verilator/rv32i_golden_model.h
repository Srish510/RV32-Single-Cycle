#ifndef RV32I_GOLDEN_MODEL_H
#define RV32I_GOLDEN_MODEL_H

#include <cstdint>
#include <string>
#include <vector>
#include <sstream>
#include <iomanip>
#include <iostream>

struct GoldenCommitPacket {
    uint32_t pc;
    uint32_t instruction;
    std::string mnemonic;
    bool reg_write;
    uint32_t rd;
    uint32_t wdata;
    bool mem_read;
    uint32_t mem_raddr;
    uint32_t mem_rdata;
    bool mem_write;
    uint32_t mem_waddr;
    uint32_t mem_wdata;
    uint32_t mem_we_mask;
    uint32_t next_pc;
};

class RV32IGoldenModel {
public:
    static const uint32_t MEM_SIZE = 2 * 1024 * 1024; // 2MB matching MEM_ADDR_WIDTH=19
    static const uint32_t MEM_MASK = MEM_SIZE - 1;

    std::vector<uint8_t> mem;
    uint32_t regs[32];
    uint32_t pc;
    uint64_t instruction_count;

    RV32IGoldenModel() : mem(MEM_SIZE, 0) {
        reset();
    }

    void reset(uint32_t initial_pc = 0) {
        std::fill(mem.begin(), mem.end(), 0);
        for (int i = 0; i < 32; i++) regs[i] = 0;
        pc = initial_pc;
        instruction_count = 0;
    }

    void write_byte(uint32_t addr, uint8_t byte_val) {
        mem[addr & MEM_MASK] = byte_val;
    }

    uint8_t read_byte(uint32_t addr) const {
        return mem[addr & MEM_MASK];
    }

    uint32_t read_word(uint32_t addr) const {
        uint32_t p = addr & MEM_MASK;
        return static_cast<uint32_t>(mem[p])
             | (static_cast<uint32_t>(mem[(p + 1) & MEM_MASK]) << 8)
             | (static_cast<uint32_t>(mem[(p + 2) & MEM_MASK]) << 16)
             | (static_cast<uint32_t>(mem[(p + 3) & MEM_MASK]) << 24);
    }

    void write_halfword(uint32_t addr, uint16_t val) {
        uint32_t p = addr & MEM_MASK;
        mem[p] = val & 0xFF;
        mem[(p + 1) & MEM_MASK] = (val >> 8) & 0xFF;
    }

    void write_word(uint32_t addr, uint32_t val) {
        uint32_t p = addr & MEM_MASK;
        mem[p] = val & 0xFF;
        mem[(p + 1) & MEM_MASK] = (val >> 8) & 0xFF;
        mem[(p + 2) & MEM_MASK] = (val >> 16) & 0xFF;
        mem[(p + 3) & MEM_MASK] = (val >> 24) & 0xFF;
    }

    static int32_t sign_extend(uint32_t val, int bits) {
        uint32_t sign_bit = 1U << (bits - 1);
        return static_cast<int32_t>((val & (sign_bit - 1)) - (val & sign_bit));
    }

    std::string disassemble(uint32_t instr) const {
        uint32_t opcode = instr & 0x7F;
        uint32_t rd = (instr >> 7) & 0x1F;
        uint32_t funct3 = (instr >> 12) & 0x07;
        uint32_t rs1 = (instr >> 15) & 0x1F;
        uint32_t rs2 = (instr >> 20) & 0x1F;
        uint32_t funct7 = (instr >> 25) & 0x7F;

        std::ostringstream oss;
        if (opcode == 0x37) {
            oss << "lui x" << rd << ", 0x" << std::hex << (instr >> 12);
        } else if (opcode == 0x17) {
            oss << "auipc x" << rd << ", 0x" << std::hex << (instr >> 12);
        } else if (opcode == 0x6F) {
            int32_t imm_j = sign_extend(
                (((instr >> 31) & 0x1) << 20)
                | (((instr >> 12) & 0xFF) << 12)
                | (((instr >> 20) & 0x1) << 11)
                | (((instr >> 21) & 0x3FF) << 1),
                21
            );
            oss << "jal x" << rd << ", " << imm_j;
        } else if (opcode == 0x67) {
            int32_t imm_i = sign_extend((instr >> 20) & 0xFFF, 12);
            oss << "jalr x" << rd << ", " << imm_i << "(x" << rs1 << ")";
        } else if (opcode == 0x63) {
            int32_t imm_b = sign_extend(
                (((instr >> 31) & 0x1) << 12)
                | (((instr >> 7) & 0x1) << 11)
                | (((instr >> 25) & 0x3F) << 5)
                | (((instr >> 8) & 0xF) << 1),
                13
            );
            const char* bnames[] = {"beq", "bne", "?", "?", "blt", "bge", "bltu", "bgeu"};
            oss << bnames[funct3] << " x" << rs1 << ", x" << rs2 << ", " << imm_b;
        } else if (opcode == 0x03) {
            int32_t imm_i = sign_extend((instr >> 20) & 0xFFF, 12);
            const char* lnames[] = {"lb", "lh", "lw", "?", "lbu", "lhu", "?", "?"};
            oss << lnames[funct3] << " x" << rd << ", " << imm_i << "(x" << rs1 << ")";
        } else if (opcode == 0x23) {
            int32_t imm_s = sign_extend(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12);
            const char* snames[] = {"sb", "sh", "sw", "?", "?", "?", "?", "?"};
            oss << snames[funct3] << " x" << rs2 << ", " << imm_s << "(x" << rs1 << ")";
        } else if (opcode == 0x13) {
            int32_t imm_i = sign_extend((instr >> 20) & 0xFFF, 12);
            if (funct3 == 0) {
                if (rs1 == 0 && imm_i == 0 && rd == 0) oss << "nop";
                else oss << "addi x" << rd << ", x" << rs1 << ", " << imm_i;
            } else if (funct3 == 1) {
                oss << "slli x" << rd << ", x" << rs1 << ", " << (imm_i & 0x1F);
            } else if (funct3 == 2) {
                oss << "slti x" << rd << ", x" << rs1 << ", " << imm_i;
            } else if (funct3 == 3) {
                oss << "sltiu x" << rd << ", x" << rs1 << ", " << static_cast<uint32_t>(imm_i);
            } else if (funct3 == 4) {
                oss << "xori x" << rd << ", x" << rs1 << ", " << imm_i;
            } else if (funct3 == 5) {
                oss << ((funct7 & 0x20) ? "srai" : "srli") << " x" << rd << ", x" << rs1 << ", " << (imm_i & 0x1F);
            } else if (funct3 == 6) {
                oss << "ori x" << rd << ", x" << rs1 << ", " << imm_i;
            } else if (funct3 == 7) {
                oss << "andi x" << rd << ", x" << rs1 << ", " << imm_i;
            }
        } else if (opcode == 0x33) {
            if (funct3 == 0) oss << ((funct7 & 0x20) ? "sub" : "add");
            else if (funct3 == 1) oss << "sll";
            else if (funct3 == 2) oss << "slt";
            else if (funct3 == 3) oss << "sltu";
            else if (funct3 == 4) oss << "xor";
            else if (funct3 == 5) oss << ((funct7 & 0x20) ? "sra" : "srl");
            else if (funct3 == 6) oss << "or";
            else if (funct3 == 7) oss << "and";
            oss << " x" << rd << ", x" << rs1 << ", x" << rs2;
        } else {
            oss << "unknown (0x" << std::hex << instr << ")";
        }
        return oss.str();
    }

    GoldenCommitPacket step(uint32_t override_instr = 0xFFFFFFFF) {
        uint32_t current_pc = pc;
        uint32_t instr = (override_instr != 0xFFFFFFFF) ? override_instr : read_word(current_pc);

        uint32_t opcode = instr & 0x7F;
        uint32_t rd = (instr >> 7) & 0x1F;
        uint32_t funct3 = (instr >> 12) & 0x07;
        uint32_t rs1 = (instr >> 15) & 0x1F;
        uint32_t rs2 = (instr >> 20) & 0x1F;
        uint32_t funct7 = (instr >> 25) & 0x7F;

        int32_t imm_i = sign_extend((instr >> 20) & 0xFFF, 12);
        int32_t imm_s = sign_extend(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12);
        int32_t imm_b = sign_extend(
            (((instr >> 31) & 0x1) << 12)
            | (((instr >> 7) & 0x1) << 11)
            | (((instr >> 25) & 0x3F) << 5)
            | (((instr >> 8) & 0xF) << 1),
            13
        );
        uint32_t imm_u = instr & 0xFFFFF000;
        int32_t imm_j = sign_extend(
            (((instr >> 31) & 0x1) << 20)
            | (((instr >> 12) & 0xFF) << 12)
            | (((instr >> 20) & 0x1) << 11)
            | (((instr >> 21) & 0x3FF) << 1),
            21
        );

        bool reg_write = false;
        uint32_t wdata = 0;
        bool mem_read = false;
        uint32_t mem_raddr = 0;
        uint32_t mem_rdata = 0;
        bool mem_write = false;
        uint32_t mem_waddr = 0;
        uint32_t mem_wdata = 0;
        uint32_t mem_we_mask = 0;
        uint32_t next_pc = current_pc + 4;

        uint32_t r1_val = regs[rs1];
        uint32_t r2_val = regs[rs2];

        if (opcode == 0x37) { // LUI
            reg_write = true;
            wdata = imm_u;
        } else if (opcode == 0x17) { // AUIPC
            reg_write = true;
            wdata = current_pc + imm_u;
        } else if (opcode == 0x6F) { // JAL
            reg_write = true;
            wdata = current_pc + 4;
            next_pc = current_pc + static_cast<uint32_t>(imm_j);
        } else if (opcode == 0x67) { // JALR
            reg_write = true;
            wdata = current_pc + 4;
            next_pc = (r1_val + static_cast<uint32_t>(imm_i)) & ~1U;
        } else if (opcode == 0x63) { // Branch
            bool taken = false;
            int32_t s_r1 = static_cast<int32_t>(r1_val);
            int32_t s_r2 = static_cast<int32_t>(r2_val);

            if (funct3 == 0) taken = (r1_val == r2_val);
            else if (funct3 == 1) taken = (r1_val != r2_val);
            else if (funct3 == 4) taken = (s_r1 < s_r2);
            else if (funct3 == 5) taken = (s_r1 >= s_r2);
            else if (funct3 == 6) taken = (r1_val < r2_val);
            else if (funct3 == 7) taken = (r1_val >= r2_val);

            if (taken) next_pc = current_pc + static_cast<uint32_t>(imm_b);
        } else if (opcode == 0x03) { // Load
            mem_read = true;
            mem_raddr = r1_val + static_cast<uint32_t>(imm_i);
            reg_write = true;

            uint32_t byte_offset = mem_raddr & 0x3;
            uint32_t hw_offset = mem_raddr & 0x2;
            uint32_t base_word = mem_raddr & ~0x3U;
            uint32_t word_val = read_word(base_word);

            if (funct3 == 0) { // LB
                uint8_t raw_b = (word_val >> (byte_offset * 8)) & 0xFF;
                wdata = static_cast<uint32_t>(sign_extend(raw_b, 8));
            } else if (funct3 == 1) { // LH
                uint16_t raw_h = (word_val >> (hw_offset * 8)) & 0xFFFF;
                wdata = static_cast<uint32_t>(sign_extend(raw_h, 16));
            } else if (funct3 == 2) { // LW
                wdata = word_val;
            } else if (funct3 == 4) { // LBU
                wdata = (word_val >> (byte_offset * 8)) & 0xFF;
            } else if (funct3 == 5) { // LHU
                wdata = (word_val >> (hw_offset * 8)) & 0xFFFF;
            }
            mem_rdata = wdata;
        } else if (opcode == 0x23) { // Store
            mem_write = true;
            mem_waddr = r1_val + static_cast<uint32_t>(imm_s);
            uint32_t byte_offset = mem_waddr & 0x3;
            uint32_t hw_offset = mem_waddr & 0x2;

            if (funct3 == 0) { // SB
                uint32_t b = r2_val & 0xFF;
                mem_we_mask = 1U << byte_offset;
                mem_wdata = b | (b << 8) | (b << 16) | (b << 24);
                write_byte(mem_waddr, static_cast<uint8_t>(b));
            } else if (funct3 == 1) { // SH
                uint32_t h = r2_val & 0xFFFF;
                mem_we_mask = 0x3U << hw_offset;
                mem_wdata = h | (h << 16);
                write_halfword((mem_waddr & ~3U) | hw_offset, static_cast<uint16_t>(h));
            } else if (funct3 == 2) { // SW
                mem_we_mask = 0xF;
                mem_wdata = r2_val;
                write_word(mem_waddr & ~3U, r2_val);
            }
        } else if (opcode == 0x13) { // Immediate ALU
            reg_write = true;
            int32_t s_r1 = static_cast<int32_t>(r1_val);
            uint32_t shamt = imm_i & 0x1F;

            if (funct3 == 0) wdata = r1_val + static_cast<uint32_t>(imm_i);
            else if (funct3 == 1) wdata = r1_val << shamt;
            else if (funct3 == 2) wdata = (s_r1 < imm_i) ? 1 : 0;
            else if (funct3 == 3) wdata = (r1_val < static_cast<uint32_t>(imm_i)) ? 1 : 0;
            else if (funct3 == 4) wdata = r1_val ^ static_cast<uint32_t>(imm_i);
            else if (funct3 == 5) {
                if (funct7 & 0x20) wdata = static_cast<uint32_t>(s_r1 >> shamt);
                else wdata = r1_val >> shamt;
            } else if (funct3 == 6) wdata = r1_val | static_cast<uint32_t>(imm_i);
            else if (funct3 == 7) wdata = r1_val & static_cast<uint32_t>(imm_i);
        } else if (opcode == 0x33) { // Register ALU
            reg_write = true;
            int32_t s_r1 = static_cast<int32_t>(r1_val);
            int32_t s_r2 = static_cast<int32_t>(r2_val);
            uint32_t shamt = r2_val & 0x1F;

            if (funct3 == 0) wdata = (funct7 & 0x20) ? (r1_val - r2_val) : (r1_val + r2_val);
            else if (funct3 == 1) wdata = r1_val << shamt;
            else if (funct3 == 2) wdata = (s_r1 < s_r2) ? 1 : 0;
            else if (funct3 == 3) wdata = (r1_val < r2_val) ? 1 : 0;
            else if (funct3 == 4) wdata = r1_val ^ r2_val;
            else if (funct3 == 5) {
                if (funct7 & 0x20) wdata = static_cast<uint32_t>(s_r1 >> shamt);
                else wdata = r1_val >> shamt;
            } else if (funct3 == 6) wdata = r1_val | r2_val;
            else if (funct3 == 7) wdata = r1_val & r2_val;
        }

        if (reg_write && rd != 0) {
            regs[rd] = wdata;
        }
        regs[0] = 0;

        pc = next_pc;
        instruction_count++;

        GoldenCommitPacket pkt;
        pkt.pc = current_pc;
        pkt.instruction = instr;
        pkt.mnemonic = disassemble(instr);
        pkt.reg_write = reg_write;
        pkt.rd = rd;
        pkt.wdata = (rd != 0) ? wdata : 0;
        pkt.mem_read = mem_read;
        pkt.mem_raddr = mem_raddr;
        pkt.mem_rdata = mem_rdata;
        pkt.mem_write = mem_write;
        pkt.mem_waddr = mem_waddr;
        pkt.mem_wdata = mem_wdata;
        pkt.mem_we_mask = mem_we_mask;
        pkt.next_pc = next_pc;
        return pkt;
    }
};

#endif // RV32I_GOLDEN_MODEL_H
