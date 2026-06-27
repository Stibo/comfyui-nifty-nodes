from comfy.samplers import KSampler
from comfy_api.latest import io
from ..core.core import load_files

NODE_CATEGORY = "nifty/selectors"


# Diffusion model selector
class NiftyDiffusionModelSelector(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        files = load_files(
            ("unet", "diffusion_models"),
            (".safetensors", ".gguf", ".pt", ".pth", ".bin"),
            "[no models found]",
        )

        return io.Schema(
            node_id="NiftyDiffusionModelSelector",
            display_name="Diffusion Model Selector",
            category=NODE_CATEGORY,
            search_aliases=[
                "diffusion model selector",
                "model selector",
                "select model",
                "pick model",
                "model picker",
                "unet selector",
            ],
            inputs=[
                io.Combo.Input(
                    "model_name",
                    options=files,
                    tooltip="Select a diffusion model (.safetensors, .gguf, .pt, .pth, .bin) from the unet / diffusion_models folder.",
                ),
            ],
            outputs=[
                io.AnyType.Output(id="model"),
                io.Boolean.Output(
                    id="is_gguf",
                    tooltip="True if the selected model is a GGUF quantized file. Useful for routing to a GGUF-compatible loader.",
                ),
            ],
        )

    @classmethod
    def execute(cls, model_name) -> io.NodeOutput:
        return io.NodeOutput(
            model_name,
            model_name.lower().endswith(".gguf"),
        )


# Clip selector
class NiftyClipSelector(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        files = load_files(
            ("clip", "text_encoders"),
            (".safetensors", ".gguf", ".pt", ".pth", ".bin"),
            "[no models found]",
        )

        return io.Schema(
            node_id="NiftyClipSelector",
            display_name="CLIP Selector",
            category=NODE_CATEGORY,
            search_aliases=[
                "clip selector",
                "text encoder selector",
                "select clip",
                "pick clip",
                "clip picker",
            ],
            inputs=[
                io.Combo.Input(
                    "clip_name",
                    options=files,
                    tooltip="Select a CLIP / text encoder model from the clip / text_encoders folder.",
                ),
            ],
            outputs=[
                io.AnyType.Output(id="clip"),
                io.Boolean.Output(
                    id="is_gguf",
                    tooltip="True if the selected model is a GGUF quantized file. Useful for routing to a GGUF-compatible loader.",
                ),
            ],
        )

    @classmethod
    def execute(cls, clip_name) -> io.NodeOutput:
        return io.NodeOutput(
            clip_name,
            clip_name.lower().endswith(".gguf"),
        )


# Clip Type selector
class NiftyClipTypeSelector(io.ComfyNode):
    clip_types = [
        "stable_diffusion",
        "stable_cascade",
        "sd3",
        "stable_audio",
        "mochi",
        "ltxv",
        "pixart",
        "cosmos",
        "lumina2",
        "wan",
        "hidream",
        "chroma",
        "ace",
        "omnigen2",
        "qwen_image",
        "hunyuan_image",
        "flux2",
        "ovis",
        "longcat_image",
    ]

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyClipTypeSelector",
            display_name="CLIP Type Selector",
            category=NODE_CATEGORY,
            search_aliases=["clip type selector", "clip type", "clip"],
            inputs=[
                io.Combo.Input(
                    "type",
                    options=cls.clip_types,
                    tooltip="Select a clip type to pass as a string to a CLIP loader.",
                ),
            ],
            outputs=[
                io.AnyType.Output(id="type"),
            ],
        )

    @classmethod
    def execute(cls, type) -> io.NodeOutput:
        return io.NodeOutput(type)


# Sampler selector
class NiftySamplerSelector(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftySamplerSelector",
            display_name="Sampler Selector",
            category=NODE_CATEGORY,
            search_aliases=[
                "sampler selector",
                "select sampler",
                "pick sampler",
                "sampler picker",
                "ksampler selector",
            ],
            inputs=[
                io.Combo.Input(
                    "sampler_name",
                    options=KSampler.SAMPLERS,
                    tooltip="Select a sampler to pass as a string to a KSampler node.",
                ),
            ],
            outputs=[
                io.AnyType.Output(id="sampler"),
            ],
        )

    @classmethod
    def execute(cls, sampler_name) -> io.NodeOutput:
        return io.NodeOutput(sampler_name)


# Scheduler selector
class NiftySchedulerSelector(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftySchedulerSelector",
            display_name="Scheduler Selector",
            category=NODE_CATEGORY,
            search_aliases=[
                "scheduler selector",
                "select scheduler",
                "pick scheduler",
                "scheduler picker",
            ],
            inputs=[
                io.Combo.Input(
                    "scheduler",
                    options=KSampler.SCHEDULERS,
                    tooltip="Select a scheduler to pass as a string to a KSampler node.",
                ),
            ],
            outputs=[
                io.AnyType.Output(id="scheduler"),
            ],
        )

    @classmethod
    def execute(cls, scheduler) -> io.NodeOutput:
        return io.NodeOutput(scheduler)


SELECTOR_CLASSES = {
    "NiftyDiffusionModelSelector": NiftyDiffusionModelSelector,
    "NiftyClipSelector": NiftyClipSelector,
    "NiftyClipTypeSelector": NiftyClipTypeSelector,
    "NiftySamplerSelector": NiftySamplerSelector,
    "NiftySchedulerSelector": NiftySchedulerSelector,
}
