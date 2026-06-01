import re
import sys
from comfy_execution.graph import ExecutionBlocker
from comfy_api.latest import io
from ..core import core as nifty_core

NODE_CATEGORY = "nifty/logic"


# Input Switch
class NiftyInputSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        return io.Schema(
            node_id="NiftyInputSwitch",
            display_name="Input Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "input switch",
                "if else",
                "conditional",
                "boolean switch",
                "select input",
                "switch node",
                "lazy switch",
            ],
            inputs=[
                io.MatchType.Input(
                    "on_true",
                    template=switch_template,
                    lazy=True,
                    optional=True,
                    tooltip="Value passed through when boolean is True. Only evaluated if actually selected (lazy).",
                ),
                io.MatchType.Input(
                    "on_false",
                    template=switch_template,
                    lazy=True,
                    optional=True,
                    tooltip="Value passed through when boolean is False. Only evaluated if actually selected (lazy).",
                ),
                io.Boolean.Input(
                    "boolean", tooltip="Determines which input is passed to the output."
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=switch_template),
            ],
        )

    @classmethod
    def check_lazy_status(
        cls, boolean, on_true=nifty_core.MISSING, on_false=nifty_core.MISSING
    ):
        if on_false is nifty_core.MISSING:
            return ["on_true"]
        if on_true is nifty_core.MISSING:
            return ["on_false"]

        if boolean and on_true is None:
            return ["on_true"]
        if not boolean and on_false is None:
            return ["on_false"]

        return []

    @classmethod
    def validate_inputs(
        cls, boolean, on_true=nifty_core.MISSING, on_false=nifty_core.MISSING
    ) -> bool | str:
        if on_false is nifty_core.MISSING and on_true is nifty_core.MISSING:
            return "At least one of on_true or on_false must be connected."
        return True

    @classmethod
    def execute(
        cls, boolean, on_true=nifty_core.MISSING, on_false=nifty_core.MISSING
    ) -> io.NodeOutput:
        if on_true is nifty_core.MISSING:
            return io.NodeOutput(on_false)
        if on_false is nifty_core.MISSING:
            return io.NodeOutput(on_true)
        return io.NodeOutput(on_true if boolean else on_false)


