# Pass every argument through unchanged; argparse in the Python script handles
# both long options (for example --prefix) and short options (for example -p).
$BlenderExe = "D:\software\blender-4.4.0-candidate\blender.exe"
$PythonScript = Join-Path $PSScriptRoot "create_eye_plane_driver.py"

& $BlenderExe --background --python $PythonScript -- $args
exit $LASTEXITCODE
