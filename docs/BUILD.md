# Build Windows exe

The quickest packaging path is PyInstaller.

## Inspector-only build

This works with the regular project dependencies and is enough for:

- `inspect`
- `backends list`
- `models list`
- JSON/Markdown report logic

```powershell
.\scripts\build_exe.ps1 -Clean
```

If PowerShell blocks local scripts, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 -Clean
```

The executable is created at:

```text
dist\accelscope.exe
```

Smoke test:

```powershell
.\dist\accelscope.exe --help
.\dist\accelscope.exe
.\dist\accelscope.exe inspect
.\dist\accelscope.exe backends list
.\dist\accelscope.exe models list
```

## OpenVINO runner build

For actual `run` and `compare` commands, build from a Python version supported by OpenVINO, usually
Python 3.10, 3.11, or 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,openvino]"
.\scripts\build_exe.ps1 -Clean -PythonExe .\.venv\Scripts\python.exe -IncludeOpenVINO
```

Then test:

```powershell
.\dist\accelscope.exe devices
.\dist\accelscope.exe compare .\models\model.xml --devices CPU,GPU,NPU,AUTO
```

OpenVINO packaging can require extra hidden imports or data files depending on the runtime version.
If a packaged OpenVINO runner fails, first confirm the same command works through Python, then add
the missing PyInstaller options to `scripts/build_exe.ps1`.

## OpenVINO plus Open Model Zoo tools

For `accelscope models download`, add OMZ tools:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -e ".[dev,openvino]" openvino-dev==2024.6.0
.\scripts\build_exe.ps1 -Clean -PythonExe .\.venv312\Scripts\python.exe -IncludeOpenVINO -IncludeOMZ
```
