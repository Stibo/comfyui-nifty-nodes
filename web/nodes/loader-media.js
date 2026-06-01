import { app } from "../../../scripts/app.js";
import { NiftyNode } from "../core/node.js";
import { uploadFile } from "../../../scripts/utils.js";

const IMAGE_EXTENSIONS = [".png", ".pjp", ".jfif", ".jpe", ".pjpeg", ".jpeg", ".jpg", ".webp"];
const ANIMATION_EXTENSIONS = [".gif", ".apng", ".webp", ".avif"];
const VIDEO_EXTENSIONS = [".mp4", ".m4v", ".mkv", ".webm"];
const NONE_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAlgAAAGQAgMAAAAPW/YLAAAADFBMVEUAAAD///////////84wDuoAAAABHRSTlMAMyUWiZlY5QAAAnxJREFUeNrt2DFuE0EUh/GHV1u4IFQ+go9AkSbKEVLkvw7BQj5Aihwhl9gjUGAKOIIlakofwQ0VDQ1Cgn1vEx7WgkTDTCS+X+FsskU+zcx6d8cAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAv/ds+9lC8+mdPfj6cHj2dmfl6aLp1Vk4SDc2aGWn0sbcifTSytN6KNDtfYG6XWR96KXVmBpni9N6L+nKBksNNpH1UYM7n1fF2eL0SrofmT4SIuug+0Gaa9BZcXqh69fScDSTrnt1kdVrK13ECHZvfNxK8+XU9Nr5wKysiYTWl/6p1sPpvd7bocLi8gJbesxzbYYjT2h95c98PhutvPfCSpMXzXVutvCjSGhjhfWXPrFrbyu/5mMxPfUx6v0oxqiN63G/ihNjYGlxET7xDvk/j882YhadD97dGFhaTNBsyGpiiUdCGzHLztfbbjwqzWMiaxYLO8ao/RmzlJnHWWGZFRPpIUdZXe2sWN3jtGXWwldV/F7KNOs8Eo6y9tWz5r/P+j74UjMrLj//8WuWwmPL6ski619lXVkV0y+I4yvx0urQ9Ov0kWVNbj41Hmmmt+rb6a16UT3rTw82VWRWPgZmVkxpcZl1/NCcWe14HZRvy6x8xcisuTb+x42Vlln5QpZZT8aXf/8oK7Py9TWzGnW+3iq+YuTLfmb5TfHGToYTZWVWbo0cZS2lrbS2sjIrN5KOsuZy9ZZ8brtlVpxxFb8gcpMyswaHSruBmZVbupkVrXdWSW6AT5xtvxkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMD/7QcRNhqO/SFQDAAAAABJRU5ErkJggg==";

async function getPreviewImage(url) {
    return new Promise((resolve, reject) => {
        const video = document.createElement("video");
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        video.muted = true;
        video.playsInline = true;
        video.preload = "auto";
        video.crossOrigin = "anonymous";

        const timeout = setTimeout(() => {
            reject(new Error("video timeout"));
        }, 10000);

        video.onloadeddata = () => {
            video.currentTime = 0;
        };

        video.onseeked = () => {
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 360;

            ctx.drawImage(video, 0, 0);

            clearTimeout(timeout);
            resolve(canvas.toDataURL("image/jpeg", 0.85));
        };

        video.onerror = () => {
            clearTimeout(timeout);
            reject(new Error("video load error"));
        };

        video.src = url;
    });
}

const OrigImage = window.Image;

window.Image = class extends OrigImage {
    set src(url) {
		if(url.includes("/api/view")) {
			if(url.includes("filename=none")) {
                super.src = NONE_IMAGE;
				return;
            }

            if(VIDEO_EXTENSIONS.some(ext => url.toLowerCase().includes(ext))) {
                getPreviewImage(url).then(preview => {
                    super.src = preview;
                }).catch(() => {
                    super.src = url;
                });

                return;
            }
		}

		super.src = url;
    }
    get src() {
		return super.src;
	}
};

app.registerExtension({
	name: "comfyui.nifty.nodes.loader-media",

	async beforeRegisterNodeDef(nodeType, nodeData) {		
		// Load & Resize (Image, Video, Media)
		if(nodeData.name.startsWith("NiftyLoadResize")) {
			const LoadResize = new NiftyNode(nodeType, nodeData, {
				properties: [
					["show_none", true, "boolean"]
				]
			});

			LoadResize.applyHook("onAfterGraphConfigured", function(node) {
				const showNone = node.properties?.show_none ?? true;
				const fileWidget = this.getWidget(node, 'file');	
				const uploadWidget = this.getWidget(node, "upload");

				if(!showNone) {
					fileWidget.options.values = fileWidget?.options.values.filter(item => item !== "none");
				}

				uploadWidget.callback = async () => {
					let accept = new Set();

					if(node.type !== "NiftyLoadResizeVideo") {
						accept = new Set([...accept, ...IMAGE_EXTENSIONS, ...ANIMATION_EXTENSIONS]);
					}

					if(node.type !== "NiftyLoadResizeImage") {
						accept = new Set([...accept, ...VIDEO_EXTENSIONS, ...ANIMATION_EXTENSIONS]);
					}

					const file = await uploadFile(
						[...accept].join(",")
					);

					const formData = new FormData();
					formData.append("image", file);
					formData.append("type", "input");
					formData.append("subfolder", "");
					formData.append("overwrite", "true");
		
					const resp = await app.api.fetchApi("/upload/image", {
						method: "POST",
						body: formData,
						signal: AbortSignal.timeout(120_000)
					})

					if(!resp.ok) {
						throw new Error(`Upload failed: ${resp.status} ${resp.statusText}`);
					}

					const data = await resp.json();
					const fileName =  data.subfolder ? `${data.subfolder}/${data.name}` : data.name;

					fileWidget.value = fileName;
					fileWidget.callback?.(fileName);

					if(fileWidget.options && Array.isArray(fileWidget.options.values)) {
						const valuesList = fileWidget?.options.values.filter(item => item !== "none");

						valuesList.push(fileName);
						valuesList.sort();

						if(showNone) {
							valuesList.unshift("none");
						}
		
						fileWidget.options.values = valuesList;
					}
				}
			});

			LoadResize.applyHook("onPropertyChanged", function(node, name, value) {
				if(name === "show_none") {
					const fileWidget = this.getWidget(node, 'file');
					const valuesList = fileWidget?.options.values.filter(item => item !== "none");
	
					if(value) {
						valuesList.unshift("none");
					}
					
					fileWidget.options.values = valuesList;
				}
			});
		}
	}
});