# Input Switch (Eager)
class NiftyInputSwitchEager(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        return io.Schema(
            node_id="NiftyInputSwitchEager",
            display_name="Input Switch (Eager)",
            category=NODE_CATEGORY,
            search_aliases=[
                "input switch eager",
                "if else eager",
                "conditional eager",
                "boolean switch",
                "select input",
                "switch node",
            ],
            inputs=[
                io.MatchType.Input(
                    "on_true",
                    template=switch_template,
                    optional=True,
                    tooltip="Value passed through when boolean is True. Both branches are evaluated regardless of the boolean value.",
                ),
                io.MatchType.Input(
                    "on_false",
                    template=switch_template,
                    optional=True,
                    tooltip="Value passed through when boolean is False. Both branches are evaluated regardless of the boolean value.",
                ),
                io.Boolean.Input(
                    "boolean", tooltip="Determines which input is passed to the output."
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=switch_template),
            ],
        )

    @classmethod
    def validate_inputs(
        cls, boolean, on_true=nifty_core.MISSING, on_false=nifty_core.MISSING
    ) -> bool | str:
        if on_false is nifty_core.MISSING and on_true is nifty_core.MISSING:
            return "At least one of on_true or on_false must be connected."
        return True

    @classmethod
    def execute(
        cls, boolean, on_true=nifty_core.MISSING, on_false=nifty_core.MISSING
    ) -> io.NodeOutput:
        if on_true is nifty_core.MISSING:
            return io.NodeOutput(on_false)
        if on_false is nifty_core.MISSING:
            return io.NodeOutput(on_true)
        return io.NodeOutput(on_true if boolean else on_false)


# None Input Switch
class NiftyNoneInputSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        return io.Schema(
            node_id="NiftyNoneInputSwitch",
            display_name="None Input Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "none input switch",
                "null switch",
                "optional switch",
                "exists switch",
                "none check switch",
                "fallback switch",
            ],
            inputs=[
                io.MatchType.Input(
                    "on_exists",
                    template=switch_template,
                    lazy=True,
                    optional=True,
                    tooltip="Value passed through when 'value' is not None. Only evaluated if selected (lazy).",
                ),
                io.MatchType.Input(
                    "on_none",
                    template=switch_template,
                    lazy=True,
                    optional=True,
                    tooltip="Value passed through when 'value' is None. Only evaluated if selected (lazy).",
                ),
                io.AnyType.Input(
                    "value",
                    optional=True,
                    tooltip="The value to check. If it is None, on_none is used; otherwise on_exists.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=switch_template),
            ],
        )

    @classmethod
    def check_lazy_status(
        cls,
        value=nifty_core.MISSING,
        on_exists=nifty_core.MISSING,
        on_none=nifty_core.MISSING,
    ):
        if on_none is nifty_core.MISSING:
            return ["on_exists"]
        if on_exists is nifty_core.MISSING:
            return ["on_none"]

        if value is None and on_none is None:
            return ["on_none"]
        if value is not None and on_exists is None:
            return ["on_exists"]

        return []

    @classmethod
    def validate_inputs(
        cls,
        value=nifty_core.MISSING,
        on_exists=nifty_core.MISSING,
        on_none=nifty_core.MISSING,
    ) -> bool | str:
        if on_exists is nifty_core.MISSING and on_none is nifty_core.MISSING:
            return "At least one of on_exists or on_none must be connected."
        return True

    @classmethod
    def execute(
        cls,
        value=nifty_core.MISSING,
        on_exists=nifty_core.MISSING,
        on_none=nifty_core.MISSING,
    ) -> io.NodeOutput:
        if on_exists is nifty_core.MISSING:
            return io.NodeOutput(on_none)
        if on_none is nifty_core.MISSING:
            return io.NodeOutput(on_exists)
        return io.NodeOutput(on_none if value is None else on_exists)


# None Input Switch (Eager)
class NiftyNoneInputSwitchEager(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")
        value_template = io.MatchType.Template("value")

        return io.Schema(
            node_id="NiftyNoneInputSwitchEager",
            display_name="None Input Switch (Eager)",
            category=NODE_CATEGORY,
            search_aliases=[
                "none input switch eager",
                "null switch eager",
                "optional switch eager",
                "exists switch eager",
                "none check switch",
            ],
            inputs=[
                io.MatchType.Input(
                    "on_exists",
                    template=switch_template,
                    optional=True,
                    tooltip="Value passed through when 'value' is not None. Both branches are always evaluated.",
                ),
                io.MatchType.Input(
                    "on_none",
                    template=switch_template,
                    optional=True,
                    tooltip="Value passed through when 'value' is None. Both branches are always evaluated.",
                ),
                io.MatchType.Input(
                    "value",
                    template=value_template,
                    optional=True,
                    tooltip="The value to check. If it is None, on_none is used; otherwise on_exists.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=switch_template),
            ],
        )

    @classmethod
    def execute(cls, value=None, on_exists=None, on_none=None) -> io.NodeOutput:
        return io.NodeOutput(on_exists if value is not None else on_none)


# Index Input Switch
class NiftyIndexInputSwitch(io.ComfyNode):
    MAX_VALUES = 16

    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        autogrow_template = io.Autogrow.TemplateNames(
            input=io.MatchType.Input(
                "value", template=switch_template, lazy=True, optional=True
            ),
            names=[f"value{i+1}" for i in range(cls.MAX_VALUES)],
            min=2,
        )

        return io.Schema(
            node_id="NiftyIndexInputSwitch",
            display_name="Index Input Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "index input switch",
                "indexed switch",
                "select by index",
                "multi input switch",
                "numbered switch",
                "index select",
            ],
            inputs=[
                io.Int.Input(
                    "index",
                    default=1,
                    min=1,
                    max=cls.MAX_VALUES,
                    tooltip=f"Which value input to pass through (1–{cls.MAX_VALUES}).",
                ),
                io.Autogrow.Input(
                    "values",
                    template=autogrow_template,
                    lazy=True,
                    optional=True,
                    tooltip="Auto-growing list of inputs. Only the selected index is evaluated (lazy).",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=switch_template),
            ],
        )

    @classmethod
    def check_lazy_status(cls, index=1, values=nifty_core.MISSING):
        if values is nifty_core.MISSING:
            return []

        key = f"value{index}"

        if key not in values:
            return []

        if values[key] is None:
            return [f"values.{key}"]

        return []

    @classmethod
    def execute(cls, index=1, values=nifty_core.MISSING) -> io.NodeOutput:
        if values is nifty_core.MISSING:
            return io.NodeOutput(None)

        key = f"value{index}"

        if key not in values:
            return io.NodeOutput(None)

        return io.NodeOutput(values.get(key))


# Index Input Switch (Eager)
class NiftyIndexInputSwitchEager(io.ComfyNode):
    MAX_VALUES = 16

    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        autogrow_template = io.Autogrow.TemplateNames(
            input=io.MatchType.Input("value", template=switch_template, optional=True),
            names=[f"value{i+1}" for i in range(cls.MAX_VALUES)],
            min=2,
        )

        return io.Schema(
            node_id="NiftyIndexInputSwitchEager",
            display_name="Index Input Switch (Eager)",
            category=NODE_CATEGORY,
            search_aliases=[
                "index input switch eager",
                "indexed switch eager",
                "select by index",
                "multi input switch eager",
                "numbered switch",
            ],
            inputs=[
                io.Int.Input(
                    "index",
                    default=1,
                    min=1,
                    max=cls.MAX_VALUES,
                    tooltip=f"Which value input to pass through (1–{cls.MAX_VALUES}). All inputs are evaluated regardless.",
                ),
                io.Autogrow.Input(
                    "values",
                    template=autogrow_template,
                    optional=True,
                    tooltip="Auto-growing list of inputs. All inputs are always evaluated regardless of the selected index.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=switch_template),
            ],
        )

    @classmethod
    def execute(cls, index=1, values=None) -> io.NodeOutput:
        if not values:
            return io.NodeOutput(None)

        key = f"value{index}"
        return io.NodeOutput(values.get(key))


# Output Switch
class NiftyOutputSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        return io.Schema(
            node_id="NiftyOutputSwitch",
            display_name="Output Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "output switch",
                "route output",
                "conditional output",
                "boolean route",
                "split output",
                "switch output",
            ],
            inputs=[
                io.MatchType.Input(
                    "input",
                    template=switch_template,
                    tooltip="Value to route to either on_true or on_false.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="on_true", template=switch_template),
                io.MatchType.Output(id="on_false", template=switch_template),
            ],
        )

    @classmethod
    def execute(cls, input, boolean=True) -> io.NodeOutput:
        if boolean:
            return io.NodeOutput(input, ExecutionBlocker(None))
        else:
            return io.NodeOutput(ExecutionBlocker(None), input)


# None Output Switch
class NiftyNoneOutputSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")
        value_template = io.MatchType.Template("value")

        return io.Schema(
            node_id="NiftyNoneOutputSwitch",
            display_name="None Output Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "none output switch",
                "null output switch",
                "optional route",
                "exists route",
                "none check output",
            ],
            inputs=[
                io.MatchType.Input(
                    "input",
                    template=switch_template,
                    optional=True,
                    tooltip="The value to route to either on_exists or on_none.",
                ),
                io.MatchType.Input(
                    "value",
                    template=value_template,
                    optional=True,
                    tooltip="The value to check. If not None, 'input' is routed to on_exists; otherwise to on_none.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="on_exists", template=switch_template),
                io.MatchType.Output(id="on_none", template=switch_template),
            ],
        )

    @classmethod
    def execute(cls, input=None, value=None) -> io.NodeOutput:
        if value is not None:
            return io.NodeOutput(input, ExecutionBlocker(None))
        else:
            return io.NodeOutput(ExecutionBlocker(None), input)


# Index Output Switch
class NiftyIndexOutputSwitch(io.ComfyNode):
    MAX_VALUES = 16

    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        return io.Schema(
            node_id="NiftyIndexOutputSwitch",
            display_name="Index Output Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "index output switch",
                "route by index",
                "indexed output",
                "numbered output switch",
                "demux",
            ],
            inputs=[
                io.MatchType.Input(
                    "input",
                    template=switch_template,
                    optional=True,
                    tooltip="Value to route to one of the indexed outputs.",
                ),
                io.Int.Input(
                    "index",
                    default=1,
                    min=1,
                    max=cls.MAX_VALUES,
                    tooltip=f"Which output to route the input to (1–{cls.MAX_VALUES}). All other outputs are blocked.",
                ),
            ],
            outputs=[
                io.MatchType.Output(
                    id=f"value{i+1}",
                    template=switch_template,
                )
                for i in range(cls.MAX_VALUES)
            ],
        )

    @classmethod
    def execute(cls, index=1, input=None) -> io.NodeOutput:
        results = [
            input if i + 1 == index else ExecutionBlocker(None)
            for i in range(cls.MAX_VALUES)
        ]

        return io.NodeOutput(*results)


# Signal Switch
class NiftySignalSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        return io.Schema(
            node_id="NiftySignalSwitch",
            display_name="Signal Switch",
            category=NODE_CATEGORY,
            # is_output_node=True
            search_aliases=[
                "signal switch",
                "gate",
                "passthrough",
                "block signal",
                "enable disable",
                "toggle node",
            ],
            inputs=[
                io.MatchType.Input(
                    "input",
                    template=switch_template,
                    tooltip="Value to gate. Passed through when passthrough is True, blocked otherwise.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=switch_template),
            ],
        )

    @classmethod
    def execute(cls, input, passthrough=True) -> io.NodeOutput:
        if not passthrough:
            return io.NodeOutput(
                ExecutionBlocker(None),
            )
        return io.NodeOutput(input)


# First Switch
class NiftyFirstSwitch(io.ComfyNode):
    MAX_VALUES = 16

    @classmethod
    def define_schema(cls) -> io.Schema:
        switch_template = io.MatchType.Template("switch")

        autogrow_template = io.Autogrow.TemplateNames(
            input=io.MatchType.Input(
                "value", template=switch_template, lazy=True, optional=True
            ),
            names=[f"value{i+1}" for i in range(cls.MAX_VALUES)],
            min=2,
        )

        return io.Schema(
            node_id="NiftyFirstSwitch",
            display_name="First Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "first switch",
                "first non null",
                "coalesce",
                "fallback",
                "first value",
                "pick first",
                "null coalesce",
            ],
            inputs=[
                io.Autogrow.Input(
                    "values",
                    template=autogrow_template,
                    lazy=True,
                    optional=True,
                    tooltip="Checks each input from top to bottom and returns the first one that is not None. Inputs are evaluated lazily — only as many as needed.",
                ),
            ],
            outputs=[
                io.MatchType.Output(id="output", template=switch_template),
            ],
        )

    @classmethod
    def check_lazy_status(cls, values=nifty_core.MISSING):
        if values is nifty_core.MISSING:
            return []

        for i in range(cls.MAX_VALUES):
            key = f"value{i+1}"
            if key not in values:
                continue
            val = values[key]
            if val is None:
                return [f"values.{key}"]
            return []

        return []

    @classmethod
    def execute(cls, values=nifty_core.MISSING) -> io.NodeOutput:
        if values is nifty_core.MISSING:
            return io.NodeOutput(None)
        for i in range(cls.MAX_VALUES):
            key = f"value{i+1}"
            val = values.get(key, nifty_core.MISSING)
            if val is nifty_core.MISSING:
                continue
            if val is not None:
                return io.NodeOutput(val)
        return io.NodeOutput(None)


# String Compare
class NiftyStringCompare(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyStringCompare",
            display_name="String Compare",
            category=NODE_CATEGORY,
            search_aliases=[
                "string compare",
                "compare strings",
                "text compare",
                "string match",
                "string equals",
                "string contains",
                "string check",
            ],
            inputs=[
                io.String.Input("string", tooltip="The string to test."),
                io.String.Input(
                    "match",
                    default="",
                    tooltip="The value to compare against. An empty match always returns False.",
                ),
                io.DynamicCombo.Input(
                    "comparison",
                    options=[
                        io.DynamicCombo.Option("exact", []),
                        io.DynamicCombo.Option("contains", []),
                        io.DynamicCombo.Option("starts with", []),
                        io.DynamicCombo.Option("ends with", []),
                        io.DynamicCombo.Option("regex", []),
                    ],
                    tooltip="Comparison mode: exact = full equality, contains = substring search, starts/ends with = prefix/suffix, regex = regular expression.",
                ),
                io.Boolean.Input(
                    "case_sensitive",
                    default=False,
                    tooltip="When enabled, the comparison is case-sensitive. Default is case-insensitive.",
                ),
                io.Boolean.Input(
                    "negate",
                    default=False,
                    tooltip="Invert the result — True becomes False and vice versa.",
                ),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(
        cls, string, match="", comparison=None, case_sensitive=False, negate=False
    ) -> io.NodeOutput:
        if match == "":
            result = False
        else:
            mode = comparison["comparison"] if comparison else "exact"

            if mode == "regex":
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    result = re.search(match, string, flags) is not None
                except Exception:
                    result = False
            else:
                s = string
                m = match

                if not case_sensitive:
                    s = s.lower()
                    m = m.lower()

                if mode == "exact":
                    result = s == m
                elif mode == "contains":
                    result = m in s
                elif mode == "starts with":
                    result = s.startswith(m)
                elif mode == "ends with":
                    result = s.endswith(m)
                else:
                    result = False
        return io.NodeOutput(not result if negate else result)


# Numer Compare
class NiftyNumberCompare(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyNumberCompare",
            display_name="Number Compare",
            category=NODE_CATEGORY,
            search_aliases=[
                "number compare",
                "compare numbers",
                "numeric compare",
                "int compare",
                "float compare",
                "greater than",
                "less than",
                "equal",
            ],
            inputs=[
                io.MultiType.Input(
                    "a", types=[io.Int, io.Float], tooltip="Left-hand operand."
                ),
                io.MultiType.Input(
                    "b", types=[io.Int, io.Float], tooltip="Right-hand operand."
                ),
                io.DynamicCombo.Input(
                    "comparison",
                    options=[
                        io.DynamicCombo.Option("a == b", []),
                        io.DynamicCombo.Option("a != b", []),
                        io.DynamicCombo.Option("a < b", []),
                        io.DynamicCombo.Option("a > b", []),
                        io.DynamicCombo.Option("a <= b", []),
                        io.DynamicCombo.Option("a >= b", []),
                        io.DynamicCombo.Option(
                            "a <= b <= c",
                            [
                                io.MultiType.Input(
                                    "c",
                                    types=[io.Int, io.Float],
                                    tooltip="Upper bound for the range check (a ≤ b ≤ c).",
                                ),
                            ],
                        ),
                    ],
                    tooltip="Comparison operator to apply. 'a <= b <= c' checks if b is within the range [a, c].",
                ),
                io.Boolean.Input(
                    "negate",
                    default=False,
                    tooltip="Invert the result — True becomes False and vice versa.",
                ),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(cls, a, b, comparison, negate=False) -> io.NodeOutput:
        mode = comparison["comparison"]
        result = False

        if mode == "a == b":
            result = a == b
        elif mode == "a != b":
            result = a != b
        elif mode == "a < b":
            result = a < b
        elif mode == "a > b":
            result = a > b
        elif mode == "a <= b":
            result = a <= b
        elif mode == "a >= b":
            result = a >= b
        elif mode == "a <= b <= c":
            c = comparison.get("c", 0.0)
            result = a <= b <= c
        return io.NodeOutput(not result if negate else result)


# Is None
class NiftyIsNone(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyIsNone",
            display_name="Is None",
            category=NODE_CATEGORY,
            search_aliases=[
                "is none",
                "null check",
                "none check",
                "is null",
                "is empty",
                "check none",
                "optional check",
            ],
            inputs=[
                io.AnyType.Input(
                    "input",
                    optional=True,
                    tooltip="The value to check. Returns True if it is None (not connected or explicitly set to None).",
                ),
                io.Boolean.Input(
                    "negate",
                    default=False,
                    tooltip="Invert the result — returns False when None and True when not None.",
                ),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(cls, input=None, negate=False) -> io.NodeOutput:
        is_none = input is None
        return io.NodeOutput(not is_none if negate else is_none)


# Int Switch
class NiftyIntSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyIntSwitch",
            display_name="Int Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "int switch",
                "integer switch",
                "boolean int",
                "conditional int",
                "select int",
            ],
            inputs=[
                io.Boolean.Input(
                    "boolean",
                    default=True,
                    tooltip="Determines which integer value is returned.",
                ),
                io.Int.Input(
                    "on_true",
                    default=0,
                    min=-sys.maxsize,
                    max=sys.maxsize,
                    tooltip="Returned when boolean is True.",
                ),
                io.Int.Input(
                    "on_false",
                    default=0,
                    min=-sys.maxsize,
                    max=sys.maxsize,
                    tooltip="Returned when boolean is False.",
                ),
            ],
            outputs=[
                io.Int.Output(),
            ],
        )

    @classmethod
    def execute(cls, boolean=True, on_true=0, on_false=0) -> io.NodeOutput:
        return io.NodeOutput(on_true if boolean else on_false)


# Float Switch
class NiftyFloatSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyFloatSwitch",
            display_name="Float Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "float switch",
                "boolean float",
                "conditional float",
                "select float",
                "decimal switch",
            ],
            inputs=[
                io.Boolean.Input(
                    "boolean",
                    default=True,
                    tooltip="Determines which float value is returned.",
                ),
                io.Float.Input(
                    "on_true",
                    default=0.0,
                    min=-sys.maxsize,
                    max=sys.maxsize,
                    step=0.01,
                    round=0.01,
                    tooltip="Returned when boolean is True.",
                ),
                io.Float.Input(
                    "on_false",
                    default=0.0,
                    min=-sys.maxsize,
                    max=sys.maxsize,
                    step=0.01,
                    round=0.01,
                    tooltip="Returned when boolean is False.",
                ),
            ],
            outputs=[
                io.Float.Output(),
            ],
        )

    @classmethod
    def execute(cls, boolean=True, on_true=0.0, on_false=0.0) -> io.NodeOutput:
        return io.NodeOutput(on_true if boolean else on_false)


# String Switch
class NiftyStringSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyStringSwitch",
            display_name="String Switch",
            category=NODE_CATEGORY,
            search_aliases=[
                "string switch",
                "boolean string",
                "conditional string",
                "select string",
                "text switch",
            ],
            inputs=[
                io.Boolean.Input(
                    "boolean",
                    default=True,
                    tooltip="Determines which string value is returned.",
                ),
                io.String.Input(
                    "on_true", default="", tooltip="Returned when boolean is True."
                ),
                io.String.Input(
                    "on_false", default="", tooltip="Returned when boolean is False."
                ),
            ],
            outputs=[
                io.String.Output(),
            ],
        )

    @classmethod
    def execute(cls, boolean=True, on_true="", on_false="") -> io.NodeOutput:
        return io.NodeOutput(on_true if boolean else on_false)


# Combo Switch
class NiftyComboSwitch(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyComboSwitch",
            display_name="Combo Switch",
            category=NODE_CATEGORY,
            is_experimental=True,
            search_aliases=[
                "combo switch",
                "boolean combo",
                "conditional combo",
                "select combo",
                "dropdown switch",
            ],
            inputs=[
                io.Boolean.Input(
                    "boolean",
                    default=True,
                    tooltip="Determines which combo value is returned.",
                ),
                io.Combo.Input(
                    "on_true",
                    options=[],
                    optional=True,
                    tooltip="Selected combo value when boolean is True.",
                ),
                io.String.Input(
                    "true_options",
                    optional=True,
                    tooltip="Combo values for on_true, separated by |.",
                ),
                io.Combo.Input(
                    "on_false",
                    options=[],
                    optional=True,
                    tooltip="Selected combo value when boolean is False.",
                ),
                io.String.Input(
                    "false_options",
                    optional=True,
                    tooltip="Combo values for on_false, separated by |",
                ),
            ],
            outputs=[
                io.Combo.Output(),
                io.Int.Output(id="index"),
            ],
        )

    @classmethod
    def validate_inputs(cls, on_true: io.Combo.Type, on_false: io.Combo.Type) -> bool:
        return True

    @classmethod
    def execute(
        cls,
        boolean=True,
        on_true=None,
        true_options=None,
        on_false=None,
        false_options=None,
    ) -> io.NodeOutput:
        selected = on_true if boolean else on_false
        options_text = true_options if boolean else false_options

        options = [
            item.strip() for item in (options_text or "").split("|") if item.strip()
        ]

        index = options.index(selected) if selected in options else -1

        return io.NodeOutput(
            selected,
            index,
        )


# Boolean AND
class NiftyBooleanAND(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBooleanAND",
            display_name="Boolean AND",
            category=NODE_CATEGORY,
            search_aliases=["boolean and", "logic and", "and gate", "both true"],
            inputs=[
                io.Boolean.Input("a", tooltip="First operand."),
                io.Boolean.Input("b", tooltip="Second operand."),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(cls, a, b) -> io.NodeOutput:
        return io.NodeOutput(a and b)


# Boolean AND All
class NiftyBooleanANDAll(io.ComfyNode):
    MAX_VALUES = 16

    @classmethod
    def define_schema(cls) -> io.Schema:
        autogrow = io.Autogrow.TemplateNames(
            input=io.Boolean.Input("value", optional=True, force_input=True),
            names=[f"boolean{i+1}" for i in range(cls.MAX_VALUES)],
            min=2,
        )

        return io.Schema(
            node_id="NiftyBooleanANDAll",
            display_name="Boolean AND All",
            category=NODE_CATEGORY,
            search_aliases=[
                "boolean and all",
                "all true",
                "all boolean",
                "logic and all",
                "multi and",
            ],
            inputs=[
                io.Autogrow.Input(
                    "values",
                    template=autogrow,
                    optional=True,
                    tooltip="Returns True only if all connected boolean inputs are True. Returns True if nothing is connected.",
                ),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(cls, values=None) -> io.NodeOutput:
        if not values:
            return io.NodeOutput(True)

        return io.NodeOutput(all(values.values()))


# Boolean OR
class NiftyBooleanOR(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBooleanOR",
            display_name="Boolean OR",
            category=NODE_CATEGORY,
            search_aliases=["boolean or", "logic or", "or gate", "either true"],
            inputs=[
                io.Boolean.Input("a", tooltip="First operand."),
                io.Boolean.Input("b", tooltip="Second operand."),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(cls, a, b) -> io.NodeOutput:
        return io.NodeOutput(a or b)


# Boolean OR Any
class NiftyBooleanORAny(io.ComfyNode):
    MAX_VALUES = 16

    @classmethod
    def define_schema(cls) -> io.Schema:
        autogrow = io.Autogrow.TemplateNames(
            input=io.Boolean.Input("value", optional=True, force_input=True),
            names=[f"boolean{i+1}" for i in range(cls.MAX_VALUES)],
            min=2,
        )

        return io.Schema(
            node_id="NiftyBooleanORAny",
            display_name="Boolean OR Any",
            category=NODE_CATEGORY,
            search_aliases=[
                "boolean or any",
                "any true",
                "any boolean",
                "logic or any",
                "multi or",
            ],
            inputs=[
                io.Autogrow.Input(
                    "values",
                    template=autogrow,
                    optional=True,
                    tooltip="Returns True if at least one connected boolean input is True. Returns False if nothing is connected.",
                ),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(cls, values=None) -> io.NodeOutput:
        if not values:
            return io.NodeOutput(False)

        return io.NodeOutput(any(values.values()))


# Boolean XOR
class NiftyBooleanXOR(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBooleanXOR",
            display_name="Boolean XOR",
            category=NODE_CATEGORY,
            search_aliases=["boolean xor", "exclusive or", "logic xor", "xor gate"],
            inputs=[
                io.Boolean.Input("a", tooltip="First operand."),
                io.Boolean.Input("b", tooltip="Second operand."),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(cls, a, b) -> io.NodeOutput:
        return io.NodeOutput(a ^ b)


# Boolean Negate
class NiftyBooleanNegate(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyBooleanNegate",
            display_name="Boolean NOT",
            category=NODE_CATEGORY,
            search_aliases=[
                "boolean not",
                "boolean negate",
                "invert boolean",
                "logic not",
                "flip boolean",
            ],
            inputs=[
                io.Boolean.Input("boolean", force_input=True),
            ],
            outputs=[
                io.Boolean.Output(),
            ],
        )

    @classmethod
    def execute(cls, boolean) -> io.NodeOutput:
        return io.NodeOutput(not boolean)


# None Value
class NiftyNoneValue(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="NiftyNoneValue",
            display_name="None",
            category=NODE_CATEGORY,
            search_aliases=[
                "none value",
                "null value",
                "none node",
                "null node",
                "empty value",
            ],
            inputs=[],
            outputs=[
                io.AnyType.Output(id="none"),
            ],
        )

    @classmethod
    def execute(cls) -> io.NodeOutput:
        return io.NodeOutput(None)


LOGIC_CLASSES = {
    "NiftyInputSwitch": NiftyInputSwitch,
    "NiftyInputSwitchEager": NiftyInputSwitchEager,
    "NiftyNoneInputSwitch": NiftyNoneInputSwitch,
    "NiftyNoneInputSwitchEager": NiftyNoneInputSwitchEager,
    "NiftyIndexInputSwitch": NiftyIndexInputSwitch,
    "NiftyIndexInputSwitchEager": NiftyIndexInputSwitchEager,
    "NiftyOutputSwitch": NiftyOutputSwitch,
    "NiftyNoneOutputSwitch": NiftyNoneOutputSwitch,
    "NiftyIndexOutputSwitch": NiftyIndexOutputSwitch,
    "NiftySignalSwitch": NiftySignalSwitch,
    "NiftyFirstSwitch": NiftyFirstSwitch,
    "NiftyStringCompare": NiftyStringCompare,
    "NiftyNumberCompare": NiftyNumberCompare,
    "NiftyIsNone": NiftyIsNone,
    "NiftyIntSwitch": NiftyIntSwitch,
    "NiftyFloatSwitch": NiftyFloatSwitch,
    "NiftyStringSwitch": NiftyStringSwitch,
    "NiftyComboSwitch": NiftyComboSwitch,
    "NiftyBooleanAND": NiftyBooleanAND,
    "NiftyBooleanANDAll": NiftyBooleanANDAll,
    "NiftyBooleanOR": NiftyBooleanOR,
    "NiftyBooleanORAny": NiftyBooleanORAny,
    "NiftyBooleanXOR": NiftyBooleanXOR,
    "NiftyBooleanNegate": NiftyBooleanNegate,
    "NiftyNoneValue": NiftyNoneValue,
}
