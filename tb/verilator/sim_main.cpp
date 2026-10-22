#include "Vrv32i_top.h"
#include "Vrv32i_top___024root.h"
#include "verilated.h"
#include "verilated_cov.h"
#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <cstdint>

double sc_time_stamp() { return 0; }

static const uint32_t MEM_ADDR_WIDTH = 19;
static const uint32_t MEM_WORDS = 1 << MEM_ADDR_WIDTH;
static const uint32_t MEM_MASK = MEM_WORDS - 1;

static void write_byte(Vrv32i_top* top, uint32_t byte_addr, uint8_t byte_val) {
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

static bool load_hex(Vrv32i_top* top, const std::string& filename) {
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
                write_byte(top, current_addr, byte_val);
                current_addr++;
            }
        }
    }
    return true;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    std::string hex_file = "";
    std::string cov_file = "coverage.dat";
    uint32_t max_cycles = 1000000;
    uint32_t tohost_addr = 0x4000;
    bool debug = false;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--hex" && i + 1 < argc) {
            hex_file = argv[++i];
        } else if (arg == "--cov" && i + 1 < argc) {
            cov_file = argv[++i];
        } else if (arg == "--max-cycles" && i + 1 < argc) {
            max_cycles = std::stoul(argv[++i]);
        } else if (arg == "--tohost" && i + 1 < argc) {
            tohost_addr = static_cast<uint32_t>(std::stoul(argv[++i], nullptr, 0));
        } else if (arg == "--debug") {
            debug = true;
        }
    }

    if (hex_file.empty()) {
        std::cerr << "Usage: Vrv32i_top --hex <program.hex> [--cov <coverage.dat>] [--tohost <addr>] [--max-cycles <N>]" << std::endl;
        return 1;
    }

    Vrv32i_top* top = new Vrv32i_top;

    // Zero memories
    for (uint32_t i = 0; i < MEM_WORDS; i++) {
        top->rootp->rv32i_top__DOT__imem_inst__DOT__memory[i] = 0;
        top->rootp->rv32i_top__DOT__dmem_inst__DOT__memory[i] = 0;
    }

    if (!load_hex(top, hex_file)) {
        delete top;
        return 1;
    }

    // Reset sequence
    top->clk = 0;
    top->rst = 1;
    for (int i = 0; i < 5; i++) {
        top->clk = 1;
        top->eval();
        top->clk = 0;
        top->eval();
    }
    top->rst = 0;

    uint32_t cycles = 0;
    bool passed = false;
    bool finished = false;

    uint32_t last_store_pc = 0xFFFFFFFF;
    uint32_t last_store_val = 0;

    while (cycles < max_cycles && !finished) {
        top->clk = 1;
        top->eval();

        uint32_t pc = top->rootp->rv32i_top__DOT__core_inst__DOT__pc_out;
        uint32_t next_pc = top->rootp->rv32i_top__DOT__core_inst__DOT__next_pc;

        // Check tohost write
        if (top->rootp->rv32i_top__DOT__data_we != 0) {
            uint32_t addr = top->rootp->rv32i_top__DOT__core_inst__DOT__alu_result;
            uint32_t status = top->rootp->rv32i_top__DOT__data_wdata;
            last_store_pc = pc;
            last_store_val = status;

            if (addr == tohost_addr || addr == 0x00004000 || addr == 0x00001000 || addr == 0x80001000) {
                passed = (status == 1);
                finished = true;
                break;
            }
        }

        // Check tight spin loop (pc == next_pc)
        if (pc == next_pc) {
            uint32_t gp = top->rootp->rv32i_top__DOT__core_inst__DOT__reg_file_inst__DOT__registers[3];
            uint32_t x1 = top->rootp->rv32i_top__DOT__core_inst__DOT__reg_file_inst__DOT__registers[1];
            if (gp == 1 || x1 == 1) {
                passed = true;
            } else {
                passed = false;
            }
            finished = true;
            break;
        }

        // Check write_tohost 2-instruction loop (sw at last_store_pc, followed by j back to last_store_pc)
        if (last_store_pc != 0xFFFFFFFF && next_pc == last_store_pc && pc == last_store_pc + 4) {
            passed = (last_store_val == 1);
            finished = true;
            break;
        }

        top->clk = 0;
        top->eval();
        cycles++;
    }

    top->final();
    VerilatedCov::write(cov_file.c_str());
    delete top;

    if (!finished) {
        std::cerr << "TIMEOUT: Simulation exceeded " << max_cycles << " cycles!" << std::endl;
        return 2;
    }

    if (passed) {
        std::cout << "TEST PASSED (Cycles: " << cycles << ")" << std::endl;
        return 0;
    } else {
        std::cout << "TEST FAILED (Cycles: " << cycles << ")" << std::endl;
        return 1;
    }
}
