# ==============================================================================
# Synopsys PrimeTime STA Script
# Target: rv32i_asic_top
# ==============================================================================

# 1. Setup Libraries
set search_path [list . ../../lib]
set target_library [list NangateOpenCellLibrary_slow.db]
set synthetic_library [list dw_foundation.sldb]
set link_library [list * $target_library $synthetic_library]

set DESIGN_NAME "rv32i_asic_top"
set NETLIST_DIR "../../layout"
set STA_DIR "../../sta"

# 2. Read Synthesized Netlist
read_verilog ${NETLIST_DIR}/${DESIGN_NAME}_synthesized.v
current_design $DESIGN_NAME
link

# 3. Apply SDC (from synthesis)
read_sdc ${NETLIST_DIR}/${DESIGN_NAME}_synthesized.sdc

# Update Timing
update_timing

# 4. Generate STA Reports
report_timing -delay max -nworst 10 -max_paths 10 > ${STA_DIR}/${DESIGN_NAME}_pt_setup.rpt
report_timing -delay min -nworst 10 -max_paths 10 > ${STA_DIR}/${DESIGN_NAME}_pt_hold.rpt
report_analysis_coverage > ${STA_DIR}/${DESIGN_NAME}_pt_coverage.rpt
report_constraint -all_violators > ${STA_DIR}/${DESIGN_NAME}_pt_violators.rpt

echo "Static Timing Analysis Completed Successfully!"
exit
