import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { NiftyNode } from "../core/node.js";
import { NiftyHelpers, NiftyDraw } from "../core/helpers.js";

async function getDynamicPrompt(node, newSeed = true) {
	const seedWidget = NiftyHelpers.getWidget(node, "seed");
	const templateWidget = NiftyHelpers.getWidget(node, "template");
	const promptWidget = NiftyHelpers.getWidget(node, "prompt");

	if(!seedWidget || !templateWidget || !promptWidget) {
		return false;
	}

    const template = templateWidget?.value ?? "";

    let seed = seedWidget.value ?? 0;
    
    if(newSeed) {
	    seed = Math.floor(Math.random() * (seedWidget.options.max + 1));
    }

    const response = await api.fetchApi("/nifty/get_dynamic_prompt", {
        method: "POST",
        body: JSON.stringify({
            template: template,
            seed: seed
        })
    });

    const data = await response?.json();
    const prompt = data?.prompt ?? templateWidget.value;

	seedWidget.value = seed;
	seedWidget.callback?.(seed);

	promptWidget.value = prompt;
	promptWidget.callback?.(prompt);

	node.setDirtyCanvas(true, true);

	return {
        seed: seed,
        template: template,
        prompt: prompt
    };
}

app.registerExtension({
    name: "comfyui.nifty.nodes.string",

    async getCustomWidgets(app) {
		return {
			NIFTY_DYNAMIC_PROMPT_ACTIONS: (node, inputName, inputData) => {
				const widgetHeight = NiftyDraw.height;

				const widget = {
					type: "NIFTY_DYNAMIC_PROMPT_ACTIONS",
					name: inputName,
					value: inputData?.[1] ?? { randomOnPrompt: true },
					options: inputData[1] ?? {},

					_node: node,
					_subgraphNode: null,
					_drawRects: [],

					computeSize(width) {
						return [width, widgetHeight];
					},

					serializeValue() {
						return this.value;
					},

					draw(ctx, node, widgetWidth, y) {
						if(node !== this._node) {
							this._subgraphNode = node;
						}

						this._drawRects = [];

						const isPromoted = false;
						const isRandomOnPrompt = widget.value?.randomOnPrompt ?? true;

						const buttonCols = NiftyDraw.calculateColumns({
							widgetWidth: widgetWidth,
							columns: {
								generate: "33.33333%",
								new: "33.33333%",
								prompt: "33.33333%"
							}
						});

						ctx.save();

						// Generate prompt
						this._drawRects.generate_button = NiftyDraw.buttonWidget(ctx, {
							label: "✨ Generate",
							x: buttonCols.generate.x,
							y: y,
							width: buttonCols.generate.width,
							promoted: isPromoted,
							pressed: NiftyDraw.isPressed(node, this, "generate")
						});

						// New random prompt
						this._drawRects.new_button = NiftyDraw.buttonWidget(ctx, {
							label: "🎲 New Prompt",
							x: buttonCols.new.x,
							y: y,
							width: buttonCols.new.width,
							promoted: isPromoted,
							pressed: NiftyDraw.isPressed(node, this, "new")
						});

						// Random prompt on queue
						this._drawRects.prompt_button = NiftyDraw.buttonWidget(ctx, {
							label: isRandomOnPrompt ? "✅ Random" : "🔀 Random",
							x: buttonCols.prompt.x,
							y: y,
							width: buttonCols.prompt.width,
							active: isRandomOnPrompt,
							promoted: isPromoted,
							pressed: NiftyDraw.isPressed(node, this, "prompt")
						});

						ctx.restore();
					},

					async mouse(event, pos, node) {
						if(!["pointerdown", "mousedown"].includes(event.type)) {
							return;
						}

						const [mouseX, mouseY] = pos;

						if(NiftyHelpers.containsPointer(mouseX, mouseY, this._drawRects.generate_button)) {
							await getDynamicPrompt(this._node, false);
							NiftyDraw.setPressed(node, widget, "generate");
						} else if(NiftyHelpers.containsPointer(mouseX, mouseY, this._drawRects.new_button)) {
							await getDynamicPrompt(this._node, true);
							NiftyDraw.setPressed(node, widget, "new");
						} else if(NiftyHelpers.containsPointer(mouseX, mouseY, this._drawRects.prompt_button)) {
							widget.value = {
								...widget.value,
								randomOnPrompt: !(widget.value?.randomOnPrompt ?? true)
							};

							NiftyDraw.setPressed(node, widget, "prompt");
							widget.callback?.(widget.value);
							node.setDirtyCanvas(true, true);
						}
					},
				};

				node.addCustomWidget(widget);

				return { widget };
			}
		};
	},

    async setup() {
        const origQueuePrompt = app.queuePrompt;

		// Random number for Seed
		app.queuePrompt = async function(...args) {
			const promptNodes = NiftyHelpers.findNodes({
				name: "NiftyDynamicPrompt"
			});

			for(const promptNode of promptNodes) {
				const enabledWidget = NiftyHelpers.getWidget(promptNode, "enabled");
				const actionWidget = NiftyHelpers.getWidget(promptNode, "prompt_actions");

				if((enabledWidget?.value ?? true) && (actionWidget?.value?.randomOnPrompt ?? true)) {
					await getDynamicPrompt(promptNode);
				}
			}
			
			return await origQueuePrompt.apply(this, args);
		};
    },

    async beforeRegisterNodeDef(nodeType, nodeData) {
        // Dynamic Prompt
        if(nodeData.name === "NiftyDynamicPrompt") {
            const DynamicPrompt = new NiftyNode(nodeType, nodeData, {
                width: 600,
                height: 560
            });
        }
    }
});