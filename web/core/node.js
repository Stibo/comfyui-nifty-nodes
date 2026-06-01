import { app } from "../../../../scripts/app.js";
import { NiftyHelpers } from "./helpers.js";

export class NiftyNode {
	nodeType = null;
	nodeData = "";
	name = "";
	args = {};

	get LGraphCanvas() {
		return app.canvas?.constructor ?? window.LGraphCanvas
	}

	get isLoading() {
		return app.configuringGraph;
	}

	constructor(nodeType, nodeData, args = {}) {
		this.nodeType = nodeType;
		this.nodeData = nodeData;
		this.name = nodeData.name;

		this.args = {
			...{
				hideTitle: false,
				color: null,
				width: null,
				height: null,
				forceSize: false,
				size: null,
				hideWidgets: [],
				hideInputs: false,
				hideOutputs: false,
				syncOutputs: false,
				removeInputs: [],
				dynInputs: null,
				dynOutputs: null,
				handleWidgets: null,
				properties: [],

				nodeProps: {},
			},
			...args
		};

		this.applyArgs();
	}

	applyHook(hook, callback) {
		const origHook = this.nodeType.prototype[hook];
		const self = this;

		this.nodeType.prototype[hook] = function(...args) {
			origHook?.apply(this, args);
			callback?.call(self, this, ...args);
		}
	}

	applyHookAfter(hook, callback) {
		const origHook = this.nodeType.prototype[hook];
		const self = this;

		this.nodeType.prototype[hook] = function(...args) {
			callback?.call(self, this, ...args);
			origHook?.apply(this, args);
		}
	}

	addEventListener(name, callback) {
		app.api.addEventListener(name, (event, ...args) => {
			const node = app.graph.getNodeById(event.detail?.node);

			if(node && node?.type === this.name) {
				callback.call(this, event, node, event.detail?.output ?? {}, ...args);
			}
		});
	}

