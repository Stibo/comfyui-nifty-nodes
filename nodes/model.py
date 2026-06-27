import re
import types
import torch
from comfy_api.latest import io
import comfy.ldm.modules.attention
import comfy.model_management as mm
import comfy.model_patcher
import comfy.samplers

NODE_CATEGORY = "nifty/model"


# Wan Video Normalized Attention Guidance (NAG)
# Fork from KJNodes, thanks to kijai for this awesome node!
class NiftyWanVideoNAG(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyWanVideoNAG",
            display_name="Wan Video NAG",
            category=NODE_CATEGORY,
            description=(
                "Normalized Attention Guidance (NAG) for WAN video models (T2V and I2V, 2.1 and 2.2). "
                "Replaces or complements CFG by applying guidance directly in attention space — "
                "stable across few-step and multi-step sampling. "
                "Recommended starting values — "
                "T2V multi-step: scale=11, tau=2.5, alpha=0.25 | "
                "T2V few-step (Lightning): scale=11-15, tau=2.5-5, alpha=0.25-0.5 | "
                "I2V (any): scale=11, tau=1.5-2.0, alpha=0.10-0.20 (lower to preserve reference image)"
            ),
            is_experimental=True,
            search_aliases=[
                "nag",
                "wan nag",
                "normalized attention guidance",
                "negative guidance",
                "cfg replacement",
                "wan video",
                "guidance",
            ],
            inputs=[
                io.Boolean.Input(
                    "enabled",
                    default=True,
                    tooltip=(
                        "Master switch. When false the node is a no-op: "
                        "model and conditioning pass through unchanged."
                    ),
                ),
                io.Model.Input("model"),
                io.Conditioning.Input(
                    "conditioning",
                    tooltip=(
                        "Your NEGATIVE conditioning (empty or negative prompt). "
                        "NAG uses this as its internal reference — the direction the model "
                        "is guided AWAY from in attention space. "
                        "Do NOT connect the positive conditioning here. "
                        "With cond_zero_out=True, this also flows to the CONDITIONING "
                        "output as a zeroed tensor for the sampler's negative slot."
                    ),
                ),
                io.Float.Input(
                    "nag_scale",
                    default=11.0,
                    min=0.0,
                    max=100.0,
                    step=0.001,
                    tooltip=(
                        "Guidance strength (φ), analogous to CFG scale. "
                        "Good range for WAN: 8–15. Setting to 0 disables NAG. "
                        "Tune this last — first settle on nag_tau and nag_alpha."
                    ),
                ),
                io.Float.Input(
                    "nag_alpha",
                    default=0.25,
                    min=0.0,
                    max=1.0,
                    step=0.001,
                    tooltip=(
                        "Blend weight (α) between NAG-guided and original positive attention (Eq. 10). "
                        "0 = no effect, 1 = full NAG. "
                        "T2V default: 0.25 | "
                        "I2V: use lower (0.10–0.20) to preserve the reference image. "
                        "Few-step (Lightning LoRA): can go higher (0.3–0.5)."
                    ),
                ),
                io.Float.Input(
                    "nag_tau",
                    default=2.5,
                    min=0.0,
                    max=10.0,
                    step=0.001,
                    tooltip=(
                        "L1-norm clipping threshold (τ): caps how far guided attention "
                        "deviates from positive attention (Eq. 9 in paper). "
                        "Lower = safer, less drift. Higher = stronger correction. "
                        "T2V default: 2.5 | "
                        "I2V: use lower (1.5–2.0) to preserve the reference image. "
                        "Few-step (Lightning LoRA): can go higher (3–5). "
                        "Paper ablation: both tau and alpha are critical — "
                        "without them output degrades sharply above scale=5."
                    ),
                ),
                io.Float.Input(
                    "nag_sigma_end",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip=(
                        "NAG is skipped when denoising sigma drops below this value. "
                        "0.0 = always active (correct for two-model high/low-noise pipelines). "
                        "For single-model pipelines: 0.75 achieves near-identical quality "
                        "with significantly less compute (paper authors' recommendation for flow-based models). "
                        "Note: WAN uses Rectified Flow where sigma runs 1.0 → 0.0."
                    ),
                ),
                io.Float.Input(
                    "nag_scale_end",
                    default=0.0,
                    min=0.0,
                    max=100.0,
                    step=0.001,
                    tooltip=(
                        "Sigma-adaptive scale: linearly interpolates from 'nag_scale' (at sigma=1.0) "
                        "to 'nag_scale_end' (at sigma=0.0). 0.0 = disabled (uses constant nag_scale). "
                    ),
                    optional=True,
                ),
                io.Combo.Input(
                    "input_type",
                    options=["default", "batch"],
                    tooltip=(
                        "default: sampler sends a [positive, negative] batch pair (standard CFG setup). "
                        "batch: single conditioning without a paired negative — use when sampling without CFG "
                        "(e.g. distilled/few-step WAN models with Lightning LoRA)."
                    ),
                ),
                io.Boolean.Input(
                    "inplace",
                    default=False,
                    tooltip=(
                        "Modify tensors in-place to reduce peak VRAM. "
                        "Slightly alters numerical results. Enable only if out of memory."
                    ),
                ),
                io.Boolean.Input(
                    "cond_zero_out",
                    default=True,
                    tooltip=(
                        "Output a zeroed-out (neutral) conditioning instead of the input conditioning. "
                        "Recommended: NAG handles guidance internally, so the sampler's negative slot "
                        "should be empty to avoid interference. "
                        "Disable only if intentionally stacking NAG on top of CFG."
                    ),
                ),
            ],
            outputs=[
                io.Model.Output(),
                io.Conditioning.Output(),
            ],
        )

    @staticmethod
    def _wan_compute_attention(self, query, context, transformer_options={}):
        k = self.norm_k(self.k(context))
        v = self.v(context)
        return comfy.ldm.modules.attention.optimized_attention(
            query, k, v, heads=self.num_heads, transformer_options=transformer_options
        ).flatten(2)

    @staticmethod
    def _wan_nag_attention(
        self, query, context_positive, nag_context, transformer_options={}
    ):
        x_positive = NiftyWanVideoNAG._wan_compute_attention(
            self, query, context_positive, transformer_options
        )
        x_negative = NiftyWanVideoNAG._wan_compute_attention(
            self, query, nag_context, transformer_options
        )
        return x_positive, x_negative

    @staticmethod
    def _normalized_attention_guidance(self, x_positive, x_negative, current_scale):
        if self.inplace:
            nag_guidance = (
                x_negative.mul_(current_scale - 1)
                .neg_()
                .add_(x_positive, alpha=current_scale)
            )
            del x_negative
        else:
            nag_guidance = x_negative * (current_scale - 1)
            del x_negative
            nag_guidance = (x_positive * current_scale).sub_(nag_guidance)

        norm_positive = torch.norm(x_positive, p=1, dim=-1, keepdim=True)
        norm_guidance = torch.norm(nag_guidance, p=1, dim=-1, keepdim=True)

        scale = norm_guidance / norm_positive
        torch.nan_to_num_(scale, nan=10.0)
        mask = scale > self.nag_tau
        del scale

        adjustment = (norm_positive * self.nag_tau) / (norm_guidance + 1e-7)
        del norm_positive, norm_guidance

        nag_guidance.mul_(torch.where(mask, adjustment, 1.0))
        del mask, adjustment

        if self.inplace:
            return nag_guidance.sub_(x_positive).mul_(self.nag_alpha).add_(x_positive)
        else:
            nag_guidance.mul_(self.nag_alpha)
            return nag_guidance.add_(x_positive * (1 - self.nag_alpha))

    @staticmethod
    def _sigma_below_end(self, transformer_options):
        if self.nag_sigma_end <= 0.0:
            return False
        sigmas = transformer_options.get("sigmas", None)
        if sigmas is None or sigmas.numel() == 0:
            return False
        return sigmas[0].item() < self.nag_sigma_end

    @staticmethod
    def _standard_crossattn(self, x, context, transformer_options):
        """Plain cross-attention without NAG, used for sigma early-exit."""
        q = self.norm_q(self.q(x))
        k = self.norm_k(self.k(context))
        v = self.v(context)
        return self.o(
            comfy.ldm.modules.attention.optimized_attention(
                q, k, v, heads=self.num_heads, transformer_options=transformer_options
            )
        )

    @staticmethod
    def _wan_crossattn_forward_nag(self, x, context, transformer_options={}, **kwargs):
        if NiftyWanVideoNAG._sigma_below_end(self, transformer_options):
            return NiftyWanVideoNAG._standard_crossattn(
                self, x, context, transformer_options
            )

        current_scale = self.nag_scale
        if getattr(self, "nag_scale_end", 0.0) > 0.0:
            sigmas = transformer_options.get("sigmas", None)
            if sigmas is not None and sigmas.numel() > 0:
                sigma_val = sigmas[0].item()
                current_scale = self.nag_scale_end + sigma_val * (
                    self.nag_scale - self.nag_scale_end
                )

        if self.input_type == "default":
            if context.shape[0] == 1:
                x_pos, context_pos = x, context
                x_neg, context_neg = None, None
            else:
                x_pos, x_neg = torch.chunk(x, 2, dim=0)
                context_pos, context_neg = torch.chunk(context, 2, dim=0)
        else:  # batch
            x_pos, context_pos = x, context
            x_neg, context_neg = None, None

        q_pos = self.norm_q(self.q(x_pos))
        nag_context = self.nag_context
        if self.input_type == "batch":
            nag_context = nag_context.repeat(x_pos.shape[0], 1, 1)
        del x_pos

        x_positive, x_negative = NiftyWanVideoNAG._wan_nag_attention(
            self,
            q_pos,
            context_pos,
            nag_context,
            transformer_options=transformer_options,
        )
        del context_pos, q_pos

        x_pos_out = NiftyWanVideoNAG._normalized_attention_guidance(
            self, x_positive, x_negative, current_scale
        )
        del x_positive, x_negative

        if x_neg is not None and context_neg is not None:
            q_neg = self.norm_q(self.q(x_neg))
            k_neg = self.norm_k(self.k(context_neg))
            v_neg = self.v(context_neg)
            x_neg_out = comfy.ldm.modules.attention.optimized_attention(
                q_neg,
                k_neg,
                v_neg,
                heads=self.num_heads,
                transformer_options=transformer_options,
            )
            x = torch.cat([x_pos_out, x_neg_out], dim=0)
        else:
            x = x_pos_out

        return self.o(x)

    @staticmethod
    def _wan_i2v_crossattn_forward_nag(
        self, x, context, context_img_len=None, transformer_options=None, **kwargs
    ):
        if transformer_options is None:
            transformer_options = {}
        if isinstance(context_img_len, dict):
            transformer_options = context_img_len
            context_img_len = transformer_options.get(
                "context_img_len",
                kwargs.get("context_img_len", getattr(self, "context_img_len", 0)),
            )
        elif context_img_len is None:
            context_img_len = kwargs.get(
                "context_img_len", getattr(self, "context_img_len", 0)
            )

        context_img = context[:, :context_img_len]
        context = context[:, context_img_len:]

        q_img = self.norm_q(self.q(x))
        k_img = self.norm_k_img(self.k_img(context_img))
        v_img = self.v_img(context_img)
        img_x = comfy.ldm.modules.attention.optimized_attention(
            q_img,
            k_img,
            v_img,
            heads=self.num_heads,
            transformer_options=transformer_options,
        )
        del q_img, k_img, v_img, context_img

        if NiftyWanVideoNAG._sigma_below_end(self, transformer_options):
            q = self.norm_q(self.q(x))
            k = self.norm_k(self.k(context))
            v = self.v(context)
            return self.o(
                comfy.ldm.modules.attention.optimized_attention(
                    q,
                    k,
                    v,
                    heads=self.num_heads,
                    transformer_options=transformer_options,
                )
                + img_x
            )

        current_scale = self.nag_scale
        if getattr(self, "nag_scale_end", 0.0) > 0.0:
            sigmas = transformer_options.get("sigmas", None)
            if sigmas is not None and sigmas.numel() > 0:
                sigma_val = sigmas[0].item()
                current_scale = self.nag_scale_end + sigma_val * (
                    self.nag_scale - self.nag_scale_end
                )

        if context.shape[0] == 2:
            x, x_real_negative = torch.chunk(x, 2, dim=0)
            context_positive, context_negative = torch.chunk(context, 2, dim=0)
        else:
            context_positive = context
            context_negative = None

        q = self.norm_q(self.q(x))
        x_positive, x_negative = NiftyWanVideoNAG._wan_nag_attention(
            self,
            q,
            context_positive,
            self.nag_context,
            transformer_options=transformer_options,
        )
        del q, context_positive
        x = NiftyWanVideoNAG._normalized_attention_guidance(
            self, x_positive, x_negative, current_scale
        )
        del x_positive, x_negative

        if context_negative is not None:
            q_real_negative = self.norm_q(self.q(x_real_negative))
            k_real_negative = self.norm_k(self.k(context_negative))
            v_real_negative = self.v(context_negative)
            x_real_negative = comfy.ldm.modules.attention.optimized_attention(
                q_real_negative,
                k_real_negative,
                v_real_negative,
                heads=self.num_heads,
                transformer_options=transformer_options,
            )
            x = torch.cat([x, x_real_negative], dim=0)

        return self.o(x + img_x)

    @staticmethod
    def _zero_out_conditioning(conditioning):
        """Mirrors ConditioningZeroOut: zeros the embedding tensor and pooled_output."""
        c = []
        for t in conditioning:
            d = t[1].copy()
            pooled_output = d.get("pooled_output", None)
            if pooled_output is not None:
                d["pooled_output"] = torch.zeros_like(pooled_output)
            conditioning_lyrics = d.get("conditioning_lyrics", None)
            if conditioning_lyrics is not None:
                d["conditioning_lyrics"] = torch.zeros_like(conditioning_lyrics)
            n = [torch.zeros_like(t[0]), d]
            c.append(n)
        return c

    @staticmethod
    def _make_wan_cross_attention_patch(
        obj,
        context,
        nag_scale,
        nag_alpha,
        nag_tau,
        nag_sigma_end,
        nag_scale_end,
        i2v,
        input_type,
        inplace,
    ):
        def wrapped(self_module, *args, **kwargs):
            self_module.nag_context = context
            self_module.nag_scale = nag_scale
            self_module.nag_alpha = nag_alpha
            self_module.nag_tau = nag_tau
            self_module.nag_sigma_end = nag_sigma_end
            self_module.nag_scale_end = nag_scale_end
            self_module.input_type = input_type
            self_module.inplace = inplace
            fn = (
                NiftyWanVideoNAG._wan_i2v_crossattn_forward_nag
                if i2v
                else NiftyWanVideoNAG._wan_crossattn_forward_nag
            )
            return fn(self_module, *args, **kwargs)

        return types.MethodType(wrapped, obj)

    @classmethod
    def execute(
        cls,
        enabled: bool,
        model,
        conditioning,
        nag_scale: float,
        nag_tau: float,
        nag_alpha: float,
        nag_sigma_end: float = 0.0,
        nag_scale_end: float = 0.0,
        input_type: str = "default",
        inplace: bool = False,
        cond_zero_out: bool = True,
    ) -> io.NodeOutput:

        if not enabled or nag_scale == 0.0:
            return io.NodeOutput(model, conditioning)

        device = mm.get_torch_device()
        dtype = mm.unet_dtype()

        model_clone = model.clone()
        diffusion_model = model_clone.get_model_object("diffusion_model")

        try:
            te_device = next(diffusion_model.text_embedding.parameters()).device
            if te_device != device:
                diffusion_model.text_embedding.to(device)
        except StopIteration:
            diffusion_model.text_embedding.to(device)

        context_tensors = []
        for c in conditioning:
            t = c[0].to(device, dtype)
            try:
                t = diffusion_model.text_embedding(t)
            except Exception:
                pass
            context_tensors.append(t)
        context = torch.cat(context_tensors, dim=1) if context_tensors else None

        i2v = "I2V" in type(model.model.model_config).__name__

        for idx, block in enumerate(diffusion_model.blocks):
            patched_attn = cls._make_wan_cross_attention_patch(
                block.cross_attn,
                context,
                nag_scale,
                nag_alpha,
                nag_tau,
                nag_sigma_end,
                nag_scale_end,
                i2v,
                input_type,
                inplace,
            )
            model_clone.add_object_patch(
                f"diffusion_model.blocks.{idx}.cross_attn.forward", patched_attn
            )

        out_cond = (
            cls._zero_out_conditioning(conditioning) if cond_zero_out else conditioning
        )
        return io.NodeOutput(model_clone, out_cond)


