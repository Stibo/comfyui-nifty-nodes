import json
import folder_paths
import comfy.utils
import comfy.sd
from comfy_api.latest import io

NODE_CATEGORY = "nifty/lora"


# Lora Loader
class NiftyLoraLoader(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLoraLoader",
            display_name="Nifty Lora Loader",
            category=NODE_CATEGORY,
            search_aliases=[
                "lora loader",
                "load lora",
                "lora stack",
                "apply lora",
                "lora list",
                "multi lora",
                "lora batch",
            ],
            inputs=[
                io.Model.Input("model", tooltip="Base model to apply LoRAs to."),
                io.Clip.Input(
                    "clip", optional=True, tooltip="CLIP model to apply LoRAs to."
                ),
                io.Custom("NIFTY_LORA_LOADER").Input("loras"),
            ],
            outputs=[
                io.Model.Output(),
                io.Clip.Output(),
            ],
        )

    @classmethod
    def execute(cls, model, loras, clip=None) -> io.NodeOutput:
        try:
            rows = json.loads(loras)
            if not isinstance(rows, list):
                rows = [rows]
        except Exception:
            rows = []

        for row in rows:
            if not row.get("enabled", False):
                continue
            lora_name = row.get("lora", "none")
            if not lora_name or lora_name == "none":
                continue
            strength = float(row.get("strength", 1.0))
            if strength == 0.0:
                continue

            lora_path = folder_paths.get_full_path("loras", lora_name)
            if lora_path is None:
                print(f"[NiftyLoraLoader] LoRA not found: {lora_name}")
                continue

            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            model, clip = comfy.sd.load_lora_for_models(
                model, clip, lora, strength, strength
            )

        return io.NodeOutput(model, clip)


# Lora Stack
class NiftyLoraStack(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLoraStack",
            display_name="Nifty Lora Stack",
            category=NODE_CATEGORY,
            search_aliases=[
                "lora selector",
                "select lora",
                "lora stack",
                "apply lora",
                "lora list",
                "multi lora",
                "lora batch",
            ],
            inputs=[
                io.Custom("NIFTY_LORA_STACK").Input("lora_stack", optional=True),
                io.Custom("NIFTY_LORA_LOADER").Input("loras"),
            ],
            outputs=[
                io.Custom("NIFTY_LORA_STACK").Output(id="lora_stack"),
            ],
        )

    @classmethod
    def execute(cls, lora_stack=None, loras=None) -> io.NodeOutput:
        try:
            rows = json.loads(loras)
            if not isinstance(rows, list):
                rows = [rows]
        except Exception:
            rows = []

        if isinstance(lora_stack, list):
            stack = list(lora_stack)
        elif lora_stack is None:
            stack = []
        else:
            stack = [lora_stack]

        for row in rows:
            if not row.get("enabled", False):
                continue
            lora_name = row.get("lora", "none")
            if not lora_name or lora_name == "none":
                continue
            strength = float(row.get("strength", 1.0))
            strength_clip = float(row.get("strength_clip", strength))
            if strength == 0.0 and strength_clip == 0.0:
                continue

            stack.append(
                {
                    "lora": lora_name,
                    "strength": strength,
                    "strength_clip": strength_clip,
                }
            )

        return io.NodeOutput(stack)


# Lora Stack Apply
class NiftyLoraStackApply(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLoraStackApply",
            display_name="Nifty Apply Lora Stack",
            category=NODE_CATEGORY,
            search_aliases=[
                "lora apply",
                "apply lora",
                "lora stack",
                "lora loader",
                "load lora",
                "lora list",
                "multi lora",
                "lora batch",
            ],
            inputs=[
                io.Custom("NIFTY_LORA_STACK").Input("lora_stack"),
                io.Model.Input("model", tooltip="Base model to apply LoRAs to."),
                io.Clip.Input(
                    "clip", optional=True, tooltip="CLIP model to apply LoRAs to."
                ),
            ],
            outputs=[
                io.Model.Output(),
                io.Clip.Output(),
            ],
        )

    @classmethod
    def execute(
        cls,
        lora_stack,
        model,
        clip=None,
    ) -> io.NodeOutput:
        if isinstance(lora_stack, list):
            rows = lora_stack
        elif lora_stack is None:
            rows = []
        else:
            try:
                rows = json.loads(lora_stack)
                if not isinstance(rows, list):
                    rows = [rows]
            except Exception:
                rows = []

        for row in rows:
            lora_name = row.get("lora", "none")
            if not lora_name or lora_name == "none":
                continue
            strength = float(row.get("strength", 1.0))
            strength_clip = float(row.get("strength_clip", strength))
            if strength == 0.0 and strength_clip == 0.0:
                continue

            lora_path = folder_paths.get_full_path("loras", lora_name)

            if lora_path is None:
                print(f"[NiftyLoraStackApply] LoRA not found: {lora_name}")
                continue

            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            model, clip = comfy.sd.load_lora_for_models(
                model, clip, lora, strength, strength_clip
            )

        return io.NodeOutput(model, clip)


LORA_CLASSES = {
    "NiftyLoraLoader": NiftyLoraLoader,
    "NiftyLoraStack": NiftyLoraStack,
    "NiftyLoraStackApply": NiftyLoraStackApply,
}
