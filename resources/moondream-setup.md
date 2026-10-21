# Moondream 3.1 setup notes (ComfyUI_VLM_nodes)

Problems I hit getting Moondream 3.1 running in Comfy Desktop on Linux (RTX 3090), and how I fixed them.

## How it works

ComfyUI_VLM_nodes runs Moondream in its **own isolated Python 3.12 environment**, separate from ComfyUI's Python. The isolated environment lives at:

```
<LLavacheckpoints folder>/moondream31-runtime/.venv
```

The setup steps are in the pack's README under *"Moondream 3 / 3.1 isolated runtime"*.

## Error: "Moondream Model License 1.0 acceptance is required"

Set `license_accepted` to true on the **Moondream 3.1 Loader** node. This means you accept the [licence](https://moondream.ai/licenses/model/1.0).

## Error: "Moondream 3.1 needs its isolated runtime"

The node looks for the runtime in the **first** `LLavacheckpoints` folder ComfyUI knows about. Comfy Desktop sets up a shared models folder (e.g. `~/ComfyUI-Shared/models`), so the node looks there rather than in the install's own `models/` folder.

Fix: create the runtime in the shared models folder, link the shared path to the existing runtime, or set the `MOONDREAM_PYTHON` environment variable to the runtime's `python`.

```bash
ln -s <install>/ComfyUI/models/LLavacheckpoints/moondream31-runtime \
      ~/ComfyUI-Shared/models/LLavacheckpoints/moondream31-runtime
```

## Error: "Cannot load kernel '.../kestrel_kernels/fused_linear.so'"

The message is misleading. The real file is `libfused_linear.so`, which is there, but it can't load because it needs **CUDA 12** libraries (`libcudart.so.12`, `libcublasLt.so.12`).

Cause: a plain `pip install` now pulls a **CUDA 13** build of PyTorch, and kestrel-kernels 0.4.6 only ships CUDA 12 kernels.

Check:

```bash
ldd <runtime>/.venv/lib/python3.12/site-packages/kestrel_kernels/libfused_linear.so | grep "not found"
```

Fix: install a CUDA 12.9 PyTorch build into the **runtime** environment (not ComfyUI's):

```bash
uv pip install --python <runtime>/.venv/bin/python \
  --index-url https://download.pytorch.org/whl/cu129 \
  --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match \
  "torch==2.13.0+cu129" "nvidia-cuda-runtime-cu12==12.9.79"
```

CUDA 12.9 matters: the kernels need `cudaLibraryLoadData`, which the CUDA 12.6 runtime doesn't export.

Verify:

```bash
<runtime>/.venv/bin/python -c "import torch, kestrel_kernels.linear_ops as lo; \
x=torch.randn(4,64,dtype=torch.bfloat16,device='cuda'); w=torch.randn(32,64,dtype=torch.bfloat16,device='cuda'); \
print(lo.linear(x,w).shape)"
```

## Comfy Desktop gotcha: a second install appeared

Comfy Desktop once created a fresh, empty install (`ComfyUI (1)`) and launched it instead of the main one. It had none of my custom nodes or workflows. If nodes are suddenly missing, check which install is running.
