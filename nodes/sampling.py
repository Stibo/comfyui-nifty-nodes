import comfy.sample
from comfy_api.latest import io

NODE_CATEGORY = "nifty/sampling"


# Random Noise
class NiftyRandomNoise(io.ComfyNode):
    class _Noise:
        def __init__(self, seed):
            self.seed = seed

        def generate_noise(self, input_latent):
            latent_image = input_latent["samples"]
            batch_inds = input_latent.get("batch_index")
            return comfy.sample.prepare_noise(latent_image, self.seed, batch_inds)

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="NiftyRandomNoise",
            display_name="Nifty Random Noise",
            category=NODE_CATEGORY,
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
            outputs=[io.Noise.Output()],
        )

    @classmethod
    def execute(cls, seed, **kwargs) -> io.NodeOutput:
        return io.NodeOutput(cls._Noise(seed))


SAMPLING_CLASSES = {
    "NiftyRandomNoise": NiftyRandomNoise,
}
