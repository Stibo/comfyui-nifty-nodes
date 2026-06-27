import math
import torch
from ..core import core as nifty_core
from comfy_api.latest import io

NODE_CATEGORY = "nifty/latent"


# Latent from Batch
class NiftyLatentFromBatch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLatentFromBatch",
            display_name="Latent From Batch",
            category=NODE_CATEGORY,
            search_aliases=[
                "latent from batch",
                "batch slice latent",
                "get latent",
                "latent index",
                "latent select",
                "latent slice",
            ],
            inputs=[
                io.Latent.Input("samples", tooltip="Input latent batch to slice from."),
                io.Int.Input(
                    "batch_index",
                    default=0,
                    min=-4096,
                    max=4096,
                    tooltip="Positive values count from the beginning. Negative values count from the end (-1 = last latent etc.).",
                ),
                io.Int.Input(
                    "length",
                    default=0,
                    min=-4096,
                    max=4096,
                    tooltip="0 = all. Positive values read a fixed amount in the selected direction. Negative values trim from the opposite end (-1 = everything except the last latent etc.).",
                ),
            ],
            outputs=[io.Latent.Output()],
        )

    @classmethod
    def execute(
        cls, samples: io.Latent.Type, batch_index: int, length: int
    ) -> io.NodeOutput:
        s = samples["samples"]

        if len(s.shape) == 4:
            num = s.shape[0]
            slicer = lambda a, b: s[a:b]

        elif len(s.shape) == 5:
            num = s.shape[2]
            slicer = lambda a, b: s[:, :, a:b]

        else:
            return io.NodeOutput({"samples": s})

        if batch_index >= 0:
            start = batch_index

            if length > 0:
                end = start + length

            elif length == 0:
                end = num

            else:
                end = num - abs(length)

        else:
            end = num + batch_index + 1

            if length > 0:
                start = end - length

            elif length == 0:
                start = 0

            else:
                start = abs(length)

        start = max(0, min(start, num))
        end = max(0, min(end, num))

        if end < start:
            start, end = end, start

        return io.NodeOutput({"samples": slicer(start, end)})


# Last Latent from Batch
class NiftyLastLatentFromBatch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLastLatentFromBatch",
            display_name="Last Latent From Batch",
            category=NODE_CATEGORY,
            search_aliases=[
                "last latent from batch",
                "last latent",
                "final latent",
                "tail latent",
                "last frame latent",
            ],
            inputs=[
                io.Latent.Input(
                    "samples",
                    tooltip="Input latent batch to take the last frames from.",
                ),
                io.Int.Input("length", default=1, min=1, max=4096),
            ],
            outputs=[io.Latent.Output()],
        )

    @classmethod
    def execute(cls, samples: io.Latent.Type, length: int) -> io.NodeOutput:
        s = samples["samples"]

        if len(s.shape) == 4:
            sliced = s[-length:]
        elif len(s.shape) == 5:
            sliced = s[:, :, -length:]
        else:
            sliced = s

        return io.NodeOutput({"samples": sliced})


# VAE Encode
class NiftyVAEEncode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyVAEEncode",
            display_name="VAE Encode",
            category=NODE_CATEGORY,
            search_aliases=[
                "vae encode",
                "encode latent",
                "image to latent",
                "pixels to latent",
                "vae encoder",
            ],
            inputs=[
                io.Image.Input(
                    "pixels", tooltip="Image frames to encode into latent space."
                ),
                io.Vae.Input("vae", tooltip="VAE model to use for encoding."),
                io.Int.Input(
                    "target_latents",
                    default=0,
                    min=-4096,
                    max=4096,
                    step=1,
                    tooltip="0 = encode all frames. Positive = encode only the first N latents worth of frames. Negative = encode only the last N latents worth of frames. The temporal compression factor is detected automatically.",
                ),
            ],
            outputs=[
                io.Latent.Output(),
                io.Image.Output(),
            ],
        )

    @classmethod
    def _detect_temporal_factor(cls, vae, frames) -> int:
        factor = 4
        try:
            test_count = min(9, frames.shape[0])
            if test_count >= 2:
                test_slice = frames[:test_count].contiguous()
                with torch.no_grad():
                    test_out = vae.encode(test_slice)

            if len(test_out.shape) == 5:
                L = test_out.shape[2]
                factor = (test_count - 1) // (L - 1) if L > 1 else 8
            elif len(test_out.shape) == 4:
                factor = 1
        except Exception:
            factor = 4

        return factor

    @classmethod
    async def execute(
        cls,
        pixels: io.Image.Type | None,
        vae: io.Vae.Type,
        target_latents: int,
    ) -> io.NodeOutput:
        if pixels is None:
            return io.NodeOutput(None, None)

        frames = pixels[..., :3]

        if target_latents != 0:
            temporal_factor = cls._detect_temporal_factor(vae, frames)
            num_frames = frames.shape[0]
            n = (abs(target_latents) - 1) * temporal_factor + 1
            n = max(1, min(n, num_frames))
            frames = frames[:n] if target_latents > 0 else frames[-n:]

        latent_samples = vae.encode(frames.contiguous())

        return io.NodeOutput({"samples": latent_samples}, pixels)


