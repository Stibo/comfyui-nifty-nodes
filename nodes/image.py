import os
import torch
import numpy as np
import comfy.model_management as model_management
from ..core import core as nifty_core
from ..core import media as nifty_media
from torch.nn import functional as F
from torchvision.transforms import ToTensor, ToPILImage
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from comfy_api.latest import io

TO_TENSOR = ToTensor()
TO_PIL = ToPILImage()

NODE_CATEGORY = "nifty/image"


# Image from Batch
class NiftyImageFromBatch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyImageFromBatch",
            display_name="Image From Batch",
            category=NODE_CATEGORY,
            search_aliases=[
                "image from batch",
                "batch slice",
                "get image",
                "image index",
                "batch index",
                "select image",
            ],
            inputs=[
                io.Image.Input("image", tooltip="Input image batch to slice from."),
                io.Int.Input(
                    "batch_index",
                    default=0,
                    min=-4096,
                    max=4096,
                    tooltip="Start index within the batch. Positive = from the beginning, negative = from the end (-1 = last image).",
                ),
                io.Int.Input(
                    "length",
                    default=1,
                    min=-1,
                    max=4096,
                    tooltip="Number of images to take. -1 = take all from start to end of batch.",
                ),
            ],
            outputs=[io.Image.Output()],
        )

    @classmethod
    def execute(
        cls, image: io.Image.Type, batch_index: int, length: int
    ) -> io.NodeOutput:
        batch_size = image.shape[0]
        start = (
            max(0, batch_size + batch_index)
            if batch_index < 0
            else min(batch_index, batch_size)
        )

        if length == -1:
            return io.NodeOutput(
                image[start:].clone(),
            )

        end = min(start + length, batch_size)

        return io.NodeOutput(
            image[start:end].clone(),
        )


# Last Image from Batch
class NiftyLastImageFromBatch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLastImageFromBatch",
            display_name="Last Image From Batch",
            category=NODE_CATEGORY,
            search_aliases=[
                "last image from batch",
                "last image",
                "final frame",
                "last frame",
                "tail batch",
            ],
            inputs=[
                io.Image.Input(
                    "image", tooltip="Input image batch to take the last frames from."
                ),
                io.Int.Input(
                    "length",
                    default=1,
                    min=1,
                    max=4096,
                    tooltip="Number of images to take from the end of the batch.",
                ),
            ],
            outputs=[io.Image.Output()],
        )

    @classmethod
    def execute(cls, image: io.Image.Type, length: int) -> io.NodeOutput:
        return io.NodeOutput(
            image[-length:].clone(),
        )


