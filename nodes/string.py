import os
import hashlib
import folder_paths
from server import PromptServer
from aiohttp import web
from comfy_api.latest import io

NODE_CATEGORY = "nifty/string"


# String split
class NiftyStringSplit(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyStringSplit",
            display_name="String Split",
            category=NODE_CATEGORY,
            search_aliases=[
                "string split",
                "split string",
                "text split",
                "split text",
                "explode string",
            ],
            inputs=[
                io.String.Input(
                    "string", force_input=True, tooltip="The string to split."
                ),
                io.String.Input(
                    "delimiter",
                    default="\\n",
                    tooltip="Character or string to split on. Use \\n for newline, \\t for tab.",
                ),
                io.Boolean.Input(
                    "trim",
                    default=False,
                    tooltip="Trim leading and trailing whitespace from each part after splitting.",
                ),
            ],
            outputs=[
                io.String.Output(id="list"),
            ],
        )

    @classmethod
    def execute(cls, string, delimiter, trim) -> io.NodeOutput:
        delimiter = delimiter.replace("\\n", "\n").replace("\\t", "\t")
        parts = string.split(delimiter)

        if trim:
            parts = [p.strip() for p in parts]

        return io.NodeOutput(parts)


# String join
class NiftyStringJoin(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyStringJoin",
            display_name="String Join",
            category=NODE_CATEGORY,
            search_aliases=[
                "string join",
                "join string",
                "text join",
                "join text",
                "implode string",
                "string concat",
            ],
            inputs=[
                io.String.Input(
                    "list", force_input=True, tooltip="List of strings to join."
                ),
                io.String.Input(
                    "delimiter",
                    default="\\n",
                    tooltip="Character or string to insert between each list item. Use \\n for newline, \\t for tab.",
                ),
            ],
            outputs=[
                io.String.Output(id="string"),
            ],
        )

    @classmethod
    def execute(cls, list, delimiter) -> io.NodeOutput:
        delimiter = delimiter.replace("\\n", "\n").replace("\\t", "\t")
        return io.NodeOutput(delimiter.join(str(s) for s in list))


# Any to String
class NiftyAnyToString(io.ComfyNode):
    MAX_SLOTS = 16

    @classmethod
    def define_schema(cls) -> io.Schema:
        autogrow_template = io.Autogrow.TemplateNames(
            input=io.AnyType.Input(
                "input", optional=True, tooltip="Value to convert to string."
            ),
            names=[f"value{i+1}" for i in range(cls.MAX_SLOTS)],
            min=1,
        )

        return io.Schema(
            node_id="NiftyAnyToString",
            display_name="Any To String",
            category=NODE_CATEGORY,
            search_aliases=[
                "any to string",
                "convert to string",
                "to string",
                "stringify",
                "value to string",
                "format string",
            ],
            inputs=[
                io.Autogrow.Input(
                    "values",
                    template=autogrow_template,
                    optional=True,
                ),
                io.DynamicCombo.Input(
                    "mode",
                    options=[
                        io.DynamicCombo.Option(
                            key="delimiter",
                            inputs=[
                                io.String.Input(
                                    "delimiter",
                                    default="-",
                                    tooltip="String inserted between each converted value.",
                                ),
                            ],
                        ),
                        io.DynamicCombo.Option(
                            key="pattern",
                            inputs=[
                                io.String.Input(
                                    "pattern",
                                    default="$1",
                                    tooltip="Template string with positional placeholders. $1 = first value, $2 = second value, etc. Example: '$1_$2' with inputs 'hello' and 'world' produces 'hello_world'.",
                                ),
                            ],
                        ),
                    ],
                    tooltip="'delimiter' joins all values with a separator. 'pattern' places values into a template string using $1, $2, ... placeholders.",
                ),
            ],
            outputs=[
                io.String.Output(id="string"),
            ],
        )

    @classmethod
    def execute(cls, mode, values) -> io.NodeOutput:
        def to_str(v):
            if v is None:
                return "none"
            if isinstance(v, bool):
                return "true" if v else "false"
            return str(v)

        selected_mode = mode.get("mode")
        delimiter = mode.get("delimiter", "-")
        pattern = mode.get("pattern", "$1")

        str_values = {k: to_str(v) for k, v in values.items()}

        if selected_mode == "delimiter":
            return io.NodeOutput(delimiter.join(str_values.values()))
        else:
            result = pattern
            for k, v in str_values.items():
                if k.startswith("value"):
                    result = result.replace(f"${k[5:]}", v)
            return io.NodeOutput(result)


# Dynamic Prompt
def generate_dynamic_prompt(template: str, seed: int) -> str:
    try:
        from dynamicprompts.generators import RandomPromptGenerator
        from dynamicprompts.wildcards import WildcardManager
    except ImportError:
        return template

    wildcard_dir = os.path.join(
        folder_paths.get_user_directory(), "default", "wildcards"
    )

    hash_seed = int(
        hashlib.sha256(f"{template}::_{seed}_".encode("utf-8")).hexdigest(), 16
    ) % (2**32 - 1)

    try:
        wm = WildcardManager(wildcard_dir)
        generator = RandomPromptGenerator(
            wildcard_manager=wm, unlink_seed_from_prompt=False
        )
        results = generator.generate(template, num_prompts=1, seeds=hash_seed)
        return str(results[0]) if results else template
    except Exception as e:
        print(f"[NiftyDynamicPrompt] Error: {e}")
        return template


@PromptServer.instance.routes.post("/nifty/get_dynamic_prompt")
async def api_get_dynamic_prompt(request):
    data = await request.json()
    template = data.get("template", "")
    seed = data.get("seed", 0)
    prompt = generate_dynamic_prompt(template, seed)
    return web.json_response({"prompt": prompt})


class NiftyDynamicPrompt(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyDynamicPrompt",
            display_name="Nifty Dynamic Prompt",
            category=NODE_CATEGORY,
            description="Generates dynamic prompts using wildcard files and random variation syntax, with support for deterministic fixed seeds.",
            search_aliases=[
                "wildcard",
                "prompt",
                "dynamic",
                "dynamic prompt",
                "random prompt",
                "random",
                "deterministic",
            ],
            inputs=[
                io.String.Input("prompt", multiline=True, socketless=True),
                io.String.Input("template", multiline=True, socketless=True),
                io.Boolean.Input("enabled", default=True),
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=1 << 50,
                    control_after_generate=False,
                ),
                io.Custom("NIFTY_DYNAMIC_PROMPT_ACTIONS").Input("prompt_actions"),
            ],
            outputs=[
                io.String.Output(id="prompt"),
                io.String.Output(id="template"),
                io.Int.Output(id="seed"),
            ],
        )

    @classmethod
    def execute(
        cls, prompt: str, template: str, enabled: bool, seed: int, **kwargs
    ) -> io.NodeOutput:
        if not enabled:
            return io.NodeOutput(prompt, template, seed)

        final_prompt = (
            prompt if prompt.strip() else generate_dynamic_prompt(template, seed)
        )

        return io.NodeOutput(final_prompt, template, seed)


STRING_CLASSES = {
    "NiftyStringSplit": NiftyStringSplit,
    "NiftyStringJoin": NiftyStringJoin,
    "NiftyAnyToString": NiftyAnyToString,
    "NiftyDynamicPrompt": NiftyDynamicPrompt,
}
