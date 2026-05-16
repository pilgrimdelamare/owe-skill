"""
OWE export_import.py — Backup e ripristino del vault
Usage:
  python export_import.py --export   # Crea owe-backup.zip sul Desktop
  python export_import.py --import   # Ripristina da owe-backup.zip sul Desktop
"""
import sys, shutil, zipfile
from pathlib import Path
from datetime import date

OWE_DIR    = Path.home() / ".owe"
DESKTOP    = Path.home() / "Desktop"
BACKUP_ZIP = DESKTOP / "owe-backup.zip"


def cmd_export():
    if not OWE_DIR.exists():
        print("Errore: ~/.owe/ non trovato. Nulla da esportare.")
        sys.exit(1)

    if BACKUP_ZIP.exists():
        confirm = input(f"owe-backup.zip esiste gia' sul Desktop. Sovrascrivere? [s/N] ").strip().lower()
        if confirm != 's':
            print("Operazione annullata.")
            return

    print(f"Creazione backup in: {BACKUP_ZIP}")
    with zipfile.ZipFile(BACKUP_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in OWE_DIR.rglob('*'):
            if f.is_file():
                zf.write(f, f.relative_to(OWE_DIR.parent))

    size_mb = BACKUP_ZIP.stat().st_size / (1024 * 1024)
    print(f"Backup completato: {BACKUP_ZIP} ({size_mb:.1f} MB)")


def cmd_import():
    if not BACKUP_ZIP.exists():
        print(f"Errore: {BACKUP_ZIP} non trovato sul Desktop.")
        sys.exit(1)

    if OWE_DIR.exists():
        bak = OWE_DIR.parent / ".owe.bak"
        confirm = input(f"Questo sovrascrivera' ~/.owe/. Un backup sara' salvato in ~/.owe.bak/. Continuare? [s/N] ").strip().lower()
        if confirm != 's':
            print("Operazione annullata.")
            return
        if bak.exists():
            shutil.rmtree(bak)
        shutil.copytree(OWE_DIR, bak)
        shutil.rmtree(OWE_DIR)
        print(f"Backup corrente salvato in: {bak}")

    print(f"Ripristino da: {BACKUP_ZIP}")
    with zipfile.ZipFile(BACKUP_ZIP, 'r') as zf:
        zf.extractall(OWE_DIR.parent)

    print(f"Ripristino completato: {OWE_DIR}")


def main():
    if "--export" in sys.argv:
        cmd_export()
    elif "--import" in sys.argv:
        cmd_import()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