# Wan Video Skip Layer Guidange (SLG)
class NiftyWanVideoSLG(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyWanVideoSLG",
            display_name="Nifty Wan Video SLG",
            category=NODE_CATEGORY,
            description=(
                "WAN-native Spatiotemporal Skip Guidance (STG/SLG) — no TeaCache required. "
                "STG-A (default): zeros self-attention contribution only — less perturbation, "
                "lower flickering risk. STG-R: entire block becomes identity — stronger. "
                "Works at CFG=1 (LightX2V). Paper: arxiv 2411.18664 (CVPR 2025)."
            ),
            is_experimental=True,
            search_aliases=[
                "slg",
                "stg",
                "skip layer guidance",
                "spatiotemporal skip guidance",
                "wan slg",
                "wan video",
                "skip layer",
                "pag",
                "guidance",
                "wan 2.1",
                "wan 2.2",
                "lightx2v",
            ],
            inputs=[
                io.Boolean.Input(
                    "enabled",
                    default=True,
                    tooltip="When false, node is a no-op and passes the input model unchanged.",
                ),
                io.Model.Input("model"),
                io.String.Input(
                    "blocks",
                    default="9, 10",
                    multiline=False,
                    tooltip=(
                        "Comma-separated block indices. Supports ranges: '9-11' = 9, 10, 11. "
                        "WAN 2.2 = 40 layers. Blocks 9, 10 empirically recommended. "
                        "Fewer blocks = safer. Start with '10' alone if flickering occurs."
                    ),
                ),
                io.Combo.Input(
                    "mode",
                    options=["STG-A", "STG-R"],
                    tooltip=(
                        "STG-A (default): zeros self-attention only — cross-attn and FFN still run. "
                        "Less perturbation, lower flickering risk. Recommended for WAN + few-step. "
                        "STG-R: entire block becomes identity. Stronger but more flickering at 2-3 steps."
                    ),
                ),
                io.Float.Input(
                    "scale",
                    default=1.0,
                    min=0.0,
                    max=10.0,
                    step=0.05,
                    tooltip=(
                        "Guidance strength. Works at CFG=1. "
                        "LightX2V (2-3 HN steps): STG-A max ~2.0–2.5, STG-R max ~1.5. "
                        "Use rescaling_scale to push higher without flickering."
                    ),
                ),
                io.Float.Input(
                    "start_percent",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.001,
                    tooltip=(
                        "Start of active range as fraction of the FULL denoising schedule "
                        "(HN + LN samplers combined). Percentages are ABSOLUTE."
                    ),
                ),
                io.Float.Input(
                    "end_percent",
                    default=1.0,
                    min=0.0,
                    max=1.0,
                    step=0.001,
                    tooltip=(
                        "End of active range. Formula: HN_steps / total_steps. "
                        "4-step (2+2): 0.5. 6-step (3+3): 0.5. "
                        "Default 1.0 = active for all sigmas this model processes."
                    ),
                ),
                io.Float.Input(
                    "rescaling_scale",
                    default=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    tooltip=(
                        "Normalizes correction std to match cond_pred std before scale. "
                        "0.0 = disabled. 0.3–0.5 = recommended if scale causes flickering. "
                        "1.0 = fully normalized."
                    ),
                    optional=True,
                ),
                io.Float.Input(
                    "scale_end",
                    default=0.0,
                    min=0.0,
                    max=10.0,
                    step=0.05,
                    tooltip=(
                        "Sigma-adaptive scale: linearly interpolates from 'scale' (at sigma_start) "
                        "to 'scale_end' (at sigma_end). 0.0 = disabled (constant scale). "
                        "Example: scale=2.0, scale_end=0.5 — stronger guidance at high noise, "
                        "fading toward low noise. Useful since STG has most structural impact early."
                    ),
                    optional=True,
                ),
            ],
            outputs=[io.Model.Output()],
        )

    @classmethod
    def execute(
        cls,
        enabled: bool,
        model,
        blocks: str,
        mode: str,
        scale: float,
        start_percent: float,
        end_percent: float,
        rescaling_scale: float = 0.0,
        scale_end: float = 0.0,
    ) -> io.NodeOutput:

        if not enabled or scale == 0.0:
            return io.NodeOutput(model)

        block_indices = []
        for part in re.split(r"[,\s]+", blocks.strip()):
            part = part.strip()
            if not part:
                continue
            try:
                range_match = re.match(r"^(\d+)-(\d+)$", part)
                if range_match:
                    block_indices.extend(
                        range(int(range_match.group(1)), int(range_match.group(2)) + 1)
                    )
                elif re.match(r"^\d+$", part):
                    block_indices.append(int(part))
            except ValueError:
                continue
        block_indices = sorted(set(block_indices))

        if not block_indices:
            return io.NodeOutput(model)

        model_sampling = model.get_model_object("model_sampling")
        sigma_start = model_sampling.percent_to_sigma(start_percent)
        sigma_end = model_sampling.percent_to_sigma(end_percent)
        use_adaptive_scale = scale_end > 0.0 and sigma_start > sigma_end

        diffusion_model = model.get_model_object("diffusion_model")
        max_blocks = len(diffusion_model.blocks)

        def post_cfg_function(args):
            model_obj = args["model"]
            cfg_result = args["denoised"]
            sigma = args["sigma"]
            x = args["input"]
            cond = args["cond"]
            model_options = args["model_options"].copy()

            cond_pred = args["cond_denoised"]
            if cond_pred is None:
                cond_pred = cfg_result

            sigma_ = sigma[0].item()
            if not (sigma_end <= sigma_ <= sigma_start):
                return cfg_result

            if use_adaptive_scale:
                t = (sigma_ - sigma_end) / (sigma_start - sigma_end)
                current_scale = scale_end + t * (scale - scale_end)
            else:
                current_scale = scale

            if current_scale == 0.0:
                return cfg_result

            if "transformer_options" not in model_options:
                model_options["transformer_options"] = {}

            restorations = []

            try:
                for idx in block_indices:
                    if idx >= max_blocks:
                        continue

                    if mode == "STG-A":
                        block_module = diffusion_model.blocks[idx]
                        if hasattr(block_module, "self_attn"):
                            self_attn = block_module.self_attn
                            original_forward = getattr(self_attn, "forward", None)
                            restorations.append((self_attn, original_forward))

                            def zero_self_attn(tensor_in, *a, **kw):
                                return torch.zeros_like(tensor_in)

                            self_attn.forward = zero_self_attn
                    else:

                        def wan_stg_r_patch(patch_args, extra_args=None):
                            return {"img": patch_args["img"]}

                        model_options = (
                            comfy.model_patcher.set_model_options_patch_replace(
                                model_options,
                                wan_stg_r_patch,
                                "dit",
                                "double_block",
                                idx,
                            )
                        )

                (slg,) = comfy.samplers.calc_cond_batch(
                    model_obj, [cond], x, sigma, model_options
                )

            finally:
                for obj, orig_fn in restorations:
                    if orig_fn is not None:
                        obj.forward = orig_fn
                    else:
                        try:
                            del obj.forward
                        except AttributeError:
                            pass

            raw_correction = cond_pred - slg

            if rescaling_scale > 0.0:
                std_cond = torch.std(cond_pred)
                std_corr = torch.std(raw_correction)
                if std_corr > 1e-8:
                    factor = std_cond / std_corr
                    raw_correction = raw_correction * (
                        rescaling_scale * factor + (1.0 - rescaling_scale)
                    )

            return cfg_result + raw_correction * current_scale

        m = model.clone()
        m.set_model_sampler_post_cfg_function(post_cfg_function)
        return io.NodeOutput(m)


MODEL_CLASSES = {
    "NiftyWanVideoNAG": NiftyWanVideoNAG,
    "NiftyWanVideoSLG": NiftyWanVideoSLG,
}
