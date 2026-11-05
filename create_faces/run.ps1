param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $PythonArgs
)

$BlenderExe = "D:\software\blender-4.4.0-candidate\blender.exe"
$PythonScript = Join-Path $PSScriptRoot "create_eye_plane_driver.py"

& $BlenderExe --background --python $PythonScript -- @PythonArgs
exit $LASTEXITCODE
