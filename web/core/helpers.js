import { app } from "../../../../scripts/app.js";

const NiftyHelpers = {
	findNodes(args = {}) {
		args = {
			graph: app.graph,
			title: [],
			name: [],
			...args
		};

		if(!Array.isArray(args.title)) {
			args.title = [args.title];
		}

		if(!Array.isArray(args.name)) {
			args.name = [args.name];
		}

		const result = [];
		const hasTitleFilter = args.title.length > 0;
		const hasNameFilter = args.name.length > 0;

		function traverse(nodes) {
			for(const node of nodes) {
				const matchesTitle = !hasTitleFilter || args.title.includes(node.title);
				const matchesName = !hasNameFilter || args.name.includes(node.type) || args.name.includes(node.name);

				if((!hasTitleFilter && !hasNameFilter) || (matchesTitle && matchesName)) {
					result.push(node);
				}

				if(node.subgraph && node.subgraph._nodes) {
					traverse(node.subgraph._nodes);
				}
			}
		}

		traverse(args.graph._nodes);

		return result;
	},

	findNodesByWidget(args = {}) {
		args = {
			graph: app.graph,
			name: [],
			...args
		};

		if(!Array.isArray(args.name)) {
			args.name = [args.name];
		}

		const result = [];
		const hasWidgetFilter = args.name.length > 0;

		function traverse(nodes) {
			for(const node of nodes) {
				const widgets = Array.isArray(node.widgets) ? node.widgets : [];
				const matchesWidget =
					!hasWidgetFilter ||
					widgets.some(widget => args.name.includes(widget?.name));

				if(matchesWidget) {
					result.push(node);
				}

				if(node.subgraph?._nodes) {
					traverse(node.subgraph._nodes);
				}
			}
		}

		traverse(args.graph._nodes);

		return result;
	},

	getWidget(node, name) {
		return node.widgets.find(w => w.name === name);
	},

	isPromoted(node, widget, graph = app.canvas.graph) {
		const targetNodeId = String(node.id);
		const targetWidgetName = String(widget.name);

		const matches = (w) => {
			if(!w) {
				return false;
			}

			const sourceName = w.sourceWidgetName;
			const sourceId = w.disambiguatingSourceNodeId ?? w.sourceNodeId;

			if(sourceName === targetWidgetName && String(sourceId) === targetNodeId) {
				return true;
			}

			return w.name === `${targetNodeId}: ${targetWidgetName}`;
		};

		const walk = (graph) => {
			for(const n of graph?.nodes ?? []) {
				for(const w of n.widgets ?? []) {
					if(matches(w)) {
						return true;
					}
				}

				if(n.subgraph && walk(n.subgraph)) {
					return true;
				}
			}

			return false;
		};

		return walk(app.graph);
	},

	removeInput(node, slotName) {
		if(!Array.isArray(slotName)) {
			slotName = [slotName];
		}

		for(let i = (node.inputs?.length || 0) - 1; i >= 0; i--) {
			const input = node.inputs[i];

			if(slotName.includes(input.name)) {
				node.removeInput(i);
			}
		}
	},

	fixNodeLinks(node) {
		if(!node || !app.graph) {
			return;
		}

		let changed = false;

		if(node.inputs) {
			node.inputs.forEach((input, index) => {
				if(input.link != null) {
					const link = app.graph.links[input.link];
					const isBroken = !link || !app.graph.getNodeById(link.origin_id);

					if(isBroken) {
						node.disconnectInput(index); 
						
						if(node.inputs[index].link != null) {
							node.inputs[index].link = null;
						}

						changed = true;
					}
				}
			});
		}

		if(node.outputs) {
			node.outputs.forEach((output, index) => {
				if(output.links && output.links.length > 0) {
					const validLinks = output.links.filter(linkId => {
						const link = app.graph.links[linkId];
						const isBroken = !link || !app.graph.getNodeById(link.target_id);

						if(isBroken) {
							if(link) {
								app.graph.removeLink(linkId); 
							}
							
							changed = true;
							return false;
						}

						return true;
					});

					output.links = validLinks;
				}
			});
		}

		if(changed) {
			node.setDirtyCanvas(true, true);
		}
	},

	numberInput(value, args = {}) {
		args = {
			round: null,
			min: null,
			max: null,
			...args
		};

		let result = Number(value);

		if(Number.isNaN(result)) {
			return NaN;
		}

		const getDecimals = (nr) => {
			const str = String(nr);

			if(str.includes("e-")) {
				return parseInt(str.split("e-")[1], 10);
			}
			
			if(str.includes(".")) {
				return str.split(".")[1].replace(/0+$/, "").length;
			}

			return 0;
		};

		const normalize = (val, step) => {
			const dec = getDecimals(step);
			return parseFloat(val.toFixed(dec));
		};

		if(args.round !== null) {
			result = Math.round(result / args.round) * args.round;
			result = normalize(result, args.round);
		}

		if(args.min !== null) {
			result = Math.max(result, args.min);
		}

		if(args.max !== null) {
			result = Math.min(result, args.max);
		}

		if(args.round !== null) {
			result = normalize(result, args.round);
		}

		return result;
	},

	containsPointer(x, y, rect) {
		return (
			x >= rect.x &&
			x <= rect.x + rect.width &&
			y >= rect.y &&
			y <= rect.y + rect.height
		);
	}
};