	applyArgs() {
		// Prepare handle widgets
		// if(this.args.handleWidgets) {
		// 	this.args.handleWidgets = this.expandHandleWidgets(
		// 		this.args.handleWidgets
		// 	);
		// }

		// Set title mode
		if(this.args.hideTitle) {
			this.nodeType.title_mode = LiteGraph.NO_TITLE;
			this.nodeType.prototype.collapse = () => {};
		}

		// Set forced size
		if(this.args.forceSize) {
			this.nodeType.prototype.computeSize = () => {
				return this.args.forceSize;
			};
		}

		this.applyHook("onNodeCreated", function(node) {
			// Set intial size
			if((this.args.width || this.args.height) && !this.isLoading) {
				let initialWidth = this.args.width ?? (node.size ? node.size[0] : LiteGraph.NODE_WIDTH);
				let initialHeight = this.args.height ?? (node.size ? node.size[1] : 20);

				node.size = [initialWidth, initialHeight];
			}

			// Set color
			if(this.args.color) {
				const colors = this.LGraphCanvas?.node_colors?.[this.args.color];

				if(colors) {
					node.color = colors.color;
					node.bgcolor = colors.bgcolor;
				}
			}

			// Set additional node properties
			for(const [key, value] of Object.entries(this.args.nodeProps)) {
				node[key] = value;
			}

			// Set settings properties
			this.args.properties.forEach((property) => {
				node.addProperty(...property);
			}) 

			// Hide widgets
			if(this.args.hideWidgets) {
				this.args.hideWidgets.forEach((name) => {
					this.hideWidget(node, name);
				});

				this.shrinkNode(node);
			}

			// Hide inputs
			if(this.args.hideInputs) {
				if(typeof this.args.hideInputs === "string") {
					this.onCallback(node, this.args.hideInputs, (widget, value, node) => {
						node._nifty_hide_inputs = value;
					});
				} else {
					node._nifty_hide_inputs = true;
				}
			}

			// Hide outputs
			if(this.args.hideOutputs) {
				if(typeof this.args.hideOutputs === "string") {
					this.onCallback(node, this.args.hideOutputs, (widget, value, node) => {
						node._nifty_hide_outputs = value;
					});
				} else {
					node._nifty_hide_outputs = true;
				}
			}

			// Sync output types
			if(this.args.syncOutputs) {
				node._nifty_sync_output = this.args.syncOutputs;

				if(node._nifty_sync_output.inputs) {
					node._nifty_sync_output.inputs = this.getFlatSlotArray(
						node._nifty_sync_output.inputs
					);
				}
			}

			// Dyn inputs
			if(this.args.dynInputs) {
				if(!this.isLoading) {
					this.handleDynSlots(
						node,
						this.args.dynInputs
					);
				}

				if(this.args.dynInputs.trigger === "widget" && this.args.dynInputs.widget) {
					this.onCallback(node, this.args.dynInputs.widget, (widget, value, node) => {
						this.handleDynSlots(
							node,
							this.args.dynInputs
						);
					});
				}
			}

			// Dyn outputs
			if(this.args.dynOutputs) {
				if(!this.isLoading) {
					this.handleDynSlots(
						node,
						this.args.dynOutputs,
						"output"
					);
				}

				if(this.args.dynOutputs.trigger === "widget" && this.args.dynOutputs.widget) {
					this.onCallback(node, this.args.dynOutputs.widget, (widget, value, node) => {
						this.handleDynSlots(
							node,
							this.args.dynOutputs,
							"output"
						);
					});
				}
			}

			// Handle widgets
			if(this.args.handleWidgets) {
				if(!this.isLoading) {
					this.handleWidgets(node, false);
				}

				for(const [name, callback] of Object.entries(this.args.handleWidgets)) {
					this.onCallback(
						node,
						name,
						(widget, value, node) => {
							callback.call(
								this,
								widget,
								value,
								Object.fromEntries(node.widgets.map(w => [w.name, w])),
								node,
								true
							);
						}
					);
				}
			}
		});

		this.applyHook("onAfterGraphConfigured", function(node) {
			// Set forced size
			if(this.args.forceSize) {
				node.setSize(this.args.forceSize);
			}

			// Hide inputs
			if(this.args.hideInputs) {
				if(typeof this.args.hideInputs === "string") {
					node._nifty_hide_inputs = this.getValue(
						node,
						this.args.hideInputs
					);
				}
			}

			// Hide outputs
			if(this.args.hideOutputs) {
				if(typeof this.args.hideOutputs === "string") {
					node._nifty_hide_outputs = this.getValue(
						node,
						this.args.hideOutputs
					);
				}
			}

			// Remove inputs
			if(this.args.removeInputs) {
				this.removeInput(node, this.args.removeInputs);
			}

			// Dyn inputs
			if(this.args.dynInputs) {
				this.handleDynSlots(
					node,
					this.args.dynInputs
				);
			}

			// Dyn outputs
			if(this.args.dynOutputs) {
				this.handleDynSlots(
					node,
					this.args.dynOutputs,
					"output"
				);
			}

			// Handle widgets
			if(this.args.handleWidgets) {
				this.handleWidgets(node, false);
			}
		});

		// Dyn inputs
		if(this.args.dynInputs && (this.args.dynInputs.trigger !== "widget" || !this.args.dynInputs.widget)) {
			this.applyHook("onConnectionsChange", function(node, side, slotId, connected, link, slot) {
				if(side === LiteGraph.INPUT) {
					this.handleDynSlots(
						node,
						this.args.dynInputs
					);
				}
			});
		}

		// Dyn outputs
		if(this.args.dynOutputs && (this.args.dynOutputs.trigger !== "widget" || !this.args.dynOutputs.widget)) {
			this.applyHook("onConnectionsChange", function(node, side, slotId, connected, link, slot) {
				if(side === LiteGraph.OUTPUT) {
					this.handleDynSlots(
						node,
						this.args.dynOutputs,
						"output"
					);
				}
			});
		}

		// this.applyHook("onConfigure", function(node) {
		// 	// Handle widgets
		// 	if(this.args.handleWidgets) {
		// 		this.handleWidgets(node, false);
		// 	}
		// });
	}

	hideExecutionTime(node) {
		if(node.executionDuration) {
			node.executionDuration = 0;
		}
	}

