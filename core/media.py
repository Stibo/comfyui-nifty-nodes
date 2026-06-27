import math
import os
import comfy.utils
import folder_paths
import imageio_ffmpeg
import node_helpers
import numpy as np
import torch
from . import core as nifty_core
from torch.nn import functional as F
from PIL import Image, ImageOps, ImageSequence
from comfy_api.latest import io, ComfyAPI

API = ComfyAPI()
IMAGE_TYPES = {".png", ".pjp", ".jfif", ".jpe", ".pjpeg", ".jpeg", ".jpg", ".webp"}
ANIMATION_TYPES = {".gif", ".apng", ".webp", ".avif"}
VIDEO_TYPES = {".mp4", ".m4v", ".mkv", ".webm"}
ALL_MEDIA_TYPES = IMAGE_TYPES | ANIMATION_TYPES | VIDEO_TYPES

RESIZE_TYPES = [
    "scale dimensions",
    "scale by multiplier",
    "scale longer dimension",
    "scale shorter dimension",
    "scale width",
    "scale height",
    "scale total pixels",
    "make divisible by",
]

SCALE_METHODS = [
    "nearest-exact",
    "bilinear",
    "area",
    "bicubic",
    "lanczos",
    "bilinear (antialias)",
    "bicubic (antialias)",
    "mitchell-netravali",
    "nvidia-rtx-vsr",
]

RESIZE_DIR_COMBO = [
    io.DynamicCombo.Option(
        key="any",
        inputs=[
            io.Combo.Input("scale_method_up", options=SCALE_METHODS, default="lanczos"),
            io.Combo.Input("scale_method_down", options=SCALE_METHODS, default="area"),
        ],
    ),
    io.DynamicCombo.Option(
        key="upscale",
        inputs=[
            io.Combo.Input("scale_method_up", options=SCALE_METHODS, default="lanczos"),
        ],
    ),
    io.DynamicCombo.Option(
        key="downscale",
        inputs=[
            io.Combo.Input("scale_method_down", options=SCALE_METHODS, default="area"),
        ],
    ),
]

RESIZE_TYPES_GENERAL_INPUTS = [
    io.Int.Input(
        "divisible_by",
        default=1,
        min=1,
        max=256,
        step=1,
        tooltip="Make sure the dimensions are divisible by this value. 1 = off, 16 = WAN",
    ),
    io.DynamicCombo.Input("scale_dir", options=RESIZE_DIR_COMBO),
    # io.Combo.Input("scale_dir", options=["any", "upscale", "downscale"], default="any"),
    # io.Combo.Input("scale_method", options=SCALE_METHODS, default="area"),
]

RESIZE_TYPES_COMBO = [
    io.DynamicCombo.Option(
        key="scale dimensions",
        inputs=[
            io.Int.Input("width", default=512, min=0, max=nifty_core.MAX_RESOLUTION),
            io.Int.Input("height", default=512, min=0, max=nifty_core.MAX_RESOLUTION),
            io.Combo.Input(
                "crop",
                options=["disabled", "center"],
                default="center",
                tooltip="How to handle aspect ratio mismatch: 'disabled' stretches to fit, 'center' crops to maintain aspect ratio.",
            ),
            *RESIZE_TYPES_GENERAL_INPUTS,
        ],
    ),
    io.DynamicCombo.Option(
        key="scale by multiplier",
        inputs=[
            io.Float.Input("multiplier", default=1.0, min=0.01, max=8.0, step=0.01),
            *RESIZE_TYPES_GENERAL_INPUTS,
        ],
    ),
    io.DynamicCombo.Option(
        key="scale longer dimension",
        inputs=[
            io.Int.Input(
                "longer_size",
                default=512,
                min=0,
                max=nifty_core.MAX_RESOLUTION,
            ),
            *RESIZE_TYPES_GENERAL_INPUTS,
        ],
    ),
    io.DynamicCombo.Option(
        key="scale shorter dimension",
        inputs=[
            io.Int.Input(
                "shorter_size", default=512, min=0, max=nifty_core.MAX_RESOLUTION
            ),
            *RESIZE_TYPES_GENERAL_INPUTS,
        ],
    ),
    io.DynamicCombo.Option(
        key="scale width",
        inputs=[
            io.Int.Input("width", default=512, min=0, max=nifty_core.MAX_RESOLUTION),
            *RESIZE_TYPES_GENERAL_INPUTS,
        ],
    ),
    io.DynamicCombo.Option(
        key="scale height",
        inputs=[
            io.Int.Input("height", default=512, min=0, max=nifty_core.MAX_RESOLUTION),
            *RESIZE_TYPES_GENERAL_INPUTS,
        ],
    ),
    io.DynamicCombo.Option(
        key="scale total pixels",
        inputs=[
            io.Float.Input("megapixels", default=1.0, min=0.01, max=16.0, step=0.01),
            *RESIZE_TYPES_GENERAL_INPUTS,
        ],
    ),
    io.DynamicCombo.Option(key="make divisible by", inputs=RESIZE_TYPES_GENERAL_INPUTS),
]

