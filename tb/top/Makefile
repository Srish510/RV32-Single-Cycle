# cocotb Makefile for RV32I Full-Core Simulation

SIM ?= icarus
TOPLEVEL_LANG = verilog

# Paths
SRC_DIR = ../../src

# Enable waveform generation (dumping to VCD/FST)
WAVES = 1

# Include directory
COMPILE_ARGS += -I$(SRC_DIR)/include

# Top-level module name
TOPLEVEL = rv32i_top

# Python test module name (without .py)
MODULE = test_rv32i_top

# Build directory for simulation output
SIM_BUILD = ../../sim/rv32i_top_full

# All Verilog Sources needed for the integrated CPU
VERILOG_SOURCES = \
    $(SRC_DIR)/top/rv32i_top.v \
    $(SRC_DIR)/core/rv32i_core.v \
    $(SRC_DIR)/core/alu.v \
    $(SRC_DIR)/core/alu_mux.v \
    $(SRC_DIR)/core/branch_unit.v \
    $(SRC_DIR)/core/immediate_gen.v \
    $(SRC_DIR)/core/lsu.v \
    $(SRC_DIR)/core/main_decoder.v \
    $(SRC_DIR)/core/pc_controller.v \
    $(SRC_DIR)/core/pc_src_mux.v \
    $(SRC_DIR)/core/pc_writeback_mux.v \
    $(SRC_DIR)/core/program_counter.v \
    $(SRC_DIR)/core/register_file.v \
    $(SRC_DIR)/core/write_back_mux.v \
    $(SRC_DIR)/mem/data_mem.v \
    $(SRC_DIR)/mem/instr_mem.v

include $(shell cocotb-config --makefiles)/Makefile.sim
