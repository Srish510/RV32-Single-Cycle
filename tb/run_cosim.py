#!/usr/bin/env python3
"""
RV32I Lockstep Co-Simulation & Golden Reference Model Regression Runner
Executes RISC-V test suites lockstep against the Golden Reference Model (ISS),
verifying PC, next PC, register writeback, and full 32 architectural registers
on every instruction retirement to immediately pinpoint RTL divergences.
"""

import argparse
import os
import sys
import subprocess
import glob
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from elftools.elf.elffile import ELFFile
except ImportError:
    ELFFile = None

PROJ_ROOT = Path(__file__).resolve().parent.parent
SIM_DIR = PROJ_ROOT / "sim"
COSIM_DIR = SIM_DIR / "cosim"
VERILATOR_BIN = SIM_DIR / "verilator_cosim" / "Vrv32i_top_cosim.exe"
COVERAGE_BUILD = SIM_DIR / "coverage_build"


def get_tohost_address(elf_path: Path) -> int:
    """Extracts tohost symbol address from ELF file."""
    if not ELFFile or not elf_path.exists():
        return 0x4000
    try:
        with open(elf_path, "rb") as f:
            elff = ELFFile(f)
            symtab = elff.get_section_by_name(".symtab")
            if symtab:
                for s in symtab.iter_symbols():
                    if s.name == "tohost":
                        return s["st_value"]
    except Exception:
        pass
    return 0x4000


def find_available_tests() -> List[Tuple[str, Path, Optional[Path]]]:
    """Finds all available tests (name, hex_path, elf_path)."""
    tests = []
    if COVERAGE_BUILD.exists():
        hex_files = sorted(COVERAGE_BUILD.glob("*.hex"))
        for h in hex_files:
            name = h.stem
            elf = COVERAGE_BUILD / f"{name}.elf"
            tests.append((name, h, elf if elf.exists() else None))
    return tests


def run_verilator_cosim(
    hex_path: Path,
    tohost: int,
    trace_path: Optional[Path] = None,
    inject_fault: Optional[int] = None,
    max_cycles: int = 1000000
) -> Tuple[bool, int, int, str]:
    """
    Runs test in Verilator lockstep co-simulation.
    Returns: (passed, instructions_verified, cycles, output_or_error)
    """
    if not VERILATOR_BIN.exists():
        return False, 0, 0, f"Binary not found: {VERILATOR_BIN}"

    cmd = [
        str(VERILATOR_BIN),
        "--hex", str(hex_path),
        "--tohost", hex(tohost),
        "--max-cycles", str(max_cycles)
    ]
    if trace_path:
        cmd += ["--trace", str(trace_path)]
    if inject_fault is not None:
        cmd += ["--inject-fault", str(inject_fault)]

    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout + res.stderr

    # Parse instructions and cycles
    instr_count = 0
    cycles = 0
    for line in out.splitlines():
        if "instructions verified in lockstep!" in line:
            parts = line.split()
            try:
                idx = parts.index("instructions")
                instr_count = int(parts[idx - 1])
            except (ValueError, IndexError):
                pass
            if "(Cycles:" in parts:
                try:
                    c_idx = parts.index("(Cycles:")
                    cycles = int(parts[c_idx + 1].rstrip(")"))
                except (ValueError, IndexError):
                    pass

    passed = (res.returncode == 0)
    return passed, instr_count, cycles, out


def run_cocotb_cosim(
    elf_path: Optional[Path],
    hex_path: Path,
    trace_path: Optional[Path] = None,
    inject_fault: Optional[int] = None
) -> Tuple[bool, int, int, str]:
    """Runs test in Cocotb lockstep co-simulation."""
    env = os.environ.copy()
    env["ENABLE_COSIM"] = "1"
    if elf_path and elf_path.exists():
        env["PROG_ELF"] = str(elf_path)
    else:
        env["PROG_HEX"] = str(hex_path)

    if trace_path:
        env["COSIM_TRACE"] = str(trace_path)
    if inject_fault is not None:
        env["COSIM_INJECT_FAULT"] = str(inject_fault)

    cmd = [sys.executable, str(PROJ_ROOT / "tb" / "top" / "run_top.py")]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = res.stdout + res.stderr

    instr_count = 0
    passed = (res.returncode == 0)
    for line in out.splitlines():
        if "instructions verified in lockstep!" in line:
            parts = line.split()
            try:
                idx = parts.index("instructions")
                instr_count = int(parts[idx - 1])
            except (ValueError, IndexError):
                pass

    return passed, instr_count, 0, out


