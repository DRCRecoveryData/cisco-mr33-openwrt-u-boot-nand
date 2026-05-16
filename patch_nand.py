#!/usr/bin/env python3
import os
import sys
import shutil
import argparse

# Configuration constants matching hardware block definitions
BLOCK_SIZE = 135168  # 0x21000
EXPECTED_SIZE = 138412032  # 0x8400000

# ANSI Terminal Styling Codes
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"

def print_status(message, level="info"):
    """Prints beautifully formatted terminal status messages."""
    if level == "info":
        print(f"[{CYAN}*{RESET}] {message}")
    elif level == "success":
        print(f"[{GREEN}✔{RESET}] {BOLD}{GREEN}{message}{RESET}")
    elif level == "warning":
        print(f"[{YELLOW}!{RESET}] {YELLOW}Warning: {message}{RESET}")
    elif level == "error":
        print(f"[{RED}✗{RESET}] {BOLD}{RED}Error: {message}{RESET}", file=sys.stderr)

def write_binary_section(target_file, source_file, seek_blocks):
    if not os.path.exists(source_file):
        print_status(f"Required component binary missing: '{source_file}'", "error")
        sys.exit(1)
        
    offset = BLOCK_SIZE * seek_blocks
    print_status(f"Injecting {CYAN}{source_file:<18}{RESET} at block {seek_blocks:<3} (Offset: {BOLD}{hex(offset)}{RESET})...")
    
    with open(source_file, 'rb') as sf:
        data = sf.read()
    with open(target_file, 'r+b') as tf:
        tf.seek(offset)
        tf.write(data)

def main():
    # Setup rich command line argument parser
    parser = argparse.ArgumentParser(
        description=f"{BOLD}{CYAN}Cisco Meraki MR33 – OpenWrt NAND Recovery Suite (CLI){RESET}",
        epilog="Dependencies: 'ubootmr332012.bin' and 'ubimr33.bin' must reside in the running directory."
    )
    parser.add_argument("infile", help="Path to the original raw NAND dump (.bin)")
    parser.add_argument(
        "outfile", 
        nargs="?", 
        default=None, 
        help="Path for patched output target file. If omitted, will auto-name to <input>_Patched.bin"
    )
    
    args = parser.parse_args()
    infile = args.infile
    outfile = args.outfile

    print(f"\n{BOLD}{CYAN}=== Meraki MR33 U-Boot & OpenWrt NAND Patcher ==={RESET}\n")

    # Environment Validation
    if not os.path.exists(infile):
        print_status("Source image file missing.", "error")
        sys.exit(1)

    if os.path.getsize(infile) != EXPECTED_SIZE:
        print_status(f"Source image size check failed! Got {os.path.getsize(infile)} bytes, expected {EXPECTED_SIZE}.", "error")
        print_status("Was this image dumped cleanly without its OOB (Out-Of-Band) layout data?", "warning")
        sys.exit(1)

    # Automated naming engine logic if output is omitted
    if not outfile:
        base, ext = os.path.splitext(infile)
        outfile = f"{base}_Patched{ext}"
        print_status(f"No explicit output path given. Auto-targeting: {outfile}", "warning")

    if os.path.abspath(infile) == os.path.abspath(outfile):
        print_status("Source destination matches target output. Overwriting source is restricted.", "error")
        sys.exit(1)

    if os.path.exists(outfile):
        print_status(f"Target destination file already exists: '{outfile}'. Refusing overwrite safety check.", "error")
        sys.exit(1)

    # Execution Sequence
    try:
        print_status(f"Cloning raw NAND container to base target file...")
        shutil.copyfile(infile, outfile)

        # Patching boot elements
        write_binary_section(outfile, "ubootmr332012.bin", seek_blocks=56)
        write_binary_section(outfile, "ubimr33.bin", seek_blocks=96)

        print()
        print_status("Recovery image successfully generated and structured!", "success")
        print_status(f"Output File: {BOLD}{outfile}{RESET}\n", "info")

    except Exception as e:
        print_status(f"An unexpected fault interrupted processing: {e}", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
