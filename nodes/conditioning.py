from comfy_api.latest import io

NODE_CATEGORY = "nifty/conditioning"


# CLIP Text Encode
class NiftyCLIPTextEncode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyCLIPTextEncode",
            display_name="Nifty CLIP Text Encode (Prompt)",
            category=NODE_CATEGORY,
            description="Encodes positive and negative text prompts using a CLIP model into embeddings that can be used to guide the diffusion model towards generating specific images.",
            search_aliases=[
                "text",
                "prompt",
                "text prompt",
                "positive prompt",
                "negative prompt",
                "encode text",
                "text encoder",
                "encode prompt",
            ],
            inputs=[
                io.Clip.Input(
                    "clip", tooltip="The CLIP model used for encoding the text."
                ),
                io.String.Input(
                    "positive",
                    multiline=True,
                    dynamic_prompts=True,
                    default="",
                    optional=True,
                    tooltip="Positive text prompt to be encoded. Leave empty for unconditional embedding.",
                ),
                io.String.Input(
                    "negative",
                    multiline=True,
                    dynamic_prompts=True,
                    default="",
                    optional=True,
                    tooltip="Negative text prompt to be encoded. Leave empty for unconditional embedding.",
                ),
            ],
            outputs=[
                io.Conditioning.Output(
                    display_name="positive",
                    tooltip="Positive conditioning containing the embedded text used to guide the diffusion model.",
                ),
                io.Conditioning.Output(
                    display_name="negative",
                    tooltip="Negative conditioning containing the embedded text used to guide the diffusion model.",
                ),
            ],
        )

    @classmethod
    def execute(cls, clip, positive: str = "", negative: str = "") -> io.NodeOutput:
        if clip is None:
            raise RuntimeError(
                "ERROR: clip input is invalid: None\n\n"
                "If the clip is from a checkpoint loader node your checkpoint does not contain a valid clip or text encoder model."
            )
        pos_tokens = clip.tokenize(positive if positive and positive.strip() else "")
        neg_tokens = clip.tokenize(negative if negative and negative.strip() else "")
        return io.NodeOutput(
            clip.encode_from_tokens_scheduled(pos_tokens),
            clip.encode_from_tokens_scheduled(neg_tokens),
        )


CONDITIONING_CLASSES = {
    "NiftyCLIPTextEncode": NiftyCLIPTextEncode,
}