def main():
    parser = argparse.ArgumentParser(
        description="RV32I Lockstep Co-Simulation & Golden Reference Model Runner"
    )
    parser.add_argument(
        "--sim",
        choices=["verilator", "cocotb", "both"],
        default="verilator",
        help="Simulation flow (default: verilator for ultra-fast C++ lockstep co-sim)"
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        help="Run specific test by name (e.g. 'add-01', 'lw-align-01', 'coverage_closure')"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run full 38-test regression suite"
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Export Spike/Whisper compatible commit log traces into sim/cosim/"
    )
    parser.add_argument(
        "--inject-fault",
        type=int,
        default=None,
        help="Inject intentional architectural corruption at cycle N to verify divergence detection"
    )
    args = parser.parse_args()

    COSIM_DIR.mkdir(parents=True, exist_ok=True)
    all_tests = find_available_tests()

    if not all_tests:
        print("[ERROR] No test hex files found in sim/coverage_build/.")
        sys.exit(1)

    if args.test:
        selected = [t for t in all_tests if t[0] == args.test or args.test in t[0]]
        if not selected:
            print(f"[ERROR] Test '{args.test}' not found. Available tests:")
            for t in all_tests:
                print(f"  - {t[0]}")
            sys.exit(1)
    else:
        selected = all_tests

    print("\n" + "=" * 80)
    print("      [*] RV32I LOCKSTEP CO-SIMULATION / GOLDEN REFERENCE MODEL [*]")
    print("=" * 80)
    print(f"  Simulator:     {args.sim.upper()}")
    print(f"  Test Count:    {len(selected)}")
    print(f"  Trace Export:  {'ENABLED (sim/cosim/*.log)' if args.trace else 'DISABLED'}")
    if args.inject_fault is not None:
        print(f"  Fault Inject:  ENABLED at cycle {args.inject_fault} (Testing Divergence Halt)")
    print("=" * 80)

    total_passed = 0
    total_failed = 0
    total_instructions = 0

    print(f"\n{'#':<4} {'Test Name':<24} {'Simulator':<12} {'Verified Instr':<16} {'Cycles':<10} {'Status'}")
    print("-" * 75)

    for idx, (name, hex_p, elf_p) in enumerate(selected, 1):
        tohost = get_tohost_address(elf_p) if elf_p else 0x4000
        trace_file = COSIM_DIR / f"{name}_trace.log" if args.trace else None

        # 1. Verilator Co-Sim
        if args.sim in ["verilator", "both"]:
            v_pass, v_instr, v_cyc, v_out = run_verilator_cosim(
                hex_p,
                tohost,
                trace_file,
                args.inject_fault
            )
            total_instructions += v_instr
            if v_pass:
                total_passed += 1
                status_str = "PASS [MATCH]"
            else:
                total_failed += 1
                status_str = "DIVERGENCE / FAIL"

            print(f"{idx:<4} {name:<24} {'Verilator':<12} {v_instr:<16} {v_cyc:<10} {status_str}")
            if not v_pass and (args.test or args.inject_fault is not None):
                print(v_out)

        # 2. Cocotb Co-Sim
        if args.sim in ["cocotb", "both"]:
            c_trace = COSIM_DIR / f"{name}_cocotb_trace.log" if args.trace else None
            c_pass, c_instr, c_cyc, c_out = run_cocotb_cosim(
                elf_p,
                hex_p,
                c_trace,
                args.inject_fault
            )
            total_instructions += c_instr
            if c_pass:
                total_passed += 1
                status_str = "PASS [MATCH]"
            else:
                total_failed += 1
                status_str = "DIVERGENCE / FAIL"

            print(f"{idx:<4} {name:<24} {'Cocotb':<12} {c_instr:<16} {'N/A':<10} {status_str}")
            if not c_pass and (args.test or args.inject_fault is not None):
                print(c_out)

    print("-" * 75)
    print(f"\n[SUMMARY]")
    print(f"  Total Runs:                 {total_passed + total_failed}")
    print(f"  Passed (100% Lockstep):     {total_passed}")
    print(f"  Failed / Diverged:          {total_failed}")
    print(f"  Total Verified Instrs:      {total_instructions:,}")

    if total_failed == 0:
        print("\n[SUCCESS] ALL TESTS MATCHED GOLDEN MODEL IN STRICT LOCKSTEP CO-SIMULATION!\n")
        sys.exit(0)
    else:
        print(f"\n[FAILURE] REGRESSION FAILED: {total_failed} run(s) diverged or timed out.\n")
        sys.exit(3 if args.inject_fault is not None else 1)


if __name__ == "__main__":
    main()
