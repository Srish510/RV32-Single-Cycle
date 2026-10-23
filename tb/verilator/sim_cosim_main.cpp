#include "Vrv32i_top.h"
#include "Vrv32i_top___024root.h"
#include "verilated.h"
#include "verilated_cov.h"
#include "rv32i_golden_model.h"

#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <vector>
#include <iomanip>
#include <cstdint>

double sc_time_stamp() { return 0; }

static const uint32_t MEM_ADDR_WIDTH = 19;
static const uint32_t MEM_WORDS = 1 << MEM_ADDR_WIDTH;
static const uint32_t MEM_MASK = MEM_WORDS - 1;

static void write_byte_dut(Vrv32i_top* top, uint32_t byte_addr, uint8_t byte_val) {
    uint32_t word_idx = (byte_addr >> 2) & MEM_MASK;
    int shift = (byte_addr % 4) * 8;
    if (word_idx < MEM_WORDS) {
        uint32_t imem_val = top->rootp->rv32i_top__DOT__imem_inst__DOT__memory[word_idx];
        imem_val &= ~(0xFF << shift);
        imem_val |= (static_cast<uint32_t>(byte_val) << shift);
        top->rootp->rv32i_top__DOT__imem_inst__DOT__memory[word_idx] = imem_val;

        uint32_t dmem_val = top->rootp->rv32i_top__DOT__dmem_inst__DOT__memory[word_idx];
        dmem_val &= ~(0xFF << shift);
        dmem_val |= (static_cast<uint32_t>(byte_val) << shift);
        top->rootp->rv32i_top__DOT__dmem_inst__DOT__memory[word_idx] = dmem_val;
    }
}

static bool load_hex(Vrv32i_top* top, RV32IGoldenModel& golden, const std::string& filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "Error: Could not open hex file: " << filename << std::endl;
        return false;
    }

    std::string line;
    uint32_t current_addr = 0;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '/' || line[0] == '#') continue;

        if (line[0] == '@') {
            current_addr = static_cast<uint32_t>(std::stoul(line.substr(1), nullptr, 16));
        } else {
            std::istringstream iss(line);
            std::string byte_str;
            while (iss >> byte_str) {
                uint8_t byte_val = static_cast<uint8_t>(std::stoul(byte_str, nullptr, 16));
                write_byte_dut(top, current_addr, byte_val);
                golden.write_byte(current_addr, byte_val);
                current_addr++;
            }
        }
    }
    return true;
}

