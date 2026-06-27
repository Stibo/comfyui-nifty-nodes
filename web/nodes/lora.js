import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import { NiftyNode } from "../core/node.js";
import { NiftyHelpers, NiftyDraw } from "../core/helpers.js";

const loraStackTypeColor = "#94dccd"; // #7892e7, #69dfd9,

let _loraCache = null;

async function getLoraList() {
	if(_loraCache) {
		return _loraCache;
	}

	try {
		const res = await api.fetchApi("/object_info/LoraLoader");
		const data = await res.json();
		const vals = data?.LoraLoader?.input?.required?.lora_name?.[0] ?? [];

		vals.sort((a, b) => a.localeCompare(b, undefined, { 
            numeric: true, 
            sensitivity: 'base' 
        }));

		_loraCache = ["none", ...vals];
	} catch {
		_loraCache = ["none"];
	}

	return _loraCache;
}

function resizeAfterRowChange(innerNode, subgraphNode, delta) {
	const innerW = innerNode.size[0];

	innerNode.setSize([innerW, innerNode.computeSize()[1]]);

	if(subgraphNode && subgraphNode !== innerNode) {
		subgraphNode.setSize([subgraphNode.size[0], subgraphNode.size[1] + delta]);
	}

	// @todo: correctly handle collapsed node

	app.canvas.setDirty(true);
}

function defaultLoraRow() {
	return {
		enabled: true,
		lora: "none",
		strength: 1.0,
	};
}

function bindWidgetMouse(event, pos, sections = {}) {
	if(!["pointerdown", "mousedown"].includes(event.type)) {
		return;
	}

	const [mouseX, mouseY] = pos;
	let clickedSection = null;
	let clickedRowIndex = 0;

	this._drawRects.forEach((rowDraw, i) => {
		if(!NiftyHelpers.containsPointer(mouseX, mouseY, rowDraw.row)) {
			return;
		}

		for(const [widgetKey, widgetDraw] of Object.entries(rowDraw)) {
			if(widgetKey === "row") {
				continue;
			}

			if(NiftyHelpers.containsPointer(mouseX, mouseY, widgetDraw)) {
				clickedSection = widgetKey;
				clickedRowIndex = i;
				return;
			}
		}
	});

	const row = this._value[clickedRowIndex];

	if(!row) {
		return;
	}

	if(sections[clickedSection]) {
		sections[clickedSection](row, clickedRowIndex, clickedSection);
	}
}