# Normalize Video Latent Start
class NiftyNormalizeVideoLatentStart(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyNormalizeVideoLatentStart",
            display_name="Normalize Video Latent Start",
            category=NODE_CATEGORY,
            description="Normalizes the initial frames of a video latent to match the mean and standard deviation of subsequent reference frames. Helps reduce differences between the starting frames and the rest of the video.",
            search_aliases=[
                "normalize video latent",
                "latent start normalize",
                "video latent fix",
                "latent normalization",
                "video start fix",
            ],
            inputs=[
                io.Latent.Input(
                    "latent",
                    tooltip="Video latent to normalise. Must be a 5D latent (video). Passed through unchanged if only 1 frame.",
                ),
                io.Boolean.Input(
                    "enabled",
                    default=True,
                    tooltip="When disabled, the latent is passed through unchanged.",
                ),
                io.Int.Input(
                    "start_frame_count",
                    default=4,
                    min=1,
                    max=nifty_core.MAX_RESOLUTION,
                    step=1,
                    tooltip="Number of latent frames to normalize, counted from the start.",
                ),
                io.Int.Input(
                    "reference_frame_count",
                    default=5,
                    min=1,
                    max=nifty_core.MAX_RESOLUTION,
                    step=1,
                    tooltip="Number of latent frames immediately after the start frames to use as the normalization reference.",
                ),
            ],
            outputs=[io.Latent.Output()],
        )

    @staticmethod
    def adaptive_mean_std_normalization(
        source,
        reference,
        clump_mean_low=0.3,
        clump_mean_high=0.35,
        clump_std_low=0.35,
        clump_std_high=0.5,
    ):
        source_mean = source.mean(dim=(1, 3, 4), keepdim=True)
        source_std = source.std(dim=(1, 3, 4), keepdim=True)

        reference_mean = torch.clamp(
            reference.mean(),
            source_mean - clump_mean_low,
            source_mean + clump_mean_high,
        )
        reference_std = torch.clamp(
            reference.std(), source_std - clump_std_low, source_std + clump_std_high
        )

        normalized = (source - source_mean) / (source_std + 1e-8)
        normalized = normalized * reference_std + reference_mean

        return normalized

    @classmethod
    def execute(
        cls,
        latent: io.Latent.Type,
        enabled: bool,
        start_frame_count: int,
        reference_frame_count: int,
    ) -> io.NodeOutput:
        if not enabled or latent["samples"].shape[2] <= 1:
            return io.NodeOutput(latent)

        s = latent.copy()
        samples = latent["samples"].clone()

        first_frames = samples[:, :, :start_frame_count]
        reference_frames_data = samples[
            :,
            :,
            start_frame_count : start_frame_count
            + min(reference_frame_count, samples.shape[2] - 1),
        ]
        normalized_first_frames = cls.adaptive_mean_std_normalization(
            first_frames, reference_frames_data
        )

        samples[:, :, :start_frame_count] = normalized_first_frames
        s["samples"] = samples
        return io.NodeOutput(s)


LATENT_CLASSES = {
    "NiftyLatentFromBatch": NiftyLatentFromBatch,
    "NiftyLastLatentFromBatch": NiftyLastLatentFromBatch,
    "NiftyVAEEncode": NiftyVAEEncode,
    "NiftyNormalizeVideoLatentStart": NiftyNormalizeVideoLatentStart,
}
