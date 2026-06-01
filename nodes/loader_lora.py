import os
import json
import folder_paths
import comfy.utils
import comfy.sd
from comfy_api.latest import io

NODE_CATEGORY = "nifty/loader"


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
                io.Clip.Input("clip", tooltip="CLIP model to apply LoRAs to."),
                io.Custom("NIFTY_LORA_LOADER").Input("loras"),
            ],
            outputs=[
                io.Model.Output(),
                io.Clip.Output(),
            ],
        )

    @classmethod
    def execute(cls, model, clip, loras) -> io.NodeOutput:
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


LOADER_LORA_CLASSES = {"NiftyLoraLoader": NiftyLoraLoader}