# Merge Image Batches
class NiftyMergeImageBatches(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        overlap_input = [
            io.Int.Input(
                "overlap",
                default=0,
                min=0,
                max=4096,
                step=1,
                tooltip="Number of frames to overlap between source and new batch during blending.",
            ),
            io.Combo.Input(
                "overlap_side",
                options=["source", "new"],
                default="source",
                tooltip="Which side provides the frames for the blend region: 'source' = end of source batch, 'new' = beginning of new batch.",
            ),
        ]

        return io.Schema(
            node_id="NiftyMergeImageBatches",
            display_name="Merge Image Batches",
            category=NODE_CATEGORY,
            search_aliases=[
                "merge image batches",
                "concatenate images",
                "join batches",
                "combine images",
                "append batch",
                "image concat",
            ],
            inputs=[
                io.Image.Input(
                    "source_images",
                    optional=True,
                    tooltip="First batch — the base sequence.",
                ),
                io.Image.Input(
                    "new_images",
                    optional=True,
                    tooltip="Second batch — appended after source. Must have the same resolution as source when using any blend mode.",
                ),
                io.DynamicCombo.Input(
                    "overlap_mode",
                    options=[
                        io.DynamicCombo.Option("none", []),
                        io.DynamicCombo.Option("cut", overlap_input),
                        io.DynamicCombo.Option("linear_blend", overlap_input),
                        io.DynamicCombo.Option("ease_in_out", overlap_input),
                        io.DynamicCombo.Option("filmic_crossfade", overlap_input),
                        io.DynamicCombo.Option("perceptual_crossfade", overlap_input),
                    ],
                    tooltip="How to handle the transition between batches. 'none' = simple concatenation. 'cut' = removes overlap frames. 'linear_blend' = simple crossfade. 'ease_in_out' = smooth S-curve crossfade. 'filmic_crossfade' = gamma-correct blend. 'perceptual_crossfade' = LAB color space blend (requires kornia).",
                ),
            ],
            outputs=[io.Image.Output(id="images")],
        )

    @classmethod
    def execute(
        cls,
        overlap_mode: dict,
        source_images: io.Image.Type | None = None,
        new_images: io.Image.Type | None = None,
    ) -> io.NodeOutput:
        selected_mode = overlap_mode["overlap_mode"]
        overlap = overlap_mode.get("overlap", 0)
        overlap_side = overlap_mode.get("overlap_side", "source")

        if source_images is None and new_images is None:
            raise ValueError(
                "Merge Image Batches: at least one of source_images or new_images must be connected."
            )

        if source_images is None:
            return io.NodeOutput(
                new_images,
            )
        if new_images is None:
            return io.NodeOutput(
                source_images,
            )

        if selected_mode == "none" or overlap == 0:
            return io.NodeOutput(
                torch.cat((source_images, new_images), dim=0),
            )

        if source_images.shape[1:3] != new_images.shape[1:3]:
            raise ValueError(
                f"Merge Image Batches: source and new images must have the same resolution "
                f"({source_images.shape[1:3]} vs {new_images.shape[1:3]})."
            )

        ov = min(overlap, source_images.shape[0], new_images.shape[0])

        if overlap_side == "source":
            blend_src = source_images[-ov:]
            blend_dst = new_images[:ov]
            prefix = source_images[:-ov]
            suffix = new_images[ov:]
        else:
            blend_src = new_images[:ov]
            blend_dst = source_images[-ov:]
            prefix = source_images[:-ov]
            suffix = new_images[ov:]

        if selected_mode == "cut":
            return io.NodeOutput(
                torch.cat((source_images[:-ov], new_images), dim=0),
            )

        elif selected_mode == "linear_blend":
            alpha = torch.linspace(
                0, 1, ov + 2, device=blend_src.device, dtype=blend_src.dtype
            )[1:-1]
            alpha = alpha.view(-1, 1, 1, 1)
            blended = (1 - alpha) * blend_src + alpha * blend_dst

        elif selected_mode == "ease_in_out":
            t = torch.linspace(
                0, 1, ov + 2, device=blend_src.device, dtype=blend_src.dtype
            )[1:-1]
            eased = 3 * t * t - 2 * t * t * t
            eased = eased.view(-1, 1, 1, 1)
            blended = (1 - eased) * blend_src + eased * blend_dst

        elif selected_mode == "filmic_crossfade":
            gamma = 2.2
            alpha = torch.linspace(
                0, 1, ov + 2, device=blend_src.device, dtype=blend_src.dtype
            )[1:-1]
            alpha = alpha.view(-1, 1, 1, 1)
            lin_src = torch.pow(blend_src.clamp(min=0), gamma)
            lin_dst = torch.pow(blend_dst.clamp(min=0), gamma)
            blended = torch.pow(
                ((1 - alpha) * lin_src + alpha * lin_dst).clamp(min=0), 1.0 / gamma
            )

        elif selected_mode == "perceptual_crossfade":
            try:
                import kornia
            except ImportError:
                raise ImportError(
                    "perceptual_crossfade requires the 'kornia' Python package."
                    "Install with: pip install kornia"
                )

            alpha = torch.linspace(
                0, 1, ov + 2, device=blend_src.device, dtype=blend_src.dtype
            )[1:-1]
            alpha = alpha.view(-1, 1, 1, 1)
            src_nchw = blend_src.float().movedim(-1, 1).clamp(0, 1)
            dst_nchw = blend_dst.float().movedim(-1, 1).clamp(0, 1)
            lab_src = kornia.color.rgb_to_lab(src_nchw)
            lab_dst = kornia.color.rgb_to_lab(dst_nchw)
            blended = kornia.color.lab_to_rgb(
                (1 - alpha) * lab_src + alpha * lab_dst
            ).movedim(1, -1)

        return io.NodeOutput(
            torch.cat((prefix, blended, suffix), dim=0),
        )


# Resize Image
class NiftyResizeImage(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("input_type", [io.Image, io.Mask])

        return io.Schema(
            node_id="NiftyResizeImage",
            display_name="Resize Image",
            description="Resize an image or mask using various scaling methods.",
            category=NODE_CATEGORY,
            search_aliases=[
                "resize image",
                "scale image",
                "rescale image",
                "image resize",
                "resize mask",
                "scale mask",
                "upscale image",
                "downscale image",
            ],
            inputs=[
                io.MatchType.Input(
                    "input", template=template, tooltip="Image or mask to resize."
                ),
                io.DynamicCombo.Input(
                    "resize",
                    options=nifty_media.RESIZE_TYPES_COMBO,
                    tooltip="Resize mode. Scaling methods: 'nearest-exact' = fastest, hard edges; 'bilinear' / 'bicubic' = general purpose; 'area' = best for downscaling; 'lanczos' = best for upscaling photos; 'mitchell-netravali' = sharp upscaling with minimal ringing; 'bilinear (antialias)' / 'bicubic (antialias)' = smooth downscaling. 'nvidia-rtx-vsr' requires an NVIDIA RTX GPU and nvidia-vfx package.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="resized", template=template),
                io.Int.Output(id="width"),
                io.Int.Output(id="height"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        input: io.Image.Type | io.Mask.Type,
        resize: dict,
    ) -> io.NodeOutput:
        resized = await nifty_media.resize_images(
            images=input,
            resize=resize,
        )

        return io.NodeOutput(
            resized["images"],
            int(resized["width"]),
            int(resized["height"]),
        )


# Image Color Match
class NiftyImageColorMatch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        methods = [
            "wavelet",
            "adain",
            "reinhard_lab",
            "mkl",
            "hm",
            "reinhard",
            "mvgd",
            "hm-mvgd-hm",
            "hm-mkl-hm",
            "reinhard_lab_gpu",
        ]

        return io.Schema(
            node_id="NiftyImageColorMatch",
            display_name="Image Color Match",
            category=NODE_CATEGORY,
            search_aliases=[
                "color match",
                "image color match",
                "color transfer",
                "style color",
                "color grading",
                "color correction",
                "match colors",
            ],
            inputs=[
                io.Image.Input(
                    "image_target",
                    optional=True,
                    tooltip="The image whose colors will be adjusted to match the reference.",
                ),
                io.Image.Input(
                    "image_ref",
                    optional=True,
                    tooltip="The reference image whose color distribution is used as the target.",
                ),
                io.Boolean.Input(
                    "enabled",
                    default=True,
                    tooltip="When disabled, image_target is passed through unchanged.",
                ),
                io.Combo.Input(
                    "method",
                    options=methods,
                    default="mkl",
                    tooltip="Color transfer algorithm. 'wavelet' and 'adain' = structure-preserving, good for textures. 'reinhard_lab' = fast statistical match in LAB space. 'mkl' = accurate linear color mapping (recommended default). 'hm' = histogram matching. 'reinhard_lab_gpu' = GPU-accelerated reinhard (requires kornia). 'mvgd', 'hm-mvgd-hm', 'hm-mkl-hm' = advanced methods from color-matcher package.",
                ),
                io.Combo.Input(
                    "transfer_mode",
                    options=["all", "color", "luminance"],
                    default="all",
                    tooltip="'all' = transfer full color. 'color' = transfer only hue/chroma, keep original luminance. 'luminance' = transfer only brightness, keep original colors.",
                ),
                io.Float.Input(
                    "strength",
                    default=1.0,
                    min=0.0,
                    max=10.0,
                    step=0.05,
                    tooltip="Blend strength of the color transfer. 1.0 = full match, 0.5 = half-way blend with original, values above 1.0 exaggerate the effect.",
                ),
                io.Boolean.Input(
                    "multithread",
                    default=True,
                    tooltip="Process batch images in parallel using multiple CPU threads. Recommended for large batches.",
                ),
            ],
            outputs=[io.Image.Output()],
        )

    @staticmethod
    def _calc_mean_std(feat: torch.Tensor, eps=1e-5):
        size = feat.size()
        assert len(size) == 4
        b, c = size[:2]
        feat_var = feat.view(b, c, -1).var(dim=2) + eps
        feat_std = feat_var.sqrt().view(b, c, 1, 1)
        feat_mean = feat.view(b, c, -1).mean(dim=2).view(b, c, 1, 1)
        return feat_mean, feat_std

    @staticmethod
    def _adaptive_instance_normalization(
        content_feat: torch.Tensor, style_feat: torch.Tensor
    ):
        size = content_feat.size()
        style_mean, style_std = NiftyImageColorMatch._calc_mean_std(style_feat)
        content_mean, content_std = NiftyImageColorMatch._calc_mean_std(content_feat)
        normalized = (content_feat - content_mean.expand(size)) / content_std.expand(
            size
        )
        return normalized * style_std.expand(size) + style_mean.expand(size)

    @staticmethod
    def _wavelet_blur(image: torch.Tensor, radius: int):
        kernel_vals = [
            [0.0625, 0.125, 0.0625],
            [0.125, 0.25, 0.125],
            [0.0625, 0.125, 0.0625],
        ]
        kernel = torch.tensor(kernel_vals, dtype=image.dtype, device=image.device)
        C = image.shape[1]
        kernel = kernel[None, None].repeat(C, 1, 1, 1)
        image = F.pad(image, (radius, radius, radius, radius), mode="replicate")
        return F.conv2d(image, kernel, groups=C, dilation=radius)

    @staticmethod
    def _wavelet_decomposition(image: torch.Tensor, levels=5):
        high_freq = torch.zeros_like(image)
        low_freq = image
        for i in range(levels):
            radius = 2**i
            new_low_freq = NiftyImageColorMatch._wavelet_blur(low_freq, radius)
            high_freq += low_freq - new_low_freq
            low_freq = new_low_freq
        return high_freq, low_freq

    @staticmethod
    def _wavelet_reconstruction(content: torch.Tensor, style: torch.Tensor):
        content_high, _ = NiftyImageColorMatch._wavelet_decomposition(content)
        _, style_low = NiftyImageColorMatch._wavelet_decomposition(style)
        return content_high + style_low

    @staticmethod
    def _wavelet_color_fix(target: Image.Image, source: Image.Image) -> Image.Image:
        if source.size != target.size:
            source = source.resize(target.size, Image.LANCZOS)
        t = TO_TENSOR(target).unsqueeze(0)
        s = TO_TENSOR(source).unsqueeze(0)
        result = NiftyImageColorMatch._wavelet_reconstruction(t, s)
        return TO_PIL(result.squeeze(0).clamp(0, 1))

    @staticmethod
    def _adain_color_fix(target: Image.Image, source: Image.Image) -> Image.Image:
        if source.size != target.size:
            source = source.resize(target.size, Image.LANCZOS)
        t = TO_TENSOR(target).unsqueeze(0)
        s = TO_TENSOR(source).unsqueeze(0)
        result = NiftyImageColorMatch._adaptive_instance_normalization(t, s)
        return TO_PIL(result.squeeze(0).clamp(0, 1))

    @staticmethod
    def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
        mask = rgb > 0.04045
        linear = np.where(mask, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
        M = np.array(
            [
                [0.4124564, 0.3575761, 0.1804375],
                [0.2126729, 0.7151522, 0.0721750],
                [0.0193339, 0.1191920, 0.9503041],
            ],
            dtype=np.float32,
        )
        xyz = linear @ M.T
        xyz /= np.array([0.95047, 1.00000, 1.08883], dtype=np.float32)
        epsilon, kappa = 0.008856, 903.3
        f = np.where(xyz > epsilon, np.cbrt(xyz), (kappa * xyz + 16.0) / 116.0)
        L = 116.0 * f[:, :, 1] - 16.0
        a = 500.0 * (f[:, :, 0] - f[:, :, 1])
        b = 200.0 * (f[:, :, 1] - f[:, :, 2])
        return np.stack([L, a, b], axis=2)

    @staticmethod
    def _lab_to_rgb(lab: np.ndarray) -> np.ndarray:
        L, a, b = lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]
        fy = (L + 16.0) / 116.0
        fx = a / 500.0 + fy
        fz = fy - b / 200.0
        epsilon, kappa = 0.008856, 903.3
        xr = np.where(fx**3 > epsilon, fx**3, (116.0 * fx - 16.0) / kappa)
        yr = np.where(L > kappa * epsilon, ((L + 16.0) / 116.0) ** 3, L / kappa)
        zr = np.where(fz**3 > epsilon, fz**3, (116.0 * fz - 16.0) / kappa)
        xyz = np.stack([xr, yr, zr], axis=2) * np.array(
            [0.95047, 1.00000, 1.08883], dtype=np.float32
        )
        M_inv = np.array(
            [
                [3.2404542, -1.5371385, -0.4985314],
                [-0.9692660, 1.8760108, 0.0415560],
                [0.0556434, -0.2040259, 1.0572252],
            ],
            dtype=np.float32,
        )
        linear = np.clip(xyz @ M_inv.T, 0, None)
        srgb = np.where(
            linear > 0.0031308,
            1.055 * linear ** (1.0 / 2.4) - 0.055,
            12.92 * linear,
        )
        return np.clip(srgb, 0, 1).astype(np.float32)

    @staticmethod
    def _reinhard_lab_cpu(target: np.ndarray, source: np.ndarray) -> np.ndarray:
        if source.shape != target.shape:
            t_pil = Image.fromarray((target * 255).astype(np.uint8))
            s_pil = Image.fromarray((source * 255).astype(np.uint8))
            source = (
                np.array(s_pil.resize(t_pil.size, Image.LANCZOS)).astype(np.float32)
                / 255.0
            )
        t_lab = NiftyImageColorMatch._rgb_to_lab(target)
        s_lab = NiftyImageColorMatch._rgb_to_lab(source)
        result_lab = np.zeros_like(t_lab)
        for c in range(3):
            t_mean = t_lab[:, :, c].mean()
            t_std = t_lab[:, :, c].std() + 1e-6
            s_mean = s_lab[:, :, c].mean()
            s_std = s_lab[:, :, c].std() + 1e-6
            result_lab[:, :, c] = (t_lab[:, :, c] - t_mean) * (s_std / t_std) + s_mean
        return NiftyImageColorMatch._lab_to_rgb(result_lab)

    @staticmethod
    def _apply_transfer_mode(
        result: torch.Tensor, target: torch.Tensor, transfer_mode: str
    ) -> torch.Tensor:
        if transfer_mode == "all":
            return result
        result_np = result.cpu().numpy()
        target_np = target.cpu().numpy()
        out = np.zeros_like(result_np)
        for i in range(result_np.shape[0]):
            r_lab = NiftyImageColorMatch._rgb_to_lab(result_np[i])
            t_lab = NiftyImageColorMatch._rgb_to_lab(target_np[i])
            if transfer_mode == "color":
                merged = np.stack(
                    [t_lab[:, :, 0], r_lab[:, :, 1], r_lab[:, :, 2]], axis=2
                )
            else:
                merged = np.stack(
                    [r_lab[:, :, 0], t_lab[:, :, 1], t_lab[:, :, 2]], axis=2
                )
            out[i] = NiftyImageColorMatch._lab_to_rgb(merged)
        return torch.from_numpy(out).float()

    @classmethod
    async def execute(
        cls,
        enabled: bool,
        method: str,
        transfer_mode: str,
        strength: float,
        multithread: bool,
        image_target: io.Image.Type | None = None,
        image_ref: io.Image.Type | None = None,
    ) -> io.NodeOutput:
        if not enabled or image_target is None or image_ref is None:
            return io.NodeOutput(
                image_target,
            )

        if strength <= 0:
            return io.NodeOutput(
                image_target,
            )

        if method in ("wavelet", "adain"):
            fix_fn = (
                cls._wavelet_color_fix if method == "wavelet" else cls._adain_color_fix
            )
            batch_size = image_target.size(0)
            ref_size = image_ref.size(0)

            out = [None] * batch_size

            def process(i):
                t_pil = TO_PIL(image_target[i].permute(2, 0, 1).clamp(0, 1))
                r_pil = TO_PIL(
                    image_ref[min(i, ref_size - 1)].permute(2, 0, 1).clamp(0, 1)
                )
                result_pil = fix_fn(t_pil, r_pil)
                result = TO_TENSOR(result_pil).permute(1, 2, 0)
                if strength != 1.0:
                    result = image_target[i] + strength * (result - image_target[i])
                return result.clamp(0, 1)

            if multithread and batch_size > 1:
                max_threads = min(os.cpu_count() or 1, batch_size)
                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = {
                        executor.submit(process, i): i for i in range(batch_size)
                    }

                    done = 0
                    for future in as_completed(futures):
                        i = futures[future]
                        out[i] = future.result()

                        done += 1
                        await nifty_core.set_progress(current=done, total=batch_size)

            else:
                for i in range(batch_size):
                    out[i] = process(i)

                    await nifty_core.set_progress(current=i + 1, total=batch_size)

            result = torch.stack(out).float().clamp(0, 1)
            return io.NodeOutput(
                cls._apply_transfer_mode(result, image_target, transfer_mode)
            )

        if method == "reinhard_lab":
            batch_size = image_target.size(0)
            ref_size = image_ref.size(0)

            out = [None] * batch_size

            def process(i):
                t_np = image_target[i].detach().cpu().numpy().copy()
                r_np = image_ref[min(i, ref_size - 1)].detach().cpu().numpy().copy()
                try:
                    result = cls._reinhard_lab_cpu(t_np, r_np)
                    if strength != 1.0:
                        result = t_np + strength * (result - t_np)
                    return torch.from_numpy(np.clip(result, 0, 1)).float()
                except Exception as e:
                    print(f"[NiftyImageColorMatch] Thread {i} error: {e}")
                    return torch.from_numpy(t_np).float()

            if multithread and batch_size > 1:
                max_threads = min(os.cpu_count() or 1, batch_size)
                with ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = {
                        executor.submit(process, i): i for i in range(batch_size)
                    }

                    done = 0
                    for future in as_completed(futures):
                        i = futures[future]
                        out[i] = future.result()

                        done += 1
                        await nifty_core.set_progress(current=done, total=batch_size)

            else:
                for i in range(batch_size):
                    out[i] = process(i)

                    await nifty_core.set_progress(current=i + 1, total=batch_size)

            result = torch.stack(out).float().clamp(0, 1)
            return io.NodeOutput(
                cls._apply_transfer_mode(result, image_target, transfer_mode)
            )

        if method == "reinhard_lab_gpu":
            try:
                import kornia
            except ImportError:
                raise ImportError(
                    "reinhard_lab_gpu requires the 'kornia' Python package."
                    "Install with: pip install kornia"
                )

            device = model_management.get_torch_device()
            B, H, W, C = image_target.shape
            src_bchw = image_target.to(device).permute(0, 3, 1, 2).contiguous()
            ref_bchw = image_ref.to(device).permute(0, 3, 1, 2).contiguous()

            src_lab = kornia.color.rgb_to_lab(src_bchw)
            ref_lab = kornia.color.rgb_to_lab(ref_bchw)

            src_lab_flat = src_lab.view(B, C, -1)

            ref_size = ref_lab.shape[0]
            ref_indices = torch.arange(B, device=device).clamp(max=ref_size - 1)
            ref_lab_flat = ref_lab[ref_indices].view(B, C, -1)

            src_std, src_mean = torch.std_mean(
                src_lab_flat, dim=-1, keepdim=True, unbiased=False
            )
            ref_std, ref_mean = torch.std_mean(
                ref_lab_flat, dim=-1, keepdim=True, unbiased=False
            )

            src_std = src_std.clamp_min(1e-6)

            corrected_flat = (src_lab_flat - src_mean) * (ref_std / src_std) + ref_mean
            corrected_lab = corrected_flat.view(B, C, H, W)
            corrected_rgb = kornia.color.lab_to_rgb(corrected_lab)

            result = (1.0 - strength) * src_bchw + strength * corrected_rgb
            result = result.permute(0, 2, 3, 1).contiguous().cpu().float().clamp(0, 1)

            await nifty_core.set_progress(current=1, total=1)

            return io.NodeOutput(
                cls._apply_transfer_mode(result, image_target, transfer_mode)
            )

        try:
            from color_matcher import ColorMatcher
        except ImportError:
            raise ImportError(
                "ColorMatcher requires the 'color-matcher' package."
                "Install with: pip install color-matcher"
            )

        batch_size = image_target.size(0)
        ref_batch_size = image_ref.size(0)

        def process(i):
            cm = ColorMatcher()
            t_np = image_target[i].detach().cpu().numpy().copy()
            r_np = image_ref[min(i, ref_batch_size - 1)].detach().cpu().numpy().copy()
            try:
                result = cm.transfer(src=t_np, ref=r_np, method=method)
                if strength != 1.0:
                    result = t_np + strength * (result - t_np)
                return torch.from_numpy(result).float()
            except Exception as e:
                print(f"[NiftyImageColorMatch] Thread {i} error: {e}")
                return torch.from_numpy(t_np).float()

        out = [None] * batch_size

        if multithread and batch_size > 1:
            max_threads = min(os.cpu_count() or 1, batch_size)
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {executor.submit(process, i): i for i in range(batch_size)}

                done = 0
                for future in as_completed(futures):
                    i = futures[future]
                    out[i] = future.result()

                    done += 1
                    await nifty_core.set_progress(
                        current=done,
                        total=batch_size,
                    )

        else:
            for i in range(batch_size):
                out[i] = process(i)

                await nifty_core.set_progress(
                    current=i + 1,
                    total=batch_size,
                )

        result = torch.stack(out).float().clamp(0, 1)
        return io.NodeOutput(
            cls._apply_transfer_mode(result, image_target, transfer_mode)
        )


IMAGE_CLASSES = {
    "NiftyImageFromBatch": NiftyImageFromBatch,
    "NiftyLastImageFromBatch": NiftyLastImageFromBatch,
    "NiftyMergeImageBatches": NiftyMergeImageBatches,
    "NiftyResizeImage": NiftyResizeImage,
    "NiftyImageColorMatch": NiftyImageColorMatch,
}