RESIZE_TYPES_COMBO_OPTIONAL = [
    io.DynamicCombo.Option(key="off", inputs=[]),
    *RESIZE_TYPES_COMBO,
]


def np_to_tensor(arr):
    return torch.from_numpy(np.array(arr, dtype=np.float32) / 255.0)


def empty_audio():
    return {"waveform": torch.zeros(1, 2, 0), "sample_rate": 44100}


def list_media_files(types):
    input_dir = folder_paths.get_input_directory()
    files = [
        f
        for f in os.listdir(input_dir)
        if os.path.isfile(os.path.join(input_dir, f))
        and os.path.splitext(f)[1].lower() in types
    ]

    files = sorted(files)

    return files


def sniff_file(path):
    with Image.open(path) as img:
        fmt = img.format
        animated = getattr(img, "is_animated", False)
        return fmt, animated


def snap_nearest_multiple(v, multiple):
    if multiple <= 1:
        return v
    snapped = (v // multiple) * multiple
    return snapped if snapped > 0 else v


def upscale_image(images, target_w, target_h, method):
    def mitchell_kernel(x):
        x = x.abs()
        B = 1 / 3
        C = 1 / 3
        x2 = x * x
        x3 = x2 * x
        w = torch.zeros_like(x)

        m1 = x < 1
        m2 = (x >= 1) & (x < 2)

        w[m1] = (
            ((12 - 9 * B - 6 * C) * x3[m1])
            + ((-18 + 12 * B + 6 * C) * x2[m1])
            + (6 - 2 * B)
        ) / 6

        w[m2] = (
            ((-B - 6 * C) * x3[m2])
            + ((6 * B + 30 * C) * x2[m2])
            + ((-12 * B - 48 * C) * x[m2])
            + (8 * B + 24 * C)
        ) / 6

        return w

    if method == "nvidia-rtx-vsr":
        try:
            import nvvfx  # type: ignore
        except ImportError:
            raise ImportError(
                "nvidia-rtx-vsr requires the 'nvidia-vfx' Python package and an NVIDIA RTX GPU. "
                "Install with: pip install nvidia-vfx"
            )

        out_w = max(8, round(target_w / 8) * 8)
        out_h = max(8, round(target_h / 8) * 8)
        ctx = nvvfx.VideoSuperRes(nvvfx.effects.QualityLevel.ULTRA)

        with ctx as sr:
            sr.output_width = out_w
            sr.output_height = out_h
            sr.load()

            frames_chw = images.movedim(-1, 1).cuda().contiguous()
            out_frames = []
            for i in range(frames_chw.shape[0]):
                dlpack_out = sr.run(frames_chw[i]).image
                out_frames.append(torch.from_dlpack(dlpack_out))

        return torch.stack(out_frames, dim=0).movedim(1, -1).cpu()

    if method == "mitchell-netravali":
        x = images.movedim(-1, 1).float()
        B, C, H, W = x.shape

        def make_idx_weights(in_size, out_size, device, dtype):
            scale = out_size / in_size
            positions = (
                torch.arange(out_size, device=device, dtype=dtype) + 0.5
            ) / scale - 0.5
            base = torch.floor(positions).to(torch.long)
            offsets = torch.tensor([-1, 0, 1, 2], device=device, dtype=torch.long)
            idx = base[:, None] + offsets[None, :] + 2

            if scale < 1:
                dist = (
                    positions[:, None] - (base[:, None] + offsets[None, :]).to(dtype)
                ) * scale
                weights = mitchell_kernel(dist) * scale
            else:
                dist = positions[:, None] - (base[:, None] + offsets[None, :]).to(dtype)
                weights = mitchell_kernel(dist)

            weights = weights / weights.sum(dim=-1, keepdim=True).clamp_min(1e-8)
            idx = idx.clamp(0, in_size + 3)
            return idx, weights

        if W != target_w:
            x = F.pad(x, (2, 2, 0, 0), mode="replicate")
            idx, weights = make_idx_weights(W, target_w, x.device, x.dtype)
            x = x.index_select(3, idx.reshape(-1)).view(B, C, H, target_w, 4)
            x = (x * weights.view(1, 1, 1, target_w, 4)).sum(dim=-1)

        if H != target_h:
            x = F.pad(x, (0, 0, 2, 2), mode="replicate")
            idx, weights = make_idx_weights(H, target_h, x.device, x.dtype)
            x = x.index_select(2, idx.reshape(-1)).view(B, C, target_h, 4, x.shape[-1])
            x = (x * weights.view(1, 1, target_h, 4, 1)).sum(dim=-2)

        return x.movedim(1, -1).to(images.device, dtype=images.dtype)

    if method in ("bilinear (antialias)", "bicubic (antialias)"):
        mode = "bilinear" if "bilinear" in method else "bicubic"
        t = images.movedim(-1, 1)
        t = torch.nn.functional.interpolate(
            t, size=(target_h, target_w), mode=mode, align_corners=False, antialias=True
        )
        return t.movedim(1, -1)

    t = images.movedim(-1, 1)
    t = comfy.utils.common_upscale(t, target_w, target_h, method, "disabled")
    return t.movedim(1, -1)


async def resize_images(images, resize):
    def pack_result(result):
        if result is None or result.shape[0] == 0:
            return {
                "images": result,
                "width": 0,
                "height": 0,
                "batch_size": 0,
            }

        return {
            "images": result,
            "width": int(result.shape[2]),
            "height": int(result.shape[1]),
            "batch_size": int(result.shape[0]),
        }

    def snap_result(result):
        if divisible_by <= 1 or result is None or result.shape[0] == 0:
            return result

        if result.dim() == 3:
            h = snap_nearest_multiple(int(result.shape[1]), divisible_by)
            w = snap_nearest_multiple(int(result.shape[2]), divisible_by)
            if h == result.shape[1] and w == result.shape[2]:
                return result
            y = max(0, (int(result.shape[1]) - h) // 2)
            x = max(0, (int(result.shape[2]) - w) // 2)
            return result[:, y : y + h, x : x + w]

        h = snap_nearest_multiple(int(result.shape[1]), divisible_by)
        w = snap_nearest_multiple(int(result.shape[2]), divisible_by)
        if h == result.shape[1] and w == result.shape[2]:
            return result
        y = max(0, (int(result.shape[1]) - h) // 2)
        x = max(0, (int(result.shape[2]) - w) // 2)
        return result[:, y : y + h, x : x + w, :]

    source_images = images
    mode = resize.get("resize", "off")

    if mode == "off" or source_images is None or source_images.shape[0] == 0:
        return pack_result(source_images)

    width = resize.get("width", 512)
    height = resize.get("height", 512)
    longer_size = resize.get("longer_size", 512)
    shorter_size = resize.get("shorter_size", 512)
    multiplier = resize.get("multiplier", 1.0)
    megapixels = resize.get("megapixels", 1.0)
    crop = resize.get("crop", "center")
    divisible_by = resize.get("divisible_by", 1)
    scale_dir = resize.get("scale_dir", "any")

    if isinstance(scale_dir, dict):
        scale_dir_mode = scale_dir.get("scale_dir", "any")
        scale_method_up = scale_dir.get("scale_method_up", "lanczos")
        scale_method_down = scale_dir.get("scale_method_down", "area")
    else:
        scale_dir_mode = scale_dir
        scale_method_up = resize.get(
            "scale_method_up", resize.get("scale_method", "lanczos")
        )
        scale_method_down = resize.get(
            "scale_method_down", resize.get("scale_method", "area")
        )

    is_mask = source_images.dim() == 3
    images = source_images.unsqueeze(-1) if is_mask else source_images

    B, orig_H, orig_W, _ = images.shape
    skip_dir_check = False

    if mode == "scale by multiplier":
        target_w = max(1, round(orig_W * multiplier))
        target_h = max(1, round(orig_H * multiplier))
        skip_dir_check = True

    elif mode == "make divisible by":
        target_w = orig_W
        target_h = orig_H
        skip_dir_check = True

    elif mode == "scale longer dimension":
        if orig_H >= orig_W:
            target_h = longer_size
            target_w = max(1, round(orig_W * longer_size / orig_H))
        else:
            target_w = longer_size
            target_h = max(1, round(orig_H * longer_size / orig_W))

    elif mode == "scale shorter dimension":
        if orig_H <= orig_W:
            target_h = shorter_size
            target_w = max(1, round(orig_W * shorter_size / orig_H))
        else:
            target_w = shorter_size
            target_h = max(1, round(orig_H * shorter_size / orig_W))

    elif mode == "scale dimensions":
        if width == 0 and height == 0:
            return pack_result(source_images)

        if crop != "disabled" and width > 0 and height > 0:
            scale = max(width / orig_W, height / orig_H)
            target_w = max(1, round(orig_W * scale))
            target_h = max(1, round(orig_H * scale))
        else:
            target_w = width if width > 0 else max(1, round(orig_W * height / orig_H))
            target_h = height if height > 0 else max(1, round(orig_H * width / orig_W))

    elif mode == "scale width":
        target_w = width
        target_h = max(1, round(orig_H * width / orig_W))

    elif mode == "scale height":
        target_h = height
        target_w = max(1, round(orig_W * height / orig_H))

    elif mode == "scale total pixels":
        total = megapixels * 1024 * 1024
        sc = math.sqrt(total / (orig_W * orig_H))
        target_w = max(1, round(orig_W * sc))
        target_h = max(1, round(orig_H * sc))

    else:
        return pack_result(source_images)

    # global divisible_by snapping
    if divisible_by > 1:
        target_w = snap_nearest_multiple(target_w, divisible_by)
        target_h = snap_nearest_multiple(target_h, divisible_by)

    # direction constraints
    if not skip_dir_check:
        orig_px = orig_W * orig_H
        target_px = target_w * target_h

        if scale_dir_mode == "upscale" and target_px <= orig_px:
            return pack_result(snap_result(source_images))
        if scale_dir_mode == "downscale" and target_px >= orig_px:
            return pack_result(snap_result(source_images))

    if target_w == orig_W and target_h == orig_H:
        return pack_result(snap_result(source_images))

    if scale_dir_mode == "upscale":
        scale_method = scale_method_up
    elif scale_dir_mode == "downscale":
        scale_method = scale_method_down
    else:
        if target_w * target_h >= orig_W * orig_H:
            scale_method = scale_method_up
        else:
            scale_method = scale_method_down

    # resize execution
    out = []
    for i in range(B):
        result = upscale_image(images[i : i + 1], target_w, target_h, scale_method)

        if (
            mode == "scale dimensions"
            and crop != "disabled"
            and width > 0
            and height > 0
        ):
            crop_width = width
            crop_height = height

            if divisible_by > 1:
                crop_width = snap_nearest_multiple(crop_width, divisible_by)
                crop_height = snap_nearest_multiple(crop_height, divisible_by)

            y = max(0, (result.shape[1] - crop_height) // 2)
            x = max(0, (result.shape[2] - crop_width) // 2)
            result = result[:, y : y + crop_height, x : x + crop_width, :]

        out.append(result)

        await nifty_core.set_progress(
            current=i + 1,
            total=B,
        )

    result = torch.cat(out, dim=0)
    result = snap_result(result)

    if is_mask:
        result = result[..., 0]

    return pack_result(result)


def resample_frames(frames, orig_fps: float, target_fps: float):
    if target_fps <= 0 or orig_fps <= 0 or abs(target_fps - orig_fps) < 0.1:
        return frames
    step = orig_fps / target_fps
    indices = [int(i * step) for i in range(max(1, int(len(frames) / step)))]
    return [frames[min(i, len(frames) - 1)] for i in indices]


def vae_encode(vae, images):
    if vae is not None and images.shape[0] > 0:
        return vae.encode(images)

    return None


async def load_media(file: str, force_frame_rate: int = 0, image_only: bool = False):
    path = folder_paths.get_annotated_filepath(file)
    ext = os.path.splitext(file)[1].lower()

    frame_rate = 1.0

    if ext in ANIMATION_TYPES:
        is_animated = False

        if not image_only:
            try:
                with Image.open(path) as probe:
                    probe.seek(1)
                    is_animated = True
            except (EOFError, AttributeError):
                pass

        if is_animated:
            img = node_helpers.pillow(Image.open, path)
            dur_ms = img.info.get("duration", 100) or 100
            orig_fps = 1000.0 / dur_ms
            frame_rate = orig_fps

            raw = [
                np.array(node_helpers.pillow(ImageOps.exif_transpose, f).convert("RGB"))
                for f in ImageSequence.Iterator(img)
            ]

            raw = resample_frames(raw, orig_fps, force_frame_rate)

            if force_frame_rate > 0:
                frame_rate = float(force_frame_rate)

            tensors = []
            for i, f in enumerate(raw):
                tensors.append(np_to_tensor(f))
                await nifty_core.set_progress(
                    current=i + 1,
                    total=len(raw),
                )

            return {
                "images": torch.stack(tensors),
                "audio": empty_audio(),
                "is_video": True,
                "frame_rate": frame_rate,
            }

    if ext in IMAGE_TYPES:
        img = node_helpers.pillow(Image.open, path)
        img = node_helpers.pillow(ImageOps.exif_transpose, img)
        t = np_to_tensor(np.array(img.convert("RGB"))).unsqueeze(0)

        return {"images": t, "audio": empty_audio(), "is_video": False, "frame_rate": 1}

    try:
        import torchaudio

        waveform, sr = torchaudio.load(path)
        audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sr}
    except Exception:
        audio = empty_audio()

    try:
        gen = imageio_ffmpeg.read_frames(path, output_params=["-vsync", "0"])
        meta = next(gen)
        W, H = meta["size"]
        fps = float(meta.get("fps", 30.0) or 30.0)
        frame_rate = fps

        frames = []
        for raw_frame in gen:
            arr = np.frombuffer(raw_frame, dtype=np.uint8).reshape(H, W, 3)
            frames.append(arr.copy())

    except Exception as e:
        print(f"[NiftyMediaLoader] ffmpeg read error: {e}")
        return {
            "images": torch.zeros(0, 1, 1, 3),
            "audio": audio,
            "is_video": True,
            "frame_rate": 1,
        }

    if not frames:
        return {
            "images": torch.zeros(0, 1, 1, 3),
            "audio": audio,
            "is_video": True,
            "frame_rate": 1,
        }

    frames = resample_frames(frames, fps, force_frame_rate)

    if force_frame_rate > 0:
        frame_rate = float(force_frame_rate)

    tensors = []
    for i, f in enumerate(frames):
        tensors.append(np_to_tensor(f))
        await nifty_core.set_progress(
            current=i + 1,
            total=len(frames),
        )

    return {
        "images": torch.stack(tensors),
        "audio": audio,
        "is_video": True,
        "frame_rate": frame_rate,
    }
