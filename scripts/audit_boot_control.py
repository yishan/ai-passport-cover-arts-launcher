#!/usr/bin/env python3
"""Audit a play for code that can break reset-to-Launcher compatibility.

The Launcher relies on the play staying unconfirmed (PENDING_VERIFY) so that a
reset or power-cycle rolls back to the factory Launcher. Two kinds of code break
that, and they often live in dependencies rather than in the play itself:

- BLOCKER: esp_ota_mark_app_valid_cancel_rollback() confirms the play, so a
  reset keeps booting it.
- REVIEW: esp_ota_set_boot_partition(), esp_https_ota() and
  esp_https_ota_finish() change the boot target. Fine inside
  launcher_contract; anywhere else it needs a human decision.

Two layers are checked:

1. Source: every C/C++/assembly file in the project, including components/,
   managed_components/ and any extra component directories, plus prebuilt
   .a/.o files, whose symbol names are searched as bytes.
2. Build (after `idf.py build`): the linker map's cross-reference table names
   every object that references each symbol, and the ELF symbol table shows
   whether the symbol survived into the firmware at all.

Usage:
  scripts/audit_boot_control.py PROJECT_DIR [--build-dir DIR] [--extra DIR ...]

Exit status: 0 no blocker, 1 blocker found, 2 usage error.
"""

import argparse
import re
import struct
import sys
from pathlib import Path

MARK_VALID = "esp_ota_mark_app_valid_cancel_rollback"
BOOT_CONTROL = ("esp_ota_set_boot_partition", "esp_https_ota", "esp_https_ota_finish")
SYMBOLS = (MARK_VALID,) + BOOT_CONTROL
OTA_BEGIN = "esp_ota_begin"

SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".S"}
BINARY_SUFFIXES = {".a", ".o", ".obj"}
SKIP_DIRS = {".git", "build", ".pio"}
ALLOWED_OWNER = "launcher_contract"
COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)

MARK_VALID_WHY = (
    "confirms the play as valid, so reset and power-cycle keep booting it "
    "instead of the Launcher")
BOOT_CONTROL_WHY = (
    "changes the boot target; outside launcher_contract this can make reset "
    "boot something other than the Launcher")
OTA_BEGIN_NOTE = (
    "The play has its own OTA path (esp_ota_begin). While it runs unconfirmed "
    "under the Launcher, esp_ota_begin() returns "
    "ESP_ERR_OTA_ROLLBACK_INVALID_STATE. Do not \"fix\" that by marking the "
    "play valid; the play's own OTA is outside this protocol and needs a "
    "creator decision.")


class Report:
    def __init__(self):
        self.findings = []  # (symbol, entry)
        self.notes = []

    def add(self, symbol, where, detail=""):
        entry = f"{symbol} in {where}" + (f" ({detail})" if detail else "")
        self.findings.append((symbol, entry))

    def drop_unlinked(self, linked, elf_name):
        """Demote findings for symbols the linker left out of the firmware.

        esp_ota_set_boot_partition is kept: launcher_contract links it, so its
        presence says nothing about other callers.
        """
        kept = []
        for symbol, entry in self.findings:
            if symbol != "esp_ota_set_boot_partition" and symbol not in linked:
                self.notes.append(
                    f"{entry}: not linked into {elf_name}, so no call path "
                    "survives today; it becomes a finding if a caller is added.")
            else:
                kept.append((symbol, entry))
        self.findings = kept

    @property
    def blockers(self):
        return [entry for symbol, entry in self.findings if symbol == MARK_VALID]

    @property
    def reviews(self):
        return [entry for symbol, entry in self.findings if symbol != MARK_VALID]


def is_allowed(path_text):
    """True for a source path or linker object inside the launcher_contract component."""
    return ALLOWED_OWNER in re.split(r"[/\\()]", path_text)


def iter_files(roots):
    seen = set()
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or SKIP_DIRS.intersection(path.relative_to(root).parts):
                continue
            real = path.resolve()
            if real not in seen:
                seen.add(real)
                yield root, path


def called(text, symbol):
    return re.search(r"\b" + re.escape(symbol) + r"\s*\(", text) is not None


def scan_sources(roots, report):
    has_ota_begin = False
    for root, path in iter_files(roots):
        rel = f"{root.name}/{path.relative_to(root)}"
        if path.suffix in SOURCE_SUFFIXES:
            text = COMMENT.sub("", path.read_text(encoding="utf-8", errors="replace"))
            for symbol in SYMBOLS:
                if called(text, symbol) and not (symbol != MARK_VALID and is_allowed(rel)):
                    report.add(symbol, rel, "source")
            has_ota_begin = has_ota_begin or called(text, OTA_BEGIN)
        elif path.suffix in BINARY_SUFFIXES:
            data = path.read_bytes()
            for symbol in SYMBOLS:
                if re.search(rb"(?<![A-Za-z0-9_])" + symbol.encode() + rb"(?![A-Za-z0-9_])", data) \
                        and not (symbol != MARK_VALID and is_allowed(rel)):
                    report.add(symbol, rel, "prebuilt library; symbol name present")
            has_ota_begin = has_ota_begin or OTA_BEGIN.encode() in data
    return has_ota_begin