struct HistoryItem {
    uint64_t step_num;
    uint32_t pc;
    uint32_t instruction;
    std::string mnemonic;
};

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    std::string hex_file = "";
    std::string cov_file = "coverage.dat";
    std::string trace_file = "";
    uint32_t max_cycles = 1000000;
    uint32_t tohost_addr = 0x4000;
    int inject_fault_cycle = -1;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--hex" && i + 1 < argc) {
            hex_file = argv[++i];
        } else if (arg == "--cov" && i + 1 < argc) {
            cov_file = argv[++i];
        } else if (arg == "--trace" && i + 1 < argc) {
            trace_file = argv[++i];
        } else if (arg == "--tohost" && i + 1 < argc) {
            tohost_addr = static_cast<uint32_t>(std::stoul(argv[++i], nullptr, 0));
        } else if (arg == "--max-cycles" && i + 1 < argc) {
            max_cycles = std::stoul(argv[++i]);
        } else if (arg == "--inject-fault" && i + 1 < argc) {
            inject_fault_cycle = std::stoi(argv[++i]);
        }
    }

    if (hex_file.empty()) {
        std::cerr << "Usage: Vrv32i_top_cosim --hex <program.hex> [--cov <coverage.dat>] [--trace <spike.log>] [--tohost <addr>]" << std::endl;
        return 1;
    }

    Vrv32i_top* top = new Vrv32i_top;
    RV32IGoldenModel* golden = new RV32IGoldenModel;

    // Trigger Verilator initial blocks (eval_initial) BEFORE loading hex!
    top->eval();

    // Zero memories
    for (uint32_t i = 0; i < MEM_WORDS; i++) {
        top->rootp->rv32i_top__DOT__imem_inst__DOT__memory[i] = 0;
        top->rootp->rv32i_top__DOT__dmem_inst__DOT__memory[i] = 0;
    }
    golden->reset(0);

    if (!load_hex(top, *golden, hex_file)) {
        delete golden;
        delete top;
        return 1;
    }

    std::ofstream trace_stream;
    if (!trace_file.empty()) {
        trace_stream.open(trace_file);
    }

    // Reset sequence
    top->clk = 0;
    top->rst = 1;
    top->eval();
    for (int i = 0; i < 5; i++) {
        top->clk = 1; top->eval();
        top->clk = 0; top->eval();
    }
    top->rst = 0;
    top->eval(); // Propagate reset deassertion into combinational paths

    uint32_t cycles = 0;
    uint64_t retired_instructions = 0;
    bool passed = false;
    bool finished = false;
    bool diverged = false;
    std::string divergence_reason = "";

    uint32_t last_store_pc = 0xFFFFFFFF;
    uint32_t last_store_val = 0;

    std::vector<HistoryItem> history;

    while (cycles < max_cycles && !finished && !diverged) {
        // 1. Sample DUT combinational outputs for current PC
        uint32_t dut_pc = top->rootp->rv32i_top__DOT__core_inst__DOT__pc_out;
        uint32_t dut_next_pc = top->rootp->rv32i_top__DOT__core_inst__DOT__next_pc;
        uint32_t word_idx = (dut_pc >> 2) & MEM_MASK;
        uint32_t dut_instr = top->rootp->rv32i_top__DOT__imem_inst__DOT__memory[word_idx];

        uint8_t dut_reg_we = top->rootp->rv32i_top__DOT__core_inst__DOT__reg_write;
        uint32_t dut_rd = (dut_instr >> 7) & 0x1F;
        uint32_t dut_wdata = top->rootp->rv32i_top__DOT__core_inst__DOT__write_data;

        uint8_t dut_mem_we = top->rootp->rv32i_top__DOT__data_we;
        uint32_t dut_mem_addr = top->rootp->rv32i_top__DOT__core_inst__DOT__alu_result;
        uint32_t dut_mem_wdata = top->rootp->rv32i_top__DOT__data_wdata;

        // Intentional fault injection mode (for testing divergence detection)
        if (inject_fault_cycle >= 0 && cycles == static_cast<uint32_t>(inject_fault_cycle)) {
            top->rootp->rv32i_top__DOT__core_inst__DOT__reg_file_inst__DOT__registers[3] ^= 0xDEADBEEF; // Corrupt register file state
        }

        // 2. Step Golden Reference Model
        GoldenCommitPacket g_pkt = golden->step(dut_instr);
        retired_instructions++;

        HistoryItem h;
        h.step_num = retired_instructions;
        h.pc = dut_pc;
        h.instruction = dut_instr;
        h.mnemonic = g_pkt.mnemonic;
        history.push_back(h);
        if (history.size() > 10) history.erase(history.begin());

        // 3. Compare Combinational Architectural Signals
        // A. Check PC
        if (dut_pc != g_pkt.pc) {
            diverged = true;
            std::ostringstream oss;
            oss << "PC Mismatch! Expected 0x" << std::hex << g_pkt.pc << ", Got 0x" << dut_pc;
            divergence_reason = oss.str();
        }
        // B. Check Next PC / Branch Target
        else if (dut_next_pc != g_pkt.next_pc) {
            diverged = true;
            std::ostringstream oss;
            oss << "Next PC / Branch Target Mismatch! Expected 0x" << std::hex << g_pkt.next_pc << ", Got 0x" << dut_next_pc;
            divergence_reason = oss.str();
        }
        // C. Check Register Write
        else if (g_pkt.reg_write && g_pkt.rd != 0) {
            if (!dut_reg_we) {
                diverged = true;
                std::ostringstream oss;
                oss << "Missing reg_write for x" << g_pkt.rd << "!";
                divergence_reason = oss.str();
            } else if (dut_rd != g_pkt.rd) {
                diverged = true;
                std::ostringstream oss;
                oss << "Destination Register (rd) Mismatch! Expected x" << g_pkt.rd << ", Got x" << dut_rd;
                divergence_reason = oss.str();
            } else if (dut_wdata != g_pkt.wdata) {
                diverged = true;
                std::ostringstream oss;
                oss << "Writeback Data Mismatch for x" << g_pkt.rd << "! Expected 0x" << std::hex << g_pkt.wdata
                    << ", Got 0x" << dut_wdata << " (Bit Diff: 0x" << (dut_wdata ^ g_pkt.wdata) << ")";
                divergence_reason = oss.str();
            }
        }
        // D. Check Spurious Register Write
        else if (!g_pkt.reg_write && dut_reg_we && dut_rd != 0) {
            diverged = true;
            std::ostringstream oss;
            oss << "Spurious reg_write to x" << dut_rd << " by DUT! Expected no write.";
            divergence_reason = oss.str();
        }
        // E. Check Memory Write
        else if (g_pkt.mem_write) {
            uint32_t active_mask = 0;
            if (g_pkt.mem_we_mask & 0x1) active_mask |= 0x000000FF;
            if (g_pkt.mem_we_mask & 0x2) active_mask |= 0x0000FF00;
            if (g_pkt.mem_we_mask & 0x4) active_mask |= 0x00FF0000;
            if (g_pkt.mem_we_mask & 0x8) active_mask |= 0xFF000000;

            if (dut_mem_we != g_pkt.mem_we_mask) {
                diverged = true;
                std::ostringstream oss;
                oss << "Memory Write Enable Mismatch! Expected 0x" << std::hex << g_pkt.mem_we_mask
                    << ", Got 0x" << static_cast<uint32_t>(dut_mem_we) << " for store to 0x" << g_pkt.mem_waddr;
                divergence_reason = oss.str();
            } else if ((dut_mem_addr & ~3U) != (g_pkt.mem_waddr & ~3U)) {
                diverged = true;
                std::ostringstream oss;
                oss << "Store Word Address Mismatch! Expected 0x" << std::hex << (g_pkt.mem_waddr & ~3U)
                    << ", Got 0x" << (dut_mem_addr & ~3U);
                divergence_reason = oss.str();
            } else if ((dut_mem_wdata & active_mask) != (g_pkt.mem_wdata & active_mask)) {
                diverged = true;
                std::ostringstream oss;
                oss << "Store Data Mismatch! Expected 0x" << std::hex << (g_pkt.mem_wdata & active_mask)
                    << ", Got 0x" << (dut_mem_wdata & active_mask);
                divergence_reason = oss.str();
            }
        }

        // Optional Spike commit trace export
        if (trace_stream.is_open()) {
            if (g_pkt.reg_write && g_pkt.rd != 0) {
                trace_stream << "core   0: 0x" << std::hex << std::setw(8) << std::setfill('0') << g_pkt.pc
                             << " (0x" << std::setw(8) << g_pkt.instruction << ") x"
                             << std::dec << std::setw(2) << std::setfill(' ') << g_pkt.rd
                             << " 0x" << std::hex << std::setw(8) << std::setfill('0') << g_pkt.wdata << "\n";
            } else if (g_pkt.mem_write) {
                trace_stream << "core   0: 0x" << std::hex << std::setw(8) << std::setfill('0') << g_pkt.pc
                             << " (0x" << std::setw(8) << g_pkt.instruction << ") mem 0x"
                             << std::hex << std::setw(8) << std::setfill('0') << g_pkt.mem_waddr << " 0x"
                             << std::setw(8) << g_pkt.mem_wdata << "\n";
            } else {
                trace_stream << "core   0: 0x" << std::hex << std::setw(8) << std::setfill('0') << g_pkt.pc
                             << " (0x" << std::setw(8) << g_pkt.instruction << ")\n";
            }
        }

        // Check tohost write
        if (dut_mem_we != 0) {
            uint32_t addr = dut_mem_addr;
            uint32_t status = dut_mem_wdata;
            last_store_pc = dut_pc;
            last_store_val = status;

            if (addr == tohost_addr || addr == 0x00004000 || addr == 0x00001000 || addr == 0x80001000) {
                passed = (status == 1);
                finished = true;
            }
        }

        // Check tight spin loop
        if (dut_pc == dut_next_pc) {
            uint32_t gp = top->rootp->rv32i_top__DOT__core_inst__DOT__reg_file_inst__DOT__registers[3];
            uint32_t x1 = top->rootp->rv32i_top__DOT__core_inst__DOT__reg_file_inst__DOT__registers[1];
            passed = (gp == 1 || x1 == 1);
            finished = true;
        }

        // Check write_tohost 2-instruction loop
        if (last_store_pc != 0xFFFFFFFF && dut_next_pc == last_store_pc && dut_pc == last_store_pc + 4) {
            passed = (last_store_val == 1);
            finished = true;
        }

        // 4. Clock edge: trigger sequential write into regfile & memory
        top->clk = 1;
        top->eval();

        // 5. Verify Full 32-Register Architectural State after commit
        if (!diverged) {
            for (int r = 1; r < 32; r++) {
                uint32_t expected_val = golden->regs[r];
                uint32_t dut_val = top->rootp->rv32i_top__DOT__core_inst__DOT__reg_file_inst__DOT__registers[r];
                if (dut_val != expected_val) {
                    diverged = true;
                    std::ostringstream oss;
                    oss << "Architectural Register State Drift at x" << r << "! Expected 0x" << std::hex << expected_val
                        << ", Got 0x" << dut_val << " (Bit Diff: 0x" << (dut_val ^ expected_val) << ")";
                    divergence_reason = oss.str();
                    break;
                }
            }
        }

        if (diverged) {
            std::cerr << "\n================================================================================" << std::endl;
            std::cerr << "     [!] LOCKSTEP CO-SIMULATION DIVERGENCE DETECTED [!]" << std::endl;
            std::cerr << "================================================================================" << std::endl;
            std::cerr << "  Failure At Retired Instruction #" << retired_instructions << " (Cycle " << cycles << ")" << std::endl;
            std::cerr << "  Program Counter: 0x" << std::hex << dut_pc << std::endl;
            std::cerr << "  Machine Code:    0x" << dut_instr << std::endl;
            std::cerr << "  Disassembly:     " << g_pkt.mnemonic << std::endl;
            std::cerr << "--------------------------------------------------------------------------------" << std::endl;
            std::cerr << "  REASON: " << divergence_reason << std::endl;
            std::cerr << "--------------------------------------------------------------------------------" << std::endl;
            std::cerr << "  RECENT INSTRUCTION TRACE:" << std::endl;
            for (const auto& item : history) {
                std::cerr << "    #" << std::dec << item.step_num << " PC: 0x" << std::hex << item.pc
                          << "  [" << item.mnemonic << "] (0x" << item.instruction << ")" << std::endl;
            }
            std::cerr << "--------------------------------------------------------------------------------" << std::endl;
            std::cerr << "  REGISTER FILE DUMP COMPARISON:" << std::endl;
            std::cerr << "  Reg    Expected (Golden)     Actual (DUT)         Status" << std::endl;
            std::cerr << "  --------------------------------------------------------" << std::endl;
            for (int r = 0; r < 32; r++) {
                uint32_t exp_v = golden->regs[r];
                uint32_t dut_v = top->rootp->rv32i_top__DOT__core_inst__DOT__reg_file_inst__DOT__registers[r];
                bool match = (exp_v == dut_v);
                if (exp_v != 0 || dut_v != 0 || !match) {
                    std::cerr << (match ? "   " : ">> ") << "x" << std::dec << std::setw(2) << r
                              << "   0x" << std::hex << std::setw(8) << std::setfill('0') << exp_v
                              << "           0x" << std::setw(8) << dut_v
                              << "           " << (match ? "OK" : "MISMATCH") << std::endl;
                }
            }
            std::cerr << "================================================================================\n" << std::endl;
            break;
        }

        // 6. Clock falling edge
        top->clk = 0;
        top->eval();
        cycles++;
    }

    top->final();
    VerilatedCov::write(cov_file.c_str());
    delete top;
    delete golden;

    if (trace_stream.is_open()) {
        trace_stream.close();
    }

    if (diverged) {
        return 3; // Co-Simulation Divergence Code
    }

    if (!finished) {
        std::cerr << "TIMEOUT: Simulation exceeded " << max_cycles << " cycles!" << std::endl;
        return 2;
    }

    if (passed) {
        std::cout << "CO-SIMULATION PASSED: " << retired_instructions << " instructions verified in lockstep! (Cycles: " << cycles << ")" << std::endl;
        return 0;
    } else {
        std::cout << "TEST FAILED (Cycles: " << cycles << ")" << std::endl;
        return 1;
    }
}
