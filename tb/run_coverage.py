#!/usr/bin/env python3
"""
RV32I Comprehensive Coverage & Verification Closure Runner
Executes the full test suite (37 Architectural Compliance Tests + Directed Closure Tests)
with both Functional (ISA) and Structural (Verilator Compiler Line/Branch/Toggle & Cocotb) coverage collection.
Generates CLI summaries, Markdown documentation, and Interactive HTML Dashboards.
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile

# Ensure project root and tb are in sys.path
PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_ROOT))
sys.path.insert(0, str(PROJ_ROOT / "tb" / "top"))

from tb.coverage.structural_coverage import StructuralCoverageMonitor
from tb.coverage.coverage_reporter import (
    generate_text_summary,
    generate_html_report,
    generate_markdown_summary,
    parse_verilator_summary,
    load_functional_summary_from_yaml
)


def get_msys_env():
    """Returns an environment with msys64 tools (perl, gcc, make) on PATH."""
    env = os.environ.copy()
    msys_paths = ["C:\\msys64\\usr\\bin", "C:\\msys64\\ucrt64\\bin"]
    cur_path = env.get("PATH", "")
    for p in reversed(msys_paths):
        if p not in cur_path:
            cur_path = p + ";" + cur_path
    env["PATH"] = cur_path
    env["VERILATOR_ROOT"] = "C:\\Users\\SRISHD~1\\scoop\\apps\\oss-cad-suite-nightly\\current\\share\\verilator"
    return env


def compile_test_elf(test_src, elf_path, build_dir, link_ld, model_dir, env_dir):
    """Compiles a .S test source into an ELF binary."""
    gcc_cmd = [
        "riscv64-unknown-elf-gcc",
        "-march=rv32i",
        "-mabi=ilp32",
        "-DXLEN=32",
        "-D__riscv_xlen=32",
        "-DTEST_CASE_1=True",
        "-static",
        "-mcmodel=medany",
        "-fvisibility=hidden",
        "-nostdlib",
        "-nostartfiles",
        "-g",
        "-T", str(link_ld),
        f"-I{model_dir}",
        f"-I{env_dir}",
        str(test_src),
        "-o",
        str(elf_path)
    ]
    res = subprocess.run(gcc_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to compile {test_src.name}: {res.stderr}")
    return elf_path


def elf_to_hex(elf_path, hex_path):
    """Converts an ELF binary to Verilog hex format using objcopy."""
    cmd = ["riscv64-unknown-elf-objcopy", "-O", "verilog", str(elf_path), str(hex_path)]
    subprocess.run(cmd, check=True, capture_output=True)


def get_tohost_address(elf_path):
    """Extracts tohost symbol address from ELF file."""
    with open(elf_path, "rb") as f:
        elff = ELFFile(f)
        symtab = elff.get_section_by_name(".symtab")
        if symtab:
            for s in symtab.iter_symbols():
                if s.name == "tohost":
                    return s["st_value"]
    return 0x4000


def build_verilator_model(verilator_cov_dir):
    """Builds the RV32I hardware simulation model with native Verilator coverage flags."""
    env = get_msys_env()
    verilator_cov_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = (
        "verilator --cc --exe --build -j 4 "
        "--coverage --coverage-line --coverage-toggle "
        "-Wno-UNOPTFLAT -Wno-fatal "
        "-Isrc/include -Isrc/core -Isrc/mem -Isrc/top "
        "-Mdir sim/verilator_cov --top-module rv32i_top "
        "tb/verilator/sim_main.cpp src/top/rv32i_top.v -o Vrv32i_top.exe"
    )
    res = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Verilator compilation failed:\n{res.stderr}\n{res.stdout}")
    return verilator_cov_dir / "Vrv32i_top.exe"


def run_verilator_suite(tests, build_dir, verilator_cov_dir, v_exe):
    """Executes all tests using the native Verilator binary with coverage output."""
    dat_files = []
    print("\n[Verilator] Running Regression Suite with Native Coverage...")
    print(f"{'#':<4} {'Test Name':<30} {'Type':<15} {'Status':<10}")
    print("-" * 65)

    passed = 0
    for idx, (name, test_type, elf_path) in enumerate(tests, 1):
        hex_path = build_dir / f"{name}.hex"
        if not hex_path.exists() or hex_path.stat().st_mtime < elf_path.stat().st_mtime:
            elf_to_hex(elf_path, hex_path)

        tohost = get_tohost_address(elf_path)
        dat_path = verilator_cov_dir / f"{name}.dat"

        cmd = [
            str(v_exe),
            "--hex", str(hex_path),
            "--cov", str(dat_path),
            "--tohost", hex(tohost)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"{idx:<4} {name:<30} {test_type:<15} PASS")
            dat_files.append(dat_path)
            passed += 1
        else:
            out = res.stdout.strip() or res.stderr.strip()
            print(f"{idx:<4} {name:<30} {test_type:<15} FAIL: {out}")

    # Merge Verilator coverage
    merged_dat = PROJ_ROOT / "sim" / "coverage" / "verilator_merged.dat"
    annotated_dir = PROJ_ROOT / "sim" / "coverage" / "verilator_annotated"
    info_file = PROJ_ROOT / "sim" / "coverage" / "verilator.info"
    
    env = get_msys_env()
    posix_dats = [p.as_posix() for p in dat_files]

    write_cmd = f"verilator_coverage --write {merged_dat.as_posix()} {' '.join(posix_dats)}"
    subprocess.run(write_cmd, shell=True, env=env, capture_output=True, check=True)

    annotate_cmd = f"verilator_coverage --annotate {annotated_dir.as_posix()} {merged_dat.as_posix()}"
    subprocess.run(annotate_cmd, shell=True, env=env, capture_output=True, check=True)

    info_cmd = f"verilator_coverage --write-info {info_file.as_posix()} {merged_dat.as_posix()}"
    subprocess.run(info_cmd, shell=True, env=env, capture_output=True, check=True)

    verilator_summary = parse_verilator_summary(str(merged_dat))
    return passed, verilator_summary


def run_cocotb_suite(tests, sim_dir, cov_yaml_dir, cov_struct_dir):
    """Executes tests via Cocotb + Icarus Verilog to sample Functional Covergroups & RTL Toggles."""
    from cocotb_tools.runner import get_runner
    from cocotb_coverage.coverage import merge_coverage

    src_dir = PROJ_ROOT / "src"
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

    runner = get_runner("icarus")
    runner.build(
        sources=sources,
        hdl_toplevel="rv32i_top",
        includes=[inc_dir],
        build_dir=sim_dir,
        waves=False
    )

    yaml_files = []
    struct_json_files = []
    passed = 0

    print("\n[Cocotb] Running Regression Suite with Functional Coverage Sampling...")
    print(f"{'#':<4} {'Test Name':<30} {'Type':<15} {'Status':<10}")
    print("-" * 65)

    for idx, (name, test_type, elf_path) in enumerate(tests, 1):
        test_yaml = cov_yaml_dir / f"{name}.yaml"
        test_struct = cov_struct_dir / f"{name}.json"

        os.environ["ENABLE_COVERAGE"] = "1"
        os.environ["PROG_ELF"] = str(elf_path)
        os.environ["COV_YAML"] = str(test_yaml)
        os.environ["COV_STRUCT_JSON"] = str(test_struct)

        try:
            runner.test(
                hdl_toplevel="rv32i_top",
                test_module="test_rv32i_top",
                test_dir=sim_dir,
                waves=False
            )
            print(f"{idx:<4} {name:<30} {test_type:<15} PASS")
            yaml_files.append(str(test_yaml))
            struct_json_files.append(str(test_struct))
            passed += 1
        except Exception as e:
            print(f"{idx:<4} {name:<30} {test_type:<15} FAIL: {e}")

    # Merge Functional Coverage
    cov_dir = PROJ_ROOT / "sim" / "coverage"
    merged_yaml = cov_dir / "merged_functional_coverage.yaml"
    if yaml_files:
        merge_coverage(print, str(merged_yaml), *yaml_files)

    merged_struct = StructuralCoverageMonitor()
    for s_file in struct_json_files:
        merged_struct.load_and_merge(s_file)

    struct_summary = merged_struct.get_summary()
    func_summary = load_functional_summary_from_yaml(merged_yaml)
    return passed, func_summary, struct_summary


def main():
    parser = argparse.ArgumentParser(description="RV32I Coverage & Verification Closure Runner")
    parser.add_argument(
        "--sim",
        choices=["verilator", "icarus", "both"],
        default=os.getenv("SIM", "both"),
        help="Simulation flow to execute (default: both for complete closure)"
    )
    args = parser.parse_args()

    print("=" * 78)
    print("      RV32I COMPREHENSIVE COVERAGE & VERIFICATION CLOSURE RUNNER")
    print(f"      Selected Simulator Flow: {args.sim.upper()}")
    print("=" * 78)

    cov_dir = PROJ_ROOT / "sim" / "coverage"
    cov_yaml_dir = cov_dir / "yaml_runs"
    cov_struct_dir = cov_dir / "struct_runs"
    build_dir = PROJ_ROOT / "sim" / "coverage_build"
    sim_dir = PROJ_ROOT / "sim" / "rv32i_cov_sim"
    verilator_cov_dir = PROJ_ROOT / "sim" / "verilator_cov"

    for d in [cov_dir, cov_yaml_dir, cov_struct_dir, build_dir, sim_dir, verilator_cov_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Discover & Compile Test Suite
    arch_test_dir = PROJ_ROOT / "riscv-arch-test"
    suite_dir = arch_test_dir / "riscv-test-suite" / "rv32i_m" / "I" / "src"
    env_dir = arch_test_dir / "riscv-test-suite" / "env"
    model_dir = PROJ_ROOT / "compliance" / "rv32i_core" / "env"
    link_ld = model_dir / "link.ld"

    compliance_tests = sorted([f for f in suite_dir.glob("*.S") if not f.name.startswith("fence")])
    tests = []
    print(f"\n[1/4] Preparing Test Suite ({len(compliance_tests) + 1} Tests)...")
    for test_src in compliance_tests:
        elf_path = build_dir / f"{test_src.stem}.elf"
        if not elf_path.exists():
            compile_test_elf(test_src, elf_path, build_dir, link_ld, model_dir, env_dir)
        tests.append((test_src.stem, "Compliance", elf_path))

    # Closure test
    closure_src = PROJ_ROOT / "tb" / "asm" / "coverage_closure.S"
    closure_elf = build_dir / "coverage_closure.elf"
    if not closure_elf.exists():
        compile_test_elf(closure_src, closure_elf, build_dir, link_ld, model_dir, env_dir)
    tests.append(("coverage_closure", "Closure Suite", closure_elf))
    print(f"      All {len(tests)} test binaries ready!")

    verilator_summary = None
    func_summary = {"groups": {}}
    struct_summary = {"toggle": {}, "decision": {}}

    # 2. Execute Verilator Flow if requested
    if args.sim in ("verilator", "both"):
        print("\n[2/4] Building Hardware Model with Verilator Coverage Flags...")
        v_exe = build_verilator_model(verilator_cov_dir)
        v_passed, verilator_summary = run_verilator_suite(tests, build_dir, verilator_cov_dir, v_exe)
        print(f"\n-> Verilator Suite Completed: {v_passed}/{len(tests)} Tests Passed!")

    # 3. Execute Cocotb / Icarus Flow if requested
    if args.sim in ("icarus", "both"):
        print("\n[3/4] Running Functional Coverage Collection with Cocotb...")
        c_passed, func_summary, struct_summary = run_cocotb_suite(tests, sim_dir, cov_yaml_dir, cov_struct_dir)
        print(f"\n-> Cocotb Suite Completed: {c_passed}/{len(tests)} Tests Passed!")
    elif (cov_dir / "merged_functional_coverage.yaml").exists():
        # Load existing functional coverage if available
        func_summary = load_functional_summary_from_yaml(cov_dir / "merged_functional_coverage.yaml")

    # If verilator was not run in this execution but data exists, load it
    merged_dat = cov_dir / "verilator_merged.dat"
    if not verilator_summary and merged_dat.exists():
        verilator_summary = parse_verilator_summary(str(merged_dat))

    # 4. Generate Reports
    print("\n[4/4] Generating Unified Coverage Reports & Visual Dashboards...")
    text_report = generate_text_summary(func_summary, struct_summary, verilator_summary)
    print("\n" + text_report)

    html_file = cov_dir / "coverage_report.html"
    generate_html_report(func_summary, struct_summary, html_file, verilator_summary)
    print(f"\n-> Interactive HTML Dashboard: file:///{html_file.resolve()}")

    md_file = cov_dir / "coverage_summary.md"
    generate_markdown_summary(func_summary, struct_summary, md_file, verilator_summary)
    print(f"-> Markdown Summary saved:     file:///{md_file.resolve()}")

    docs_cov = PROJ_ROOT / "docs" / "coverage.md"
    generate_markdown_summary(func_summary, struct_summary, docs_cov, verilator_summary)
    print(f"-> Documentation updated:      file:///{docs_cov.resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