const loraLoader = {
	drawLoraSelectRow: function(ctx, widgetTop, widgetWidth, args = {}) {
		args = {
			...{
				suffix: "",

				enabled: true,
				lora: "none",
				strength: 1.00,

				hint: '',

				promoted: false,
				show_enabled : true,
				show_remove: true
			},
			...args
		};

		const widgetLeft = NiftyDraw.left;
		const widgetRight = NiftyDraw.right;
		const widgetHeight = NiftyDraw.height;
		const widgetColGap = 4;

		const boolX = widgetLeft + widgetColGap;
		const boolWidth = 20;
		const boolHeight = 12;
		const boolToggleSize = 14;

		const floatWidth = 58;
		const floatX = widgetWidth - widgetRight - floatWidth;
		const floatArrowWidth = 16;

		const comboX = widgetLeft + boolWidth + widgetColGap * 3;
		const comboWidth = floatX - widgetColGap - comboX;

		const removeX = comboX + comboWidth - widgetColGap;
		const removeSize = 10;

		const isNone = args.lora === "none";
		
		// Background
		NiftyDraw.roundRect(ctx, {
			x: widgetLeft,
			y: widgetTop,
			width: widgetWidth - widgetLeft - widgetRight,
			height: widgetHeight,
			fill: NiftyDraw.colors.bg,
			stroke: args.promoted ? NiftyDraw.colors.promoted : NiftyDraw.colors.outline,
			radius: "round"
		});
		
		// Enable field
		let enableDraw = {
			x: 0,
			y: 0,
			width: 0,
			height: 0
		};

		if(args.show_enabled) {
			enableDraw = NiftyDraw.roundRect(ctx, {
				x: boolX,
				y: widgetTop + ((widgetHeight - boolHeight) / 2),
				width: boolWidth,
				height: boolHeight,
				fill: NiftyDraw.colors.inactive,
				radius: "round"
			});

			NiftyDraw.circle(ctx, {
				x: args.enabled ? (boolX + boolWidth - boolToggleSize + 1) : (boolX - 1),
				y: widgetTop + (widgetHeight - boolToggleSize) / 2,
				size: boolToggleSize,
				fill: args.enabled ? NiftyDraw.colors.active : NiftyDraw.colors.text2
			});
		}

		// Delimiter
		NiftyDraw.line(ctx, {
			x: comboX - widgetColGap,
			y: widgetTop + (widgetHeight - boolToggleSize) / 2,
			height: boolToggleSize,
			fill: NiftyDraw.colors.inactive
		});

		// Combo field
		let noneLabel = args.hint.length ? `none (${args.hint})`: "none";

		const loraDraw = NiftyDraw.text(ctx, {
			text: isNone ? noneLabel: args.lora.replace(/\\/g, "/"),
			x: comboX,
			y: widgetTop + widgetHeight / 2,
			width: comboWidth - (args.show_remove ? removeSize : 0),
			font: NiftyDraw.font.type,
			fontSize: NiftyDraw.font.sizeSmall,
			color: !args.enabled ? NiftyDraw.colors.inactive : (isNone ? NiftyDraw.colors.text2 : NiftyDraw.colors.text),
		});

		// Remove button
		let removeDraw = {
			x: 0,
			y: 0,
			width: 0,
			height: 0
		};

		if(args.show_remove) {
			removeDraw = NiftyDraw.removeButton(ctx, {
				x: removeX,
				y: widgetTop + widgetHeight / 2,
				size: removeSize,
				disabled: !args.enabled
			});
		}

		// Delimiter
		NiftyDraw.line(ctx, {
			x: floatX,
			y: widgetTop + (widgetHeight - boolToggleSize) / 2,
			height: boolToggleSize,
			fill: NiftyDraw.colors.inactive
		});

		// Strength field
		const strengthDownDraw = NiftyDraw.text(ctx, {
			text: "◀",
			x: floatX + floatArrowWidth / 2,
			y: widgetTop + widgetHeight / 2,
			fontSize: NiftyDraw.font.sizeSmall,
			color: args.enabled ? (isNone ? NiftyDraw.colors.text2 : NiftyDraw.colors.text) : NiftyDraw.colors.inactive,
			align: "center"
		});

		const strengthDraw = NiftyDraw.text(ctx, {
			text: args.strength.toFixed(2),
			x: floatX + floatWidth / 2,
			y: widgetTop + widgetHeight / 2,
			fontSize: NiftyDraw.font.sizeSmall,
			color: args.enabled ? (isNone ? NiftyDraw.colors.text2 : NiftyDraw.colors.text) : NiftyDraw.colors.inactive,
			align: "center"
		});

		const strengthUpDraw = NiftyDraw.text(ctx, {
			text: "▶",
			x: floatX + floatWidth - floatArrowWidth / 2,
			y: widgetTop + widgetHeight / 2,
			fontSize: NiftyDraw.font.sizeSmall,
			color: args.enabled ? (isNone ? NiftyDraw.colors.text2 : NiftyDraw.colors.text) : NiftyDraw.colors.inactive,
			align: "center"
		});

		return {
			[`enabled${args.suffix}`]: enableDraw,
			[`lora${args.suffix}`]: loraDraw,
			[`remove${args.suffix}`]: removeDraw,
			[`strength_down${args.suffix}`]: strengthDownDraw,
			[`strength${args.suffix}`]: strengthDraw,
			[`strength_up${args.suffix}`]: strengthUpDraw
		};
	},

	updateEnabled: function(row, widgetName = "enabled") {
		row[widgetName] = !row[widgetName];
		this.callback?.(this._value);
		this._node.setDirtyCanvas(true, true);
	},

	updateLora: async function(row, event, widgetName = "lora", contextTitle = "Select a lora") {
		const loras = await getLoraList();

		const menu = new LiteGraph.ContextMenu(loras, {
			event: event,
			className: "dark",
			parentMenu: null,
			title: contextTitle,
			callback: async (v) => {
				row[widgetName] = v;
				this.callback?.(this._value);
				this._node.setDirtyCanvas(true, true);
			},
		});

		requestAnimationFrame(() => requestAnimationFrame(() => {
			const items = [
				...menu.root.querySelectorAll(".litemenu-entry")
			];

			const menuFilter = menu.root.querySelector('.comfy-context-menu-filter');

			if(menuFilter) {
				menuFilter.style.position = "sticky";
				menuFilter.style.top = "0px";
			}

			const menuTitle = menu.root.querySelector('.litemenu-title');

			if(menuTitle) {
				menuTitle.style.position = "sticky";
				menuTitle.style.top = "19px";
			}

			items.forEach(el => {
				el.style.removeProperty("background-color");
				el.style.removeProperty("color");
			});

			const match = items.find(el => {
				return el.textContent?.trim() === row[widgetName];
			});

			if(match) {
				match.style.setProperty("background-color", "#ccc", "important");
				match.style.setProperty("color", "#000", "important");
				match.scrollIntoView({ block: "center" });
			}
		}));
	},

	removeRow: function(row, rowIndex, widgetHeight) {
		this._value.splice(rowIndex, 1);
		this.callback?.(this._value);
		
		resizeAfterRowChange(
			this._node,
			this._subgraphNode,
			-(widgetHeight + NiftyDraw.rowGap)
		);
	},

	strengthDown: function(row, widgetName = "strength") {
		row[widgetName] = NiftyHelpers.numberInput(row[widgetName] - 0.05, {
			round: 0.05,
			min: -100,
			max: 100
		});

		this.callback?.(this._value);
		this._node.setDirtyCanvas(true, true);
	},

	strengthUpdate: function(row, widgetName = "strength") {
		app.canvas.prompt("strength", row[widgetName], (value) => {
			const numberValue = parseFloat(value);
			
			if(!isNaN(numberValue)) {
				row[widgetName] = NiftyHelpers.numberInput(numberValue, {
					min: -100,
					max: 100
				});

				this.callback?.(this._value);
				this._node.setDirtyCanvas(true, true);
			}
		}, event);
	},

	strengthUp: function(row, widgetName = "strength") {
		row[widgetName] = NiftyHelpers.numberInput(row[widgetName] + 0.05, {
			round: 0.05,
			min: -100,
			max: 100
		});

		this.callback?.(this._value);
		this._node.setDirtyCanvas(true, true);
	}
};

