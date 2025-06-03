# WAUR 3D Pipeline – UV Snapshot Capture Tool

---

## 📋 Overview

The UV Snapshot Capture Tool allows the WAUR team to quickly generate UV layout images (.PNG) from selected meshes without opening Maya GUI.

It uses Maya Standalone (`mayapy.exe`) to automate the process, ensuring minimal user interaction and fully batchable workflows.

---

## ⚙️ System Structure

| Module | Purpose |
|:---|:---|
| `ma_uvshot_quicktool.py` | Export selected meshes to temp FBX and launch capture process |
| `ma_uvshot_capture_standalone.py` | Initialize Standalone, import FBX, call UV capture |
| `ma_capture_uv.py` | Directly capture UV sets from each mesh into .PNG images |

---

## 📂 How It Works

1. User selects one or more meshes inside Maya.
2. Runs:

    ```python
    import ma_uvshot_quicktool
    ma_uvshot_quicktool.quick_uv_capture()
    ```

3. User selects the output folder.
4. The tool exports a temporary FBX.
5. Launches Maya Standalone (`mayapy.exe`).
6. Imports the FBX into Standalone.
7. Captures all UV sets as `.png` files.
8. Temporary FBX is deleted automatically.

---

## 🖼️ Output

- PNG files named as:

<mesh_name>_<uvset_name>.png

- Resolution: **1024x1024 px** (default, configurable)
- Format: **PNG**

Example:
pCylinder1_map1.png pCube2_UVSet2.png


---

## 🚀 Requirements

- Maya 2018 installed at default path.
- Python scripts copied to:
  
C:\Users<User>\Documents\maya\2018\scripts\


- `mayapy.exe` accessible at:

C:\Program Files\Autodesk\Maya2018\bin\mayapy.exe

---

## ⚡ Technical Notes

- FBX plugin (`fbxmaya.mll`) is loaded automatically in Standalone if missing.
- Uses pure `maya.cmds.uvSnapshot()` instead of MEL for UV capture (better compatibility).
- No extra dependencies, fully self-contained.
- Can be extended later to specify different resolutions, file formats, etc.

---

## 📣 Future Extensions (Optional)

- Support custom image resolutions via UI.
- Batch capture multiple selected objects in a single session.
- Integrate into validation workflows.

---

# ✅ Current Status

Tool is **100% functional** in WAUR Pipeline  
Ready for **artistic testing** and **batch processing**!

---

---

## ⚡ Technical Notes

- FBX plugin (`fbxmaya.mll`) is loaded automatically in Standalone if missing.
- Uses pure `maya.cmds.uvSnapshot()` instead of MEL for UV capture (better compatibility).
- No extra dependencies, fully self-contained.
- Can be extended later to specify different resolutions, file formats, etc.

---

## 📣 Future Extensions (Optional)

- Support custom image resolutions via UI.
- Batch capture multiple selected objects in a single session.
- Integrate into validation workflows.

---

# ✅ Current Status

Tool is **100% functional** in WAUR Pipeline  
Ready for **artistic testing** and **batch processing**!

---
