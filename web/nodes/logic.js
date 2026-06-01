import { app } from "../../../scripts/app.js";
import { NiftyNode } from "../core/node.js";

app.registerExtension({
	name: "comfyui.nifty.nodes.logic",

	async beforeRegisterNodeDef(nodeType, nodeData) {
		// Index Output Switch
		if(nodeData.name === "NiftyIndexOutputSwitch") {
			const IndexOutputSwitch = new NiftyNode(nodeType, nodeData, {
				dynOutputs: {
                    name: "value",
                    min: 2,
                    max: 16,
					syncType: "input" 
                }
			});
		}

		// Combo Switch
		if(nodeData.name === "NiftyComboSwitch") {
			const ComboSwitch = new NiftyNode(nodeType, nodeData);

			function updateCombo(node, widgetName) {
				const valuesWidget = this.getWidget(node, widgetName);
				const comboWidget = this.getWidget(node, widgetName === "true_options" ? "on_true" : "on_false");
				const values = valuesWidget.value.split("|").map(v => v.trim()).filter(v => v.length);
				
				comboWidget.options.values = values;

				if(!values.includes(comboWidget.value)) {
					comboWidget.value = values[0] ?? "";
				}
			}

			ComboSwitch.applyHook("onNodeCreated", function(node) {
				this.onCallback(node, ["true_options", "false_options"], (widget, value, node, widgetName) => {
					updateCombo.call(this, node, widgetName);
				});
			});

			ComboSwitch.applyHook("onAfterGraphConfigured", function(node) {
				updateCombo.call(this, node, "true_options");
				updateCombo.call(this, node, "false_options");
			});
		}
	}
});