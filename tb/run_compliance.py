#!/usr/bin/env python3
"""
RV32I Architectural Compliance Test Suite Runner
Runs official RISC-V Architectural Compliance Tests against the RV32I Core.
Note: fence, ecall, and ebreak are intentionally excluded per architecture specification.
"""

import os
import sys
import subprocess
from pathlib import Path
from cocotb_tools.runner import get_runner

def main():
    proj_root = Path(__file__).resolve().parent.parent
    arch_test_dir = proj_root / "riscv-arch-test"
    suite_dir = arch_test_dir / "riscv-test-suite" / "rv32i_m" / "I" / "src"
    env_dir = arch_test_dir / "riscv-test-suite" / "env"
    model_dir = proj_root / "compliance" / "rv32i_core" / "env"
    link_ld = model_dir / "link.ld"
    
    # Auto-initialize submodule if tests directory is missing
    if not suite_dir.exists() or not any(suite_dir.glob("*.S")):
        print("riscv-arch-test suite not found. Initializing git submodule...")
        try:
            subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=proj_root, check=True)
        except Exception as e:
            print(f"Failed to initialize submodule: {e}")
            sys.exit(1)
            
    build_dir = proj_root / "sim" / "compliance_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    
    sim_dir = proj_root / "sim" / "rv32i_compliance"
    sim_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Discover all test files, excluding fence
    test_files = sorted([f for f in suite_dir.glob("*.S") if not f.name.startswith("fence")])
    if not test_files:
        print(f"Error: No test files found in {suite_dir}")
        sys.exit(1)
        
    print("=" * 70)
    print("  RV32I ARCHITECTURAL COMPLIANCE TEST SUITE")
    print(f"  Found {len(test_files)} compliance tests to run (excluding fence, ecall, ebreak)")
    print("=" * 70)
    
    # 2. Build the hardware simulator once
    print("\n[1/3] Building RV32I Core Simulation Model with Icarus Verilog...")
    src_dir = proj_root / "src"
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
    
    sim = os.getenv("SIM", "icarus")
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="rv32i_top",
        includes=[inc_dir],
        build_dir=sim_dir,
        waves=False
    )
    print("      Build complete!")
    
    # 3. Compile and Run each compliance test
    print("\n[2/3] Executing Compliance Tests...")
    print(f"{'#':<4} {'Test Name':<25} {'Result':<10}")
    print("-" * 45)
    
    passed_count = 0
    failed_tests = []
    
    # Set cocotb test module location
    tb_top_dir = proj_root / "tb" / "top"
    sys.path.insert(0, str(tb_top_dir))
    
    for i, test_src in enumerate(test_files, 1):
        test_name = test_src.stem
        elf_path = build_dir / f"{test_name}.elf"
        
        # Compile test with GCC
        gcc_cmd = [
            "riscv64-unknown-elf-gcc",
            "-march=rv32i",
            "-mabi=ilp32",
            "-DXLEN=32",
            "-D__riscv_xlen=32",
            "-static",
            "-mcmodel=medany",
            "-fvisibility=hidden",
            "-nostdlib",
            "-nostartfiles",
            "-g",
            f"-T{link_ld}",
            f"-I{model_dir}",
            f"-I{env_dir}",
            str(test_src),
            "-o",
            str(elf_path)
        ]
        
        res = subprocess.run(gcc_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"{i:<4} {test_name:<25} FAIL (Compilation Error)")
            failed_tests.append((test_name, "GCC Compilation Failed: " + res.stderr.splitlines()[0]))
            continue
            
        # Run test via cocotb
        os.environ["PROG_ELF"] = str(elf_path)
        try:
            runner.test(
                hdl_toplevel="rv32i_top",
                test_module="test_rv32i_top",
                test_dir=sim_dir,
                waves=False
            )
            print(f"{i:<4} {test_name:<25} PASS")
            passed_count += 1
        except Exception as e:
            print(f"{i:<4} {test_name:<25} FAIL")
            failed_tests.append((test_name, str(e)))
            
    print("\n" + "=" * 70)
    print("  COMPLIANCE TEST SUMMARY")
    print(f"  Passed: {passed_count} / {len(test_files)}")
    if failed_tests:
        print(f"  Failed: {len(failed_tests)}")
        for name, reason in failed_tests:
            print(f"    - {name}: {reason}")
    else:
        print("  ALL TESTS PASSED! 100% COMPLIANT!")
    print("=" * 70)
    
    if failed_tests:
        sys.exit(1)

if __name__ == "__main__":
    main()
