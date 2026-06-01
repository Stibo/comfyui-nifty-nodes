import { app } from "../../../scripts/app.js";
import { NiftyHelpers, NiftyDraw } from "../core/helpers.js";
import { NiftyNode } from "../core/node.js";

function setRandomSeed(node) {
	const seedWidget = NiftyHelpers.getWidget(node, "seed");

	if(!seedWidget) {
		return;
	}

	const seed = Math.floor(Math.random() * (seedWidget.options.max + 1));

	seedWidget.value = seed;
	seedWidget.callback?.(seed);
	node.setDirtyCanvas(true, true);

	return seed;
}

app.registerExtension({
	name: "comfyui.nifty.nodes.number",

	async getCustomWidgets(app) {
		return {
			NIFTY_SEED_ACTIONS: (node, inputName, inputData) => {
				const widgetHeight = NiftyDraw.height;

				const widget = {
					type: "NIFTY_SEED_ACTIONS",
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
								new: "50%",
								prompt: "50%"
							}
						});

						ctx.save();

						// New fixed seed
						this._drawRects.new_button = NiftyDraw.buttonWidget(ctx, {
							label: "🎲 New Seed",
							x: buttonCols.new.x,
							y: y,
							width: buttonCols.new.width,
							promoted: isPromoted,
							pressed: NiftyDraw.isPressed(node, this, "new")
						});

						// Random seed on prompt
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

						if(NiftyHelpers.containsPointer(mouseX, mouseY, this._drawRects.new_button)) {
							setRandomSeed(this._node);
							NiftyDraw.setPressed(node, widget, "new");
						} else if(NiftyHelpers.containsPointer(mouseX, mouseY, this._drawRects.prompt_button)) {
							widget.value = {
								...widget.value,
								randomOnPrompt: !widget.value?.randomOnPrompt
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
			const seedNodes = NiftyHelpers.findNodes({
				name: "NiftySeed"
			});

			for(const seedNode of seedNodes) {
				const actionWidget = NiftyHelpers.getWidget(seedNode, "seed_actions");

				if(actionWidget?.value?.randomOnPrompt ?? true) {
					setRandomSeed(seedNode);
				}
			}
			
			return await origQueuePrompt.apply(this, args);
		};
	},

	async beforeRegisterNodeDef(nodeType, nodeData) {
		// Nifty Seed
		if(nodeData.name === "NiftySeed") {
			const NiftySeed = new NiftyNode(nodeType, nodeData, {});

			NiftySeed.applyHook("onNodeCreated", function(node) {
				app.widgets.NIFTY_SEED_ACTIONS(
					node,
					"seed_actions",
					["NIFTY_SEED_ACTIONS", {}]
				);

				NiftySeed.shrinkNode(node);
			});
		}
	}
});