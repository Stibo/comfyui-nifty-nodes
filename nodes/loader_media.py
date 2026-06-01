from ..core import media as nifty_media
from ..core import core as nifty_core
from comfy_api.latest import io

NODE_CATEGORY = "nifty/loader"

FRAME_RATE_INPUT = io.Int.Input(
    "force_frame_rate",
    default=0,
    min=0,
    max=240,
    step=1,
    tooltip="Force a specific frame rate for playback and resampling. 0 = keep the original frame rate of the file.",
)


# Load & Resize Image
class NiftyLoadResizeImage(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLoadResizeImage",
            display_name="Load & Resize Image",
            description="Load and resize an image using various scaling methods.",
            category=NODE_CATEGORY,
            search_aliases=[
                "load image",
                "open image",
                "import image",
                "image input",
                "upload image",
                "load resize image",
                "image loader",
                "load and resize",
            ],
            inputs=[
                io.Combo.Input(
                    "file",
                    options=[
                        "none",
                        *nifty_media.list_media_files(
                            nifty_media.IMAGE_TYPES | nifty_media.ANIMATION_TYPES
                        ),
                    ],
                    default="none",
                    upload=io.UploadType.image,
                    tooltip="Image or animation file to load. Select 'none' to pass through an empty output.",
                ),
                io.DynamicCombo.Input(
                    "resize",
                    options=nifty_media.RESIZE_TYPES_COMBO_OPTIONAL,
                    tooltip="Resize mode to apply after loading. 'off' loads the image at its original size.",
                ),
            ],
            outputs=[
                io.Image.Output(),
                io.Int.Output(id="width"),
                io.Int.Output(id="height"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        file: str,
        resize: dict,
    ) -> io.NodeOutput:
        if file == "none":
            return io.NodeOutput(None, 1, 1)

        media = await nifty_media.load_media(
            file=file, force_frame_rate=0, image_only=True
        )

        resized = await nifty_media.resize_images(
            images=media["images"],
            resize=resize,
        )

        return io.NodeOutput(
            resized["images"],
            int(resized["width"]),
            int(resized["height"]),
        )

    @classmethod
    def fingerprint_inputs(cls, file: str, **kwargs):
        return nifty_core.get_annotated_file_hash(file)

    @classmethod
    def validate_inputs(cls, file: str, **kwargs) -> bool | str:
        return nifty_core.validate_annotated_file(file, cls.__name__)


# Load & Resize Video
class NiftyLoadResizeVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLoadResizeVideo",
            display_name="Load & Resize Video",
            description="Load and resize a video using various scaling methods.",
            category=NODE_CATEGORY,
            search_aliases=[
                "load video",
                "open video",
                "import video",
                "video input",
                "upload video",
                "load resize video",
                "video loader",
                "load and resize video",
            ],
            inputs=[
                io.Combo.Input(
                    "file",
                    options=[
                        "none",
                        *nifty_media.list_media_files(
                            nifty_media.VIDEO_TYPES | nifty_media.ANIMATION_TYPES
                        ),
                    ],
                    default="none",
                    upload=io.UploadType.image,
                    tooltip="Video or animation file to load. Select 'none' to pass through an empty output.",
                ),
                FRAME_RATE_INPUT,
                io.DynamicCombo.Input(
                    "resize",
                    options=nifty_media.RESIZE_TYPES_COMBO_OPTIONAL,
                    tooltip="Resize mode to apply after loading. 'off' loads the video at its original size.",
                ),
            ],
            outputs=[
                io.Image.Output(),
                io.Int.Output(id="frames"),
                io.Int.Output(id="width"),
                io.Int.Output(id="height"),
                io.Int.Output(id="frame_rate"),
                io.Audio.Output(id="audio"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        file: str,
        force_frame_rate: int,
        resize: dict,
    ) -> io.NodeOutput:
        if file == "none":
            return io.NodeOutput(None, 1, 1, 1, 1, nifty_media.empty_audio())

        media = await nifty_media.load_media(
            file=file, force_frame_rate=force_frame_rate, image_only=False
        )

        resized = await nifty_media.resize_images(
            images=media["images"],
            resize=resize,
        )

        return io.NodeOutput(
            resized["images"],
            int(resized["batch_size"]),
            int(resized["width"]),
            int(resized["height"]),
            int(media["frame_rate"]),
            media["audio"],
        )

    @classmethod
    def fingerprint_inputs(cls, file: str, **kwargs):
        return nifty_core.get_annotated_file_hash(file)

    @classmethod
    def validate_inputs(cls, file: str, **kwargs) -> bool | str:
        return nifty_core.validate_annotated_file(file, cls.__name__)


# Load & Resize Media
class NiftyLoadResizeMedia(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="NiftyLoadResizeMedia",
            display_name="Load & Resize Media",
            description="Load and resize an image or a video using various scaling methods.",
            category=NODE_CATEGORY,
            search_aliases=[
                "load media",
                "open media",
                "import media",
                "load image or video",
                "media loader",
                "load and resize media",
                "universal loader",
            ],
            inputs=[
                io.Combo.Input(
                    "file",
                    options=[
                        "none",
                        *nifty_media.list_media_files(nifty_media.ALL_MEDIA_TYPES),
                    ],
                    default="none",
                    upload=io.UploadType.image,
                    tooltip="Image, video or animation file to load. Select 'none' to pass through an empty output.",
                ),
                FRAME_RATE_INPUT,
                io.DynamicCombo.Input(
                    "resize",
                    options=nifty_media.RESIZE_TYPES_COMBO_OPTIONAL,
                    tooltip="Resize mode to apply after loading. 'off' loads the file at its original size.",
                ),
            ],
            outputs=[
                io.Image.Output(),
                io.Int.Output(id="frames"),
                io.Int.Output(id="width"),
                io.Int.Output(id="height"),
                io.Int.Output(id="frame_rate"),
                io.Audio.Output(id="audio"),
                io.Boolean.Output(id="is_video"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        file: str,
        force_frame_rate: int,
        resize: dict,
    ) -> io.NodeOutput:
        if file == "none":
            return io.NodeOutput(None, 1, 1, 1, 1, nifty_media.empty_audio(), False)

        media = await nifty_media.load_media(
            file=file, force_frame_rate=force_frame_rate, image_only=False
        )

        resized = await nifty_media.resize_images(
            images=media["images"],
            resize=resize,
        )

        return io.NodeOutput(
            resized["images"],
            int(resized["batch_size"]),
            int(resized["width"]),
            int(resized["height"]),
            int(media["frame_rate"]),
            media["audio"],
            media["is_video"],
        )

    @classmethod
    def fingerprint_inputs(cls, file: str, **kwargs):
        return nifty_core.get_annotated_file_hash(file)

    @classmethod
    def validate_inputs(cls, file: str, **kwargs) -> bool | str:
        return nifty_core.validate_annotated_file(file, cls.__name__)


LOADER_MEDIA_CLASSES = {
    "NiftyLoadResizeImage": NiftyLoadResizeImage,
    "NiftyLoadResizeVideo": NiftyLoadResizeVideo,
    "NiftyLoadResizeMedia": NiftyLoadResizeMedia,
}
