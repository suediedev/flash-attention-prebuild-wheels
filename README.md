# flash-attention pre-build wheels

This repository provides wheels for the pre-build [flash-attention](https://github.com/Dao-AILab/flash-attention).  

Since building flash-attention takes a **very long time** and is resource-intensive, 
I also build and provide combinations of CUDA and PyTorch that are not officially distributed.

The building Github Actions Workflow can be found [here](./.github/workflows/build.yml).

The built packages are available on the [release page](https://github.com/mjun0812/flash-attention-prebuild-wheels/releases).


## Install

```bash
pip install https://github.com/mjun0812/flash-attention-prebuild-wheels/releases/download/v0.0.0/flash_attn-2.6.3+cu124torch2.5-cp312-cp312-linux_x86_64.whl
```

## Packages

```bash
flash_attn-[FLASH_ATTN_VERSION]+cu[CUDA_VERSION]torch[TORCH_VERSION]-cp[PYTHON_VERSION]-cp[PYTHON_VERSION]-linux_x86_64.whl

# example: flash_attn=v2.6.3, CUDA=12.4.1, torch=2.5.1, Python=3.12
flash_attn-2.6.3+cu124torch2.5-cp312-cp312-linux_x86_64.whl
```

### v0.0.0

[Release](https://github.com/mjun0812/flash-attention-prebuild-wheels/releases/tag/v0.0.0)

|flash-attention|Python|PyTorch|CUDA|
|-|-|-|-|
|2.4.3, 2.5.6, 2.5.9, 2.6.3|3.11, 3.12|2.0.1, 2.1.2, 2.2.2, 2.3.1, 2.4.1, 2.5.0|11.8.0, 12.1.1, 12.4.1|
