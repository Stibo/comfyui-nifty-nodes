import { app } from "../../../scripts/app.js";
import { NiftyNode } from "../core/node.js";

const bundleTypeColor = "#8c685e";
const bundleNodeColor = "brown";

app.registerExtension({
	name: "comfyui.nifty.nodes.bundle",

	async beforeRegisterNodeDef(nodeType, nodeData) {
		// Bundle Pack
		if(nodeData.name === "NiftyBundlePack") {
			const BundlePack = new NiftyNode(nodeType, nodeData, {
				color: bundleNodeColor,
				hideWidgets: ["_slot_names"],
				//hideWidgetInputs: ["count", "hide_links"],
				hideInputs: "hide_links",
				dynInputs: {
                    name: "value",
                    min: 1,
                    max: 32,
					trigger: "widget",
					widget: "count"
                },
			});

			BundlePack.applyHook("onSerialize", function(node) {
				const slotsWidget = this.getWidget(node, "_slot_names");
				const inputSlots = {};

				node.inputs?.slice(1).forEach((input, i) => {
					inputSlots[input.name] = input.label?.trim() || input?.name || `value${i + 1}`;
				});

				const json = JSON.stringify(inputSlots);
				slotsWidget.value = json;

				const widgetIndex = node.widgets?.indexOf(slotsWidget);

				if(widgetIndex !== -1) {
					node.widgets_values ??= [];
					node.widgets_values[widgetIndex] = json;
				}
			});
		}

		// Bundle Unpack
		if(nodeData.name === "NiftyBundleUnpack") {
			const BundleUnpack = new NiftyNode(nodeType, nodeData, {
				color: bundleNodeColor,
				hideWidgets: ["_slot_names"],
				//hideWidgetInputs: ["count", "hide_links"],
				hideOutputs: "hide_links",
				dynOutputs: {
                    name: "value",
                    min: 1,
                    max: 32,
					trigger: "widget",
					widget: "count"
                }
			});

			BundleUnpack.applyHook("onSerialize", function(node) {
				const slotsWidget = this.getWidget(node, "_slot_names");
				const outputSlots = {};

				node.outputs?.slice(1).forEach((output, i) => {
					outputSlots[output.name] = output.label?.trim() || output?.name || `value${i + 1}`;
				});

				const json = JSON.stringify(outputSlots);
				slotsWidget.value = json;

				const widgetIndex = node.widgets?.indexOf(slotsWidget);

				if(widgetIndex !== -1) {
					node.widgets_values ??= [];
					node.widgets_values[widgetIndex] = json;
				}
			});
		}

		// Bundle Get
		if(nodeData.name === "NiftyBundleGet") {
			const BundleGet = new NiftyNode(nodeType, nodeData, {
				color: bundleNodeColor
			});
		}

		// Bundle Set
		if(nodeData.name === "NiftyBundleSet") {
			const BundleSet = new NiftyNode(nodeType, nodeData, {
				color: bundleNodeColor
			});
		}
	},

	async afterConfigureGraph(arg, app) {
		app.canvas.constructor.link_type_colors["BUNDLE"] = bundleTypeColor;
		app.canvas.default_connection_color_byType["BUNDLE"] = bundleTypeColor;
	},
});