const NiftyDraw = {
	height: LiteGraph.NODE_WIDGET_HEIGHT,
	buttonHeight: 22,
	left: 15,
	right: 15,
	rowGap: 4,
	rowGapLarge: 8,
	colGap: 4,
	colors: {
		text: LiteGraph.WIDGET_TEXT_COLOR,
		text2: LiteGraph.WIDGET_SECONDARY_TEXT_COLOR,
		inactive: "#595959",
		bg: LiteGraph.WIDGET_BGCOLOR,
		outline: LiteGraph.WIDGET_OUTLINE_COLOR,
		promoted: LiteGraph.WIDGET_PROMOTED_OUTLINE_COLOR,
		active: "#7892b3",
		remove: "rgb(179,58,58)",

		buttonBg: "#191919",
		buttonBorder: "#595959",
		buttonBgActive: "#24352A",
		buttonBorderActive: "#3B5E38",
		buttonBgPressed: "rgba(255,255,255,0.12)"
	},
	font: {
		type: LiteGraph.NODE_FONT,
		size: LiteGraph.NODE_SUBTEXT_SIZE,
		sizeSmall: LiteGraph.NODE_SUBTEXT_SIZE - 1,
	},

	setPressed(node, widget, codename = "widget") {
		if(!widget._pressed) {
			widget._pressed = {};
		}

		widget._pressed[codename] = true;

		setTimeout(() => {
			widget._pressed[codename] = false;
			node.setDirtyCanvas(true, true);
		}, 80);

		node.setDirtyCanvas(true, true);
	},

	isPressed(node, widget, codename = "widget") {
		return widget._pressed?.[codename] ?? false;
	},

	calculateColumns(args) {
        const columns = args.columns;

        if(!columns) {
            return {};
        }

        const widgetWidth = args.widgetWidth || 0;
        const gap = args.gap ?? this.colGap;
        const indentLeft = args.indentLeft ?? this.left; 
        const indentRight = args.indentRight ?? this.right; 

        let totalPxWidth = 0;
        let numCols = 0;

        for(const key in columns) {
            const val = columns[key];
            
            if(typeof val === 'string' && val.endsWith('px')) {
                totalPxWidth += parseFloat(val) || 0;
            }

            numCols++;
        }

        const totalGapWidth = (numCols > 1 ? numCols - 1 : 0) * gap;
        const usableWidgetWidth = Math.max(0, widgetWidth - indentLeft - indentRight);
        const availableWidth = Math.max(0, usableWidgetWidth - totalPxWidth - totalGapWidth);
        const result = {};
        let currentX = indentLeft;

        for(const key in columns) {
            const val = columns[key];
            let colWidth = 0;

            if(typeof val === 'number') {
                colWidth = (val / 100) * availableWidth;
            } else if(typeof val === 'string') {
                const numValue = parseFloat(val) || 0;
                colWidth = val.endsWith('px') ? numValue : (numValue / 100) * availableWidth;
            }

            result[key] = {
                width: colWidth,
                x: currentX
            };

            currentX += colWidth + gap;
        }

        return result;
    },

	roundRect(ctx, args = {}) {
		args = {
			x: 0,
			y: 0,
			width: 0,
			height: 0,
			radius: null,
			fill: null,
			stroke: null,
			strokeWidth: 1,

			...args
		};

		if(args.radius === "round") {
			args.radius = args.height / 2;
		}

		ctx.beginPath();
		ctx.roundRect(args.x, args.y, args.width, args.height, args.radius);

		if(args.fill) {
			ctx.fillStyle = args.fill;
			ctx.fill();
		}

		if(args.stroke) {
			ctx.strokeStyle = args.stroke;
			ctx.lineWidth = args.strokeWidth;
			ctx.stroke();
		}

		return {
			x: args.x,
			y: args.y,
			width: args.width,
			height: args.height
		};
	},

	circle(ctx, args = {}) {
		args = {
			x: 0,
			y: 0,
			size: 0,
			fill: null,
			stroke: null,
			strokeWidth: 1,

			...args
		};

		this.roundRect(ctx, {
			x: args.x,
			y: args.y,
			width: args.size,
			height: args.size,
			radius: "round",
			fill: args.fill,
			stroke: args.stroke,
			strokeWidth: args.strokeWidth
		});

		return {
			x: args.x,
			y: args.y,
			width: args.size,
			height: args.size
		};
	},

	line(ctx, args = {}) {
		args = {
			x: 0,
			y: 0,
			height: 0,
			width: 1,
			fill: "#FFFFFF",

			...args
		};

		ctx.save();
		ctx.strokeStyle = args.fill;
		ctx.lineWidth = args.width;
		ctx.beginPath();
		ctx.moveTo(args.x, args.y);
		ctx.lineTo(args.x, args.y + args.height);
		ctx.stroke();
		ctx.restore();
	},

	text(ctx, args = {}) {
		args = {
			text: '',
			ellipsis: ' …',
			x: 0,
			y: 0,
			width: 0,
			font: this.font.type,
			fontSize: this.font.size,
			color: this.colors.text,
			align: "left",

			...args
		};

		ctx.save();
		ctx.font = `${args.fontSize}px ${args.font}`;
		ctx.textAlign = args.align;
		ctx.textBaseline = "middle";
		ctx.fillStyle = args.color;

		let text = args.text;
		let textWidth = 0;

		if(args.width) {
			const fullWidth = ctx.measureText(text).width;
			const maxWidth = args.width;

			if(fullWidth > maxWidth) {
				let clipped = text;
				const ellipsisWidth = ctx.measureText(args.ellipsis).width;

				while(clipped.length > 0) {
					const test = clipped + args.ellipsis;

					if(ctx.measureText(test).width <= maxWidth) {
						text = test;
						break;
					}

					clipped = clipped.slice(0, -1);
				}

				if(clipped.length === 0) {
					text = args.ellipsis.trim();
				}
			}
		}

		const renderedTextSize = ctx.measureText(text);
		const renderedTextHeight = renderedTextSize.actualBoundingBoxAscent + renderedTextSize.actualBoundingBoxDescent;
		const renderWidth = args.width ? args.width : renderedTextSize.width;

		let renderX = args.x;
		let renderY = args.y - (renderedTextHeight / 2);

		if(args.align === "center") {
			renderX -= renderedTextSize.width / 2;
		} else if(args.align === "right") {
			renderX -= renderedTextSize.width;
		}

		ctx.fillText(text, args.x, args.y);
		ctx.restore();

		return {
			x: renderX,
			y: renderY,
			width: renderWidth,
			height: renderedTextHeight
		};
	},

	removeButton(ctx, args = {}) {
		args = {
			x: 0,
			y: 0,
			size: 10,

			disabled: false,

			...args
		};

		ctx.beginPath();
		ctx.arc(args.x, args.y, args.size / 2, 0, Math.PI * 2);
		ctx.fillStyle = args.disabled ? this.colors.inactive : this.colors.remove;
		ctx.fill();
		ctx.fillStyle = args.disabled ? this.colors.text2 : "#fff";
		ctx.font = "bold 7px sans-serif";
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		ctx.fillText("✕", args.x, args.y + 0.5);

		return {
			x: args.x - (args.size / 2),
			y: args.y - (args.size / 2),
			width: args.size,
			height: args.size
		};
	},

	buttonWidget(ctx, args = {}) {
		args = {
			label: "Button",

			x: 0,
			y: 0,
			width: 0,
			height: this.height,

			active: false,
			promoted: false,
			pressed: false,

			...args
		};

		let bgColor = this.colors.buttonBg;
		let borderColor = this.colors.buttonBorder;

		if(args.active) {
			bgColor = this.colors.buttonBgActive;
			borderColor = this.colors.buttonBorderActive;
		}

		if(args.pressed) {
			bgColor = this.colors.buttonBgPressed;
		}

		if(args.promoted) {
			borderColor = this.colors.promoted;
		}

		this.roundRect(ctx, {
			x: args.x,
			y: args.y,
			width: args.width,
			height: args.height,
			fill: bgColor, 
			stroke: borderColor, 
			radius: 2
		});

		this.text(ctx, {
			text: args.label,
			x: args.x + (args.width / 2),
			y: args.y + 1 + (args.height / 2),
			width: args.width,
			font: this.font.type,
			fontSize: 11,
			align: "center",
			color: this.colors.text,
		});

		return {
			x: args.x,
			y: args.y,
			width: args.width,
			height: args.height
		};
	},

	stringWidget(ctx, widgetTop, args = {}) {
		args = {
			label: "value",
			value: "",

			left: 0,
			top: widgetTop,
			height: this.height,
			width: 0,

			indent: 10,
			spacing: 6,

			disabled: false,
			promoted: false,

			...args
		};

		this.roundRect(ctx, {
			x: args.left,
			y: args.top,
			width: args.width,
			height: args.height,
			fill: this.colors.bg,
			stroke: args.promoted ? this.colors.promoted : this.colors.outline,
			radius: "round"
		});

		const labelDraw = this.text(ctx, {
			text: args.label,
			x: args.left + args.indent,
			y: args.top + (args.height / 2),
			fontSize: this.font.sizeSmall,
			color: args.disabled ? this.colors.inactive : this.colors.text2,
			align: "left"
		});

		this.text(ctx, {
			text: args.value,
			x: args.left + args.width - args.indent,
			y: args.top + (args.height / 2),
			width: args.width - labelDraw.width - args.spacing - (args.indent * 2),
			fontSize: this.font.sizeSmall,
			color: args.disabled ? this.colors.inactive : this.colors.text,
			align: "right"
		});

		return {
			x: args.left,
			y: args.top,
			width: args.width,
			height: args.height
		};
	}
};

export { NiftyHelpers, NiftyDraw };