param(
    [Parameter(Mandatory=$true)]
    [string]$FlashAttnVersion,
    
    [Parameter(Mandatory=$true)]
    [string]$PythonVersion,
    
    [Parameter(Mandatory=$true)]
    [string]$TorchVersion,
    
    [Parameter(Mandatory=$true)]
    [string]$CudaVersion
)

# Error handling
$ErrorActionPreference = "Stop"

Write-Host "Building Flash Attention with parameters:"
Write-Host "  Flash-Attention: $FlashAttnVersion"
Write-Host "  Python: $PythonVersion"
Write-Host "  PyTorch: $TorchVersion"
Write-Host "  CUDA: $CudaVersion"

# Set CUDA and PyTorch versions
$CudaVersionClean = $CudaVersion -replace '\.', ''
$MatrixCudaVersion = $CudaVersionClean.Substring(0, [Math]::Min(3, $CudaVersionClean.Length))
$MatrixTorchVersion = $TorchVersion -replace '^(\d+\.\d+).*', '$1'

Write-Host "Derived versions:"
Write-Host "  CUDA Matrix: $MatrixCudaVersion"
Write-Host "  Torch Matrix: $MatrixTorchVersion"

# Install PyTorch
Write-Host "Installing PyTorch $TorchVersion+cu$CudaVersion..."
$env:TORCH_CUDA_VERSION = python -c "from os import environ as env; support_cuda_versions = { '2.1': [121], '2.2': [121], '2.3': [121], '2.4': [121, 124], '2.5': [121, 124], '2.6': [124, 126], '2.7': [126, 128], '2.8': [128], }; target_cuda_versions = support_cuda_versions['$MatrixTorchVersion']; cuda_version = int('$MatrixCudaVersion'); closest_version = min(target_cuda_versions, key=lambda x: abs(x - cuda_version)); print(closest_version)"

if ($TorchVersion -like "*dev*") {
    pip install --pre torch=$TorchVersion --index-url https://download.pytorch.org/whl/nightly/cu$env:TORCH_CUDA_VERSION
} else {
    pip install --no-cache-dir torch=$TorchVersion --index-url https://download.pytorch.org/whl/cu$env:TORCH_CUDA_VERSION
}

# Verify installation
Write-Host "Verifying installations..."
nvcc --version
python -V
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import torch; print('CUDA:', torch.version.cuda)"
python -c "from torch.utils import cpp_extension; print(cpp_extension.CUDA_HOME)"

# Checkout flash-attn
Write-Host "Checking out flash-attention v$FlashAttnVersion..."
git clone https://github.com/Dao-AILab/flash-attention.git -b "v$FlashAttnVersion"

# Build wheels
Write-Host "Building wheels..."
Import-Module 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\Microsoft.VisualStudio.DevShell.dll'
Enter-VsDevShell -VsInstallPath 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools' -DevCmdArguments '-arch=x64 -host_arch=x64'
$env:DISTUTILS_USE_SDK = 1
$env:BUILD_TARGET = "cuda"
# Use environment variables from workflow if available, otherwise use defaults
if (-not $env:MAX_JOBS) { $env:MAX_JOBS = "2" }
if (-not $env:NVCC_THREADS) { $env:NVCC_THREADS = "2" }
$env:FLASH_ATTENTION_FORCE_BUILD = "TRUE"

cd flash-attention
python setup.py bdist_wheel --dist-dir=dist
$baseWheelName = Get-ChildItem -Path "dist\*.whl" | Select-Object -First 1 | ForEach-Object { $_.Name }
$wheelName = $baseWheelName.Replace($FlashAttnVersion, "$FlashAttnVersion+cu$MatrixCudaVersion" + "torch$MatrixTorchVersion")
Move-Item "dist\$baseWheelName" "dist\$wheelName"
Write-Host "Built wheel: $wheelName"