# setup_venv.ps1
# Create a Python virtual environment and install dependencies.

$ErrorActionPreference = "Stop"

$venvPath = "venv"
$requirementsPath = "requirements.txt"
$pipExe = ".\$venvPath\Scripts\pip.exe"

# 1. Find Python executable
$pythonExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $pythonExe = "py" }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pythonExe = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonExe = "python3" }

if (-not $pythonExe) {
    $fallback = Get-ChildItem -Path "$env:LOCALAPPDATA\Programs\Python" -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName

    if ($fallback) {
        $pythonExe = $fallback
        Write-Host "Using Python found at: $pythonExe" -ForegroundColor Yellow
    } else {
        Write-Host "Python launcher not found. Install Python or add it to PATH." -ForegroundColor Red
        exit 1
    }
}

# 2. Check if venv does NOT exist (Fresh setup)
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at '$venvPath'..." -ForegroundColor Cyan
    & $pythonExe -m venv $venvPath
    
    Write-Host "Activating virtual environment..."
    & ".\$venvPath\Scripts\Activate.ps1"
    
    Write-Host "Upgrading pip..."
    & ".\$venvPath\Scripts\python.exe" -m pip install --upgrade pip

    if (-not (Test-Path $requirementsPath)) {
        Write-Host "Creating missing requirements.txt file..." -ForegroundColor Yellow
        New-Item -Path "." -Name $requirementsPath -ItemType "file" | Out-Null
    }

    Write-Host "Installing packages from '$requirementsPath'..." -ForegroundColor Green
    & $pipExe install -r $requirementsPath
    
    Write-Host "Fresh setup complete!" -ForegroundColor Green
} 
# 3. If venv ALREADY exists, install dependencies
else {
    Write-Host "Virtual environment already exists." -ForegroundColor Cyan
    
    if (-not (Test-Path $requirementsPath)) {
        Write-Host "Creating missing requirements.txt file..." -ForegroundColor Yellow
        New-Item -Path "." -Name $requirementsPath -ItemType "file" | Out-Null
    }

    Write-Host "Installing packages from '$requirementsPath'..." -ForegroundColor Green
    & $pipExe install -r $requirementsPath
}

# 4. Activate the environment for the current terminal session
Write-Host "Activating session environment..."
& ".\$venvPath\Scripts\Activate.ps1"
