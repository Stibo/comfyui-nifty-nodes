import json
from comfy_api.latest import io

NODE_CATEGORY = "nifty/bundle"
BUNDLE_MAX_SLOTS = 32


# Get bundle value
def get_bundle_value(data, key_path):
    current = data
    for key in key_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


# Set bundle value
def set_bundle_value(data, key_path, value):
    current = data
    keys = key_path.split(".")

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        if not isinstance(current[key], dict):
            return
        current = current[key]

    if isinstance(current, dict):
        current[keys[-1]] = value


# Bundle Pack
class NiftyBundlePack(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBundlePack",
            display_name="Bundle Pack",
            category=NODE_CATEGORY,
            search_aliases=[
                "bundle pack",
                "pack bundle",
                "create bundle",
                "bundle create",
                "group values",
                "bundle merge",
            ],
            inputs=[
                io.Custom("BUNDLE").Input(
                    "bundle",
                    optional=True,
                    tooltip="Optional existing bundle to merge into. New values will be added or overwrite keys with the same name.",
                ),
                *[
                    io.AnyType.Input(
                        f"value{i+1}",
                        optional=True,
                        tooltip="Value to pack into the bundle. Rename the slot label to set the key name.",
                    )
                    for i in range(BUNDLE_MAX_SLOTS)
                ],
                io.Int.Input(
                    "count",
                    default=1,
                    min=1,
                    max=BUNDLE_MAX_SLOTS,
                    step=1,
                    socketless=True,
                    tooltip="Number of value slots to show (1–32).",
                ),
                io.Boolean.Input(
                    "hide_links",
                    default=False,
                    socketless=True,
                    tooltip="Hide the connection wires going into this node to reduce visual clutter.",
                ),
                io.String.Input("_slot_names", default="[]", socketless=True),
            ],
            outputs=[
                io.Custom("BUNDLE").Output(id="bundle"),
            ],
        )

    @classmethod
    def execute(
        cls,
        bundle=None,
        count=1,
        hide_links=False,
        _slot_names="[]",
        **kwargs,
    ) -> io.NodeOutput:
        try:
            slot_names = json.loads(_slot_names or "{}")
        except Exception:
            slot_names = {}

        result = dict(bundle) if isinstance(bundle, dict) else {}

        for i in range(min(int(count), BUNDLE_MAX_SLOTS)):
            key = f"value{i+1}"
            value = kwargs.get(key)
            if value is None:
                continue

            label = slot_names.get(key, key)
            set_bundle_value(result, label, value)

        return io.NodeOutput(result)


# Bundle Unpack
class NiftyBundleUnpack(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBundleUnpack",
            display_name="Bundle Unpack",
            category=NODE_CATEGORY,
            search_aliases=[
                "bundle unpack",
                "unpack bundle",
                "extract bundle",
                "bundle extract",
                "bundle split",
                "bundle values",
            ],
            inputs=[
                io.Custom("BUNDLE").Input("bundle", tooltip="The bundle to unpack."),
                io.Int.Input(
                    "count",
                    default=1,
                    min=1,
                    max=BUNDLE_MAX_SLOTS,
                    step=1,
                    socketless=True,
                    tooltip="Number of value outputs to show (1–32). The slot labels must match the keys used when packing.",
                ),
                io.Boolean.Input(
                    "hide_links",
                    default=False,
                    socketless=True,
                    tooltip="Hide the connection wires going out of this node to reduce visual clutter.",
                ),
                io.String.Input("_slot_names", default="[]", socketless=True),
            ],
            outputs=[
                io.Custom("BUNDLE").Output(id="bundle"),
                *[io.AnyType.Output(id=f"value{i+1}") for i in range(BUNDLE_MAX_SLOTS)],
            ],
        )

    @classmethod
    def execute(
        cls,
        bundle,
        count=1,
        hide_links=False,
        _slot_names="[]",
    ) -> io.NodeOutput:
        try:
            slot_names = json.loads(_slot_names or "{}")
        except Exception:
            slot_names = {}

        ordered_slots = list(slot_names.values())
        outputs = [bundle]

        for i in range(BUNDLE_MAX_SLOTS):
            if i < int(count) and i < len(ordered_slots):
                outputs.append(get_bundle_value(bundle, ordered_slots[i]))
            else:
                outputs.append(None)

        return io.NodeOutput(*outputs)


# Bundle Get
class NiftyBundleGet(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBundleGet",
            display_name="Bundle Get",
            category=NODE_CATEGORY,
            search_aliases=[
                "bundle get",
                "get bundle value",
                "bundle read",
                "bundle access",
                "bundle key",
            ],
            inputs=[
                io.Custom("BUNDLE").Input("bundle", tooltip="The bundle to read from."),
                io.String.Input(
                    "key",
                    default="value1",
                    tooltip="Key to read from the bundle. Use dot notation for nested keys, e.g. 'settings.width'.",
                ),
            ],
            outputs=[
                io.AnyType.Output(id="value"),
            ],
        )

    @classmethod
    def execute(cls, bundle, key) -> io.NodeOutput:
        return io.NodeOutput(
            get_bundle_value(bundle, key),
        )


# Bundle Set
class NiftyBundleSet(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBundleSet",
            display_name="Bundle Set",
            category=NODE_CATEGORY,
            search_aliases=[
                "bundle set",
                "set bundle value",
                "bundle write",
                "bundle update",
                "bundle key",
            ],
            inputs=[
                io.Custom("BUNDLE").Input(
                    "bundle",
                    tooltip="The bundle to update. A new copy is returned — the original is not modified.",
                ),
                io.String.Input(
                    "key",
                    default="value1",
                    tooltip="Key to write in the bundle. Use dot notation for nested keys, e.g. 'settings.width'.",
                ),
                io.AnyType.Input("value", tooltip="Value to store at the given key."),
            ],
            outputs=[
                io.Custom("BUNDLE").Output(id="bundle"),
            ],
        )

    @classmethod
    def execute(cls, bundle, key, value) -> io.NodeOutput:
        result = dict(bundle) if isinstance(bundle, dict) else {}
        set_bundle_value(result, key, value)
        return io.NodeOutput(result)


BUNDLE_CLASSES = {
    "NiftyBundlePack": NiftyBundlePack,
    "NiftyBundleUnpack": NiftyBundleUnpack,
    "NiftyBundleGet": NiftyBundleGet,
    "NiftyBundleSet": NiftyBundleSet,
}
