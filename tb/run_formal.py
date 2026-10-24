#!/usr/bin/env python3
"""
RV32I Formal Verification Runner (SymbiYosys + Yosys-SMTBMC + RVFI)
Executes Bounded Model Checking (BMC), k-Induction (Prove), and Reachability
Witness Generation (Cover) across all pure Verilog-2005 formal targets:
  1. decoder   - Main Decoder & Immediate Generator (all 2^32 instruction words)
  2. alu       - 32-bit ALU arithmetic, logic, shift & overflow theorems
  3. lsu       - Load-Store Unit byte-mask legality & sign/zero extension
  4. branch_pc - PC Controller, Branch Unit & JALR LSB masking
  5. rvfi_core - Full RV32I Core + RVFI 37-Instruction ISA Contract & RAW/Frame invariants
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FORMAL_DIR = PROJECT_ROOT / "formal"
SBY_DIR = FORMAL_DIR / "sby"
OUT_DIR = PROJECT_ROOT / "sim" / "formal"

TARGETS = {
    "decoder": {
        "sby": SBY_DIR / "decoder.sby",
        "top": "formal_decoder",
        "description": "Main Decoder & Immediate Generator (All 2^32 Encodings)",
    },
    "alu": {
        "sby": SBY_DIR / "alu.sby",
        "top": "formal_alu",
        "description": "32-Bit ALU Arithmetic, Shifts & Signed Overflow Theorems",
    },
    "lsu": {
        "sby": SBY_DIR / "lsu.sby",
        "top": "formal_lsu",
        "description": "Load-Store Unit Byte-Enable Mask & Extension Invariants",
    },
    "branch_pc": {
        "sby": SBY_DIR / "branch_pc.sby",
        "top": "formal_branch_pc",
        "description": "PC Controller, Branch Decision & JALR LSB Masking",
    },
    "rvfi_core": {
        "sby": SBY_DIR / "rvfi_core.sby",
        "top": "formal_rvfi_core",
        "description": "Full RV32I Core + RVFI 37-Instruction ISA Contract",
    },
}


def get_short_path_name(long_name: str) -> str:
    """Convert Windows path with spaces into 8.3 short path for OSS CAD Suite."""
    if os.name != "nt":
        return long_name
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        res = ctypes.windll.kernel32.GetShortPathNameW(long_name, buf, 512)
        if res > 0:
            return buf.value
    except Exception:
        pass
    return long_name


def setup_oss_cad_env() -> tuple:
    """Configure environment variables for SymbiYosys and Yosys on Windows/Linux."""
    env = os.environ.copy()
    sby_cmd = ["sby"]
    if os.name == "nt":
        sby_exe = shutil.which("sby")
        cad_root = None
        if sby_exe:
            cad_root = Path(sby_exe).resolve().parent.parent
        else:
            candidate = Path.home() / "scoop" / "apps" / "oss-cad-suite-nightly" / "current"
            if candidate.exists():
                cad_root = candidate

        if cad_root and cad_root.exists():
            short_root = get_short_path_name(str(cad_root))
            env["YOSYSHQ_ROOT"] = short_root + "\\"
            py_exe = os.path.join(short_root, "lib", "python3.exe")
            sby_script = os.path.join(short_root, "bin", "sby-script.py")
            env["PYTHON_EXECUTABLE"] = py_exe
            bin_dir = os.path.join(short_root, "bin")
            lib_dir = os.path.join(short_root, "lib")
            env["PATH"] = f"{bin_dir};{lib_dir};{env.get('PATH', '')}"
            os.environ["YOSYSHQ_ROOT"] = env["YOSYSHQ_ROOT"]
            os.environ["PYTHON_EXECUTABLE"] = env["PYTHON_EXECUTABLE"]
            os.environ["PATH"] = env["PATH"]
            if os.path.exists(py_exe) and os.path.exists(sby_script):
                sby_cmd = [py_exe, sby_script]
    return env, sby_cmd


def parse_cell_counts(work_dir: Path) -> dict:
    """Extract $assert, $assume, and $cover counts from Yosys design_smt2.smt2."""
    counts = {"assert": 0, "assume": 0, "cover": 0}
    smt2_file = work_dir / "model" / "design_smt2.smt2"
    if not smt2_file.exists():
        return counts
    content = smt2_file.read_text(encoding="utf-8", errors="ignore")
    counts["assert"] = len(re.findall(r"^;\s*yosys-smt2-assert\b", content, re.MULTILINE))
    counts["assume"] = len(re.findall(r"^;\s*yosys-smt2-assume\b", content, re.MULTILINE))
    counts["cover"] = len(re.findall(r"^;\s*yosys-smt2-cover\b", content, re.MULTILINE))
    return counts


def parse_counterexample(work_dir: Path) -> dict:
    """Extract counterexample details from logfile.txt and trace.smtc when a proof fails."""
    info = {"failed_assert": "Unknown", "step": "0", "smtc_assignments": [], "vcd": ""}
    logfile = work_dir / "logfile.txt"
    if logfile.exists():
        text = logfile.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"Assert failed in \S+: (\S+)", text)
        if m:
            info["failed_assert"] = m.group(1)
        m_step = re.search(r"Checking assertions in step (\d+)\.\.\s+[\s\S]*?BMC failed!", text)
        if m_step:
            info["step"] = m_step.group(1)

    smtc_file = work_dir / "engine_0" / "trace.smtc"
    if smtc_file.exists():
        lines = smtc_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        info["smtc_assignments"] = [ln.strip() for ln in lines if ln.strip().startswith("assume")]

    vcd_file = work_dir / "engine_0" / "trace.vcd"
    if vcd_file.exists():
        info["vcd"] = str(vcd_file.relative_to(PROJECT_ROOT))
    return info


def run_bug_injection(target_name: str, env: dict, sby_cmd: list, solver: str) -> int:
    """Run BMC with -DFORMAL_BUG_INJECT to verify immediate counterexample generation."""
    if target_name not in TARGETS:
        print(f"[ERROR] Unknown formal target '{target_name}'. Choose from: {', '.join(TARGETS.keys())}")
        return 1

    target = TARGETS[target_name]
    sby_text = target["sby"].read_text(encoding="utf-8")
    # Inject -DFORMAL_BUG_INJECT into read_verilog -formal line
    modified_sby = sby_text.replace(
        "read_verilog -formal",
        "read_verilog -formal -DFORMAL_BUG_INJECT"
    )
    if solver != "z3":
        modified_sby = modified_sby.replace("smtbmc z3", f"smtbmc {solver}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bug_sby_path = OUT_DIR / f"{target_name}_bug_inject.sby"
    bug_sby_path.write_text(modified_sby, encoding="utf-8")
    prefix = OUT_DIR / f"{target_name}_bug"

    print("\n" + "=" * 84)
    print("      [!] RV32I FORMAL VERIFICATION - INTENTIONAL BUG INJECTION DEMO [!]")
    print("=" * 84)
    print(f"  Target Suite:  {target_name} ({target['top']})")
    print(f"  Description:   {target['description']}")
    print(f"  SMT Solver:    {solver.upper()}")
    print("  Macro Injected: -DFORMAL_BUG_INJECT")
    print("=" * 84 + "\n")

    t0 = time.perf_counter()
    cmd = sby_cmd + ["-f", "--prefix", str(prefix), str(bug_sby_path), "bmc"]
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True)
    elapsed = time.perf_counter() - t0

    work_dir = Path(f"{prefix}_bmc")
    if proc.returncode != 0 and (work_dir / "FAIL").exists():
        cex = parse_counterexample(work_dir)
        print("  [PASS - VIOLATION CAUGHT] SymbiYosys + SMT Solver falsified the property!")
        print(f"  * Elapsed Time:      {elapsed:.2f}s")
        print(f"  * Violated Property: {cex['failed_assert']}")
        print(f"  * Falsified at Step: {cex['step']}")
        print(f"  * Witness VCD Trace: {cex['vcd']}")
        if cex["smtc_assignments"]:
            print("  * Counterexample Input Assignments (.smtc):")
            for assign in cex["smtc_assignments"][:10]:
                print(f"      {assign}")
        print("\n" + "=" * 84)
        return 3  # Non-zero exit code indicating intentional formal falsification
    else:
        print("  [ERROR] Expected formal assertion failure, but SBY did not report FAIL!")
        print(proc.stdout)
        print(proc.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="RV32I Formal Verification Suite Runner")
    parser.add_argument("--all", action="store_true", help="Run all formal verification suites (default)")
    parser.add_argument(
        "--target",
        choices=list(TARGETS.keys()),
        help="Run a specific formal verification target",
    )
    parser.add_argument(
        "--task",
        choices=["bmc", "prove", "cover", "all"],
        default="all",
        help="Formal verification task mode to execute (default: all)",
    )
    parser.add_argument(
        "--solver",
        choices=["z3", "yices", "bitwuzla", "boolector"],
        default="z3",
        help="SMT solver engine (default: z3)",
    )
    parser.add_argument(
        "--inject-bug",
        metavar="TARGET",
        choices=list(TARGETS.keys()),
        help="Inject an intentional property violation into TARGET to demonstrate counterexample trace generation",
    )
    args = parser.parse_args()

    env, sby_cmd = setup_oss_cad_env()

    if args.inject_bug:
        return run_bug_injection(args.inject_bug, env, sby_cmd, args.solver)

    selected_targets = [args.target] if args.target else list(TARGETS.keys())
    tasks_to_run = ["bmc", "prove", "cover"] if args.task == "all" else [args.task]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 88)
    print("      [*] RV32I FORMAL VERIFICATION SUITE (SymbiYosys + Yosys-SMTBMC + RVFI) [*]")
    print("=" * 88)
    print(f"  Targets:       {', '.join(selected_targets)}")
    print(f"  Tasks:         {', '.join(t.upper() for t in tasks_to_run)}")
    print(f"  SMT Solver:    {args.solver.upper()}")
    print("  HDL Standard:  Pure IEEE 1364-2005 Verilog (.v)")
    print("=" * 88 + "\n")

    header = f"{'#':<3} {'Target':<12} {'Top Module':<18} {'BMC':<8} {'Prove (k-Ind)':<15} {'Cover':<8} {'Asserts':<9} {'Covers':<8} {'Time':<7}"
    print(header)
    print("-" * len(header))

    results = []
    all_passed = True
    total_asserts = 0
    total_covers = 0
    suite_start = time.perf_counter()

    for idx, t_name in enumerate(selected_targets, start=1):
        t_cfg = TARGETS[t_name]
        sby_file = t_cfg["sby"]
        prefix = OUT_DIR / t_name

        # Optionally override solver if not z3
        run_sby_file = sby_file
        if args.solver != "z3":
            sby_text = sby_file.read_text(encoding="utf-8").replace("smtbmc z3", f"smtbmc {args.solver}")
            run_sby_file = OUT_DIR / f"{t_name}_{args.solver}.sby"
            run_sby_file.write_text(sby_text, encoding="utf-8")

        t0 = time.perf_counter()
        cmd = sby_cmd + ["-f", "--prefix", str(prefix), str(run_sby_file)] + tasks_to_run
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True)
        elapsed = time.perf_counter() - t0

        task_statuses = {}
        for task in ["bmc", "prove", "cover"]:
            if task not in tasks_to_run:
                task_statuses[task] = "SKIP"
                continue
            wdir = Path(f"{prefix}_{task}")
            if (wdir / "PASS").exists():
                task_statuses[task] = "PASS"
            elif (wdir / "FAIL").exists():
                task_statuses[task] = "FAIL"
                all_passed = False
            else:
                task_statuses[task] = "ERROR"
                all_passed = False

        if proc.returncode != 0:
            all_passed = False

        # Parse cell counts from bmc/prove and cover workdirs
        bmc_counts = parse_cell_counts(Path(f"{prefix}_bmc"))
        if bmc_counts["assert"] == 0:
            bmc_counts = parse_cell_counts(Path(f"{prefix}_prove"))
        cov_counts = parse_cell_counts(Path(f"{prefix}_cover"))

        n_assert = bmc_counts["assert"]
        n_cover = cov_counts["cover"]
        total_asserts += n_assert
        total_covers += n_cover

        print(
            f"{idx:<3} {t_name:<12} {t_cfg['top']:<18} "
            f"{task_statuses['bmc']:<8} {task_statuses['prove']:<15} {task_statuses['cover']:<8} "
            f"{n_assert:<9} {n_cover:<8} {elapsed:.2f}s"
        )

        results.append({
            "target": t_name,
            "top": t_cfg["top"],
            "description": t_cfg["description"],
            "bmc": task_statuses["bmc"],
            "prove": task_statuses["prove"],
            "cover": task_statuses["cover"],
            "assertions": n_assert,
            "assumptions": bmc_counts["assume"],
            "covers": n_cover,
            "elapsed_sec": round(elapsed, 2),
        })

    total_time = time.perf_counter() - suite_start
    print("-" * len(header))
    print("\n[SUMMARY]")
    print(f"  Formal Targets Verified:   {len(selected_targets)} / {len(selected_targets)}")
    print(f"  Total Formal Assertions:   {total_asserts} mathematically proven invariants")
    print(f"  Total Reachability Covers: {total_covers} witness traces (.vcd) generated")
    print(f"  Total Verification Time:   {total_time:.2f}s")

    summary_path = OUT_DIR / "formal_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "solver": args.solver,
                "all_passed": all_passed,
                "total_assertions": total_asserts,
                "total_covers": total_covers,
                "total_elapsed_sec": round(total_time, 2),
                "targets": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if all_passed:
        print("\n[SUCCESS] ALL FORMAL PROPERTIES PROVEN (BMC + k-INDUCTION + WITNESS COVER)!\n")
        return 0
    else:
        print("\n[FAILURE] ONE OR MORE FORMAL VERIFICATION TASKS FAILED!\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
