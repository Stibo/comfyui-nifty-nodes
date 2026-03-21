import os
import sys
import comfy.samplers

any_type = type("AnyType", (str,), {"__ne__": lambda s, o: False})("*")

_EMPTY = object()


class BundlePack:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "count": ("INT", {"default": 1, "min": 1, "max": 32, "step": 1}),
            },
            "optional": {
                "bundle": ("BUNDLE",),
            }
        }
    RETURN_TYPES = ("BUNDLE",)
    RETURN_NAMES = ("bundle",)
    FUNCTION = "pack"
    CATEGORY = "nifty/bundle"

    def pack(self, count, bundle=None, **kwargs):
        result = list(bundle) if bundle else []
        for i in range(count):
            val = kwargs.get(f"value{i+1}", _EMPTY)
            if val is _EMPTY:
                continue
            while len(result) <= i:
                result.append(None)
            result[i] = val
        return (result,)


class BundleUnpack:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bundle":     ("BUNDLE",),
                "count":      ("INT", {"default": 1, "min": 1, "max": 32, "step": 1}),
                "hide_links": ("BOOLEAN", {"default": False}),
            }
        }
    RETURN_TYPES = ("BUNDLE",) + (any_type,) * 32
    RETURN_NAMES = ("bundle",) + tuple(f"value{i+1}" for i in range(32))
    FUNCTION = "unpack"
    CATEGORY = "nifty/bundle"

    def unpack(self, bundle, count, **kwargs):
        bundle = bundle or []
        return (bundle,) + tuple(bundle[i] if i < len(bundle) else None for i in range(32))


class BundleGet:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bundle": ("BUNDLE",),
                "index":  ("INT", {"default": 1, "min": 1, "max": 32, "step": 1}),
            }
        }
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("value",)
    FUNCTION = "get_value"
    CATEGORY = "nifty/bundle"

    def get_value(self, bundle, index, **kwargs):
        bundle = bundle or []
        i = index - 1
        return (bundle[i] if i < len(bundle) else None,)


class BundleSet:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bundle": ("BUNDLE",),
                "index":  ("INT", {"default": 1, "min": 1, "max": 32, "step": 1}),
                "value":  (any_type,),
            }
        }
    RETURN_TYPES = ("BUNDLE",)
    RETURN_NAMES = ("bundle",)
    FUNCTION = "set_value"
    CATEGORY = "nifty/bundle"

    def set_value(self, bundle, index, value, **kwargs):
        result = list(bundle) if bundle else []
        i = index - 1
        while len(result) <= i:
            result.append(None)
        result[i] = value
        return (result,)


class StringSplit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string":    ("STRING", {"forceInput": True}),
                "delimiter": ("STRING", {"default": "\\n"}),
                "trim":      ("BOOLEAN", {"default": False}),
            }
        }
    RETURN_TYPES = ("STRING_LIST",)
    RETURN_NAMES = ("list",)
    FUNCTION = "split"
    CATEGORY = "nifty/string"

    def split(self, string, delimiter, trim):
        delimiter = delimiter.replace("\\n", "\n").replace("\\t", "\t")
        parts = string.split(delimiter)
        if trim:
            parts = [p.strip() for p in parts]
        return (parts,)


class StringJoin:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list":      ("STRING_LIST",),
                "delimiter": ("STRING", {"default": "\\n"}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "join"
    CATEGORY = "nifty/string"

    def join(self, list, delimiter):
        delimiter = delimiter.replace("\\n", "\n").replace("\\t", "\t")
        return (delimiter.join(str(s) for s in list),)


class DiffusionModelSelector:
    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths as fp, os
        EXTENSIONS = {".safetensors", ".gguf", ".pt", ".pth", ".bin"}
        files = set()
        for key in ("unet", "diffusion_models"):
            try: files.update(fp.get_filename_list(key))
            except: pass
        for key in ("unet", "diffusion_models"):
            try:
                for base in fp.get_folder_paths(key):
                    for root, dirs, fnames in os.walk(base):
                        for f in fnames:
                            if os.path.splitext(f)[1].lower() in EXTENSIONS:
                                rel = os.path.relpath(os.path.join(root, f), base)
                                files.add(rel)
            except: pass
        files = sorted(files) or ["[no models found]"]
        return {"required": {"model_name": (files,)}}

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import folder_paths as fp, os
        EXTENSIONS = {".safetensors", ".gguf", ".pt", ".pth", ".bin"}
        files = set()
        for key in ("unet", "diffusion_models"):
            try:
                for base in fp.get_folder_paths(key):
                    for root, dirs, fnames in os.walk(base):
                        for f in fnames:
                            if os.path.splitext(f)[1].lower() in EXTENSIONS:
                                files.add(f)
            except: pass
        return str(sorted(files))

    RETURN_TYPES = (any_type, "BOOLEAN")
    RETURN_NAMES = ("model", "is_gguf")
    FUNCTION = "run"
    CATEGORY = "nifty/selectors"

    def run(self, model_name):
        return (model_name, model_name.endswith(".gguf"))


class InputSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "on_true":  (any_type, {"lazy": True}),
                "on_false": (any_type, {"lazy": True}),
                "boolean":  ("BOOLEAN", {"default": True}),
            }
        }
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def check_lazy_status(self, boolean, **kwargs):
        return ["on_true"] if boolean else ["on_false"]

    def run(self, boolean, on_true=None, on_false=None, **kwargs):
        return (on_true if boolean else on_false,)


class OutputSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input":   (any_type,),
                "boolean": ("BOOLEAN", {"default": True}),
            }
        }
    RETURN_TYPES = (any_type, any_type)
    RETURN_NAMES = ("on_true", "on_false")
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def run(self, input, boolean, **kwargs):
        if boolean:
            return (input, None)
        else:
            return (None, input)


class SignalSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": (any_type,),
"passthrough": ("BOOLEAN", {"default": True}),
            }
        }
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"
    OUTPUT_NODE = True

    def run(self, input, passthrough, **kwargs):
        if not passthrough:
            return {"ui": {}, "result": (None,)}
        return (input,)


class SubgraphLabel:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "label1": ("STRING", {"default": ""}),
                "label2": ("STRING", {"default": ""}),
                "label3": ("STRING", {"default": ""}),
                "label4": ("STRING", {"default": ""}),
                "label5": ("STRING", {"default": ""}),
                "label6": ("STRING", {"default": ""}),
                "label7": ("STRING", {"default": ""}),
                "label8": ("STRING", {"default": ""}),
                "label9": ("STRING", {"default": ""}),
                "label10": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ()
    FUNCTION = "run"
    CATEGORY = "nifty/utils"
    OUTPUT_NODE = True

    def run(self, label1, label2, label3, label4, label5, label6, label7, label8, label9, label10):
        return ()


class HiddenLink:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                " ": (any_type,),
            }
        }
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = (" ",)
    FUNCTION = "passthrough"
    CATEGORY = "nifty/utils"

    def passthrough(self, **kwargs):
        return (next(iter(kwargs.values()), None),)




class IsNone:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "negate": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "input": (any_type,),
            }
        }
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("boolean",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def run(self, negate, input=None):
        is_none = input is None
        return (not is_none if negate else is_none,)



class BooleanNegate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "boolean": ("BOOLEAN", {"forceInput": True}),
            }
        }
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("boolean",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def run(self, boolean):
        return (not boolean,)


class StringCompare:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input":          ("STRING", {"forceInput": True}),
                "value":          ("STRING", {"default": ""}),
                "case_sensitive": ("BOOLEAN", {"default": False}),
                "negate":         ("BOOLEAN", {"default": False}),
            }
        }
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("boolean",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def run(self, input, value, case_sensitive, negate):
        a, b = (input, value) if case_sensitive else (input.lower(), value.lower())
        result = a == b
        return (not result if negate else result,)


class StringContains:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input":          ("STRING", {"forceInput": True}),
                "value":          ("STRING", {"default": ""}),
                "case_sensitive": ("BOOLEAN", {"default": False}),
                "negate":         ("BOOLEAN", {"default": False}),
            }
        }
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("boolean",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def run(self, input, value, case_sensitive, negate):
        a, b = (input, value) if case_sensitive else (input.lower(), value.lower())
        result = b in a
        return (not result if negate else result,)


class NumberCompare:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input":    ("FLOAT", {"forceInput": True}),
                "operator": (["==", "!=", ">", "<", ">=", "<="],),
                "value":    ("FLOAT", {"default": 0.0}),
                "negate":   ("BOOLEAN", {"default": False}),
            }
        }
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("boolean",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def run(self, input, operator, value, negate):
        ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">":  lambda a, b: a > b,
            "<":  lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }
        result = ops[operator](input, value)
        return (not result if negate else result,)