def parse_cross_reference(map_text):
    """Return {symbol: [referencing objects]} from a GNU ld map with --cref."""
    start = map_text.find("Cross Reference Table")
    if start < 0:
        return None
    refs = {}
    current = None
    for line in map_text[start:].splitlines()[1:]:
        if not line.strip() or line.startswith("Symbol"):
            continue
        if not line[0].isspace():
            parts = line.split(None, 1)
            current = parts[0] if parts[0] in SYMBOLS or parts[0] == OTA_BEGIN else None
            if current:
                # The first file listed defines the symbol; the rest reference it.
                refs[current] = []
        elif current:
            refs[current].append(line.strip())
    return refs


def elf_defined_symbols(path):
    """Return names of defined symbols in an ELF file's .symtab."""
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise ValueError(f"{path} is not an ELF file")
    is64 = data[4] == 2
    endian = "<" if data[5] == 1 else ">"
    if is64:
        shoff, = struct.unpack_from(endian + "Q", data, 0x28)
        shentsize, shnum = struct.unpack_from(endian + "HH", data, 0x3A)
    else:
        shoff, = struct.unpack_from(endian + "I", data, 0x20)
        shentsize, shnum = struct.unpack_from(endian + "HH", data, 0x2E)

    sections = []
    for index in range(shnum):
        base = shoff + index * shentsize
        if is64:
            _, sh_type, _, _, offset, size, link, _, _, entsize = struct.unpack_from(
                endian + "IIQQQQIIQQ", data, base)
        else:
            _, sh_type, _, _, offset, size, link, _, _, entsize = struct.unpack_from(
                endian + "IIIIIIIIII", data, base)
        sections.append((sh_type, offset, size, link, entsize))

    names = set()
    for sh_type, offset, size, link, entsize in sections:
        if sh_type != 2 or entsize == 0:  # SHT_SYMTAB
            continue
        strtab_offset = sections[link][1]
        for entry in range(offset, offset + size, entsize):
            if is64:
                name_offset, _, _, shndx = struct.unpack_from(endian + "IBBH", data, entry)
            else:
                name_offset, = struct.unpack_from(endian + "I", data, entry)
                shndx, = struct.unpack_from(endian + "H", data, entry + 14)
            if shndx == 0:  # undefined
                continue
            end = data.index(b"\0", strtab_offset + name_offset)
            names.add(data[strtab_offset + name_offset:end].decode("utf-8", "replace"))
    return names


def scan_build(build_dir, report):
    """Check the linked firmware. Returns whether esp_ota_begin is linked."""
    maps = sorted(p for p in build_dir.glob("*.map") if "bootloader" not in p.name)
    elves = sorted(p for p in build_dir.glob("*.elf") if "bootloader" not in p.name)
    if not maps or not elves:
        report.notes.append(
            f"No application .map/.elf in {build_dir}; build layer skipped. "
            "Run `idf.py build` for full coverage of prebuilt dependencies.")
        return False

    refs = parse_cross_reference(maps[0].read_text(encoding="utf-8", errors="replace"))
    linked = elf_defined_symbols(elves[0])
    if refs is None:
        report.notes.append(f"{maps[0].name} has no cross-reference table; build layer skipped.")
        return False

    report.drop_unlinked(linked, elves[0].name)
    for symbol, referrers in refs.items():
        if symbol == OTA_BEGIN or symbol not in linked:
            continue
        for referrer in referrers:
            if symbol == MARK_VALID or not is_allowed(referrer):
                report.add(symbol, referrer, f"linked into {elves[0].name}")
    return OTA_BEGIN in linked


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--build-dir", type=Path,
                        help="build directory (default: PROJECT/build)")
    parser.add_argument("--extra", type=Path, action="append", default=[],
                        help="extra component directory outside the project")
    args = parser.parse_args(argv)

    project = args.project.resolve()
    if not project.is_dir():
        print(f"{project} is not a directory", file=sys.stderr)
        return 2
    for extra in args.extra:
        if not extra.is_dir():
            print(f"{extra} is not a directory", file=sys.stderr)
            return 2

    report = Report()
    ota_in_source = scan_sources([project] + [e.resolve() for e in args.extra], report)
    build_dir = (args.build_dir or project / "build").resolve()
    ota_in_build = scan_build(build_dir, report) if build_dir.is_dir() else False
    if not build_dir.is_dir():
        report.notes.append(
            f"{build_dir} does not exist; build layer skipped. "
            "Run `idf.py build` for full coverage of prebuilt dependencies.")
    if ota_in_source or ota_in_build:
        report.notes.append(OTA_BEGIN_NOTE)

    print(f"Boot-control audit: {project}")
    for title, items, why in (("BLOCKER", report.blockers, MARK_VALID_WHY),
                              ("REVIEW", report.reviews, BOOT_CONTROL_WHY)):
        for item in sorted(set(items)):
            print(f"  {title}: {item}")
        if items:
            print(f"    why: {why}")
    for note in report.notes:
        print(f"  NOTE: {note}")
    if not report.blockers and not report.reviews:
        print("  OK: no code outside launcher_contract confirms the play or changes the boot target")
    return 1 if report.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
