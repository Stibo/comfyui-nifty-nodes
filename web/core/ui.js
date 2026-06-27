import { app } from "../../../scripts/app.js";
import { NiftyHelpers, NiftyDraw } from "./helpers.js";

const hiddenInputNodes = new Set();
const hiddenOutputNodes = new Set();
const activeNodes = new Set();

app.registerExtension({
	name: "comfyui.nifty.ui.hiddenlinks",

	async init(app) {
		const canvas = app.canvas;
		const origDrawConnections = canvas.drawConnections;

		canvas.drawConnections = function(...args) {
			const nodes = this.graph._nodes;

			hiddenInputNodes.clear();
			hiddenOutputNodes.clear();

			for(let i = 0; i < nodes.length; i++) {
				const node = nodes[i];

				if(node.graph !== this.graph) {
					continue;
				}

				if(node._nifty_hide_inputs) {
					hiddenInputNodes.add(node.id);
				}

				if(node._nifty_hide_outputs) {
					hiddenOutputNodes.add(node.id);
				}

				if(node.is_selected || node === this.node_over) {
					activeNodes.add(node.id);
				} else {
					activeNodes.delete(node.id);
				}
			}

			return origDrawConnections.apply(this, args);
		};

		const origRenderLink = canvas.renderLink;

		canvas.renderLink = function(ctx, a, b, link, ...args) {
			let alpha = 1;

			const inputHasTarget = hiddenInputNodes.has(link.target_id);
			const outputHasOrigin = hiddenOutputNodes.has(link.origin_id);
			const targetIsActive = activeNodes.has(link.target_id);
			const originIsActive = activeNodes.has(link.origin_id);

			const inputSelf = inputHasTarget && targetIsActive;
			const inputPrev = inputHasTarget && originIsActive;
			const outputSelf = outputHasOrigin && originIsActive;
			const outputNext = outputHasOrigin && targetIsActive;

			if(inputHasTarget || outputHasOrigin) {
				alpha = 0;
			}

			if(inputSelf || inputPrev || outputSelf || outputNext) {
				alpha = 0.5;
			}

			if(alpha === 0) {
				return;
			}

			ctx.save();
			ctx.globalAlpha = alpha;
			const res = origRenderLink.call(this, ctx, a, b, link, ...args);
			ctx.restore();

			return res;
		};
	},

	// async beforeRegisterNodeDef(nodeType, nodeData) {
	// 	nodeType.prototype.onRemoved = function() {
	// 		hiddenInputNodes.delete(this.id);
	// 		hiddenOutputNodes.delete(this.id);
	// 	};
	// },
});

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
	name: "comfyui.nifty.ui.seed",

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
			const seedNodes = NiftyHelpers.findNodesByWidget({
				name: "seed_actions"
			});

			for(const seedNode of seedNodes) {
				const actionWidget = NiftyHelpers.getWidget(seedNode, "seed_actions");

				if(actionWidget?.value?.randomOnPrompt ?? true) {
					setRandomSeed(seedNode);
				}
			}
			
			return await origQueuePrompt.apply(this, args);
		};
	}
});