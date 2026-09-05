
import argparse
import sys
import os

from .assembler import Assembler, to_hex_file, to_annotated_hex, to_binary_listing

def main():
    parser = argparse.ArgumentParser(
        description='RV32I Assembler - Assemble RISC-V RV32I assembly into hex files'
    )
    parser.add_argument('input', help='Input assembly file (.s or .asm)')
    parser.add_argument('-o', '--output', help='Output hex file (default: input with .hex extension)')
    parser.add_argument('-a', '--annotated', action='store_true',
                        help='Add address annotations as comments in the hex file')
    parser.add_argument('-l', '--listing', action='store_true',
                        help='Print a binary listing to stdout')
    parser.add_argument('-b', '--base', type=lambda x: int(x, 0), default=0,
                        help='Base address for the program (default: 0)')

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base_name = os.path.splitext(args.input)[0]
        output_path = base_name + '.hex'

    # Read input
    try:
        with open(args.input, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    # Assemble
    asm = Assembler(args.base)
    words = asm.assemble(source)

    if asm.errors:
        print(f"\nAssembly FAILED with {len(asm.errors)} error(s):", file=sys.stderr)
        for err in asm.errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    if not words:
        print("Warning: No instructions generated.", file=sys.stderr)
        sys.exit(0)

    # Generate output
    if args.annotated:
        hex_content = to_annotated_hex(words, args.base)
    else:
        hex_content = to_hex_file(words, args.base)

    with open(output_path, 'w') as f:
        f.write(hex_content)

    print(f"Assembled {len(words)} words ({len(words) * 4} bytes)")
    print(f"Output: {output_path}")

    # Print listing if requested
    if args.listing:
        print("\n--- Binary Listing ---")
        print(to_binary_listing(words, args.base))

if __name__ == '__main__':
    main()
