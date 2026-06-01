import torch
import json

import os
import folder_paths
from PIL import Image
import numpy as np

from comfy_api.latest import io, ui

NODE_CATEGORY = "nifty/utils"

# @todo: simple title correct height for click


# Subgraph Labels
class NiftySubgraphLabels(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftySubgraphLabels",
            display_name="Subgraph Labels",
            category=NODE_CATEGORY,
            is_experimental=True,
            search_aliases=[
                "subgraph labels",
                "subgraph ports",
                "group labels",
                "node group labels",
            ],
            inputs=[
                *[
                    io.String.Input(f"label{i+1}", default="", socketless=True)
                    for i in range(10)
                ]
            ],
        )

    @classmethod
    def execute(cls, **kwargs) -> io.NodeOutput:
        return io.NodeOutput()


# Simple Title
class NiftySimpleTitle(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftySimpleTitle",
            display_name="Simple Title",
            category=NODE_CATEGORY,
            is_experimental=True,
            search_aliases=[
                "simple title",
                "title node",
                "label node",
                "text label",
                "annotation",
            ],
            inputs=[
                io.String.Input("title", default="", socketless=True),
            ],
        )

    @classmethod
    def execute(cls, **kwargs) -> io.NodeOutput:
        return io.NodeOutput()


