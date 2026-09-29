# ==============================================================================
# Synopsys Design Compiler Synthesis Script
# Target: rv32i_asic_top
# ==============================================================================

# 1. Setup Libraries
set search_path [list . ../../lib]
set target_library [list NangateOpenCellLibrary_slow.db]
set synthetic_library [list dw_foundation.sldb]
set link_library [list * $target_library $synthetic_library]

set DESIGN_NAME "rv32i_asic_top"
set RTL_DIR "../../src/core"
set WRAPPER_DIR "../../src/wrappers"
set OUTPUT_DIR "../../layout"

# 2. Read RTL
# Note: We do NOT read sram_macro_1024x32.v because we want DC to treat 
# the SRAMs as black boxes to be resolved by the physical design tools.
set rtl_files [list \
    ${RTL_DIR}/alu.v \
    ${RTL_DIR}/alu_mux.v \
    ${RTL_DIR}/branch_unit.v \
    ${RTL_DIR}/immediate_gen.v \
    ${RTL_DIR}/lsu.v \
    ${RTL_DIR}/main_decoder.v \
    ${RTL_DIR}/pc_controller.v \
    ${RTL_DIR}/pc_src_mux.v \
    ${RTL_DIR}/pc_writeback_mux.v \
    ${RTL_DIR}/program_counter.v \
    ${RTL_DIR}/register_file.v \
    ${RTL_DIR}/write_back_mux.v \
    ${RTL_DIR}/rv32i_core.v \
    ${WRAPPER_DIR}/rv32i_asic_top.v \
]

read_verilog $rtl_files
current_design $DESIGN_NAME
link

# 3. Apply Constraints
source ../../constraints/${DESIGN_NAME}.sdc

# 4. Compile the Design
compile_ultra 
# If compile_ultra is not available, use: compile -map_effort high

# 5. Generate Reports
report_timing -delay_type max -max_paths 10 > ${DESIGN_NAME}_timing_setup.rpt
report_timing -delay_type min -max_paths 10 > ${DESIGN_NAME}_timing_hold.rpt
report_area > ${DESIGN_NAME}_area.rpt
report_power > ${DESIGN_NAME}_power.rpt

# 6. Write Outputs (netlist for STA and layout)
write -format verilog -hierarchy -output ${OUTPUT_DIR}/${DESIGN_NAME}_synthesized.v
write_sdc ${OUTPUT_DIR}/${DESIGN_NAME}_synthesized.sdc

echo "Synthesis Completed Successfully!"
exit
