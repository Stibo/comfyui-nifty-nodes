from comfy_api.latest import ComfyExtension

from .nodes.bundle import BUNDLE_CLASSES
from .nodes.image import IMAGE_CLASSES
from .nodes.latent import LATENT_CLASSES
from .nodes.logic import LOGIC_CLASSES
from .nodes.string import STRING_CLASSES
from .nodes.number import NUMBER_CLASSES
from .nodes.selector import SELECTOR_CLASSES
from .nodes.media import MEDIA_CLASSES
from .nodes.lora import LORA_CLASSES
from .nodes.model import MODEL_CLASSES
from .nodes.conditioning import CONDITIONING_CLASSES
from .nodes.sampling import SAMPLING_CLASSES
from .nodes.utils import UTILS_CLASSES

WEB_DIRECTORY = "./web"


class NiftyNodesExtension(ComfyExtension):
    async def get_node_list(self):
        return list(
            {
                **BUNDLE_CLASSES,
                **IMAGE_CLASSES,
                **LATENT_CLASSES,
                **LOGIC_CLASSES,
                **STRING_CLASSES,
                **NUMBER_CLASSES,
                **SELECTOR_CLASSES,
                **MEDIA_CLASSES,
                **LORA_CLASSES,
                **MODEL_CLASSES,
                **CONDITIONING_CLASSES,
                **SAMPLING_CLASSES,
                **UTILS_CLASSES,
            }.values()
        )


async def comfy_entrypoint():
    return NiftyNodesExtension()


__all__ = ["WEB_DIRECTORY"]
