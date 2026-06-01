import { app } from "../../../scripts/app.js";

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
