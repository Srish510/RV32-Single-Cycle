import os
from pathlib import Path
from cocotb_tools.runner import get_runner

def run_top_level_test():
    # Set paths
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")
    
    proj_path = Path(__file__).resolve().parent.parent.parent
    src_dir = proj_path / "src"
    
    # Store build and test outputs in the /sim directory
    sim_dir = proj_path / "sim" / "rv32i_top_full"
    
    # Include the top level and ALL sub-modules
    sources = [
        src_dir / "top" / "rv32i_top.v",
        src_dir / "core" / "rv32i_core.v",
        src_dir / "core" / "alu.v",
        src_dir / "core" / "alu_mux.v",
        src_dir / "core" / "branch_unit.v",
        src_dir / "core" / "immediate_gen.v",
        src_dir / "core" / "lsu.v",
        src_dir / "core" / "main_decoder.v",
        src_dir / "core" / "pc_controller.v",
        src_dir / "core" / "pc_src_mux.v",
        src_dir / "core" / "pc_writeback_mux.v",
        src_dir / "core" / "program_counter.v",
        src_dir / "core" / "register_file.v",
        src_dir / "core" / "write_back_mux.v",
        src_dir / "mem" / "data_mem.v",
        src_dir / "mem" / "instr_mem.v"
    ]
    
    inc_dir = src_dir / "include"
    
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="rv32i_top",
        includes=[inc_dir],
        build_dir=sim_dir,
        waves=True # Enables VCD/FST waveform dumping
    )
    
    runner.test(
        hdl_toplevel="rv32i_top",
        test_module="test_rv32i_top",
        test_dir=sim_dir,
        waves=True
    )

if __name__ == "__main__":
    print(f"\n=====================================")
    print(f"Running Full-Core Simulation")
    print(f"=====================================")
    run_top_level_test()
