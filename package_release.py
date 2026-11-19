"""Create clean Release folder structure for distribution."""

import os
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT_DIR, "dist", "Lumination")
RELEASE_DIR = os.path.join(ROOT_DIR, "release", "Lumination")

def main():
    exe_source = os.path.join(DIST_DIR, "Lumination.exe")
    if not os.path.isfile(exe_source):
        raise SystemExit("Build Lumination.spec on Windows before packaging a Windows release.")
    if os.path.exists(RELEASE_DIR):
        shutil.rmtree(RELEASE_DIR)

    os.makedirs(os.path.dirname(RELEASE_DIR), exist_ok=True)
    print(f"Copying from {DIST_DIR} to {RELEASE_DIR}...")
    shutil.copytree(DIST_DIR, RELEASE_DIR)
    license_path = os.path.join(ROOT_DIR, "LICENSE")
    if os.path.isfile(license_path):
        shutil.copy2(license_path, os.path.join(RELEASE_DIR, "LICENSE"))

    # Add quickstart README in release folder
    readme_path = os.path.join(RELEASE_DIR, "README_QUICKSTART.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("=" * 65 + "\n")
        f.write("LUMINATION — REAL-ROOM ILLUMINANCE SURVEY & ANALYSIS\n")
        f.write("=" * 65 + "\n\n")
        f.write("HOW TO LAUNCH:\n")
        f.write("Double-click 'Lumination.exe' to start the application.\n\n")
        f.write("Extract the entire ZIP first. Keep Lumination.exe and the _internal folder together.\n")
        f.write("Python does not need to be installed. This is an unsigned preview build.\n\n")
        f.write("KEY FEATURES:\n")
        f.write("1. Create room and define survey grid (by count or target spacing).\n")
        f.write("2. Serpentine walking traversal order for physical walkthroughs.\n")
        f.write("3. Dedicated Survey Mode bar: type lux reading, press Enter to advance.\n")
        f.write("4. Live Photometric KPIs: E_avg, E_min, E_max, Uniformity U_0, Std Dev.\n")
        f.write("5. Scientific 2D False-Colour Heatmaps & Isolux Contours.\n")
        f.write("6. Comparison with Target Illuminance.\n")
        f.write("7. Non-destructive spatial outlier awareness.\n")
        f.write("8. Full CSV import/export and professional multi-page PDF reporting.\n\n")
        f.write("Start with New survey, Open survey, Resume, or the explicitly labeled Practice survey.\n")
        f.write("Manual lux entry is supported. Physical USB/Bluetooth capture requires a qualified meter profile.\n")
        f.write("DIALux reference data is imported as CSV expected_lux values, not native DIALux project files.\n")

    print("Release folder successfully prepared at:", RELEASE_DIR)
    exe_path = os.path.join(RELEASE_DIR, "Lumination.exe")
    print("Executable location:", exe_path)
    archive = shutil.make_archive(
        os.path.join(os.path.dirname(RELEASE_DIR), "Lumination-windows-x64"),
        "zip", root_dir=os.path.dirname(RELEASE_DIR), base_dir="Lumination",
    )
    print("Portable Windows archive:", archive)

if __name__ == "__main__":
    main()
