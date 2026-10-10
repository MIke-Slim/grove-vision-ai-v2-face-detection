$ErrorActionPreference = 'Stop'
$faceRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Split-Path -Parent $faceRoot
$pythonPath = Join-Path $faceRoot '.vela-venv/Scripts/python.exe'
& $pythonPath (Join-Path $PSScriptRoot 'prepare_firmware.py')
if ($LASTEXITCODE -ne 0) { throw 'Firmware preparation failed.' }
$gitCommand = Get-Command git -ErrorAction Stop
$gitRoot = Split-Path -Parent (Split-Path -Parent $gitCommand.Source)
$gitRuntime = Join-Path $gitRoot 'mingw64/bin'
if (-not (Test-Path -LiteralPath (Join-Path $gitRuntime 'libintl-8.dll'))) {
    throw 'Install Git for Windows with mingw64/bin/libintl-8.dll available.'
}

# Short paths are needed by the Windows compiler and SDK build commands.
$existing = subst | Where-Object { $_ -like 'T:*' }
$created = $false
if ($existing) {
    $target = ($existing -split '=>',2)[1].Trim()
    if ($target.TrimEnd('\') -ne $projectRoot.TrimEnd('\')) {
        throw 'T: is already assigned to another directory. Choose another free drive.'
    }
} else {
    subst T: $projectRoot
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the workspace drive mapping.' }
    $created = $true
}
$oldPath = $env:PATH
try {
    $env:PATH = 'T:\face_detection\tc\bin;T:\face_detection\toolchains\mingw64\bin;' + $gitRuntime + ';' + $oldPath
    & T:/face_detection/toolchains/mingw64/bin/mingw32-make.exe -C T:/face_detection/sdk/EPII_CM55M_APP_S -j8 APP_TYPE=tflm_yolov8_face OUT_DIR_ROOT=.. GNU_TOOLPATH=T:/face_detection/tc/bin V=0 *> (Join-Path $faceRoot 'logs/build-face.log')
    if ($LASTEXITCODE -ne 0) { throw 'Firmware compilation failed; see logs/build-face.log.' }
    Copy-Item -LiteralPath T:/face_detection/sdk/obj_epii_evb_icv30_bdv10/gnu_epii_evb_WLCSP65/EPII_CM55M_gnu_epii_evb_WLCSP65_s.elf -Destination T:/face_detection/sdk/we2_image_gen_local/input_case1_secboot/ -Force
    Push-Location T:/face_detection/sdk/we2_image_gen_local
    try {
        & ./we2_local_image_gen.exe project_case1_blp_wlcsp.json *> (Join-Path $faceRoot 'logs/image-generation.log')
        if ($LASTEXITCODE -ne 0) { throw 'Firmware packaging failed.' }
    } finally { Pop-Location }
    New-Item -ItemType Directory -Force -Path (Join-Path $faceRoot 'artifacts') | Out-Null
    Copy-Item -LiteralPath (Join-Path $faceRoot 'sdk/we2_image_gen_local/output_case1_sec_wlcsp/output.img') -Destination (Join-Path $faceRoot 'artifacts/v2-face-rebuilt.img') -Force
    & $pythonPath (Join-Path $PSScriptRoot 'record_manifest.py') *> (Join-Path $faceRoot 'logs/artifact-manifest.log')
    if ($LASTEXITCODE -ne 0) { throw 'Artifact manifest generation failed.' }
    Get-Item (Join-Path $faceRoot 'sdk/we2_image_gen_local/output_case1_sec_wlcsp/output.img') | Select-Object FullName,Length
} finally {
    $env:PATH = $oldPath
    if ($created) { subst T: /D }
}