	handleWidgets(node, isCallback = false) {
		const widgets = Object.fromEntries(node.widgets.map(w => [w.name, w]));

		for(const [name, callback] of Object.entries(this.args.handleWidgets)) {
			const widget = this.getWidget(node, name);

			if(!widget) {
				continue;
			}

			callback.call(this, widget, widget.value, widgets, node, isCallback);
		}
	}

	handleDynSlots(node, args, slotsType = "input") {
		args = {
			...{
				slots: slotsType,
				min: 2,
				max: 16,
				type: "*",
				syncType: "input",
				shape: slotsType === "input" ? LiteGraph.SlotShape.HollowCircle : undefined,
				trigger: "auto", // auto/widget
				widget: null,
				syncOutputs: false
			},
			...args
		};

		const isDynamic = (slot) => {
			if(!slot) {
				return false;
			}

			if(args.slots === "input" && slot.widget) {
				return false;
			}

			for(let i = 1; i <= args.max; i++) {
				if(slot.name === `${args.name}${i}`) {
					return true;
				}
			}

			return false;
		};

		let slots = args.slots === "input" ? node.inputs : node.outputs;
		slots = slots.map((slot, realIndex) => ({ slot, realIndex }));
		slots = slots.filter(({ slot }) => isDynamic(slot));

		const targetCount = this.getDynSlotsTarget(
			node,
			args,
			slots
		);
		
		for(let index = args.max - 1; index > args.min - 1; index--) {
			const entry = slots[index];
			const slotName = `${args.name}${index+1}`;

			if(index >= targetCount) {
				if(entry) {
					if(args.slots === "input") {
						node.removeInput(entry.realIndex);

						if(args.syncOutputs) {
							node.removeOutput(entry.realIndex);
						}
					} else {
						node.removeOutput(entry.realIndex);
					}
				}
			} else if(!entry) {
				let slot = null;

				if(args.slots === "input") {
					node.addInput(slotName, args.type);
					slot = this.getInput(node, slotName);

					if(args.syncOutputs) {
						node.addOutput(slotName, args.type);
					}
				} else {
					if(args.syncType) {
						node.addOutput(slotName, node.outputs[0].type);
					} else {
						node.addOutput(slotName, args.type);
					}

					slot = this.getOutput(node, slotName);
				}

				if(slot) {
					slot.localized_name = slotName;
					slot.shape = args.shape;
				}
			}
		}

		const allSlots = args.slots === "input" ? node.inputs : node.outputs;
		const anyInputs = new Set();

		for(let i = 0; i < allSlots.length; i++) {
			const slot = allSlots[i];

			if(slot.type === "*") {
				anyInputs.add(slot.name);
			}
		}
		
		node._nifty_any_type_input_slots = anyInputs;

		this.shrinkNode(node);
	}

	getDynSlotsTarget(node, args, slots) {
		if(args.trigger === "widget") {
			const widget = node.widgets?.find(w => w.name === args.widget);
			const value = parseInt(widget?.value) || args.min;
			return Math.min(Math.max(value, args.min), args.max);
		}

		const isConnected = (slot) => {
			if(!slot) return false;
			return args.slots === "input" ? !!slot.link : !!(slot.links?.length);
		};

		let lastSlot = args.min - 1;

		for(let index = args.max - 1; index > args.min - 1; index--) {
			if(isConnected(slots[index]?.slot) || isConnected(slots[index - 1]?.slot)) {
				lastSlot = index;
				break;
			}
		}

		return lastSlot + 1;
	}

	getWidget(node, name) {
		return node.widgets.find(w => w.name === name);
	}

	getWidgetByType(node, type) {
		return node.widgets.find(w => w.type === type);
	}

	getInput(node, name) {
		return node.inputs.find(w => w.name === name);
	}

	getOutput(node, name) {
		return node.outputs.find(w => w.name === name);
	}

