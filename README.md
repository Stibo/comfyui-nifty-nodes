# ComfyUI Nifty Nodes

A collection of utility nodes for ComfyUI focused on workflow control, logic, and convenience.

## Installation

Install via [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) or clone manually:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/comfyui-nifty-nodes.git
```

---

## Features

- **Type-aware slots** — all `any`-type inputs/outputs automatically adopt the color and type of connected nodes, reset on disconnect or copy-paste
- **Lazy evaluation** — switch nodes only execute the branch they need
- **Subgraph-aware** — bypass nodes work recursively across all nesting levels

---

## Nodes

### Bundle

| Node | Description |
|------|-------------|
| **Bundle Pack** | Packs N values into a single `BUNDLE`. `count` controls how many value inputs are shown. |
| **Bundle Unpack** | Unpacks a `BUNDLE` into N outputs. `hide_links` hides outgoing wires visually. |
| **Bundle Get** | Gets a value from a bundle by 1-based index. |
| **Bundle Set** | Sets a value in a bundle at a 1-based index. |

### String

| Node | Description |
|------|-------------|
| **String Split** | Splits a string into a `STRING_LIST` by delimiter. |
| **String Join** | Joins a `STRING_LIST` into a single string. |

### Selectors

| Node | Description |
|------|-------------|
| **Diffusion Model Selector** | Lists all `.safetensors`/`.gguf` files from `models/unet` and `models/diffusion_models`. Outputs `model` (any) and `is_gguf` (BOOLEAN). |
| **Clip Selector** | Lists all `.safetensors`/`.gguf` files from `models/clip` and `models/text_encoders`. |
| **Sampler Selector** | Lists all samplers from ComfyUI's registry. |
| **Scheduler Selector** | Lists all schedulers from ComfyUI's registry. |

### Logic

| Node | Description |
|------|-------------|
| **Input Switch** | Returns one of two inputs based on a boolean. Lazy — only selected branch executes. |
| **Output Switch** | Routes one input to one of two outputs based on a boolean. |
| **Signal Switch** | Gates a signal — passes through when `passthrough=true`. |
| **Index Input Switch** | Selects one of N inputs by 1-based index. Dynamic slots up to 16. Lazy evaluation. |
| **Index Output Switch** | Routes input to one of N outputs by 1-based index. Dynamic slots up to 16. |
| **First Switch** | Returns the first non-None input. Lazy — evaluates in order until a value is found. |
| **Int Switch** | Returns one of two INT values based on a boolean. |
| **Float Switch** | Returns one of two FLOAT values based on a boolean. |
| **String Switch** | Returns one of two STRING values based on a boolean. |
| **Is None** | Returns true if the input is None. Optional `negate`. |
| **Boolean Negate** | Negates a boolean. |
| **String Compare** | Checks string equality. Optional `case_sensitive` and `negate`. |
| **String Contains** | Checks for a substring. Optional `case_sensitive` and `negate`. |
| **Number Compare** | Compares a float using `==`, `!=`, `>`, `<`, `>=`, `<=`. Optional `negate`. |

### Utils

| Node | Description |
|------|-------------|
| **None** | Outputs a `None` value. No inputs. |
| **Subgraph Labels** | Display-only label node for organizing subgraph interiors. Up to 10 labels. |
| **Hidden Link** | Passes a value through while hiding the wire. Shows semi-transparent on hover/select. |
| **Bypass by Title** | Toggles bypass on nodes by title across the whole workflow. Lines with `!` are inverted. `enforce` re-applies before every execution. |
| **Bypass Switch by Title** | Multi-configuration bypass. Define N named configurations each with a list of titles to bypass/activate. Select via combo. |
| **Node Duplicator** | Duplicates a node (by title) N times in a row, optionally connecting specified slots between copies. Excess copies are bypassed or deleted when count decreases. |
| **Magic Getter** | Auto-connects to the rightmost free output slot matching a given name. Useful for dynamic chain workflows. |
| **Sync VHS Preview** | Button that resets all VHS video previews to frame 0. Requires ComfyUI-VideoHelperSuite. |
| **Auto Sync VHS Preview** | Auto-syncs VHS previews after each generation. Requires ComfyUI-VideoHelperSuite. |

### Image

| Node | Description |
|------|-------------|
| **Calculate Image Size** | Calculates target width/height for resizing with snap-to-multiple support. Modes: `scale shorter/longer dimension`, `scale width/height`, `scale by multiplier`, `snap only`. `scale` field controls `upscale`/`downscale`/`any` direction. |
| **Image From Batch** | Extracts a slice from an image batch. Supports negative index and `length=-1` for all. |
| **Last Image From Batch** | Returns the last N images from a batch. |

### Latent

| Node | Description |
|------|-------------|
| **Latent From Batch** | Same as Image From Batch but for latents. |
| **Last Latent From Batch** | Returns the last N latents from a batch. |

---

## Bypass by Title — Syntax

Both **Bypass by Title** and **Bypass Switch by Title** use the same syntax in their node text fields:

```
My Node          ← bypassed when active
!My Other Node   ← activated when active (inverted with !)
```

Nodes inside a bypassed subgraph are never activated regardless of `!` prefix.

---

## Requirements

- ComfyUI (latest)
- ComfyUI-VideoHelperSuite (optional, for VHS Preview nodes)
