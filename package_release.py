"""Create clean Release folder structure for distribution."""

import os
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT_DIR, "dist", "Luxious")
RELEASE_DIR = os.path.join(ROOT_DIR, "release", "Luxious")

def main():
    exe_source = os.path.join(DIST_DIR, "Luxious.exe")
    if not os.path.isfile(exe_source):
        raise SystemExit("Build Luxious.spec on Windows before packaging a Windows release.")
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
        f.write("LUXIOUS - REAL-ROOM ILLUMINANCE SURVEY & ANALYSIS\n")
        f.write("=" * 65 + "\n\n")
        f.write("HOW TO LAUNCH:\n")
        f.write("Double-click 'Luxious.exe' to start the application.\n\n")
        f.write("Extract the entire ZIP first. Keep Luxious.exe and the _internal folder together.\n")
        f.write("Python does not need to be installed. This is an unsigned preview build.\n\n")
        f.write("KEY FEATURES:\n")
        f.write("1. Create room and define survey grid (by count or target spacing).\n")
        f.write("2. Serpentine walking traversal order for physical walkthroughs.\n")
        f.write("3. Dedicated Survey Mode bar: type lux reading, press Enter to advance.\n")
        f.write("4. Live Photometric KPIs: E_avg, E_min, E_max, Uniformity U_0, Std Dev.\n")
        f.write("5. Scientific 2D False-Colour Heatmaps & Isolux Contours.\n")
        f.write("6. Comparison with Target Illuminance.\n")
        f.write("7. Non-destructive spatial outlier awareness.\n")
        f.write("8. Excel and CSV tables (open and save) and a multi-page PDF report.\n")
        f.write("9. Comparison with another Luxious project, Excel or CSV file, with light depreciation.\n")
        f.write("10. English, Romanian and German; the last language used is remembered.\n\n")
        f.write("Start with New survey, Open survey, Resume, or the explicitly labeled Practice survey.\n")

    print("Release folder successfully prepared at:", RELEASE_DIR)
    exe_path = os.path.join(RELEASE_DIR, "Luxious.exe")
    print("Executable location:", exe_path)
    archive = shutil.make_archive(
        os.path.join(os.path.dirname(RELEASE_DIR), "Luxious-windows-x64"),
        "zip", root_dir=os.path.dirname(RELEASE_DIR), base_dir="Luxious",
    )
    print("Portable Windows archive:", archive)

if __name__ == "__main__":
    main()