app.registerExtension({
	name: "comfyui.nifty.nodes.lora",

	async getCustomWidgets(app) {
		getLoraList();

		return {
			NIFTY_LORA_LOADER: (node, inputName, inputData) => {
				const widgetHeight = NiftyDraw.height;

				const widget = {
					type: "NIFTY_LORA_LOADER",
					name: inputName,
					options: inputData[1] ?? {},

					_minRows: 1,
					_value: [defaultLoraRow()],
					_node: node,
					_subgraphNode: null,
					_drawRects: [],

					get value() {
						return this._value;
					},

					set value(value) {
						let parsed = value;

						if(typeof value === "string") {
							try {
								parsed = JSON.parse(value);
							} catch {
								parsed = null;
							}
						}

						let rows = null;

						if(Array.isArray(parsed)) {
							rows = parsed;
						} else if(parsed?.rows && Array.isArray(parsed.rows)) {
							rows = parsed.rows;
						}

						if(rows !== null) {
							this._value = JSON.parse(JSON.stringify(rows));
						}
					},

					serializeValue() {
						return JSON.stringify(this._value);
					},

					setMinRows(n) {
						this._minRows = Math.max(0, n);

						const before = this._value.length;

						while(this._value.length < this._minRows) {
							this._value.push(defaultLoraRow());
						}

						const added = this._value.length - before;

						if(added > 0) {
							resizeAfterRowChange(
								this._node,
								this._subgraphNode,
								added * (widgetHeight + NiftyDraw.rowGap)
							);
						}

						app.canvas.setDirty(true);
					},

					computeSize(width) {
						const n = this._value.length;
						return [width, n * widgetHeight + (n - 1) * NiftyDraw.rowGap];
					},

					draw(ctx, node, widgetWidth, y) {
						if(node !== this._node) {
							this._subgraphNode = node;
						}

						this._drawRects = [];

						//const isPromoted = NiftyHelpers.isPromoted(node, widget);
						const isPromoted = false;

						ctx.save();

						this._value.forEach((row, rowIndex) => {
							const rowY = y + rowIndex * (widgetHeight + NiftyDraw.rowGap);
							const mandatory = rowIndex < this._minRows;

							row = {
								enabled: true,
								lora: "none",
								strength: 1.0,
								...row
							};

							let rowDraw = {
								row: {
									x: NiftyDraw.left,
									y: rowY,
									width: widgetWidth - NiftyDraw.left - NiftyDraw.right,
									height: widgetHeight,
								}
							};

							// Lora
							const loraDraw = loraLoader.drawLoraSelectRow(ctx, rowY, widgetWidth, {
								enabled: row.enabled,
								lora: row.lora,
								strength: row.strength,
								promoted: isPromoted,
								show_remove: !mandatory
							});

							rowDraw = {
								...rowDraw,
								...loraDraw,
							}

							this._drawRects.push(rowDraw);
						});

						ctx.restore();
					},

					async mouse(event, pos, node) {
						bindWidgetMouse.call(this, event, pos, {
							enabled: (row) => {
								loraLoader.updateEnabled.call(this, row);
							},

							lora: (row) => {
								loraLoader.updateLora.call(
									this,
									row,
									event,
									"lora",
									this._node.properties?.context_title?.trim() || "Select a lora"
								);
							},
			
							remove: (row, rowIndex, section) => {
								loraLoader.removeRow.call(this, row, rowIndex, widgetHeight);
							},

							strength_down: (row) => {
								loraLoader.strengthDown.call(this, row, "strength");
							},

							strength: (row) => {
								loraLoader.strengthUpdate.call(this, row, "strength");
							},

							strength_up: (row) => {
								loraLoader.strengthUp.call(this, row, "strength");
							},
						});
					},
				};

				node.addCustomWidget(widget);

				return { widget };
			}
		};
	},

	async beforeRegisterNodeDef(nodeType, nodeData) {
		// Lora Loader
		if(["NiftyLoraLoader", "NiftyLoraStack"].includes(nodeData.name)) {
			const LoraStack = new NiftyNode(nodeType, nodeData, {
				width: 400,
				removeInputs: ["loras", "add_row"],
				properties: [
					["min_rows", 1, "string"],
					["button_label", "", "string"],
					["context_title", "", "string"],
				],
			});

			LoraStack.applyHook("onNodeCreated", function(node) {
				const buttonWidget = node.addWidget("button", "add_lora", null, function(value, canvas, currentNode, pos, event) {
					const partner = NiftyHelpers.getWidget(this._node, "loras");

					if(!partner) {
						return;
					}

					NiftyDraw.setPressed(currentNode, this, "add");
					partner._value.push(defaultLoraRow());
					partner.callback?.(partner._value);

					resizeAfterRowChange(
						this._node,
						this._subgraphNode ?? partner._subgraphNode ?? null,
						LiteGraph.NODE_WIDGET_HEIGHT + NiftyDraw.rowGap
					);
				});

				buttonWidget._subgraphNode = null;
				buttonWidget._node = node;

				buttonWidget.draw = function(ctx, node, widgetWidth, y) {
					const widget = this;
					
					if(node !== this._node) {
						this._subgraphNode = node;
					}

					const isPromoted = NiftyHelpers.isPromoted(node, widget);
					const buttonLabel = this._node.properties?.button_label?.trim() || "➕ Add Lora";

					// Button
					NiftyDraw.buttonWidget(ctx, {
						label: buttonLabel,
						x: NiftyDraw.left,
						y: y + 2,
						width: widgetWidth - NiftyDraw.left - NiftyDraw.right,
						promoted: isPromoted,
						pressed: NiftyDraw.isPressed(node, this, "add")
					});
				}
			});

			LoraStack.applyHook("onAfterGraphConfigured", function(node) {
				let minRowsValue = node.properties.min_rows ?? 1;
				minRowsValue = isNaN(minRowsValue) ? 1 : parseInt(minRowsValue);

				const minRows = Math.max(0, minRowsValue);
				const paramsWidget = this.getWidgetByType(node, "NIFTY_LORA_LOADER");

				node.properties.min_rows = minRows;

				if(paramsWidget) {
					paramsWidget.setMinRows(minRows);
				}
			});

			LoraStack.applyHook("onPropertyChanged", function(node, name, value) {
				switch (name) {
					case "min_rows":
						let minRowsValue = isNaN(value) ? 1 : parseInt(value);
						const minRows = Math.max(0, minRowsValue);
						const paramsWidget = this.getWidgetByType(node, "NIFTY_LORA_LOADER");

						node.properties.min_rows = minRows;

						if(paramsWidget) {
							paramsWidget.setMinRows(minRows);
						}

						break;

					case "button_label":
						node.properties.button_label = value;
						app.canvas.setDirty(true);

						break;

					case "context_title":
						node.properties.context_title = value;
	
						break;
				}
			});
		}
	},

	async afterConfigureGraph(arg, app) {
		app.canvas.constructor.link_type_colors["NIFTY_LORA_STACK"] = loraStackTypeColor;
		app.canvas.default_connection_color_byType["NIFTY_LORA_STACK"] = loraStackTypeColor;
	},
});