# Hidden Link
class NiftyHiddenLink(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("link")

        return io.Schema(
            node_id="NiftyHiddenLink",
            display_name="Hidden Link",
            category=NODE_CATEGORY,
            search_aliases=[
                "hidden link",
                "hide link",
                "invisible link",
                "link router",
                "wire cleaner",
            ],
            inputs=[
                io.MatchType.Input(
                    "input",
                    template=template,
                    optional=True,
                    tooltip="Any value to pass through. The connection wire into this node will be hidden to reduce visual clutter.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=template),
            ],
        )

    @classmethod
    def execute(cls, **kwargs) -> io.NodeOutput:
        return io.NodeOutput(
            next(iter(kwargs.values()), None),
        )


# Bypass By Title
class NiftyBypassByTitle(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBypassByTitle",
            display_name="Bypass By Title",
            category=NODE_CATEGORY,
            is_output_node=True,
            is_experimental=True,
            search_aliases=[
                "bypass by title",
                "bypass node",
                "skip node",
                "disable node by title",
            ],
            inputs=[
                io.Boolean.Input(
                    "bypass",
                    default=False,
                    socketless=True,
                    tooltip="When True, the nodes listed below will be bypassed.",
                ),
                io.String.Input(
                    "nodes",
                    default="",
                    multiline=True,
                    tooltip="Node titles to bypass, one per line. Matching is case-insensitive and supports partial titles.",
                ),
                io.Boolean.Input(
                    "search_from_root",
                    default=True,
                    tooltip="When True, searches for nodes in the root graph even when used inside a subgraph.",
                ),
                io.Boolean.Input(
                    "enforce",
                    default=True,
                    tooltip="When True, the bypass state is actively enforced and cannot be overridden by other nodes.",
                ),
            ],
            outputs=[
                io.Boolean.Output(id="bypass"),
            ],
        )

    @classmethod
    def execute(cls, bypass, **kwargs) -> io.NodeOutput:
        return io.NodeOutput(bypass)


# Bypass Switch By Title
class NiftyBypassSwitchByTitle(io.ComfyNode):
    MAX_SLOTS = 16

    @classmethod
    def define_schema(cls) -> io.Schema:
        inputs = [
            io.Combo.Input(
                "bypass",
                options=[f"option {i+1}" for i in range(cls.MAX_SLOTS)],
                default="option 1",
                tooltip="The currently active option. All other options' nodes will be bypassed.",
            ),
        ]

        for i in range(cls.MAX_SLOTS):
            inputs.append(
                io.String.Input(
                    f"label{i+1}",
                    default=f"option {i+1}",
                    tooltip=f"Display label for option {i+1}.",
                )
            )
            inputs.append(
                io.String.Input(
                    f"nodes{i+1}",
                    default="",
                    multiline=True,
                    tooltip=f"Node titles to bypass when option {i+1} is NOT active, one per line.",
                )
            )

        inputs.extend(
            [
                io.Int.Input(
                    "count",
                    default=1,
                    min=1,
                    max=cls.MAX_SLOTS,
                    tooltip="Number of options to show (1–16).",
                ),
                io.Boolean.Input(
                    "search_from_root",
                    default=True,
                    tooltip="When True, searches for nodes in the root graph even when used inside a subgraph.",
                ),
                io.Boolean.Input(
                    "enforce",
                    default=True,
                    tooltip="When True, the bypass state is actively enforced and cannot be overridden by other nodes.",
                ),
                io.Int.Input(
                    "selected",
                    default=1,
                    min=1,
                    max=cls.MAX_SLOTS,
                    tooltip="Index of the currently active option (1-based). Updated automatically when bypass combo changes.",
                ),
            ]
        )

        return io.Schema(
            node_id="NiftyBypassSwitchByTitle",
            display_name="Bypass Switch By Title",
            category=NODE_CATEGORY,
            is_output_node=True,
            is_experimental=True,
            search_aliases=[
                "bypass switch by title",
                "bypass switch",
                "node switch bypass",
                "option switch bypass",
                "multi bypass",
            ],
            inputs=inputs,
            outputs=[
                io.String.Output(id="bypass"),
                io.Int.Output(id="index"),
            ],
        )

    @classmethod
    def validate_inputs(cls, selected, **kwargs) -> bool | str:
        return True

    @classmethod
    def execute(cls, selected, **kwargs) -> io.NodeOutput:
        bypass = kwargs.get("bypass", f"option {selected}")
        return io.NodeOutput(bypass, selected)


# Node Chain Extender
class NiftyNodeChainExtender(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyNodeChainExtender",
            display_name="Node Chain Extender",
            category=NODE_CATEGORY,
            is_output_node=True,
            is_experimental=True,
            search_aliases=[
                "node chain extender",
                "chain extender",
                "extend chain",
                "repeat node",
                "node repeater",
            ],
            inputs=[
                io.Int.Input(
                    "count",
                    default=1,
                    min=1,
                    max=32,
                    socketless=True,
                    tooltip="Number of chained node copies to create (1–32).",
                ),
                io.String.Input(
                    "source_node",
                    default="",
                    tooltip="Title of the node to use as the template for each chain link.",
                ),
                io.String.Input(
                    "end_node",
                    default="",
                    tooltip="Title of the node that marks the end of the chain — new copies are inserted before it.",
                ),
                io.String.Input(
                    "connect_slots",
                    default="",
                    tooltip="Comma-separated list of slot name pairs to connect between adjacent chain links, e.g. 'output:input'.",
                ),
                io.Int.Input(
                    "gap",
                    default=20,
                    min=0,
                    max=2048,
                    tooltip="Pixel gap between adjacent chain nodes in the graph layout.",
                ),
                io.Boolean.Input(
                    "bypass_on_remove",
                    default=True,
                    tooltip="Bypass removed chain links instead of deleting them outright.",
                ),
                io.Boolean.Input(
                    "search_from_root",
                    default=True,
                    tooltip="When True, searches for nodes in the root graph even when used inside a subgraph.",
                ),
            ],
            outputs=[
                io.Int.Output(id="count"),
            ],
        )

    @classmethod
    def execute(cls, count=1, **kwargs) -> io.NodeOutput:
        return io.NodeOutput(int(count))


# Debug Any
class NiftyDebugAny(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyDebugAny",
            display_name="Debug Any",
            category=NODE_CATEGORY,
            is_output_node=True,
            is_experimental=True,
            search_aliases=[
                "debug any",
                "debug node",
                "inspect value",
                "print value",
                "show value",
                "log value",
            ],
            inputs=[
                io.AnyType.Input(
                    "input",
                    optional=True,
                    tooltip="Any value to inspect. Primitives are shown as-is; complex types are serialized to JSON where possible.",
                ),
            ],
        )

    @classmethod
    def execute(cls, input=None) -> io.NodeOutput:
        value = "None"

        if isinstance(input, str):
            value = input

        elif isinstance(input, (int, float, bool)):
            value = str(input)

        elif input is not None:
            try:
                value = json.dumps(input, indent=4)

            except Exception:
                try:
                    value = str(input)

                except Exception:
                    value = "None"

        return io.NodeOutput(ui=ui.PreviewText(value))


# Preview Any
class NiftyPreviewAny(io.ComfyNode):
    MAX_SLOTS = 16

    @classmethod
    def define_schema(cls):
        autogrow_template = io.Autogrow.TemplateNames(
            input=io.AnyType.Input(
                "input", optional=True, tooltip="Value to preview inline."
            ),
            names=[f"input{i+1}" for i in range(cls.MAX_SLOTS)],
            min=1,
        )

        return io.Schema(
            node_id="NiftyPreviewAny",
            display_name="Preview Any",
            category=NODE_CATEGORY,
            is_output_node=True,
            is_experimental=True,
            search_aliases=[
                "preview any",
                "preview value",
                "show value",
                "inspect value",
                "multi preview",
                "value preview",
            ],
            inputs=[
                io.Autogrow.Input(
                    "inputs",
                    template=autogrow_template,
                    optional=True,
                    tooltip="One or more values to preview inline. For image tensors, shows a summary (frame count and dimensions) rather than the image itself.",
                ),
            ],
            outputs=[],
        )

    @classmethod
    def execute(cls, inputs: io.Autogrow.Type) -> io.NodeOutput:
        values = []

        for item in inputs.values():
            if isinstance(item, torch.Tensor) and len(item.shape) == 4:
                # imgs = []
                # for tensor in item:
                #     array = 255. * tensor.cpu().numpy()
                #     img = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))

                #     name = f"debug_preview_{uuid.uuid4().hex}.png"
                #     output_dir = folder_paths.get_temp_directory()
                #     img.save(os.path.join(output_dir, name))
                #     api_path = f"/view?filename={name}&type=temp&subfolder="

                #     imgs.append(api_path)
                # values.append({"niftyimages": imgs})
                count = len(item)
                label = "image" if count == 1 else "images"
                values.append(f"{count} {label}, {item.shape[-1]}x{item.shape[-2]}")
            elif item is None:
                values.append("None")
            elif isinstance(item, (str, int, float, bool)):
                values.append(item)
            else:
                try:
                    values.append(json.dumps(item, indent=4))
                except Exception:
                    try:
                        values.append(str(item))
                    except Exception:
                        values.append("None")

        return io.NodeOutput(ui={"text": values})


UTILS_CLASSES = {
    "NiftySubgraphLabels": NiftySubgraphLabels,
    "NiftySimpleTitle": NiftySimpleTitle,
    "NiftyHiddenLink": NiftyHiddenLink,
    "NiftyBypassByTitle": NiftyBypassByTitle,
    "NiftyBypassSwitchByTitle": NiftyBypassSwitchByTitle,
    "NiftyNodeChainExtender": NiftyNodeChainExtender,
    "NiftyDebugAny": NiftyDebugAny,
    "NiftyPreviewAny": NiftyPreviewAny,
}
