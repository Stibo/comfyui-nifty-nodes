import math
import string as _string
from comfy_api.latest import io

NODE_CATEGORY = "nifty/number"


# Seed
class NiftySeed(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftySeed",
            display_name="Nifty Seed",
            category=NODE_CATEGORY,
            search_aliases=[
                "seed",
                "random seed",
                "nifty seed",
                "seed node",
                "seed generator",
                "seed control",
            ],
            inputs=[
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=1 << 50,
                    control_after_generate=False,
                ),
                io.Custom("NIFTY_SEED_ACTIONS").Input("seed_actions"),
            ],
            outputs=[
                io.Int.Output(id="seed"),
            ],
        )

    @classmethod
    def execute(cls, seed, **kwargs) -> io.NodeOutput:
        return io.NodeOutput(seed)


# Math
class NiftyMath(io.ComfyNode):
    MAX_SLOTS = 16
    SLOT_LETTERS = list(_string.ascii_lowercase[:16])

    SAFE_GLOBALS = {
        "__builtins__": {},
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow,
        "sqrt": math.sqrt,
        "floor": math.floor,
        "ceil": math.ceil,
        "log": math.log,
        "log2": math.log2,
        "log10": math.log10,
        "exp": math.exp,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "atan2": math.atan2,
        "radians": math.radians,
        "degrees": math.degrees,
        "hypot": math.hypot,
        "clamp": lambda v, lo, hi: max(lo, min(hi, v)),
        "lerp": lambda a, b, t: a + (b - a) * t,
        "remap": lambda v, a, b, c, d: (
            c + (d - c) * ((v - a) / (b - a)) if (b - a) != 0 else c
        ),
        "pi": math.pi,
        "tau": math.tau,
        "e": math.e,
        "inf": math.inf,
        "True": True,
        "False": False,
    }

    @classmethod
    def define_schema(cls) -> io.Schema:
        autogrow_template = io.Autogrow.TemplateNames(
            input=io.MultiType.Input(
                "value",
                types=[io.Int, io.Float],
                optional=True,
                tooltip="Numeric input value. Unconnected slots default to 0.",
            ),
            names=cls.SLOT_LETTERS,
            min=2,
        )

        return io.Schema(
            node_id="NiftyMath",
            display_name="Nifty Math",
            category=NODE_CATEGORY,
            search_aliases=[
                "math",
                "math node",
                "expression",
                "formula",
                "calculate",
                "nifty math",
                "math expression",
                "eval",
                "compute",
            ],
            inputs=[
                io.Autogrow.Input(
                    "values",
                    template=autogrow_template,
                    optional=True,
                    tooltip="Named variable inputs a–p. Connect values here to use them in the expression. Unconnected slots default to 0.",
                ),
                io.String.Input(
                    "expression",
                    default="a + b",
                    tooltip=(
                        "Mathematical expression evaluated with the slot letters as variables. "
                        "Supports: + - * / // % ** (power), comparisons (==, !=, <, >, <=, >=), "
                        "boolean logic (and, or, not), ternary (x if cond else y), "
                        "and functions: abs, round, min, max, pow, sqrt, floor, ceil, "
                        "log, log2, log10, exp, sin, cos, tan, asin, acos, atan, atan2, "
                        "radians, degrees, hypot, clamp(v,lo,hi), lerp(a,b,t), "
                        "remap(v,a,b,c,d), and constants pi, tau, e, inf. "
                        "Unconnected slots default to 0."
                    ),
                ),
            ],
            outputs=[
                io.Int.Output(id="int"),
                io.Float.Output(id="float"),
                io.Boolean.Output(id="boolean"),
            ],
        )

    @classmethod
    def execute(cls, expression: str, values=None) -> io.NodeOutput:
        variables = {letter: 0 for letter in cls.SLOT_LETTERS}

        if values:
            for letter in cls.SLOT_LETTERS:
                v = values.get(letter)
                if v is not None:
                    variables[letter] = v

        try:
            result = eval(
                expression,
                cls.SAFE_GLOBALS,
                variables,
            )
        except ZeroDivisionError:
            result = 0
        except Exception as e:
            raise ValueError(f"[NiftyMath] Expression error: {e}") from e

        try:
            as_float = float(result)
        except (TypeError, ValueError):
            as_float = 1.0 if result else 0.0

        return io.NodeOutput(
            int(as_float),
            as_float,
            bool(result),
        )


NUMBER_CLASSES = {
    "NiftySeed": NiftySeed,
    "NiftyMath": NiftyMath,
}
