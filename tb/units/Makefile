# cocotb Makefile for RV32I unit tests
# Usage:
#   make TOPLEVEL=<verilog_module> MODULE=<python_test_script>
# Example:
#   make TOPLEVEL=alu MODULE=test_alu

SIM ?= icarus
TOPLEVEL_LANG = verilog

# Use relative paths to avoid Windows space-in-path issues
SRC_DIR = ../../src/core
INC_DIR = ../../src/include

# Enable waveform generation (dumping to VCD)
WAVES = 1

COMPILE_ARGS += -I$(INC_DIR)

TOPLEVEL ?= alu
MODULE ?= test_alu

# Change the build directory to the project's sim/ folder
SIM_BUILD = ../../sim/$(TOPLEVEL)

VERILOG_SOURCES = $(SRC_DIR)/$(TOPLEVEL).v

include $(shell cocotb-config --makefiles)/Makefile.sim
