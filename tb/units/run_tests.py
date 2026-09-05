import os
from pathlib import Path
from cocotb_tools.runner import get_runner

def test_runner(module_name, toplevel_name):
    # Set paths
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")
    
    proj_path = Path(__file__).resolve().parent.parent.parent
    src_dir = proj_path / "src" / "core"
    inc_dir = proj_path / "src" / "include"
    
    # Store build and test outputs in the /sim directory
    sim_dir = proj_path / "sim" / toplevel_name
    
    sources = [src_dir / f"{toplevel_name}.v"]
    
    runner = get_runner(sim)
    runner.build(
        verilog_sources=sources,
        hdl_toplevel=toplevel_name,
        includes=[inc_dir],
        build_dir=sim_dir,
        waves=True 
    )
    
    runner.test(
        hdl_toplevel=toplevel_name,
        test_module=module_name,
        test_dir=sim_dir,
        waves=True 
    )

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        toplevel = sys.argv[1]
        module = sys.argv[2]
        test_runner(module, toplevel)
    else:
        tests = [
            ("alu", "test_alu"),
            ("immediate_gen", "test_immediate_gen"),
            ("branch_unit", "test_branch_unit"),
            ("main_decoder", "test_main_decoder"),
            ("register_file", "test_register_file"),
            ("lsu", "test_lsu")
        ]
        
        for toplevel, module in tests:
            print(f"\n=====================================")
            print(f"Running tests for: {toplevel}")
            print(f"=====================================")
            test_runner(module, toplevel)
