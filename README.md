# ComfyUI Nifty Nodes

A ComfyUI node pack focused on workflow organisation and flexibility. The centrepiece is a **Bundle system** for passing arbitrary named values through a single wire, alongside smart **media loaders** with built-in resize, a **multi-LoRA loader**, a full set of **logic and switch nodes**, image processing tools, latent utilities, and various quality-of-life helpers.

## Installation

Clone the repository into your ComfyUI `custom_nodes` folder:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Stibo/comfyui-nifty-nodes
```

Then restart ComfyUI. Optional dependencies for certain nodes:

```bash
pip install kornia        # reinhard_lab_gpu and perceptual_crossfade in Image Color Match
pip install color-matcher # additional color transfer methods in Image Color Match
```

## Features

- **ComfyUI v3 native** — built entirely on the `comfy_api.latest` API with proper `define_schema`, lazy evaluation, `fingerprint_inputs` caching and async execution where applicable
- **Bundle system** — pass any number of named values through a single BUNDLE wire, with dot-notation support for nested structures
- **Smart media loaders** — load images, videos or both with an integrated resize pipeline and optional frame rate control
- **Multi-LoRA loader** — manage an entire LoRA stack in one node with per-row enable/disable and strength controls
- **Full logic suite** — lazy and eager input switches, output routers, boolean operators, string/number comparisons and more
- **Image Color Match** — 10 color transfer methods including GPU-accelerated options, batch multithreading and selective channel transfer
- **Search aliases** on every node for fast discovery via the node search

---

## Nodes

### Bundle

The Bundle system lets you pack multiple values of any type into a single `BUNDLE` wire and unpack or access them wherever needed. This keeps graphs clean when many values need to travel together.

#### Bundle Pack

Packs up to 32 values of any type into a Bundle. An optional incoming Bundle can be merged — new values are added to it or overwrite existing keys.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| bundle | BUNDLE | No | — | Existing bundle to merge into. New slot values overwrite keys with the same name. |
| value1 … value32 | ANY | No | — | Values to pack. Controlled by `count`. |
| count | INT | No | 1 | Number of value slots to show (1–32). |
| hide_links | BOOL | No | False | Hide the connection wires going into this node to reduce visual clutter. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| bundle | BUNDLE | The resulting bundle containing all packed values. |

#### Bundle Unpack

Unpacks a Bundle back into up to 32 individual outputs. Output labels are set by renaming the slots, matching the keys used when packing.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| bundle | BUNDLE | Yes | — | The bundle to unpack. |
| count | INT | No | 1 | Number of output slots to show (1–32). |
| hide_links | BOOL | No | False | Hide the connection wires going out of this node to reduce visual clutter. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| bundle | BUNDLE | The original bundle, passed through unchanged. |
| value1 … value32 | ANY | Unpacked values. Slots beyond `count` output `None`. |

#### Bundle Get

Reads a single value from a Bundle by key.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| bundle | BUNDLE | Yes | — | The bundle to read from. |
| key | STRING | Yes | `value1` | Key to read. Supports **dot notation** for nested keys, e.g. `settings.width`. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| value | ANY | The value at the given key, or `None` if the key does not exist. |

#### Bundle Set

Writes or overwrites a single key in a Bundle.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| bundle | BUNDLE | Yes | — | The bundle to update. |
| key | STRING | Yes | `value1` | Key to write. Supports **dot notation** for nested keys, e.g. `settings.width`. |
| value | ANY | Yes | — | Value to store at the given key. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| bundle | BUNDLE | Updated bundle. The original is not modified — a new copy is returned. |

##### Slot Labels and Key Names

When you rename a slot in Bundle Pack or Bundle Unpack (double-click the slot label), the new name becomes the key used inside the bundle. The same label must be used on both ends for values to align correctly.

##### Dot Notation and Nesting

Keys use `.` as a path separator, allowing you to read and write into nested structures. For example:

```
Bundle Pack  →  slot label: "camera.fov"   →  value: 90
Bundle Get   →  key: "camera.fov"          →  returns: 90
```

You can nest arbitrarily deep: `"render.output.format"`, `"lora.0.strength"`, etc. Bundle Get and Bundle Set both support full dot-path access.

##### Merging Bundles

Bundle Pack accepts an optional incoming Bundle. Any values you pack are merged on top of it — existing keys are overwritten, other keys are preserved. This makes it easy to incrementally build up a shared parameter object across multiple nodes.

---

### Media Loader

#### Load & Resize Media

The most versatile loader — accepts images **and** videos in a single node, with a built-in resize pipeline. A `is_video` boolean output lets you route the result differently depending on what was loaded.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| file | COMBO | Yes | none | File to load. Supports image formats (jpg, png, webp, …), animated formats (gif, apng, webp, avif) and video formats (mp4, mkv, webm, …). |
| force_frame_rate | INT | No | 0 | Enforce a specific frame rate. **0 = keep original.** Values like 24, 30 or 60 resample the video during loading. |
| resize | DYNAMIC | No | off | Resize mode to apply after loading — see [Resize Modes](#resize-modes). |

##### Outputs

| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Loaded frames as a batch tensor. `None` if file is `none`. |
| frames | INT | Total number of frames (1 for still images). |
| width | INT | Output width after any resize. |
| height | INT | Output height after any resize. |
| frame_rate | INT | Frame rate of the source (or the forced rate if set). |
| audio | AUDIO | Extracted audio track. Silent if the file has no audio. |
| **is_video** | BOOL | **True if the loaded file is a video or animation, False for still images.** |

#### Load & Resize Video

Same as Load & Resize Media but restricted to video and animation file types.

##### Inputs / Outputs

Same as Load & Resize Media, minus the `is_video` output.

#### Load & Resize Image

Same as Load & Resize Media but restricted to image and animation file types. No `frames`, `frame_rate` or `audio` outputs.

##### Outputs

| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Loaded image as a tensor. `None` if file is `none`. |
| width | INT | Output width after any resize. |
| height | INT | Output height after any resize. |

##### Resize Modes

All three loaders share the same resize pipeline, available via the `resize` dropdown:

| Mode | Description |
|---|---|
| **off** | No resize — load at original dimensions. |
| scale dimensions | Scale to exact `width × height`. Optional center crop to avoid stretching. |
| scale by multiplier | Scale both dimensions by a float multiplier. |
| scale longer dimension | Scale so the longer side equals the given size, preserving aspect ratio. |
| scale shorter dimension | Scale so the shorter side equals the given size, preserving aspect ratio. |
| scale width | Scale to a specific width, preserving aspect ratio. |
| scale height | Scale to a specific height, preserving aspect ratio. |
| scale total pixels | Scale to a target megapixel count. |
| make divisible by | Round dimensions to the nearest multiple (e.g. 16 for WAN). |

All modes include a `divisible_by` option and separate scale method selectors for upscaling and downscaling:

| Scale Method | Best for |
|---|---|
| nearest-exact | Fastest, pixel art / sharp pixel edges |
| bilinear / bicubic | General purpose |
| area | **Downscaling** — sharp, minimal aliasing |
| lanczos | **Upscaling** — smooth, good detail retention |
| mitchell-netravali | Sharp upscaling with minimal ringing |
| bilinear (antialias) / bicubic (antialias) | Smooth downscaling with anti-aliasing |
| nvidia-rtx-vsr | AI upscaling — requires an NVIDIA RTX GPU and the nvidia-vfx package |

---

### Lora Loader

#### Nifty Lora Loader

Applies a full LoRA stack to a model and CLIP in one node. Each row has its own enable toggle and strength slider. Rows with strength `0.0` or disabled are skipped entirely.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| model | MODEL | Yes | — | Base model to apply LoRAs to. |
| clip | CLIP | Yes | — | CLIP model to apply LoRAs to. |
| loras | NIFTY_LORA_LOADER | Yes | — | LoRA stack widget. Add rows, pick a LoRA file, set strength and toggle enabled. **Strength 1.0 = full effect, 0.5 = half, negative values invert.** |

##### Outputs

| Name | Type | Description |
|---|---|---|
| MODEL | MODEL | Model with all enabled LoRAs applied in order. |
| CLIP | CLIP | CLIP with all enabled LoRAs applied in order. |

---

### Logic

A full set of flow control nodes. Most come in two variants: **lazy** (only evaluates the branch that will actually be used) and **eager** (evaluates both branches regardless).

#### Input Switch

Routes one of two inputs to the output based on a boolean. **Lazy** — the unused branch is never executed.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| on_true | ANY | No | — | Passed through when `boolean` is `True`. |
| on_false | ANY | No | — | Passed through when `boolean` is `False`. |
| boolean | BOOL | Yes | — | Selector. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| output | ANY | The selected input value. |

#### Input Switch (Eager)

Same as Input Switch but both branches are always evaluated.

#### None Input Switch

Routes between `on_exists` and `on_none` depending on whether `value` is `None`. **Lazy.**

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| on_exists | ANY | No | — | Passed through when `value` is not `None`. |
| on_none | ANY | No | — | Passed through when `value` is `None`. |
| value | ANY | No | — | The value to check. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| output | ANY | The selected branch. |

#### None Input Switch (Eager)

Same as None Input Switch but both branches are always evaluated.

#### Index Input Switch

Routes one of up to 16 inputs to the output by index. **Lazy** — only the selected input is evaluated.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| index | INT | Yes | 1 | Which input to pass through (1–16). |
| value1 … value16 | ANY | No | — | Auto-growing input list. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| output | ANY | The value at the selected index, or `None` if the slot is not connected. |

#### Index Input Switch (Eager)

Same as Index Input Switch but all inputs are always evaluated.

#### Output Switch

Routes a single input to either `on_true` or `on_false`. The unselected output is blocked (downstream nodes do not execute).

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| input | ANY | Yes | — | Value to route. |
| boolean | BOOL | No | True | `True` = route to `on_true`, `False` = route to `on_false`. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| on_true | ANY | Active when `boolean` is `True`, blocked otherwise. |
| on_false | ANY | Active when `boolean` is `False`, blocked otherwise. |

#### None Output Switch

Routes `input` to either `on_exists` or `on_none` depending on whether `value` is `None`.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| input | ANY | No | — | Value to route. |
| value | ANY | No | — | Value to check for `None`. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| on_exists | ANY | Active when `value` is not `None`. |
| on_none | ANY | Active when `value` is `None`. |

#### Index Output Switch

Routes a single input to one of up to 16 outputs by index. All other outputs are blocked.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| input | ANY | No | — | Value to route. |
| index | INT | Yes | 1 | Which output to route to (1–16). |

##### Outputs

| Name | Type | Description |
|---|---|---|
| value1 … value16 | ANY | Only the output at `index` is active; all others are blocked. |

#### Signal Switch

Simple on/off gate. When `passthrough` is `False`, the output is blocked and all downstream nodes skip execution.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| input | ANY | Yes | — | Value to gate. |
| passthrough | BOOL | No | True | `True` = pass through, `False` = block. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| output | ANY | The input value, or blocked if `passthrough` is `False`. |

#### First Switch

Returns the first non-`None` value from a list of up to 16 inputs. **Lazy** — inputs are evaluated one by one until a non-`None` value is found.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| value1 … value16 | ANY | No | — | Auto-growing input list checked in order from top to bottom. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| output | ANY | First non-`None` value found, or `None` if all inputs are `None`. |

#### String Compare

Compares a string against a match value and returns a boolean.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| string | STRING | Yes | — | The string to test. |
| match | STRING | Yes | `` | The value to compare against. An empty match always returns `False`. |
| comparison | DYNAMIC | Yes | exact | **exact** = full equality · **contains** = substring · **starts with** / **ends with** = prefix/suffix · **regex** = regular expression |
| case_sensitive | BOOL | No | False | Enable case-sensitive comparison. |
| negate | BOOL | No | False | Invert the result. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| BOOL | BOOL | Result of the comparison. |

#### Number Compare

Compares two numbers and returns a boolean.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| a | INT / FLOAT | Yes | — | Left-hand operand. |
| b | INT / FLOAT | Yes | — | Right-hand operand. |
| comparison | DYNAMIC | Yes | a == b | **a == b** · **a != b** · **a < b** · **a > b** · **a <= b** · **a >= b** · **a <= b <= c** (range check) |
| negate | BOOL | No | False | Invert the result. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| BOOL | BOOL | Result of the comparison. |

#### Is None

Returns `True` if the input is `None` (not connected or explicitly `None`).

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| input | ANY | No | — | Value to check. |
| negate | BOOL | No | False | Invert — returns `False` when `None`, `True` otherwise. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| BOOL | BOOL | `True` if input is `None`, `False` otherwise (before negation). |

#### Int Switch / Float Switch / String Switch

Each returns one of two primitive values based on a boolean.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| boolean | BOOL | No | True | Selector. |
| on_true | INT / FLOAT / STRING | No | 0 / 0.0 / `` | Returned when `boolean` is `True`. |
| on_false | INT / FLOAT / STRING | No | 0 / 0.0 / `` | Returned when `boolean` is `False`. |

#### Combo Switch

Switches between two combo (dropdown) values based on a boolean. Each side has its own options list, defined as a pipe-separated string (`option1|option2|option3`). Also outputs the index of the selected value within its option list.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| boolean | BOOL | No | True | Selector. |
| on_true | COMBO | No | — | Selected value when `True`. |
| true_options | STRING | No | — | Available options for `on_true`, separated by `\|`. |
| on_false | COMBO | No | — | Selected value when `False`. |
| false_options | STRING | No | — | Available options for `on_false`, separated by `\|`. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| COMBO | COMBO | Selected combo value. |
| index | INT | Index of the selected value within its option list. `-1` if not found. |

#### Boolean AND / OR / XOR

Standard two-input boolean gates.

#### Boolean AND All / OR Any

Multi-input variants using an auto-growing input list (up to 16). AND All returns `True` only if every connected input is `True`. OR Any returns `True` if at least one is `True`.

#### Boolean NOT

Inverts a boolean value.

#### None

Outputs a `None` value. Useful as an explicit empty input for optional slots.

---

### Image

#### Image Color Match

Transfers the color distribution of a reference image onto a target image. Supports 10 transfer methods, selective channel transfer, adjustable strength and batch multithreading.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| image_target | IMAGE | No | — | Image whose colors will be adjusted. |
| image_ref | IMAGE | No | — | Reference image providing the color distribution. |
| enabled | BOOL | No | True | When disabled, `image_target` passes through unchanged. |
| method | COMBO | No | mkl | Color transfer algorithm — see [Methods](#color-match-methods) below. |
| transfer_mode | COMBO | No | all | **all** = full color transfer · **color** = hue/chroma only, keep original luminance · **luminance** = brightness only, keep original colors |
| strength | FLOAT | No | 1.0 | Blend amount. **1.0 = full match**, 0.5 = half-way blend, values above 1.0 exaggerate the effect. Range 0.0–10.0. |
| multithread | BOOL | No | True | Process batch frames in parallel using multiple CPU threads. Recommended for large batches. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Color-matched image batch. `None` if either input is not connected. |

##### Color Match Methods

| Method | Notes |
|---|---|
| **mkl** | Monge-Kantorovich linear map — accurate and general purpose, recommended default |
| **reinhard_lab** | Fast statistical match in LAB color space — CPU |
| **reinhard_lab_gpu** | Same as above but GPU-accelerated — requires `kornia` |
| **wavelet** | Structure-preserving, transfers low-frequency color info — good for textures |
| **adain** | Adaptive instance normalisation — fast, works well for style-like transfers |
| hm | Histogram matching |
| reinhard | Classic Reinhard RGB |
| mvgd | Multivariate Gaussian — requires `color-matcher` |
| hm-mvgd-hm | Histogram + MVGD combo — requires `color-matcher` |
| hm-mkl-hm | Histogram + MKL combo — requires `color-matcher` |

#### Merge Image Batches

Concatenates two image batches with optional blending at the transition. Useful for stitching video segments.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| source_images | IMAGE | No | — | First batch. |
| new_images | IMAGE | No | — | Second batch, appended after source. |
| overlap_mode | DYNAMIC | No | none | Transition mode — see below. |

| Overlap Mode | Description |
|---|---|
| none | Simple concatenation, no blending. |
| cut | Remove `overlap` frames from the selected side before concatenating. |
| linear_blend | Simple linear crossfade over the overlap region. |
| ease_in_out | S-curve (smoothstep) crossfade — more natural motion. |
| filmic_crossfade | Gamma-correct (2.2) crossfade — preserves perceived brightness. |
| perceptual_crossfade | LAB color space crossfade — perceptually even transition. Requires `kornia`. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| images | IMAGE | Merged batch. `None` if both inputs are disconnected. |

#### Resize Image

Resizes an image or mask using the full Nifty resize pipeline. Accepts both IMAGE and MASK types.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| input | IMAGE / MASK | Yes | — | Image or mask to resize. |
| resize | DYNAMIC | Yes | — | Resize mode — see [Resize Modes](#resize-modes). |

##### Outputs

| Name | Type | Description |
|---|---|---|
| resized | IMAGE / MASK | Resized output (same type as input). |
| width | INT | Output width. |
| height | INT | Output height. |

#### Image From Batch

Extracts a slice from an image batch by start index and length.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| image | IMAGE | Yes | — | Input batch. |
| batch_index | INT | No | 0 | Start index. **Positive = from beginning, negative = from end** (-1 = last image). Range −4096–4096. |
| length | INT | No | 1 | Number of images to take. **-1 = all from start to end of batch.** Range −1–4096. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Extracted slice. |

#### Last Image From Batch

Shortcut to take the last N images from a batch.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| image | IMAGE | Yes | — | Input batch. |
| length | INT | No | 1 | Number of images to take from the end (1–4096). |

##### Outputs

| Name | Type | Description |
|---|---|---|
| IMAGE | IMAGE | Last `length` images from the batch. |

---

### Latent

#### VAE Encode

Encodes an image batch into latents. Automatically detects the temporal compression factor of the VAE and can optionally encode only a subset of frames specified by a target latent count.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| pixels | IMAGE | Yes | — | Image frames to encode. |
| vae | VAE | Yes | — | VAE model to use for encoding. |
| target_latents | INT | No | 0 | **0 = encode all frames.** Positive = encode only the first N latents' worth of frames. Negative = encode only the last N latents' worth. The temporal factor is detected automatically from the VAE. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Encoded latent samples. |
| IMAGE | IMAGE | The original pixel frames, passed through unchanged. |

#### Normalize Video Latent Start

Normalises the statistics (mean and standard deviation) of the first few latent frames to match the subsequent frames. Helps reduce flicker or discontinuity at the beginning of a generated video.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| latent | LATENT | Yes | — | Video latent to process. Passthrough if the latent has only 1 frame. |
| enabled | BOOL | No | True | When disabled, the latent is passed through unchanged. |
| start_frame_count | INT | No | 4 | Number of latent frames from the start to normalise (1–max). |
| reference_frame_count | INT | No | 5 | Number of frames immediately after the start region to use as the normalisation reference (1–max). |

##### Outputs

| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Latent with normalised start frames. |

#### Latent From Batch

Extracts a slice from a latent batch by start index and length. Supports both 4D (image) and 5D (video) latents.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| samples | LATENT | Yes | — | Input latent batch. |
| batch_index | INT | No | 0 | Start index. **Positive = from beginning, negative = from end** (-1 = last frame). Range −4096–4096. |
| length | INT | No | 0 | **0 = all from start to end. Positive = first N frames. Negative = trim N frames from the opposite end** (e.g. -1 = all except the last). |

##### Outputs

| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Extracted latent slice. |

#### Last Latent From Batch

Shortcut to take the last N latents from a batch.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| samples | LATENT | Yes | — | Input latent batch. |
| length | INT | No | 1 | Number of latents to take from the end (1–4096). |

##### Outputs

| Name | Type | Description |
|---|---|---|
| LATENT | LATENT | Last `length` latents from the batch. |

---

### Selectors

Lightweight selector nodes that output a filename or name string. They exist to keep your actual loader nodes clean — connect these to a loader and swap models or settings without touching the loader itself.

#### Diffusion Model Selector

Selects a diffusion model file from the `unet` / `diffusion_models` folder. Supports `.safetensors`, `.gguf`, `.pt`, `.pth`, `.bin`.

##### Outputs

| Name | Type | Description |
|---|---|---|
| model | ANY | Selected model filename string. |
| is_gguf | BOOL | `True` if the selected file has a `.gguf` extension. |

#### Clip Selector

Selects a CLIP / text encoder model file from the `clip` / `text_encoders` folder.

##### Outputs

| Name | Type | Description |
|---|---|---|
| clip | ANY | Selected model filename string. |
| is_gguf | BOOL | `True` if the selected file has a `.gguf` extension. |

#### Sampler Selector

Selects a sampler name from the full list of available ComfyUI samplers.

#### Scheduler Selector

Selects a scheduler name from the full list of available ComfyUI schedulers.

---

### String

#### Any To String

Converts one or more values of any type to a single string. Booleans become `true`/`false`, `None` becomes `"none"`, everything else uses `str()`.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| value1 … value16 | ANY | No | — | Auto-growing list of values to convert. `None` values are excluded. |
| mode | DYNAMIC | No | delimiter | **delimiter** = join all values with a separator string · **pattern** = insert values into a template using `$1`, `$2`, … placeholders (e.g. `"$1_$2"` with `hello` and `world` → `"hello_world"`) |

##### Outputs

| Name | Type | Description |
|---|---|---|
| string | STRING | Resulting string. |

#### String Split

Splits a string into a list by a delimiter.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| string | STRING | Yes | — | String to split. Must be connected. |
| delimiter | STRING | No | `\n` | Split character or string. Use `\n` for newline, `\t` for tab. |
| trim | BOOL | No | False | Trim leading and trailing whitespace from each part. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| list | STRING | List of string parts. |

#### String Join

Joins a list of strings into a single string.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| list | STRING | Yes | — | List to join. Must be connected. |
| delimiter | STRING | No | `\n` | Separator inserted between each item. Use `\n` for newline, `\t` for tab. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| string | STRING | Joined string. |

---

### Number

#### Nifty Math

Evaluates a free-form mathematical expression using up to 16 named inputs (`a`–`p`). Unconnected slots default to `0`. The result is cast to all three output types simultaneously.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| a … p | INT / FLOAT | No | 0 | Auto-growing variable inputs. The first two (`a`, `b`) are always visible; additional slots appear as needed up to 16. |
| expression | STRING | Yes | `a + b` | Expression to evaluate. See supported syntax below. |

##### Outputs

| Name | Type | Description |
|---|---|---|
| int | INT | Result cast to integer (truncated, not rounded). |
| float | FLOAT | Result as a float. |
| boolean | BOOL | `False` if result is `0` or `0.0`, `True` otherwise. |

##### Supported Syntax

| Category | Examples |
|---|---|
| Arithmetic | `a + b`, `a - b`, `a * b`, `a / b`, `a // b`, `a % b`, `a ** b` |
| Comparisons | `a == b`, `a != b`, `a < b`, `a > b`, `a <= b`, `a >= b` |
| Boolean logic | `a and b`, `a or b`, `not a` |
| Ternary | `a if a > 0 else b` |
| Math functions | `abs`, `round`, `min`, `max`, `pow`, `sqrt`, `floor`, `ceil`, `log`, `log2`, `log10`, `exp` |
| Trig | `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `radians`, `degrees`, `hypot` |
| Helpers | `clamp(v, lo, hi)`, `lerp(a, b, t)`, `remap(v, a, b, c, d)` |
| Constants | `pi`, `tau`, `e`, `inf` |

Division by zero returns `0`. Any other expression error raises a descriptive exception.

---

#### Nifty Seed

A seed node with integrated **New Seed** and **Random on Prompt** controls. Clicking **New Seed** immediately randomises the seed. **Random on Prompt** automatically generates a new random seed every time the queue is triggered.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| seed | INT | No | 0 | Seed value (0–1125899906842624). |

##### Outputs

| Name | Type | Description |
|---|---|---|
| seed | INT | The seed value, clamped to the valid range. |

---

### Utils

Experimental workflow organisation and debugging nodes.

#### Hidden Link

Passes any value through unchanged while hiding the connection wire on the incoming side. Useful for keeping graphs readable when a connection has to cross a large distance.

#### Bypass By Title

Bypasses a set of nodes by title when a boolean is `True`. Node titles are matched case-insensitively and support partial matches.

##### Inputs

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| bypass | BOOL | No | False | When `True`, the listed nodes are bypassed. |
| nodes | STRING | No | `` | Node titles to bypass, one per line. |
| search_from_root | BOOL | No | True | Search in the root graph even when called from inside a subgraph. |
| enforce | BOOL | No | True | Actively enforce the bypass state so it cannot be overridden. |

#### Bypass Switch By Title

A multi-option version of Bypass By Title. Each option has its own label and list of nodes to bypass. Selecting an option bypasses all nodes in that option's list and activates the others.

#### Node Chain Extender

Dynamically duplicates a node and chains the copies together, connecting specified slots between adjacent links.

#### Subgraph Labels

Assigns display labels to up to 10 subgraph ports. Experimental — requires subgraph support in your ComfyUI version.

#### Simple Title

A display-only node showing a text label in the graph. Useful for annotating sections of a workflow.

#### Debug Any

Displays any value as a text preview below the node. Primitives are shown as-is; complex types are serialized to JSON.

#### Preview Any

Displays up to 16 values simultaneously as inline text previews. For image tensors, shows a summary (`N images, WxH`) rather than rendering the images.