	findNodesByName(startNode, name, fromRoot = false) {
		const results = [];
		const startGraph = fromRoot ? app.graph : startNode?.graph;

		if(!startGraph) {
			return results;
		}

		function walk(graph) {
			const nodes = graph._nodes || graph.nodes || [];

			for(const node of nodes) {
				if(node.title === name || node.type === name) {
					results.push(node);
				}

				if(node.subgraph) {
					walk(node.subgraph);
				}
			}
		}

		walk(startGraph);

		results.sort((a, b) => {
			const ay = a.pos?.[1] ?? 0;
			const by = b.pos?.[1] ?? 0;

			if (ay !== by) return ay - by;

			const ax = a.pos?.[0] ?? 0;
			const bx = b.pos?.[0] ?? 0;

			return ax - bx;
		});

		return results;
	}

	findNodesByType(name) {
		const results = [];
		const startGraph = app.graph;

		if(!startGraph) {
			return results;
		}

		function walk(graph) {
			const nodes = graph._nodes || graph.nodes || [];

			for(const node of nodes) {
				if(node.type === name) {
					results.push(node);
				}

				if(node.subgraph) {
					walk(node.subgraph);
				}
			}
		}

		walk(startGraph);

		results.sort((a, b) => {
			const ay = a.pos?.[1] ?? 0;
			const by = b.pos?.[1] ?? 0;

			if (ay !== by) return ay - by;

			const ax = a.pos?.[0] ?? 0;
			const bx = b.pos?.[0] ?? 0;

			return ax - bx;
		});

		return results;
	}

	connectByName(node1, outName, node2, inName, removeOutLinks = true) {
		const sourceIndex = node1.outputs.findIndex(x => x.name === outName);
		const targetIndex = node2.inputs.findIndex(x => x.name === inName);

		if(removeOutLinks) {
			const sourceSlot = node1.outputs.find(o => o.name === outName);

			for(const linkId of [...sourceSlot.links]) {
				node1.graph.removeLink(linkId);
			}
		}

		if(sourceIndex !== -1 && targetIndex !== -1) {
			node1.connect(sourceIndex, node2, targetIndex);
		}
	}

	shrinkNode(node) {
		const computed = node.computeSize?.() || node.size;
		node.setSize?.([node.size[0], computed[1]]);
	}

	toggleWidget(node, widget, show = true) {
		if(typeof widget === "string") {
			widget = this.getWidget(node, widget);

			if(!widget) {
				return;
			}
		}

		widget.hidden = !show;
		widget.disabled = !show;
		widget.y = !show ? -100 : 0;

		const input = this.getInput(node, widget.name);

		if(!show && input?.link != null) {
			node.graph.removeLink(input.link);
		}
	}

	showWidget(node, widget) {
		this.toggleWidget(node, widget, true);
	}

	hideWidget(node, widget) {
		this.toggleWidget(node, widget, false);
	}

	removeInput(node, name) {
		NiftyHelpers.removeInput(node, name);
	}

	getValue(node, widgetName) {
		const widget = this.getWidget(node, widgetName);

		if(!widget) {
			return null;
		}

		const value = widget.value;

		switch(widget.type) {
			case "INT":
			case "int":
				return parseInt(value ?? 0);

			case "FLOAT":
			case "float":
				return parseFloat(value ?? 0);

			case "BOOLEAN":
			case "bool":
				return Boolean(value);

			case "STRING":
			case "string":
				return value ?? "";

			default:
				return value;
		}
	}

	onCallback(node, widgetName, callback) {
		if(!Array.isArray(widgetName)) {
			widgetName = [widgetName];
		}

		widgetName.forEach((widgetNameSingle) => {
			const widget = this.getWidget(node, widgetNameSingle);

			if(!widget) {
				return;
			}
			
			const origCallback = widget.callback;
			
			widget.callback = (...args) => {
				origCallback?.apply(widget, args);
				callback.call(this, widget, this.getValue(node, widgetNameSingle), node, widgetNameSingle);
			};
		});

	}

	getFlatSlotArray(slots) {
		return slots.flatMap(str => {
			const match = str.match(/(\w+)(\d+)\.\.\.(\d+)/);
			if (!match) return [str];

			const [, prefix, start, end] = match;
			const s = parseInt(start, 10);
			const e = parseInt(end, 10);

			return Array.from(
				{ length: e - s + 1 },
				(_, i) => `${prefix}${s + i}`
			);
		});
	}
}