class BypassByTitle:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bypass":           ("BOOLEAN", {"default": False}),
                "nodes":            ("STRING",  {"default": "", "multiline": True}),
                "search_from_root": ("BOOLEAN", {"default": True}),
                "enforce":          ("BOOLEAN", {"default": True}),
            }
        }
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("bypass",)
    FUNCTION = "run"
    CATEGORY = "nifty/utils"
    OUTPUT_NODE = True

    def run(self, bypass, nodes, search_from_root, enforce):
        return (bypass,)


class BypassSwitchByTitle:
    @classmethod
    def INPUT_TYPES(cls):
        d = {"required": {
            "selected":         ("INT",     {"default": 1, "min": 1, "max": 16}),
            "bypass":           ([f"option {i+1}" for i in range(16)], {"default": "option 1", "forceInput": False}),
        }}
        for i in range(16):
            d["required"][f"label{i+1}"] = ("STRING",  {"default": f"option {i+1}", "multiline": False})
            d["required"][f"nodes{i+1}"] = ("STRING",  {"default": "",              "multiline": True})
        d["required"]["count"]            = ("INT",     {"default": 2, "min": 1, "max": 16})
        d["required"]["search_from_root"] = ("BOOLEAN", {"default": True})
        d["required"]["enforce"]          = ("BOOLEAN", {"default": True})
        return d
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("bypass",)
    FUNCTION = "run"
    CATEGORY = "nifty/utils"
    OUTPUT_NODE = True

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True  # bypass validation for dynamic combo values

    def run(self, selected, count, search_from_root, enforce, **kwargs):
        return (kwargs.get("bypass", f"option {selected}"),)


class IndexInputSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "index": ("INT", {"default": 1, "min": 1, "max": 16}),
            },
            "optional": {
                **{f"value{i+1}": (any_type, {"lazy": True}) for i in range(16)},
            }
        }
    # Note: all value inputs are handled dynamically in JS; Python accepts them via **kwargs
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def check_lazy_status(self, index, **kwargs):
        return [f"value{index}"]

    def run(self, index, **kwargs):
        return (kwargs.get(f"value{index}", None),)



class IndexOutputSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": (any_type,),
                "index": ("INT", {"default": 1, "min": 1, "max": 16}),
            }
        }
    RETURN_TYPES = tuple([any_type] * 16)
    RETURN_NAMES = tuple(f"value{i+1}" for i in range(16))
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def run(self, input, index, **kwargs):
        return tuple(input if i + 1 == index else None for i in range(16))


class FirstSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                **{f"value{i+1}": (any_type, {"lazy": True}) for i in range(16)},
            }
        }
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"

    def check_lazy_status(self, **kwargs):
        # Only request connected slots, in order, until one returns non-None
        needed = []
        for i in range(16):
            key = f"value{i+1}"
            if key not in kwargs:
                continue  # not connected, skip
            val = kwargs[key]
            if val is not None:
                return needed + [key]  # request up to and including this one
            needed.append(key)
        return needed

    def run(self, **kwargs):
        for i in range(16):
            val = kwargs.get(f"value{i+1}")
            if val is not None:
                return (val,)
        return (None,)


class IntSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "boolean":  ("BOOLEAN", {"default": True}),
            "on_true":  ("INT",     {"default": 0, "min": -2**31, "max": 2**31}),
            "on_false": ("INT",     {"default": 0, "min": -2**31, "max": 2**31}),
        }}
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("int",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"
    def run(self, boolean, on_true, on_false):
        return (on_true if boolean else on_false,)


class FloatSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "boolean":  ("BOOLEAN", {"default": True}),
            "on_true":  ("FLOAT",   {"default": 0.0, "min": -2**31, "max": 2**31, "step": 0.01, "round": 0.01}),
            "on_false": ("FLOAT",   {"default": 0.0, "min": -2**31, "max": 2**31, "step": 0.01, "round": 0.01}),
        }}
    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("float",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"
    def run(self, boolean, on_true, on_false):
        return (on_true if boolean else on_false,)


class StringSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "boolean":  ("BOOLEAN", {"default": True}),
            "on_true":  ("STRING",  {"default": ""}),
            "on_false": ("STRING",  {"default": ""}),
        }}
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "run"
    CATEGORY = "nifty/logic"
    def run(self, boolean, on_true, on_false):
        return (on_true if boolean else on_false,)


class ImageFromBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image":       ("IMAGE",),
            "batch_index": ("INT", {"default": 0, "min": -4096, "max": 4096}),
            "length":      ("INT", {"default": 1, "min": -1, "max": 4096}),
        }}
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = "nifty/image"

    def run(self, image, batch_index, length):
        batch_size = image.shape[0]
        start = max(0, batch_size + batch_index) if batch_index < 0 else min(batch_index, batch_size)
        if length == -1:
            return (image[start:],)
        end = min(start + length, batch_size)
        return (image[start:end],)


class NodeDuplicator:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "title":          ("STRING",  {"default": ""}),
            "count":          ("INT",     {"default": 1, "min": 1, "max": 32}),
            "connect_slots":  ("STRING",  {"default": ""}),
            "gap":            ("INT",     {"default": 20, "min": 0, "max": 2048}),
            "delete_excess":  ("BOOLEAN", {"default": False}),
            "search_from_root": ("BOOLEAN", {"default": True}),
        }}
    RETURN_TYPES = ()
    FUNCTION = "run"
    CATEGORY = "nifty/utils"
    def run(self, **kwargs):
        return ()


class MagicGetter:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "input":        (any_type,),
            "slot_name":    ("STRING",  {"default": ""}),
            "auto_connect": ("BOOLEAN", {"default": True}),
        }}
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"
    CATEGORY = "nifty/utils"

    def run(self, input, slot_name, auto_connect):
        return (input,)


class CalculateImageSize:
    RESIZE_TYPES = ["scale shorter dimension", "scale longer dimension", "scale width", "scale height", "scale by multiplier", "snap only"]

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "input":       ("IMAGE,MASK",),
            "resize_type": (cls.RESIZE_TYPES, {"default": "scale shorter dimension"}),
            "target_size": ("INT",   {"default": 720, "min": 1, "max": 32768}),
            "scale":       (["any", "upscale", "downscale"], {"default": "any"}),
            "multiplier":  ("FLOAT", {"default": 1.0, "min": 0.01, "max": 64.0, "step": 0.01}),
            "snap_to":     ("INT",   {"default": 1, "min": 1, "max": 256}),
        }}
    RETURN_TYPES = ("IMAGE,MASK", "INT", "INT")
    RETURN_NAMES = ("output", "width", "height")
    FUNCTION = "run"
    CATEGORY = "nifty/image"

    def run(self, input, resize_type, target_size, scale, multiplier, snap_to):
        # Get dimensions from first item in batch
        if hasattr(input, 'shape'):
            if len(input.shape) == 4:  # IMAGE: [batch, h, w, c]
                h, w = input.shape[1], input.shape[2]
            else:  # MASK: [batch, h, w]
                h, w = input.shape[1], input.shape[2]
        else:
            h, w = 512, 512

        def snap(val, s):
            return max(s, (int(val) // s) * s)

        if resize_type == "snap only":
            new_w = snap(w, snap_to)
            new_h = snap(h, snap_to)
        elif resize_type == "scale by multiplier":
            new_w = snap(w * multiplier, snap_to)
            new_h = snap(h * multiplier, snap_to)
        else:
            t = snap(target_size, snap_to)
            if resize_type == "scale shorter dimension":
                if w <= h:
                    new_w = t; new_h = snap(h * t / w, snap_to)
                else:
                    new_h = t; new_w = snap(w * t / h, snap_to)
            elif resize_type == "scale longer dimension":
                if w >= h:
                    new_w = t; new_h = snap(h * t / w, snap_to)
                else:
                    new_h = t; new_w = snap(w * t / h, snap_to)
            elif resize_type == "scale width":
                new_w = t; new_h = snap(h * t / w, snap_to)
            elif resize_type == "scale height":
                new_h = t; new_w = snap(w * t / h, snap_to)
            else:
                new_w, new_h = t, t

            # Apply scale direction (skip for snap only and multiplier)
            if scale == "upscale" and (new_w < w or new_h < h):
                new_w, new_h = snap(w, snap_to), snap(h, snap_to)
            elif scale == "downscale" and (new_w > w or new_h > h):
                new_w, new_h = snap(w, snap_to), snap(h, snap_to)

        return (input, int(new_w), int(new_h))


class LatentFromBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "samples":     ("LATENT",),
            "batch_index": ("INT", {"default": 0, "min": -4096, "max": 4096}),
            "length":      ("INT", {"default": 1, "min": -1, "max": 4096}),
        }}
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "run"
    CATEGORY = "nifty/latent"

    def run(self, samples, batch_index, length):
        s = samples["samples"]
        batch_size = s.shape[0]
        start = max(0, batch_size + batch_index) if batch_index < 0 else min(batch_index, batch_size)
        if length == -1:
            sliced = s[start:]
        else:
            sliced = s[start:min(start + length, batch_size)]
        return ({"samples": sliced},)



class LastImageFromBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "count": ("INT", {"default": 1, "min": 1, "max": 4096}),
        }}
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = "nifty/image"

    def run(self, image, count):
        return (image[-count:],)


class LastLatentFromBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "samples": ("LATENT",),
            "count":   ("INT", {"default": 1, "min": 1, "max": 4096}),
        }}
    RETURN_TYPES = ("LATENT",)
    FUNCTION = "run"
    CATEGORY = "nifty/latent"

    def run(self, samples, count):
        return ({"samples": samples["samples"][-count:]},)


class SamplerSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
        }}
    RETURN_TYPES = (comfy.samplers.KSampler.SAMPLERS,)
    RETURN_NAMES = ("sampler",)
    FUNCTION = "run"
    CATEGORY = "nifty/selectors"

    def run(self, sampler_name):
        return (sampler_name,)

class SchedulerSelector:
    @classmethod
    def INPUT_TYPES(cls):
        from comfy.samplers import KSampler
        return {"required": {
            "scheduler": (KSampler.SCHEDULERS,),
        }}
    RETURN_TYPES = (comfy.samplers.KSampler.SCHEDULERS,)
    RETURN_NAMES = ("scheduler",)
    FUNCTION = "run"
    CATEGORY = "nifty/selectors"

    def run(self, scheduler):
        return (scheduler,)


class NoneValue:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("none",)
    FUNCTION = "run"
    CATEGORY = "nifty/utils"

    def run(self):
        return (None,)


class SyncVHSPreview:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}
    RETURN_TYPES = ()
    FUNCTION = "run"
    CATEGORY = "nifty/utils"
    OUTPUT_NODE = True

    def run(self):
        return ()


class AutoSyncVHSPreview:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "auto_sync": ("BOOLEAN", {"default": False}),
        }}
    RETURN_TYPES = ()
    FUNCTION = "run"
    CATEGORY = "nifty/utils"
    OUTPUT_NODE = True

    def run(self, auto_sync):
        return ()


class ClipSelector:
    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths as fp, os
        EXTENSIONS = {".safetensors", ".gguf", ".pt", ".pth", ".bin"}
        files = set()
        for key in ("clip", "text_encoders"):
            try: files.update(fp.get_filename_list(key))
            except: pass
        for key in ("clip", "text_encoders"):
            try:
                for base in fp.get_folder_paths(key):
                    for root, dirs, fnames in os.walk(base):
                        for f in fnames:
                            if os.path.splitext(f)[1].lower() in EXTENSIONS:
                                rel = os.path.relpath(os.path.join(root, f), base)
                                files.add(rel)
            except: pass
        files = sorted(files) or ["[no models found]"]
        return {"required": {"clip_name": (files,)}}

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import folder_paths as fp, os
        EXTENSIONS = {".safetensors", ".gguf", ".pt", ".pth", ".bin"}
        files = set()
        for key in ("clip", "text_encoders"):
            try:
                for base in fp.get_folder_paths(key):
                    for root, dirs, fnames in os.walk(base):
                        for f in fnames:
                            if os.path.splitext(f)[1].lower() in EXTENSIONS:
                                files.add(os.path.join(root, f))
            except: pass
        return str(sorted(files))

    RETURN_TYPES = (any_type, "BOOLEAN")
    RETURN_NAMES = ("clip", "is_gguf")
    FUNCTION = "run"
    CATEGORY = "nifty/selectors"

    def run(self, clip_name):
        is_gguf = clip_name.lower().endswith(".gguf")
        return (clip_name, is_gguf)

