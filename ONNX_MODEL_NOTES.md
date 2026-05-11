# ONNX Model Notes

Howard VOX uses a native Android ONNX vocal separator. The app expects the model file to be present locally before Android build/runtime use.

## Required Model Path

```text
android/app/src/main/assets/models/UVR_MDXNET_Main.onnx
```

## Current Local Model

- Filename: `UVR_MDXNET_Main.onnx`
- Size: `59,074,342 bytes` / about `57 MB`
- SHA-256: `811cb24095d865763752310848b7ec86aeede0626cb05749ab35350e46897000`
- Model identity: UVR MDX-NET vocal separation model prepared for Howard VOX under the stable asset name `UVR_MDXNET_Main.onnx`.

## Repository Storage Decision

This model is not committed as a normal Git blob. It is larger than the project threshold for normal GitHub storage, and `git lfs` is not installed in the current build environment.

Current strategy: external/manual model placement.

The `.gitignore` excludes:

```text
android/app/src/main/assets/models/*.onnx
```

## Manual Placement Instructions

On a fresh clone, place the model at the required path before building the Android APK:

```bash
mkdir -p android/app/src/main/assets/models
cp /path/to/UVR_MDXNET_Main.onnx android/app/src/main/assets/models/UVR_MDXNET_Main.onnx
sha256sum android/app/src/main/assets/models/UVR_MDXNET_Main.onnx
```

The checksum should match:

```text
811cb24095d865763752310848b7ec86aeede0626cb05749ab35350e46897000
```

If Git LFS becomes available later, the preferred repository-managed approach is:

```bash
git lfs track "android/app/src/main/assets/models/*.onnx"
git add .gitattributes android/app/src/main/assets/models/UVR_MDXNET_Main.onnx
```

Do not commit the ONNX file through normal Git.
