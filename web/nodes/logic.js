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

			ComboSwitch.updateCombo = function(node, widgetName) {
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
					this.updateCombo(node, widgetName);
				});
			});

			ComboSwitch.applyHook("onAfterGraphConfigured", function(node) {
				this.updateCombo(node, "true_options");
				this.updateCombo(node, "false_options");
			});
		}

		// Index Combo Switch
		if(["NiftyIndexComboSwitch", "NiftyIndexComboSwitchEager"].includes(nodeData.name)) {
			const IndexComboSwitch = new NiftyNode(nodeType, nodeData);

			IndexComboSwitch.updateCombo = function(node) {
				const comboWidget = this.getWidget(node, "choise");
				const oldIndex = comboWidget.options.values?.indexOf(comboWidget.value) ?? -1;

				const values = [];

				for(const widget of node.widgets) {
					if(widget?.name?.startsWith("option") && widget.value) {
						values.push(widget.value);
					}
				}

				comboWidget.options.values = values;

				if(oldIndex >= 0 && oldIndex < values.length) {
					comboWidget.value = values[oldIndex];
				}

				if(!values.includes(comboWidget.value)) {
					comboWidget.value = values[0] ?? "";
				}
			};

			IndexComboSwitch.updateOptionWidgets = function(node) {
				const valueInputs = node.inputs.filter(input =>
					input.name.startsWith("values.value")
				);

				const connectedInputs = valueInputs.filter(i => i.link);
				const valueInputsCount = Math.max(connectedInputs.length, 1);

				for(let i = node.widgets.length - 1; i >= 0; i--) {
					const widget = node.widgets[i];

					if(!widget?.name?.startsWith("option")) {
						continue;
					}

					const idx = Number(widget.name.slice(6));

					if(idx > valueInputsCount) {
						node.removeWidget(widget);
					}
				}

				for(let i = 1; i <= valueInputsCount; i++) {
					const name = `option${i}`;

					if(!node.widgets.some(w => w?.name === name)) {
						node.addWidget(
							"string",
							name,
							`Option ${i}`,
							() => {}
						)

						this.onCallback(node, name, (widget, value, node, widgetName) => {
							this.updateCombo(node);
						});
					}
				}

				this.updateCombo(node);
			}

			IndexComboSwitch.applyHook("onNodeCreated", function(node) {
				this.onCallback(node, [...Array(16)].map((_, i) => `option${i + 1}`), (widget, value, node, widgetName) => {
					this.updateCombo(node);
				});
			});

			IndexComboSwitch.applyHook("onAfterGraphConfigured", function(node) {
				this.updateOptionWidgets(node);
			});

			IndexComboSwitch.applyHook("onConnectionsChange", function(node, side, slotId, connected, link, slot) {
				if(!this.isLoading && side === LiteGraph.INPUT && link && slot.name.startsWith("values.value")) {
					this.updateOptionWidgets(node);
				}
			});
		}
	}
});