NODE_CLASS_MAPPINGS = {
    "NiftyBundlePack":          BundlePack,
    "NiftyBundleUnpack":        BundleUnpack,
    "NiftyBundleGet":           BundleGet,
    "NiftyBundleSet":           BundleSet,
    "NiftyStringSplit":         StringSplit,
    "NiftyStringJoin":          StringJoin,
    "NiftyDiffusionModelSelector": DiffusionModelSelector,
    "NiftyClipSelector":          ClipSelector,
    "NiftySamplerSelector":      SamplerSelector,
    "NiftySchedulerSelector":    SchedulerSelector,
    "NiftyInputSwitch":         InputSwitch,
    "NiftyOutputSwitch":        OutputSwitch,
    "NiftySignalSwitch":        SignalSwitch,
    "NiftyFirstSwitch":         FirstSwitch,
    "NiftyIndexInputSwitch":    IndexInputSwitch,
    "NiftyIndexOutputSwitch":   IndexOutputSwitch,
    "NiftyIntSwitch":           IntSwitch,
    "NiftyFloatSwitch":         FloatSwitch,
    "NiftyStringSwitch":        StringSwitch,
    "NiftyIsNone":              IsNone,
    "NiftyBooleanNegate":       BooleanNegate,
    "NiftyStringCompare":       StringCompare,
    "NiftyStringContains":      StringContains,
    "NiftyNumberCompare":       NumberCompare,
    "NiftySubgraphLabels":      SubgraphLabel,
    "NiftyNoneValue":           NoneValue,
    "NiftyHiddenLink":          HiddenLink,
    "NiftyImageFromBatch":      ImageFromBatch,
    "NiftyNodeDuplicator":      NodeDuplicator,
    "NiftyMagicGetter":         MagicGetter,
    "NiftyCalculateImageSize":  CalculateImageSize,
    "NiftyLatentFromBatch":     LatentFromBatch,
    "NiftyLastImageFromBatch":   LastImageFromBatch,
    "NiftyLastLatentFromBatch":  LastLatentFromBatch,
    "NiftyBypassByTitle":       BypassByTitle,
    "NiftyBypassSwitchByTitle":  BypassSwitchByTitle,
    "NiftySyncVHSPreview":      SyncVHSPreview,
    "NiftyAutoSyncVHSPreview":  AutoSyncVHSPreview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NiftyBundlePack":          "Bundle Pack",
    "NiftyBundleUnpack":        "Bundle Unpack",
    "NiftyBundleGet":           "Bundle Get",
    "NiftyBundleSet":           "Bundle Set",
    "NiftyStringSplit":         "String Split",
    "NiftyStringJoin":          "String Join",
    "NiftyDiffusionModelSelector": "Diffusion Model Selector",
    "NiftyClipSelector":          "Clip Selector",
    "NiftySamplerSelector":      "Sampler Selector",
    "NiftySchedulerSelector":    "Scheduler Selector",
    "NiftyInputSwitch":         "Input Switch",
    "NiftyOutputSwitch":        "Output Switch",
    "NiftySignalSwitch":        "Signal Switch",
    "NiftyFirstSwitch":         "First Switch",
    "NiftyIndexInputSwitch":    "Index Input Switch",
    "NiftyIndexOutputSwitch":   "Index Output Switch",
    "NiftyIntSwitch":           "Int Switch",
    "NiftyFloatSwitch":         "Float Switch",
    "NiftyStringSwitch":        "String Switch",
    "NiftyIsNone":              "Is None",
    "NiftyBooleanNegate":       "Boolean Negate",
    "NiftyStringCompare":       "String Compare",
    "NiftyStringContains":      "String Contains",
    "NiftyNumberCompare":       "Number Compare",
    "NiftySubgraphLabels":      "Subgraph Labels",
    "NiftyNoneValue":           "None",
    "NiftyHiddenLink":          "Hidden Link",
    "NiftyImageFromBatch":      "Image From Batch",
    "NiftyNodeDuplicator":      "Node Duplicator",
    "NiftyMagicGetter":         "Magic Getter",
    "NiftyCalculateImageSize":  "Calculate Image Size",
    "NiftyLatentFromBatch":     "Latent From Batch",
    "NiftyLastImageFromBatch":   "Last Image From Batch",
    "NiftyLastLatentFromBatch":  "Last Latent From Batch",
    "NiftyBypassByTitle":       "Bypass by Title",
    "NiftyBypassSwitchByTitle":  "Bypass Switch by Title",
    "NiftySyncVHSPreview":      "Sync VHS Preview",
    "NiftyAutoSyncVHSPreview":  "Auto Sync VHS Preview",
}
