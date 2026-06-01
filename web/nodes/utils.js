import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { ComfyWidgets } from "../../../scripts/widgets.js"
import { NiftyNode } from "../core/node.js";
import { NiftyHelpers, NiftyDraw } from "../core/helpers.js";

function addPreviewAnyNode() {
	const newAddedNodes = [];

	for(const selectedNode of Object.values(app.canvas?.selected_nodes)) {
		const selectedX = selectedNode.pos[0];
		const selectedY = selectedNode.pos[1];
		const selectedWidth = selectedNode.size[0];

		NiftyHelpers.fixNodeLinks(selectedNode);

		if(!selectedNode.outputs.length || selectedNode.outputs.some(output => output.links && output.links.length > 0)) {
			continue;
		}

		const newNode = LiteGraph.createNode("NiftyPreviewAny");

		if(!newNode) {
			continue;
		}

		newNode.pos = [
			selectedX + selectedWidth + 30,
			selectedY
		];

		app.graph.add(newNode);

		selectedNode.outputs.forEach((output, i) => {
			selectedNode.connect(i, newNode, i);
		});

		newAddedNodes.push(newNode);
	}

	if(newAddedNodes.length) {
		app.graph.setDirtyCanvas(true, true);
	}
}

app.registerExtension({
	name: "comfyui.nifty.nodes.utils",

	commands: [
		{
			id: "Nifty.previewAllOutputs",
			label: "Adds an Preview Any Node to all outputs for the selected nodes.",
			function: addPreviewAnyNode	
		},
	],

	keybindings: [
		{
			commandId: "Nifty.previewAllOutputs",
			combo: { key: "p", ctrl: true },
		},
	],

	async beforeRegisterNodeDef(nodeType, nodeData) {
		// Hidden Link
		if(nodeData.name === "NiftyHiddenLink") {
			const HiddenLink = new NiftyNode(nodeType, nodeData, {
				forceSize: [60, 26],
				hideTitle: true,
				color: "brown",
				hideOutputs: true,
				nodeProps: {
					badges: [],
					resizable: false
				}
			});

			HiddenLink.applyHookAfter("onNodeCreated", function(node) {
				for(const input of node.inputs ?? []) {
					input.label = " ";
				}

				for(const output of node.outputs ?? []) {
					output.label = " ";
				}
			});

			HiddenLink.applyHookAfter("onDrawForeground", function(node, ctx) {
				if(node.flags?.collapsed) {
					return;
				}

				if(node.executionDuration) {
					node.executionDuration = 0;
				}

				ctx.save();
				ctx.font = "18px serif";
				ctx.textAlign = "center";
				ctx.textBaseline = "middle";
				ctx.fillText("🥷", node.size[0] / 2, node.size[1] / 1.8);
				ctx.restore();
			});	
		}

		// Simple Title
		if(nodeData.name === "NiftySimpleTitle") {
			const SimpleTitle = new NiftyNode(nodeType, nodeData, {
				width: 200,
				height: 58,
				hideTitle: true,
				color: "yellow",
				nodeProps: {
					badges: []
				}
			});

			SimpleTitle.applyHook("onDrawBackground", function(node) {
				if(node.color) {
					node.bgcolor = node.color;
				}

				if(node.executionDuration) {
					node.executionDuration = 0;
				}
			});

			SimpleTitle.applyHook("onNodeCreated", function(node) {
				const widget = this.getWidget(node, "title");
					
				node.removeInput(0);

				//node.widgets_start_y = 0;

				// widget.computeSize = function(width) {
				// 	return [width, 58];
				// };

				widget.draw = function(ctx, node, widgetWidth, y, widgetHeight) {
					ctx.save();
					
					ctx.font = "32px sans-serif";
					ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
					ctx.textAlign = "left";
					ctx.textBaseline = "top";

					let x = 10;
					let maxWidth = widgetWidth - x * 2;
					let clipped = this.value ?? "";

					while (
						clipped.length > 0 &&
						ctx.measureText(clipped).width > maxWidth
					) {
						clipped = clipped.slice(0, -1);
					}

					ctx.fillText(clipped, x, 15);

					ctx.restore();
				};
			});
		}

		// Debug Any
		if(nodeData.name === "NiftyDebugAny") {
			const DebugAny = new NiftyNode(nodeType, nodeData, {
				hideTitle: true,
				color: "yellow",
				nodeProps: {
					badges: []
				}
			});

			DebugAny.applyHookAfter("onDrawForeground", function(node, ctx) {
				if(node.executionDuration) {
					node.executionDuration = 0;
				}

				ctx.save();
				ctx.font = "18px serif";
				ctx.textAlign = "right";
				ctx.textBaseline = "top";
				ctx.fillText("🐞", node.size[0] -6, 9);
				ctx.restore();
			});

			DebugAny.applyHook("onNodeCreated", function(node) {
				const widget = ComfyWidgets["STRING"](
					node,
					"debug",
					["STRING", { multiline: true }],
					app
				).widget;
	
				const element = widget.inputEl;				

				element.placeholder = "";
				element.style.fontFamily = "monospace";
				element.style.fontSize = "9px";
				element.style.background = "rgba(0,0,0,0.5)";
				element.style.color = "#eee";
				element.style.borderRadius = "3px";
				element.style.border = "none";
				element.style.outline = "none";

				widget.options.read_only = true
				widget.element.readOnly = true
				widget.element.disabled = true
				widget.serialize = false
			});

			DebugAny.addEventListener("executed", function(event, node, output) {
				const widget = this.getWidget(node, "debug");
				const element = widget.inputEl;

				widget.value = output?.text ?? "";

				const overhead = node.size[1] - element.offsetHeight;
				element.style.height = "auto";
				const naturalHeight = element.scrollHeight;
				element.style.height = "";

				node.setSize([
					node.size[0],
					Math.max(
						Math.max(60, Math.min(overhead + naturalHeight, 600)),
						node.computeSize()[1]
					)
				]);
			});
		}

		// Preview Any
		if(nodeData.name === "NiftyPreviewAny") {
			const PreviewAny = new NiftyNode(nodeType, nodeData, {
				width: 200,
				hideTitle: true,
				color: "yellow",
				nodeProps: {
					badges: []
				}
			});

			PreviewAny.applyHookAfter("onDrawForeground", function(node, ctx) {
				this.hideExecutionTime(node);

				if(node._nifty_has_preview) {
					return;
				}

				ctx.save();
				ctx.font = "16px serif";
				ctx.textAlign = "right";
				ctx.textBaseline = "top";
				ctx.fillText("🐞", node.size[0] -6, 9); // 🔍
				ctx.restore();
			});

			PreviewAny.applyHookAfter("onConnectionsChange", function(node, side, slotId, connected, link, slot) {
				slot.label = " ";
			});

			PreviewAny.applyHookAfter("onInputAdded", function(node, slot) {
				slot.label = " ";
			});

			PreviewAny.addEventListener("executed", function(event, node, output) {
				const currentWidth = node.size[0];
				
				while(node.widgets?.length) {
					node.removeWidget(node.widgets[0]);
				}

				node._nifty_has_preview = true;
				node.widgets_start_y = 2;

				if(!output?.text) {
					return;
				}

				node._nifty_has_preview = true;

				output.text.forEach((input, i) => {
					const link =  app.graph.links[node.inputs[i]?.link];
					const inputType = link?.type ?? null;
					let inputColor = "";

					if(inputType) {
						inputColor = app.canvas.default_connection_color_byType[inputType];
					}

					if(inputColor === "") {
						inputColor = LiteGraph.CONNECTING_LINK_COLOR;
					}

					const outputSlot = app.graph.getNodeById(link?.origin_id)?.outputs?.[link.origin_slot];
					let widgetLabel = outputSlot.label ?? outputSlot.name;

					const widget = ComfyWidgets["STRING"](
						node,
						`debug${i}`,
						["STRING", { multiline: true }],
						app
					).widget;

					widget.serialize = false;
					widget.options.serialize = false;
					widget.value = input;

					const fontSize = 9;
					const lineHeight = 1.2;
					const padding = 5;
					const widgetIndent = 11;
					const maxRows = 15;

					let heightDiff = 5;

					requestAnimationFrame(() => {
						const element = widget.inputEl;
						
						element.placeholder = "";
						element.readOnly = true;
						element.rows = 1;

						element.style.height = "auto";
						element.style.width = `calc(100% - ${widgetIndent}px)`;
						element.style.padding = `${padding}px`;
						element.style.marginLeft = `${widgetIndent}px`;
						element.style.fontFamily = "monospace";
						element.style.fontSize = `${fontSize}px`;
						element.style.lineHeight = lineHeight;
						element.style.background = "rgba(0,0,0,0.5)";
						element.style.color = "#eee";
						element.style.borderRadius = "3px";
						element.style.cursor = "pointer";
						element.style.borderLeft = `3px solid ${inputColor}`;

						if(widgetLabel !== "" && element.parentElement) {
							const elementLabel = document.createElement("div");
							elementLabel.innerHTML = `${widgetLabel} (${inputType})`;
							elementLabel.style.height = "auto"
							elementLabel.style.width = `calc(100% - ${widgetIndent}px)`;
							elementLabel.style.marginTop = "-4px"
							elementLabel.style.marginBottom = "2px"
							elementLabel.style.marginLeft = `${widgetIndent + 8}px`;
							elementLabel.style.fontSize = `${fontSize}px`;
							elementLabel.style.lineHeight = lineHeight;
							elementLabel.style.pointerEvents = "none";

							element.parentElement.prepend(elementLabel);

							heightDiff += elementLabel.clientHeight
						}

						element.onclick = () => {
							navigator.clipboard.writeText(element.value).then(() => {
								app.extensionManager.toast.add({
									severity: "success",
									summary: "Nifty Preview Any",
									detail: "Preview text copied to clipboard",
									life: 3000
								});
							}).catch(() => {});
						};

						while (
							element.scrollHeight > element.clientHeight &&
							element.rows < maxRows
						) {
							element.rows++;
						}

						requestAnimationFrame(() => {
							widget.computeSize = function(width) {
								return [width, element.clientHeight + heightDiff];
							};

							node.setSize([currentWidth, node.computeSize()[1]]);
							node.setDirtyCanvas(true, true);
						});
					});
				});
			});

		}

		// Subgraph Labels
		if(nodeData.name === "NiftySubgraphLabels") {
			const SubgraphLabels = new NiftyNode(nodeType, nodeData);

			SubgraphLabels.applyHook("onNodeCreated", function(node) {
				for(let index = 0; index < node.widgets.length; index++) {
					const widget = node.widgets[index];

					widget.draw = function(ctx, node, widgetWidth, y, widgetHeight) {
						const isEmpty = !this.value.trim().length;
						const text = isEmpty ? "" : this.value.trim(); // `Label ${index+1}`
						const ellipsis = " …";

						ctx.save();

						if(!node.subgraph) {
							const isPromoted = false;
							//const isPromoted = NiftyHelpers.isPromoted(node, widget);

							NiftyDraw.stringWidget(ctx, y, {
								label: `label${index+1}`,
								value: text,
								left: NiftyDraw.left,
								width: widgetWidth - NiftyDraw.left - NiftyDraw.right,
								promoted: isPromoted
							});
						} else {
							NiftyDraw.text(ctx, {
								text: text,
								x: 20,
								y: y + widgetHeight / 2 + 3,
								width: widgetWidth - 40,
								font: NiftyDraw.font.type,
								fontSize: 13,
								color: NiftyDraw.colors.text
							});
						}

						ctx.restore();
					};
				}
			});
		}

		// Bypass By Title
		if(nodeData.name === "NiftyBypassByTitle") {
			const bypassByTitleFunc = function(node) {
				let bypass = this.getValue(node, "bypass");
				let searchFromRoot = this.getValue(node, "search_from_root");

				let nodesNames = this.getValue(node, "nodes");
				nodesNames = nodesNames.split(/\r?\n/).map(s => s.trim()).filter(s => s.length > 0);

				nodesNames.forEach((nodeNameRaw) => {
					let negate = nodeNameRaw.startsWith("!");
					let nodeName = negate ? nodeNameRaw.slice(1) : nodeNameRaw;
					let bypassNode = negate ? !bypass : bypass;
					let foundNodes = this.findNodesByName(node, nodeName, searchFromRoot);

					foundNodes.forEach((foundNode) => {
						const mode = bypassNode ? 4 : 0;

						if(mode !== foundNode.mode) {
							foundNode.mode = mode;
						}
					});
				});
			}

			const BypassByTitle = new NiftyNode(nodeType, nodeData, {
				handleWidgets: {
					bypass: function(widget, value, widgets, node) {
						if(!this.isLoading) {
							bypassByTitleFunc.call(this, node);
						}
					}
				}
			});

			BypassByTitle.addEventListener("execution_start", function(...args) {
				this.findNodesByType(nodeData.name).forEach((node) => {
					if(this.getValue(node, "enforce")) {
						bypassByTitleFunc.call(this, node);
					}
				});
			});
		}

		// Bypass Switch By Title
		if(nodeData.name === "NiftyBypassSwitchByTitle") {
			const bypassSwitchByTitleFunc = function(node) {
				let bypass = this.getValue(node, "bypass");
				let selected = this.getValue(node, "selected");
				let searchFromRoot = this.getValue(node, "search_from_root");

				let nodesNames = this.getValue(node, `nodes${selected}`);
				nodesNames = nodesNames.split(/\r?\n/).map(s => s.trim()).filter(s => s.length > 0);

				nodesNames.forEach((nodeNameRaw) => {
					let negate = nodeNameRaw.startsWith("!");
					let nodeName = negate ? nodeNameRaw.slice(1) : nodeNameRaw;
					let bypassNode = negate ? !bypass : bypass;
					let foundNodes = this.findNodesByName(node, nodeName, searchFromRoot);

					foundNodes.forEach((foundNode) => {
						const mode = bypassNode ? 4 : 0;

						if(mode !== foundNode.mode) {
							foundNode.mode = mode;
						}
					});
				});
			}

			const bypassSwitchByTitleUpdateCombo = function(node) {
				const selectedWidget = this.getWidget(node, "selected");
				const bypassWidget = this.getWidget(node, "bypass");
				const count = this.getValue(node, "count");
				const selectedIndex = selectedWidget.value - 1;
				const comboValues = [];

				for(let index = 1; index <= count; index++) {
					comboValues.push(
						this.getValue(node, `label${index}`)
					);
				}

				bypassWidget.options.values = comboValues;

				if(comboValues[selectedIndex]) {
					bypassWidget.value = comboValues[selectedIndex];
				} else {
					bypassWidget.value = comboValues[0];
					bypassWidget.callback?.(bypassWidget.value);
					selectedWidget.value = 1;
				}
			}

			const BypassSwitchByTitle = new NiftyNode(nodeType, nodeData, {
				hideWidgets: ["selected"],
				handleWidgets: {
					count: function(widget, value, widgets, node) {
						for(let index = 1; index <= 16; index++) {
							this.toggleWidget(
								node,
								widgets[`nodes${index}`],
								index <= value
							);

							this.toggleWidget(
								node,
								widgets[`label${index}`],
								index <= value
							);
						}

						bypassSwitchByTitleUpdateCombo.call(this, node);
					},
					bypass: function(widget, value, widgets, node) {
						let currentIndex = Math.max(0, widget.options.values.indexOf(value));
						widgets.selected.value = currentIndex + 1;

						if(!this.isLoading) {
							bypassSwitchByTitleFunc.call(this, node);
						}
					}
				}
			});

			BypassSwitchByTitle.applyHook("onNodeCreated", function(node) {
				if(!this.isLoading) {
					this.shrinkNode(node);
				}

				for(let index = 1; index <= 16; index++) {
					this.onCallback(node, `label${index}`, (widget, value, node) => {
						bypassSwitchByTitleUpdateCombo.call(this, node);
					});
				}
			});

			BypassSwitchByTitle.applyHook("onAfterGraphConfigured", function(node) {
				bypassSwitchByTitleUpdateCombo.call(this, node);
			});

			BypassSwitchByTitle.addEventListener("execution_start", function(event) {
				this.findNodesByType(nodeData.name).forEach((node) => {
					if(this.getValue(node, "enforce")) {
						bypassSwitchByTitleFunc.call(this, node);
					}
				});
			});
		}

		// Node Chain Extender
		if(nodeData.name === "NiftyNodeChainExtender") {
			const NodeChainExtender = new NiftyNode(nodeType, nodeData, {
				handleWidgets: {
					count: function(widget, value, widgets, node, isCallback) {
						if(this.isLoading || !isCallback) {
							return;
						}

						const count = this.getValue(node, "count");
						const connectSlots = this.getValue(node, "connect_slots").split(",").map(s => s.trim()).filter(Boolean);
						const gap = this.getValue(node, "gap");
						const bypass = this.getValue(node, "bypass_on_remove");
	
						const sourceNodes = this.findNodesByName(
							node,
							widgets.source_node.value,
							widgets.search_from_root.value
						);

						const endNode = this.findNodesByName(
							node,
							widgets.end_node.value,
							widgets.search_from_root.value
						)[0] ?? null;

						if(!sourceNodes[0] || !endNode) {
							return;
						}

						// Enable bypassed nodes
						for(let index = 0; index < count; index++) {
							if(sourceNodes[index] && sourceNodes[index].mode === 4) {
								sourceNodes[index].mode = 0;
							}
						}

						let lastNode = sourceNodes.at(-1);
						let nextX = lastNode.pos[0] + lastNode.size[0] + gap;
						let nextY = lastNode.pos[1];

						if(sourceNodes.length < count) {
							const nodesBefore = new Set(Object.keys(sourceNodes[0].graph._nodes_by_id));
							const selectedNodes = Object.values(app.canvas.selected_nodes);

							app.canvas.deselectAll();
							app.canvas.selectNodes([sourceNodes[0]]);
							app.canvas.copyToClipboard();
							app.canvas.deselectAll();

							for(let index = sourceNodes.length; index < count; index++) {
								app.canvas.pasteFromClipboard();
							}

							app.canvas.selectNodes(selectedNodes);

							const nodesAfter = Object.keys(sourceNodes[0].graph._nodes_by_id);
							const newNodesIds = nodesAfter.filter(id => !nodesBefore.has(id));

							newNodesIds.forEach((nodeId, i) => {
								const newNode = sourceNodes[0].graph._nodes_by_id[nodeId];
								newNode.pos = [nextX, nextY];
								nextX = newNode.pos[0] + newNode.size[0] + gap;
								nextY = newNode.pos[1];
							});
						} else if(sourceNodes.length > count) {
							for(let index = sourceNodes.length - 1; index >= count; index--) {
								const sourceNode = sourceNodes[index];

								if(bypass) {
									sourceNode.mode = 4;
								} else {
									nextX = sourceNode.pos[0];
									nextY = sourceNode.pos[1];

									sourceNode.graph.remove(sourceNode);
								}						
							}
						}

						endNode.pos = [nextX, nextY];

						const sourceNodesNew = this.findNodesByName(
							node,
							widgets.source_node.value,
							widgets.search_from_root.value
						);

						sourceNodesNew.forEach((newNode, i) => {
							connectSlots.forEach((slotName) => {
								this.connectByName(
									newNode,
									slotName,
									sourceNodesNew[i + 1] ?? endNode,
									slotName
								);
							});
						});

						app.graph.setDirtyCanvas(true, true);						
					}
				}
			});
		}
	}
});
