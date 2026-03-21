import { app } from "../../scripts/app.js";

const BUNDLE_TYPE  = "BUNDLE";
const BUNDLE_COLOR = "#c77dff";

let _lgPatched = false;
function patchLGCanvas() {
    if (_lgPatched) return;
    try {
        const LGC = window.LGraphCanvas ?? (typeof LGraphCanvas !== "undefined" ? LGraphCanvas : null);
        if (!LGC?.prototype) return;
        _lgPatched = true;

        if (typeof LGC.prototype.renderLink === "function") {
            const orig = LGC.prototype.renderLink;
            LGC.prototype.renderLink = function(ctx, a, b, link, skipBorder, flow, color, ...rest) {
                if (link?.type === BUNDLE_TYPE) color = BUNDLE_COLOR;
                return orig.call(this, ctx, a, b, link, skipBorder, flow, color, ...rest);
            };
        }
        if (typeof LGC.prototype.getLinkColor === "function") {
            const orig = LGC.prototype.getLinkColor;
            LGC.prototype.getLinkColor = function(link, ...a) {
                if (link?.type === BUNDLE_TYPE) return BUNDLE_COLOR;
                return orig.call(this, link, ...a);
            };
        }
        (LGC.link_type_colors ??= {})[BUNDLE_TYPE] = BUNDLE_COLOR;

        // Hidden Link — only hide links where the SOURCE is a HiddenLink node
        if (typeof LGC.prototype.drawConnections === "function") {
            const origDraw = LGC.prototype.drawConnections;
            LGC.prototype.drawConnections = function(ctx) {
                const graph = this.graph ?? app.graph;
                const hiddenLinks = new Set();
                const activeHiddenLinks = new Set();
                try {
                    const L = graph.links;
                    const entries = L instanceof Map ? L.entries() : Object.entries(L);
                    const selected = app.canvas.selected_nodes ?? {};
                    for (const [id, link] of entries) {
                        if (!link) continue;
                        const srcNode = graph.getNodeById(link.origin_id);
                        const dstNode = graph.getNodeById(link.target_id);
                        const isHiddenLinkNode = srcNode?.type === "NiftyHiddenLink";
                        const isHiddenUnpack = srcNode?.type === "NiftyBundleUnpack"
                            && srcNode?.widgets?.find(w => w.name === "hide_links")?.value === true;
                        const isMagicInput = dstNode?.type === "NiftyMagicGetter" && link.target_slot === 0;
                        if (!isHiddenLinkNode && !isHiddenUnpack && !isMagicInput) continue;
                        const active =
                            srcNode?.mouseOver || selected[link.origin_id] !== undefined ||
                            dstNode?.mouseOver || selected[link.target_id] !== undefined;
                        if (active) activeHiddenLinks.add(+id);
                        else hiddenLinks.add(+id);
                    }
                } catch (_) {}

                if (!hiddenLinks.size && !activeHiddenLinks.size) return origDraw.call(this, ctx);

                const origRL = LGC.prototype.renderLink;
                LGC.prototype.renderLink = function(ctx, a, b, link, ...rest) {
                    if (link && hiddenLinks.has(link.id)) {
                        return; // opacity 0 — invisible
                    }
                    if (link && activeHiddenLinks.has(link.id)) {
                        ctx.save();
                        ctx.globalAlpha = 0.5;
                        const r = origRL.call(this, ctx, a, b, link, ...rest);
                        ctx.restore();
                        return r;
                    }
                    return origRL.call(this, ctx, a, b, link, ...rest);
                };
                const result = origDraw.call(this, ctx);
                LGC.prototype.renderLink = origRL;
                return result;
            };
        }

    } catch (_) {}
}

function registerColors() {
    patchLGCanvas();
    try { const m = app.canvas?.default_connection_colors_by_type; if (m) m[BUNDLE_TYPE] = BUNDLE_COLOR; } catch (_) {}
    try { if (typeof LGraphCanvas !== "undefined") (LGraphCanvas.link_type_colors ??= {})[BUNDLE_TYPE] = BUNDLE_COLOR; } catch (_) {}
    try {
        const pinia = app.vueApp?._context?.provides?.pinia ?? window.__pinia;
        if (pinia) for (const [, s] of pinia._s) {
            if (s.colorPalette?.colors?.node_slot) s.colorPalette.colors.node_slot[BUNDLE_TYPE] = BUNDLE_COLOR;
            if (s.completedActivePalette?.node_slot) s.completedActivePalette.node_slot[BUNDLE_TYPE] = BUNDLE_COLOR;
        }
    } catch (_) {}
}

function getLink(id, graph) {
    if (id == null) return null;
    try { const L = (graph ?? app.graph).links; return (L instanceof Map ? L.get(id) : L[id]) ?? null; } catch (_) { return null; }
}
function getNode(id, graph) { try { return (graph ?? app.graph).getNodeById(id) ?? null; } catch (_) { return null; } }

function typeColor(type) {
    if (!type || type === "*") return null;
    if (type === BUNDLE_TYPE) return BUNDLE_COLOR;
    try { const c = app.canvas?.default_connection_colors_by_type?.[type]; return (c && c !== "") ? c : null; } catch (_) { return null; }
}

function resizeH(node) { try { const s = node.computeSize(); node.setSize([node.size[0], s[1]]); } catch (_) {} }
function dirty() { try { app.graph.setDirtyCanvas(true, true); } catch (_) {} }
function getCount(node) { return Math.max(1, Math.min(32, Math.round(node.widgets?.find(w => w.name === "count")?.value ?? 1))); }
function slotName(i) { return `value${i + 1}`; }
function setBundleSlot(slot) { if (!slot) return; slot.type = BUNDLE_TYPE; slot.color_on = BUNDLE_COLOR; slot.color_off = BUNDLE_COLOR; }

function syncInputSlots(node, startIdx, count) {
    const desired = startIdx + count;
    while (node.inputs.length < desired) {
        const i = node.inputs.length - startIdx;
        node.addInput(slotName(i), "*");
        node.inputs[node.inputs.length - 1].label = slotName(i);
    }
    while (node.inputs.length > desired) {
        const last = node.inputs[node.inputs.length - 1];
        if (last.link != null) try { (node.graph ?? app.graph).removeLink(last.link); } catch (_) {}
        node.removeInput(node.inputs.length - 1);
    }
    resizeH(node);
    dirty();
}

function syncOutputSlots(node, startIdx, count) {
    const desired = startIdx + count;
    while (node.outputs.length < desired) {
        const i = node.outputs.length - startIdx;
        node.addOutput(slotName(i), "*");
        node.outputs[node.outputs.length - 1].label = slotName(i);
    }
    while (node.outputs.length > desired) {
        const last = node.outputs[node.outputs.length - 1];
        for (const lid of last.links ?? []) try { (node.graph ?? app.graph).removeLink(lid); } catch (_) {}
        node.removeOutput(node.outputs.length - 1);
    }
    resizeH(node);
    dirty();
}

function colorInput(node, idx) {
    const inp = node.inputs?.[idx];
    if (!inp) return;
    if (inp.link == null) { inp.type = "*"; delete inp.color_on; }
    else {
        const g = node.graph ?? null;
        const lnk = getLink(inp.link, g); if (!lnk) return;
        const src = getNode(lnk.origin_id, g);
        const t = src?.outputs?.[lnk.origin_slot]?.type ?? "*";
        inp.type = t; lnk.type = t;
        const c = typeColor(t); if (c) inp.color_on = c; else delete inp.color_on;
    }
}

function colorOutput(node, idx) {
    const out = node.outputs?.[idx];
    if (!out) return;
    if (!out.links?.length) { out.type = "*"; delete out.color_on; }
    else {
        const g = node.graph ?? null;
        const lnk = getLink(out.links[0], g); if (!lnk) return;
        const dst = getNode(lnk.target_id, g);
        const t = dst?.inputs?.[lnk.target_slot]?.type ?? "*";
        if (t && t !== "*") {
            out.type = t; lnk.type = t;
            const c = typeColor(t); if (c) out.color_on = c; else delete out.color_on;
        }
    }
}

function setupWidget(node, syncFn) {
    const w = node.widgets?.find(w => w.name === "count");
    if (!w) return;
    w.options = { ...w.options, min: 1, max: 32, step: 1, precision: 0 };
    const origCb = w.callback?.bind(w);
    w.callback = function(value) {
        w.value = Math.max(1, Math.min(32, Math.round(+value)));
        syncFn(node);
        origCb?.(w.value);
    };
}


function doAutoConnect(node) {
    const slotNameW = node.widgets?.find(w => w.name === "slot_name");
    const slotName  = slotNameW?.value?.trim();
    if (!slotName) return;

    const g = node.graph ?? app.graph;

    // Find all matching output slots, sorted by X position descending
    const candidates = [];
    for (const n of collectAllNodes(g)) {
        if (n.id === node.id) continue;
        for (let i = 0; i < (n.outputs?.length ?? 0); i++) {
            const out = n.outputs[i];
            const name = (out.label ?? out.name ?? "").trim();
            if (name === slotName) {
                // Free = no links, OR only linked to this magic getter node
                const otherLinks = (out.links ?? []).filter(lid => {
                    const lnk = g.links instanceof Map ? g.links.get(lid) : g.links[lid];
                    return lnk && lnk.target_id !== node.id;
                });
                const isFree = otherLinks.length === 0;
                candidates.push({ node: n, slot: i, x: n.pos?.[0] ?? 0, free: isFree });
            }
        }
    }

    if (!candidates.length) return;

    // Only use free slots — if none found, do nothing
    const freeOnly = candidates.filter(c => c.free);
    if (!freeOnly.length) return;
    freeOnly.sort((a, b) => b.x - a.x);
    const best = freeOnly[0];

    // Check current connection
    const inp = node.inputs?.[0];
    const existingLink = inp?.link != null
        ? (g.links instanceof Map ? g.links.get(inp.link) : g.links[inp.link])
        : null;

    const alreadyCorrect = existingLink &&
        existingLink.origin_id === best.node.id &&
        existingLink.origin_slot === best.slot;
    if (alreadyCorrect) return;

    // Disconnect current if wrong or slot name changed
    if (existingLink) {
        try {
            const on = g.getNodeById?.(existingLink.origin_id);
            if (on?.disconnectOutput) on.disconnectOutput(existingLink.origin_slot);
        } catch(_) {}
    }

    best.node.connect(best.slot, node, 0);
    dirty();
}


function runDuplicator(ctrlNode) {
    const titleW       = ctrlNode.widgets?.find(w => w.name === "title");
    const countW       = ctrlNode.widgets?.find(w => w.name === "count");
    const connectW     = ctrlNode.widgets?.find(w => w.name === "connect_slots");
    const gapW         = ctrlNode.widgets?.find(w => w.name === "gap");
    const deleteW      = ctrlNode.widgets?.find(w => w.name === "delete_excess");
    const srootW       = ctrlNode.widgets?.find(w => w.name === "search_from_root");

    const title        = titleW?.value?.trim();
    const count        = Math.max(1, Math.min(32, Math.round(countW?.value ?? 1)));
    const slotNames    = (connectW?.value ?? "").split(",").map(s => s.trim()).filter(Boolean);
    const gap          = Math.max(0, Math.round(gapW?.value ?? 20));
    const deleteExcess = deleteW?.value ?? false;
    const fromRoot     = srootW?.value ?? true;

    if (!title) return;

    const g = fromRoot ? app.graph : (ctrlNode.graph ?? app.graph);

    // Find all nodes with matching title, sorted by X position
    const matches = (g._nodes ?? [])
        .filter(n => n.title?.trim() === title && n.id !== ctrlNode.id)
        .sort((a, b) => (a.pos?.[0] ?? 0) - (b.pos?.[0] ?? 0));

    if (!matches.length) return;

    const original = matches[0]; // leftmost = original
    const existing = matches;    // all including original

    // Handle excess nodes (count < existing)
    if (existing.length > count) {
        const excess = existing.slice(count); // rightmost extras
        for (const n of excess) {
            if (deleteExcess) {
                g.remove(n);
            } else {
                n.mode = 4; // bypass
                n.setDirtyCanvas?.(true, true);
            }
        }
    }

    // Reactivate nodes that were bypassed if count increased
    for (let i = 0; i < Math.min(count, existing.length); i++) {
        if (existing[i].mode === 4) {
            existing[i].mode = 0;
            existing[i].setDirtyCanvas?.(true, true);
        }
    }

    // Create missing copies via canvas copy/paste — only reliable method for subgraphs
    let prev = existing[existing.length - 1] ?? original;
    for (let i = existing.length; i < count; i++) {
        // Select only original, call copy/paste directly bypassing focus checks
        const prevSelected = app.canvas.selected_nodes ?? {};
        const prevSelectedItems = app.canvas.selectedItems;
        app.canvas.selected_nodes = { [original.id]: original };
        if (app.canvas.selectedItems) app.canvas.selectedItems = new Set([original]);

        const beforeIds = new Set((g._nodes ?? []).map(n => n.id));

        // Call directly without focus check
        const canvas = app.canvas;
        if (canvas.copyToClipboard) canvas.copyToClipboard();
        if (canvas.pasteFromClipboard) canvas.pasteFromClipboard();

        app.canvas.selected_nodes = prevSelected;
        if (prevSelectedItems !== undefined) app.canvas.selectedItems = prevSelectedItems;

        // Find the newly added node
        const copy = (g._nodes ?? []).find(n => !beforeIds.has(n.id));
        if (!copy) continue;

        copy.pos = [
            prev.pos[0] + (prev.size?.[0] ?? 200) + gap,
            prev.pos[1]
        ];

        // Connect slots
        if (slotNames.length) {
            for (const slotName of slotNames) {
                const outIdx = prev.outputs?.findIndex(o => (o.label ?? o.name) === slotName);
                const inIdx  = copy.inputs?.findIndex(i => (i.label ?? i.name) === slotName);
                if (outIdx >= 0 && inIdx >= 0) {
                    prev.connect(outIdx, copy, inIdx);
                }
            }
        }

        prev = copy;
    }

    app.graph.setDirtyCanvas(true, true);
}


app.registerExtension({
    name: "NiftyNodes",

    setup() { registerColors(); },

    async beforeRegisterNodeDef(nodeType, nodeData) {

        if (nodeData.name === "NiftyBundlePack") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                registerColors();
                if (!this.inputs.length) this.addInput("bundle", BUNDLE_TYPE);
                while (this.inputs.length > 1) this.removeInput(this.inputs.length - 1);
                setBundleSlot(this.inputs[0]);
                if (!this.outputs.length) this.addOutput("bundle", BUNDLE_TYPE);
                setBundleSlot(this.outputs[0]);
                setupWidget(this, (n) => syncInputSlots(n, 1, getCount(n)));
                syncInputSlots(this, 1, getCount(this));
                const node = this;
                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType === LiteGraph.INPUT) {
                        if (slotIdx === 0) setBundleSlot(node.inputs[0]);
                        else { (function(){ const _inp = node.inputs?.[slotIdx]; if (_inp) { _inp.type = "*"; delete _inp.color_on; } })(); queueMicrotask(() => { colorInput(node, slotIdx); dirty(); }); }
                    }
                };
            };

        }

        if (nodeData.name === "NiftyBundleUnpack") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                const hideWidget = this.widgets?.find(w => w.name === "hide_links");
                if (hideWidget) {
                    const origCb = hideWidget.callback?.bind(hideWidget);
                    hideWidget.callback = function(value) { origCb?.(value); dirty(); };
                }
                registerColors();
                if (!this.inputs.length) this.addInput("bundle", BUNDLE_TYPE);
                while (this.inputs.length > 1) this.removeInput(this.inputs.length - 1);
                setBundleSlot(this.inputs[0]);
                if (!this.outputs.length) this.addOutput("bundle", BUNDLE_TYPE);
                while (this.outputs.length > 1) this.removeOutput(this.outputs.length - 1);
                setBundleSlot(this.outputs[0]);
                setupWidget(this, (n) => syncOutputSlots(n, 1, getCount(n)));
                syncOutputSlots(this, 1, getCount(this));
                const node = this;
                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType === LiteGraph.INPUT && slotIdx === 0) setBundleSlot(node.inputs[0]);
                    if (slotType === LiteGraph.OUTPUT && slotIdx > 0) { (function(){ const _out = node.outputs?.[slotIdx]; if (_out) { _out.type = "*"; delete _out.color_on; } })(); queueMicrotask(() => { colorOutput(node, slotIdx); dirty(); }); }
                };
            };

        }

        if (nodeData.name === "NiftyBundleGet") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                registerColors();
                if (!this.inputs.length) this.addInput("bundle", BUNDLE_TYPE);
                while (this.inputs.length > 1) this.removeInput(this.inputs.length - 1);
                setBundleSlot(this.inputs[0]);
                if (!this.outputs.length) this.addOutput("value", "*");
                const node = this;
                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType === LiteGraph.INPUT && slotIdx === 0) setBundleSlot(node.inputs[0]);
                    if (slotType === LiteGraph.OUTPUT) { (function(){ const _out = node.outputs?.[0]; if (_out) { _out.type = "*"; delete _out.color_on; } })(); queueMicrotask(() => { colorOutput(node, 0); dirty(); }); }
                };
            };
            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const nd = this;
                if (nd.outputs?.[0]) { nd.outputs[0].type = "*"; delete nd.outputs[0].color_on; }
                queueMicrotask(() => { colorOutput(nd, 0); dirty(); });
            }; })(nodeType.prototype.onConfigure);
        }

        if (nodeData.name === "NiftyBundleSet") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                registerColors();
                if (!this.inputs.length) this.addInput("bundle", BUNDLE_TYPE);
                while (this.inputs.length > 1) this.removeInput(this.inputs.length - 1);
                setBundleSlot(this.inputs[0]);
                if (!this.inputs[1]) this.addInput("value", "*");
                if (!this.outputs.length) this.addOutput("bundle", BUNDLE_TYPE);
                setBundleSlot(this.outputs[0]);
                const node = this;
                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType === LiteGraph.INPUT && slotIdx === 0) setBundleSlot(node.inputs[0]);
                    if (slotType === LiteGraph.INPUT && slotIdx === 1) { (function(){ const _inp = node.inputs?.[1]; if (_inp) { _inp.type = "*"; delete _inp.color_on; } })(); queueMicrotask(() => { colorInput(node, 1); dirty(); }); }
                };
            };
            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const nd = this;
                if (nd.inputs?.[1]) { nd.inputs[1].type = "*"; delete nd.inputs[1].color_on; }
                queueMicrotask(() => { colorInput(nd, 1); dirty(); });
            }; })(nodeType.prototype.onConfigure);
        }


        if (nodeData.name === "NiftySubgraphLabels") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                this.color   = "#443322";
                this.bgcolor = "#665533";

                const self = this;

                for (const w of (this.widgets ?? [])) {
                    w.draw = function(ctx, node, widgetWidth, y, H) {
                        if (node.type === "NiftySubgraphLabels") {
                            // ── On the node itself: pill-shaped string widget ──
                            const margin = 15;
                            const r = (H - 4) / 2; // full pill radius
                            const bg  = LiteGraph.WIDGET_BGCOLOR  ?? "#1a1a1a";
                            const fg  = LiteGraph.WIDGET_TEXT_COLOR ?? "#ddd";
                            const lc  = LiteGraph.WIDGET_SECONDARY_TEXT_COLOR ?? "#888";
                            ctx.save();
                            // Background
                            ctx.fillStyle = bg;
                            ctx.beginPath();
                            if (ctx.roundRect) ctx.roundRect(margin, y + 2, widgetWidth - margin * 2, H - 4, r);
                            else ctx.rect(margin, y + 2, widgetWidth - margin * 2, H - 4);
                            ctx.fill();
                            // Border
                            ctx.strokeStyle = "#666";
                            ctx.lineWidth = 1;
                            ctx.beginPath();
                            if (ctx.roundRect) ctx.roundRect(margin, y + 2, widgetWidth - margin * 2, H - 4, r);
                            else ctx.rect(margin, y + 2, widgetWidth - margin * 2, H - 4);
                            ctx.stroke();
                            // Text
                            ctx.font = "12px Arial";
                            ctx.textAlign = "left";
                            ctx.textBaseline = "middle";
                            const label = w.name ? (w.name + ":  ") : "";
                            ctx.fillStyle = lc;
                            ctx.fillText(label, margin + r, y + H / 2);
                            ctx.fillStyle = fg;
                            const labelW = ctx.measureText(label).width;
                            ctx.fillText(w.value || "", margin + r + labelW, y + H / 2);
                            ctx.restore();
                        } else {
                            // ── In subgraph: draw as read-only label ──
                            if (!w.value) return;
                            const margin = 15;
                            ctx.save();
                            ctx.font = "12px Arial";
                            ctx.fillStyle = "#aaa";
                            ctx.textAlign = "left";
                            ctx.textBaseline = "middle";
                            ctx.fillText(w.value, margin + 8, y + H / 2 + 3);
                            ctx.restore();
                        }
                    };
                    // Block editing when in subgraph
                    w.mouse = function(event, pos, node) {
                        if (node.type !== "NiftySubgraphLabels") return false;
                        // Trigger normal text edit on click
                        if (event.type === "pointerdown") {
                            const canvas = app.canvas;
                            canvas?.prompt("Value", w.value, (v) => { w.value = v; }, event);
                        }
                        return true;
                    };
                }
            };
        }



        if (nodeData.name === "NiftyFirstSwitch") {
            const MAX_INPUTS = 16;

            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;

                // Remove ALL inputs (Python-defined ones look different), start fresh
                while (node.inputs.length > 0) node.removeInput(node.inputs.length - 1);
                node.addInput("value1", "*");
                node.addInput("value2", "*");
                resizeH(node);

                const idxWidget = null; // No index widget for FirstSwitch

                function getLockedType() {
                    for (const inp of node.inputs) {
                        if (inp.link != null && inp.type && inp.type !== "*") return inp.type;
                    }
                    return null;
                }

                function applyType(t) {
                    const c = typeColor(t);
                    for (const inp of node.inputs) {
                        inp.type = t ?? "*";
                        if (t && c) inp.color_on = c; else delete inp.color_on;
                    }
                    const out = node.outputs?.[0];
                    if (out) {
                        out.type = t ?? "*";
                        if (t && c) out.color_on = c; else delete out.color_on;
                    }
                }

                function syncSlots() {
                    const connected = node.inputs.filter(i => i.link != null).length;
                    const target = Math.min(MAX_INPUTS, Math.max(2, connected + 1)); // min 2, always one trailing empty
                    // Add missing
                    while (node.inputs.length < target) {
                        node.addInput(`value${node.inputs.length + 1}`, "*");
                    }
                    // Remove trailing empty slots only if there are 2+ empty at the end
                    while (
                        node.inputs.length > 2 &&
                        node.inputs[node.inputs.length - 1].link == null &&
                        node.inputs[node.inputs.length - 2].link == null
                    ) {
                        node.removeInput(node.inputs.length - 1);
                    }
                    // Rename all slots
                    for (let i = 0; i < node.inputs.length; i++) {
                        node.inputs[i].name  = `value${i + 1}`;
                        node.inputs[i].label = `value${i + 1}`;
                    }

                    resizeH(node);
                    dirty();
                }

                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType !== LiteGraph.INPUT) return;
                    const inp = node.inputs[slotIdx];
                    if (inp) { inp.type = "*"; delete inp.color_on; }
                    setTimeout(() => {
                        colorInput(node, slotIdx);
                        syncSlots();
                        const locked = getLockedType();
                        applyType(locked);
                        dirty();
                    }, 50);
                };
            };

            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const node = this;
                // Reset all slots, recolor, resync
                for (let i = 0; i < node.inputs.length; i++) { node.inputs[i].type = "*"; delete node.inputs[i].color_on; }
                if (node.outputs?.[0]) { node.outputs[0].type = "*"; delete node.outputs[0].color_on; }
                queueMicrotask(() => {
                    for (let i = 0; i < node.inputs.length; i++) colorInput(node, i);
                    const locked = node.inputs.find(i => i.link != null && i.type && i.type !== "*");
                    if (locked) {
                        const c2 = typeColor(locked.type);
                        for (const inp of node.inputs) { inp.type = locked.type; if (c2) inp.color_on = c2; else delete inp.color_on; }
                        const out = node.outputs?.[0];
                        if (out) { out.type = locked.type; if (c2) out.color_on = c2; else delete out.color_on; }
                    }
                    dirty();
                });
            }; })(nodeType.prototype.onConfigure);
        }


        if (nodeData.name === "NiftyIndexInputSwitch") {
            const MAX_INPUTS = 16;

            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;

                // Remove ALL inputs (Python-defined ones look different), start fresh
                while (node.inputs.length > 0) node.removeInput(node.inputs.length - 1);
                node.addInput("value1", "*");
                node.addInput("value2", "*");
                resizeH(node);

                // Clamp index widget
                const idxWidget = node.widgets?.find(w => w.name === "index");
                if (idxWidget) {
                    idxWidget.options = { ...idxWidget.options, min: 1, max: MAX_INPUTS };
                }

                function getLockedType() {
                    for (const inp of node.inputs) {
                        if (inp.link != null && inp.type && inp.type !== "*") return inp.type;
                    }
                    return null;
                }

                function applyType(t) {
                    const c = typeColor(t);
                    for (const inp of node.inputs) {
                        inp.type = t ?? "*";
                        if (t && c) inp.color_on = c; else delete inp.color_on;
                    }
                    const out = node.outputs?.[0];
                    if (out) {
                        out.type = t ?? "*";
                        if (t && c) out.color_on = c; else delete out.color_on;
                    }
                }

                function syncSlots() {
                    const connected = node.inputs.filter(i => i.link != null).length;
                    const target = Math.min(MAX_INPUTS, Math.max(2, connected + 1)); // min 2, always one trailing empty
                    // Add missing
                    while (node.inputs.length < target) {
                        node.addInput(`value${node.inputs.length + 1}`, "*");
                    }
                    // Remove trailing empty slots only if there are 2+ empty at the end
                    while (
                        node.inputs.length > 2 &&
                        node.inputs[node.inputs.length - 1].link == null &&
                        node.inputs[node.inputs.length - 2].link == null
                    ) {
                        node.removeInput(node.inputs.length - 1);
                    }
                    // Rename all slots
                    for (let i = 0; i < node.inputs.length; i++) {
                        node.inputs[i].name  = `value${i + 1}`;
                        node.inputs[i].label = `value${i + 1}`;
                    }
                    if (idxWidget) {
                        idxWidget.options.max = node.inputs.length;
                        if (idxWidget.value > node.inputs.length) idxWidget.value = node.inputs.length;
                    }
                    resizeH(node);
                    dirty();
                }

                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType !== LiteGraph.INPUT) return;
                    const inp = node.inputs[slotIdx];
                    if (inp) { inp.type = "*"; delete inp.color_on; }
                    setTimeout(() => {
                        colorInput(node, slotIdx);
                        syncSlots();
                        const locked = getLockedType();
                        applyType(locked);
                        dirty();
                    }, 50);
                };
            };

            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const node = this;
                // Reset all slots, recolor, resync
                for (let i = 0; i < node.inputs.length; i++) { node.inputs[i].type = "*"; delete node.inputs[i].color_on; }
                if (node.outputs?.[0]) { node.outputs[0].type = "*"; delete node.outputs[0].color_on; }
                queueMicrotask(() => {
                    for (let i = 0; i < node.inputs.length; i++) colorInput(node, i);
                    const locked = node.inputs.find(i => i.link != null && i.type && i.type !== "*");
                    if (locked) {
                        const c2 = typeColor(locked.type);
                        for (const inp of node.inputs) { inp.type = locked.type; if (c2) inp.color_on = c2; else delete inp.color_on; }
                        const out = node.outputs?.[0];
                        if (out) { out.type = locked.type; if (c2) out.color_on = c2; else delete out.color_on; }
                    }
                    dirty();
                });
            }; })(nodeType.prototype.onConfigure);
        }


        if (nodeData.name === "NiftyIndexOutputSwitch") {
            const MAX_OUTPUTS = 16;

            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;

                // Remove all Python-defined outputs, start fresh with 2
                while (node.outputs.length > 0) node.removeOutput(node.outputs.length - 1);
                node.addOutput("value1", "*");
                node.addOutput("value2", "*");
                resizeH(node);

                const idxWidget = node.widgets?.find(w => w.name === "index");
                if (idxWidget) idxWidget.options = { ...idxWidget.options, min: 1, max: MAX_OUTPUTS };

                function syncSlots() {
                    const connected = node.outputs.filter(o => o.links?.length > 0).length;
                    const target = Math.min(MAX_OUTPUTS, Math.max(2, connected + 1));
                    // Add missing
                    while (node.outputs.length < target) {
                        node.addOutput(`value${node.outputs.length + 1}`, "*");
                    }
                    // Remove trailing empty slots only if there are 2+ empty at the end
                    while (
                        node.outputs.length > 2 &&
                        !(node.outputs[node.outputs.length - 1].links?.length > 0) &&
                        !(node.outputs[node.outputs.length - 2].links?.length > 0)
                    ) {
                        node.removeOutput(node.outputs.length - 1);
                    }
                    for (let i = 0; i < node.outputs.length; i++) {
                        node.outputs[i].name  = `value${i + 1}`;
                        node.outputs[i].label = `value${i + 1}`;
                    }
                    if (idxWidget) {
                        idxWidget.options.max = node.outputs.length;
                        if (idxWidget.value > node.outputs.length) idxWidget.value = node.outputs.length;
                    }
                    resizeH(node);
                    dirty();
                }

                function applyTypeFromInput() {
                    const inp = node.inputs?.[0];
                    if (!inp || inp.link == null) {
                        for (const out of node.outputs) { out.type = "*"; delete out.color_on; }
                    } else {
                        const t = inp.type ?? "*";
                        const col = typeColor(t);
                        for (const out of node.outputs) {
                            out.type = t;
                            if (col) out.color_on = col; else delete out.color_on;
                        }
                    }
                }

                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType === LiteGraph.INPUT) {
                        const inp = node.inputs?.[0];
                        if (inp) { inp.type = "*"; delete inp.color_on; }
                        queueMicrotask(() => {
                            colorInput(node, 0);
                            applyTypeFromInput();
                            dirty();
                        });
                    }
                    if (slotType === LiteGraph.OUTPUT) {
                        setTimeout(() => {
                            syncSlots();
                            applyTypeFromInput();
                        }, 50);
                    }
                };
            };

            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const node = this;
                if (node.inputs?.[0]) { node.inputs[0].type = "*"; delete node.inputs[0].color_on; }
                const hasLinks = node.outputs.some(o => o.links?.length > 0);
                if (!hasLinks) {
                    // Copy-paste: reset to 2 slots
                    while (node.outputs.length > 0) node.removeOutput(node.outputs.length - 1);
                    node.addOutput("value1", "*");
                    node.addOutput("value2", "*");
                    resizeH(node);
                }
                queueMicrotask(() => {
                    // syncSlots inline — can't reference local fn from onNodeCreated
                    const connected = node.outputs.filter(o => o.links?.length > 0).length;
                    const target = Math.min(16, Math.max(2, connected + 1));
                    while (node.outputs.length < target) node.addOutput(`value${node.outputs.length + 1}`, "*");
                    while (node.outputs.length > target && !(node.outputs[node.outputs.length - 1].links?.length > 0) && !(node.outputs[node.outputs.length - 2].links?.length > 0)) node.removeOutput(node.outputs.length - 1);
                    for (let i = 0; i < node.outputs.length; i++) { node.outputs[i].name = `value${i+1}`; node.outputs[i].label = `value${i+1}`; }
                    colorInput(node, 0);
                    const inp = node.inputs?.[0];
                    if (inp?.link != null) {
                        const t = inp.type ?? "*"; const col = typeColor(t);
                        for (const out of node.outputs) { out.type = t; if (col) out.color_on = col; else delete out.color_on; }
                    }
                    dirty();
                });
            }; })(nodeType.prototype.onConfigure);
        }

        if (nodeData.name === "NiftyInputSwitch") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;
                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType === LiteGraph.INPUT && (slotIdx === 0 || slotIdx === 1)) {
                        (function(){ const s = node.inputs?.[slotIdx]; if (s) { s.type = "*"; delete s.color_on; } })();
                        queueMicrotask(() => {
                            colorInput(node, slotIdx);
                            // Output takes type from on_true (idx 0) if connected, else on_false (idx 1)
                            const src = node.inputs[0]?.link != null ? node.inputs[0] : node.inputs[1];
                            const out = node.outputs?.[0];
                            if (!out) return;
                            if (!src || src.link == null) { out.type = "*"; delete out.color_on; }
                            else { out.type = src.type ?? "*"; if (src.color_on) out.color_on = src.color_on; else delete out.color_on; }
                            dirty();
                        });
                    }
                };
            };
            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const nd = this;
                if (nd.inputs?.[0]) { nd.inputs[0].type = '*'; delete nd.inputs[0].color_on; } if (nd.inputs?.[1]) { nd.inputs[1].type = '*'; delete nd.inputs[1].color_on; }
                if (nd.outputs?.[0]) { nd.outputs[0].type = '*'; delete nd.outputs[0].color_on; }
                queueMicrotask(() => {
                    colorInput(nd, 0); colorInput(nd, 1);
                    // output 0 will be set by connection
                    dirty();
                });
            }; })(nodeType.prototype.onConfigure);
        }

        if (nodeData.name === "NiftyOutputSwitch") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;
                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType === LiteGraph.INPUT && slotIdx === 0) {
                        (function(){ const s = node.inputs?.[0]; if (s) { s.type = "*"; delete s.color_on; } })();
                        queueMicrotask(() => {
                            colorInput(node, 0);
                            const inp = node.inputs[0];
                            for (const out of (node.outputs ?? [])) {
                                if (!inp || inp.link == null) { out.type = "*"; delete out.color_on; }
                                else { out.type = inp.type ?? "*"; if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on; }
                            }
                            dirty();
                        });
                    }
                };
            };
            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const nd = this;
                if (nd.inputs?.[0]) { nd.inputs[0].type = '*'; delete nd.inputs[0].color_on; }
                if (nd.outputs?.[0]) { nd.outputs[0].type = '*'; delete nd.outputs[0].color_on; } if (nd.outputs?.[1]) { nd.outputs[1].type = '*'; delete nd.outputs[1].color_on; }
                queueMicrotask(() => {
                    colorInput(nd, 0);
                    // output 0 will be set by connection // output 1 will be set by connection
                    dirty();
                });
            }; })(nodeType.prototype.onConfigure);
        }

        if (nodeData.name === "NiftySignalSwitch") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;
                this.onConnectionsChange = function(slotType, slotIdx) {
                    if (slotType === LiteGraph.INPUT && slotIdx === 0) {
                        (function(){ const s = node.inputs?.[0]; if (s) { s.type = "*"; delete s.color_on; } })();
                        queueMicrotask(() => {
                            colorInput(node, 0);
                            const inp = node.inputs[0];
                            const out = node.outputs?.[0];
                            if (!out) return;
                            if (!inp || inp.link == null) { out.type = "*"; delete out.color_on; }
                            else { out.type = inp.type ?? "*"; if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on; }
                            dirty();
                        });
                    }
                };
            };
            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const nd = this;
                if (nd.inputs?.[0]) { nd.inputs[0].type = '*'; delete nd.inputs[0].color_on; }
                if (nd.outputs?.[0]) { nd.outputs[0].type = '*'; delete nd.outputs[0].color_on; }
                queueMicrotask(() => {
                    colorInput(nd, 0);
                    // output 0 will be set by connection
                    dirty();
                });
            }; })(nodeType.prototype.onConfigure);
        }


        if (nodeData.name === "NiftyCalculateImageSize") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;

                function updateWidgetVisibility() {
                    const resizeType = node.widgets?.find(w => w.name === "resize_type")?.value ?? "";
                    const isMultiplier = resizeType === "scale by multiplier";
                    const isSnapOnly   = resizeType === "snap only";
                    for (const w of node.widgets ?? []) {
                        if (w.name === "target_size") w.hidden = isMultiplier || isSnapOnly;
                        if (w.name === "scale")       w.hidden = isMultiplier || isSnapOnly;
                        if (w.name === "multiplier")  w.hidden = !isMultiplier;
                    }
                    resizeH(node);
                    dirty();
                }

                const resizeTypeWidget = node.widgets?.find(w => w.name === "resize_type");
                if (resizeTypeWidget) {
                    const origCb = resizeTypeWidget.callback?.bind(resizeTypeWidget);
                    resizeTypeWidget.callback = function(value) {
                        origCb?.(value);
                        updateWidgetVisibility();
                    };
                }
                updateWidgetVisibility();
            };
        }


        if (nodeData.name === "NiftyMagicGetter") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;

                const btn = node.addWidget("button", "Auto Connect", null, function() {
                    doAutoConnect(node);
                });
                btn.serialize = false;

                this.onConnectionsChange = function(slotType, slotIdx) {
                    const inp = node.inputs?.[0];
                    const out = node.outputs?.[0];
                    if (!inp || !out) return;
                    if (slotType === LiteGraph.INPUT) {
                        inp.type = "*"; delete inp.color_on;
                        out.type = "*"; delete out.color_on;
                        queueMicrotask(() => {
                            colorInput(node, 0);
                            out.type = inp.type ?? "*";
                            if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on;
                            dirty();
                        });
                    }
                    if (slotType === LiteGraph.OUTPUT) {
                        queueMicrotask(() => {
                            out.type = inp.type ?? "*";
                            if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on;
                            dirty();
                        });
                    }
                };
            };
            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const nd = this;
                if (nd.inputs?.[0])  { nd.inputs[0].type  = "*"; delete nd.inputs[0].color_on; }
                if (nd.outputs?.[0]) { nd.outputs[0].type = "*"; delete nd.outputs[0].color_on; }
                queueMicrotask(() => {
                    colorInput(nd, 0);
                    const inp = nd.inputs?.[0]; const out = nd.outputs?.[0];
                    if (inp && out) { out.type = inp.type ?? "*"; if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on; }
                    dirty();
                });
            }; })(nodeType.prototype.onConfigure);
        }


        if (nodeData.name === "NiftyNodeDuplicator") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                orig?.apply(this, arguments);
                const node = this;

                const countW = node.widgets?.find(w => w.name === "count");
                if (!countW) return;

                const origCb = countW.callback?.bind(countW);
                countW.callback = function(value) {
                    origCb?.(value);
                    runDuplicator(node);
                };
            };
        }

        if (nodeData.name === "NiftyHiddenLink") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                if (this.inputs.length === 0)  this.addInput(" ", "*");
                if (this.outputs.length === 0) this.addOutput(" ", "*");
                this.inputs[0].name  = " "; this.inputs[0].label  = " ";
                this.outputs[0].name = " "; this.outputs[0].label = " ";
                const node = this;
                this.onConnectionsChange = function(slotType, slotIdx) {
                    const inp = node.inputs[0];
                    const out = node.outputs[0];
                    if (!inp || !out) return;
                    if (slotType === LiteGraph.INPUT) {
                        inp.type = "*"; delete inp.color_on;
                        out.type = "*"; delete out.color_on;
                        queueMicrotask(() => {
                            colorInput(node, 0);
                            out.type = inp.type ?? "*";
                            if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on;
                            dirty();
                        });
                    }
                    if (slotType === LiteGraph.OUTPUT) {
                        // Re-sync output from input, not from target
                        queueMicrotask(() => {
                            out.type = inp.type ?? "*";
                            if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on;
                            dirty();
                        });
                    }
                };
            };
            nodeType.prototype.onConfigure = (function(_orig) { return function() {
                _orig?.apply(this, arguments);
                const nd = this;
                if (nd.inputs?.[0])  { nd.inputs[0].type  = "*"; delete nd.inputs[0].color_on; }
                if (nd.outputs?.[0]) { nd.outputs[0].type = "*"; delete nd.outputs[0].color_on; }
                queueMicrotask(() => {
                    colorInput(nd, 0);
                    const inp = nd.inputs[0]; const out = nd.outputs[0];
                    if (inp && out) { out.type = inp.type ?? "*"; if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on; }
                    dirty();
                });
            }; })(nodeType.prototype.onConfigure);
        }

    },

    async afterConfigureGraph() {
        registerColors();
        function walkGraph(graph) {
            for (const node of graph._nodes ?? []) {
                if (node.type === "NiftyBundlePack")   { syncInputSlots(node, 1, getCount(node)); for (let i = 1; i < node.inputs.length; i++) colorInput(node, i); }
                if (node.type === "NiftyBundleUnpack") { syncOutputSlots(node, 1, getCount(node)); for (let i = 1; i < node.outputs.length; i++) colorOutput(node, i); }
                if (node.type === "NiftyMagicGetter") {
                    colorInput(node, 0);
                    const inp = node.inputs?.[0]; const out = node.outputs?.[0];
                    if (inp && out) { out.type = inp.type ?? "*"; if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on; }
                }
                if (node.type === "NiftyBundleGet")    { colorOutput(node, 0); }
                if (node.type === "NiftyBundleSet")    { colorInput(node, 1); }
                if (node.type === "NiftyHiddenLink")   {
                    colorInput(node, 0);
                    const inp = node.inputs?.[0]; const out = node.outputs?.[0];
                    if (inp && out) { out.type = inp.type ?? "*"; if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on; }
                }
                if (node.type === "NiftyIndexOutputSwitch") {
                    colorInput(node, 0);
                    const inp = node.inputs?.[0];
                    if (inp?.link != null) {
                        const t = inp.type ?? "*"; const col = typeColor(t);
                        for (const out of node.outputs) { out.type = t; if (col) out.color_on = col; else delete out.color_on; }
                    }
                }
                if (node.type === "NiftyFirstSwitch") {
                    for (let i = 0; i < node.inputs.length; i++) colorInput(node, i);
                    const locked = node.inputs.find(i => i.link != null && i.type && i.type !== "*");
                    if (locked) {
                        const c2 = typeColor(locked.type);
                        for (const inp of node.inputs) { inp.type = locked.type; if (c2) inp.color_on = c2; else delete inp.color_on; }
                        const out = node.outputs?.[0]; if (out) { out.type = locked.type; if (c2) out.color_on = c2; else delete out.color_on; }
                    }
                }
                if (node.type === "NiftyIndexInputSwitch")  {
                    for (let i = 0; i < node.inputs.length; i++) colorInput(node, i);
                    const locked = node.inputs.find(i => i.link != null && i.type && i.type !== "*");
                    if (locked) {
                        const c2 = typeColor(locked.type);
                        for (const inp of node.inputs) { inp.type = locked.type; if (c2) inp.color_on = c2; else delete inp.color_on; }
                        const out = node.outputs?.[0]; if (out) { out.type = locked.type; if (c2) out.color_on = c2; else delete out.color_on; }
                    }
                }
                if (node.type === "NiftyInputSwitch")  {
                    colorInput(node, 0); colorInput(node, 1);
                    const src = node.inputs[0]?.link != null ? node.inputs[0] : node.inputs[1];
                    const out = node.outputs?.[0];
                    if (out && src?.link != null) { out.type = src.type ?? "*"; if (src.color_on) out.color_on = src.color_on; else delete out.color_on; }
                }
                if (node.type === "NiftyOutputSwitch") {
                    colorInput(node, 0);
                    const inp = node.inputs?.[0];
                    for (const out of (node.outputs ?? [])) { if (inp?.link != null) { out.type = inp.type ?? "*"; if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on; } }
                }
                if (node.type === "NiftySignalSwitch") {
                    colorInput(node, 0);
                    const inp = node.inputs?.[0]; const out = node.outputs?.[0];
                    if (out && inp?.link != null) { out.type = inp.type ?? "*"; if (inp.color_on) out.color_on = inp.color_on; else delete out.color_on; }
                }
                if (node.subgraph) walkGraph(node.subgraph);
            }
        }
        walkGraph(app.graph);
    },
});


function collectAllNodes(graph, result = []) {
    for (const node of graph._nodes ?? []) {
        result.push(node);
        if (node.subgraph) collectAllNodes(node.subgraph, result);
    }
    return result;
}

function findParentSubgraphNode(graph) {
    const parentGraph = graph?.inputNode?.graph;
    if (parentGraph) {
        for (const n of parentGraph._nodes ?? []) {
            if (n.subgraph === graph || n.subgraph?.id === graph?.id) return n;
        }
    }
    // fallback: check all graphs
    for (const g of [app.graph, ...(app.graph.subgraphs?.values() ?? [])]) {
        for (const n of g._nodes ?? []) {
            if (n.subgraph === graph || n.subgraph?.id === graph?.id) return n;
        }
    }
    return null;
}

function isInBypassedSubgraph(node) {
    let graph = node.graph;
    while (graph && graph !== app.graph) {
        const subgraphNode = findParentSubgraphNode(graph);
        if (!subgraphNode) break;
        if (subgraphNode.mode === 4) return true;
        graph = subgraphNode.graph;
    }
    return false;
}

function setSubgraphNodeMode(node, mode) {
    node.mode = mode;
    node.setDirtyCanvas?.(true, true);
    if (node.subgraph) {
        for (const inner of node.subgraph._nodes ?? []) {
            setSubgraphNodeMode(inner, mode);
        }
    }
}

function applyBypassSwitch(nodesStr, startGraph) {
    const lines = (nodesStr ?? "").split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const normal   = lines.filter(l => !l.startsWith("!"));
    const inverted = lines.filter(l =>  l.startsWith("!")).map(l => l.slice(1).trim());
    if (!normal.length && !inverted.length) return;
    const all = collectAllNodes(startGraph ?? app.graph);
    for (const n of all) {
        const title = n.title?.trim();
        if (!title) continue;
        if (normal.includes(title)) {
            // no ! = bypass this node
            const mode = 4;
            if (n.mode !== mode) setSubgraphNodeMode(n, mode);
        } else if (inverted.includes(title)) {
            // ! = activate this node (unless inside bypassed subgraph)
            const mode = isInBypassedSubgraph(n) ? 4 : 0;
            if (n.mode !== mode) setSubgraphNodeMode(n, mode);
        }
    }
}

function applyBypassByTitle(bypass, nodesStr, startGraph) {
    const lines = (nodesStr ?? "").split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
    const normal   = lines.filter(l => !l.startsWith("!")).map(l => l);
    const inverted = lines.filter(l =>  l.startsWith("!")).map(l => l.slice(1).trim());
    if (normal.length === 0 && inverted.length === 0) return;

    const allNodes = collectAllNodes(startGraph ?? app.graph);
    for (const node of allNodes) {
        const title = node.title?.trim();
        if (!title) continue;
        if (normal.includes(title)) {
            // No ! — bypass when bypass=true, activate when bypass=false
            const mode = (bypass === false && isInBypassedSubgraph(node)) ? 4 : (bypass ? 4 : 0);
            if (node.mode !== mode) setSubgraphNodeMode(node, mode);
        } else if (inverted.includes(title)) {
            // ! prefix — activate when bypass=true, bypass when bypass=false
            const mode = (bypass === true && isInBypassedSubgraph(node)) ? 4 : (bypass ? 0 : 4);
            if (node.mode !== mode) setSubgraphNodeMode(node, mode);
        }
    }
}

// ─── Bypass Switch by Title ───────────────────────────────────────────────────
(function() {
const MAX = 16;

function updateBSBT(node) {
    const selW     = node.widgets?.find(w => w.name === "selected");
    const countW   = node.widgets?.find(w => w.name === "count");
    const srootW   = node.widgets?.find(w => w.name === "search_from_root");
    const enforceW = node.widgets?.find(w => w.name === "enforce");
    const comboW   = node.widgets?.find(w => w.name === "bypass");
    if (!countW || !selW || !comboW) return;

    // Keep selW visible but tiny — hiding it causes serialization issues
    selW.computeSize = () => [0, -4];

    const cnt = Math.max(1, Math.min(MAX, Math.round(countW.value)));
    const sel = Math.max(1, Math.min(cnt, Math.round(selW.value)));

    // Show/hide label+nodes pairs
    for (let i = 0; i < MAX; i++) {
        const lw = node.widgets?.find(w => w.name === `label${i+1}`);
        const nw = node.widgets?.find(w => w.name === `nodes${i+1}`);
        if (lw) lw.hidden = (i >= cnt);
        if (nw) nw.hidden = (i >= cnt);
    }

    function getLabels() {
        return Array.from({length: cnt}, (_, i) => {
            const lw = node.widgets?.find(w => w.name === `label${i+1}`);
            return lw?.value || `option ${i+1}`;
        });
    }

    // Update combo options
    comboW.options.values = getLabels();
    const selLabel = node.widgets?.find(w => w.name === `label${sel}`)?.value || `option ${sel}`;
    comboW.value = comboW.options.values.includes(selLabel) ? selLabel : comboW.options.values[0];

    // Hook combo callback (once) — reads countW fresh to avoid stale closure
    if (!comboW._bsbtHooked) {
        comboW._bsbtHooked = true;
        const origCb = comboW.callback?.bind(comboW);
        comboW.callback = function(val) {
            origCb?.(val);
            const freshCnt = Math.max(1, Math.min(MAX, Math.round(countW.value)));
            const freshLabels = Array.from({length: freshCnt}, (_, i) => {
                const lw = node.widgets?.find(w => w.name === `label${i+1}`);
                return lw?.value || `option ${i+1}`;
            });
            const idx = freshLabels.indexOf(val);
            const newSel = idx >= 0 ? idx + 1 : 1;
            selW.value = newSel;
            const nw = node.widgets?.find(w => w.name === `nodes${newSel}`);
            const fromRoot = srootW?.value ?? true;
            applyBypassSwitch(nw?.value ?? "", fromRoot ? app.graph : (node.graph ?? app.graph));
        };
    }

    // Hook count callback (once)
    if (!countW._bsbtHooked) {
        countW._bsbtHooked = true;
        const origCb = countW.callback?.bind(countW);
        countW.callback = function(val) {
            origCb?.(val);
            updateBSBT(node);
        };
    }

    // Hook label callbacks (once each)
    for (let i = 0; i < MAX; i++) {
        const lw = node.widgets?.find(w => w.name === `label${i+1}`);
        if (!lw || lw._bsbtHooked) continue;
        lw._bsbtHooked = true;
        const origCb = lw.callback?.bind(lw);
        lw.callback = function(val) {
            origCb?.(val);
            const labels = getLabels();
            comboW.options.values = labels;
            if (!labels.includes(comboW.value)) comboW.value = labels[0];
            dirty();
        };
    }

    node._bsbtState = () => ({
        fromRoot: srootW?.value ?? true,
        enforce:  enforceW?.value ?? true,
        graph:    node.graph ?? app.graph,
        nodesStr: () => {
            const s = Math.max(1, Math.min(MAX, Math.round(selW.value)));
            return node.widgets?.find(w => w.name === `nodes${s}`)?.value ?? "";
        },
    });

    node.size[0] = Math.max(node.size[0] ?? 0, 240);
    const sz = node.computeSize?.();
    if (sz) node.setSize([node.size[0], sz[1]]);
    dirty();
}


app.registerExtension({
    name: "nifty.BypassSwitchByTitle",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "NiftyBypassSwitchByTitle") return;
        nodeType.prototype.onNodeCreated = function() { updateBSBT(this); };
        nodeType.prototype.onConfigure = (function(_o) { return function() {
            _o?.apply(this, arguments);
            updateBSBT(this);
        }; })(nodeType.prototype.onConfigure);
    },
});

(function() {
    if (app._bsbtPatched) return;
    app._bsbtPatched = true;
    const orig = app.graphToPrompt?.bind(app);
    if (!orig) return;
    app.graphToPrompt = async function(...a) {
        for (const g of [app.graph, ...(app.graph.subgraphs?.values() ?? [])]) {
            for (const n of g._nodes ?? []) {
                if (n.type !== "NiftyBypassSwitchByTitle") continue;
                const s = n._bsbtState?.();
                if (s?.enforce) applyBypassSwitch(s.nodesStr(), s.fromRoot ? app.graph : s.graph);
            }
        }
        return orig(...a);
    };
})();

})();


// ─── Bypass by Title ──────────────────────────────────────────────────────────
(function() {



// Apply bypass switch (no boolean toggle — always applies selected nodes config)

// Enforce hook — re-applies bypass state before workflow serialization
(function() {
    const origGTP = app.graphToPrompt?.bind(app);
    if (!origGTP) return;
    app.graphToPrompt = async function(...args) {
        // Find all BypassByTitle nodes and enforce if enabled
        for (const graph of [app.graph, ...(app.graph.subgraphs?.values() ?? [])]) {
            for (const node of graph._nodes ?? []) {
                if (node.type !== "NiftyBypassByTitle") continue;
                const state = node._getBypassState?.();
                if (!state?.enforce) continue;
                const startGraph = state.fromRoot ? app.graph : state.graph;
                applyBypassByTitle(state.bypass, state.nodes, startGraph);
            }
        }
        return origGTP(...args);
    };
})();


app.registerExtension({
    name: "nifty.BypassByTitle",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "NiftyBypassByTitle") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            origCreated?.apply(this, arguments);
            this.size = this.computeSize();
            this.size[0] = Math.max(this.size[0], 210);

            const bypassWidget     = this.widgets?.find(w => w.name === "bypass");
            const nodesWidget      = this.widgets?.find(w => w.name === "nodes");
            const searchRootWidget = this.widgets?.find(w => w.name === "search_from_root");
            if (!bypassWidget) return;

            const node = this;
            let _bypassVal = bypassWidget.value;
            try {
                Object.defineProperty(bypassWidget, 'value', {
                    get: () => _bypassVal,
                    set: (v) => {
                        _bypassVal = v;
                        const fromRoot = searchRootWidget?.value ?? true;
                        const startGraph = fromRoot ? app.graph : (node.graph ?? app.graph);
                        applyBypassByTitle(v, nodesWidget?.value ?? "", startGraph);
                    },
                    configurable: true,
                });
            } catch(_) {}
            node._getBypassState = () => ({
                bypass:   bypassWidget?.value ?? false,
                nodes:    nodesWidget?.value ?? "",
                fromRoot: searchRootWidget?.value ?? true,
                enforce:  node.widgets?.find(w => w.name === "enforce")?.value ?? true,
                graph:    node.graph ?? app.graph,
            });
        };
    },
});

})();

// ─── Sync VHS Preview ─────────────────────────────────────────────────────────
(function() {

function syncAllVHSPreviews() {
    for (const p of document.getElementsByClassName("vhs_preview")) {
        for (const child of p.children) {
            if (child.tagName === "VIDEO") {
                child.currentTime = 0;
            } else if (child.tagName === "IMG") {
                child.src = child.src;
            }
        }
    }
}

// Manual sync — button only, no Python params
app.registerExtension({
    name: "nifty.SyncVHSPreview",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "NiftySyncVHSPreview") return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            orig?.apply(this, arguments);
            const btn = this.addWidget("button", "Sync Preview", null, syncAllVHSPreviews);
            btn.serialize = false;
        };
    },
});

// Auto sync — boolean only, fires when any VHS node updates its preview
app.registerExtension({
    name: "nifty.AutoSyncVHSPreview",
    async setup() {
        let debounceTimer = null;

        function isAutoSyncEnabled() {
            for (const graph of [app.graph, ...(app.graph.subgraphs?.values() ?? [])]) {
                for (const node of graph._nodes ?? []) {
                    if (node.type === "NiftyAutoSyncVHSPreview") {
                        const w = node.widgets?.find(w => w.name === "auto_sync");
                        if (w?.value === true) return true;
                    }
                }
            }
            return false;
        }

        function debouncedSync() {
            if (debounceTimer) return; // already scheduled, skip
            debounceTimer = setTimeout(() => {
                debounceTimer = null;
                syncAllVHSPreviews();
            }, 150);
        }

        // Fire when any node finishes executing and has a vhs_preview widget
        api.addEventListener("executed", ({ detail }) => {
            if (!isAutoSyncEnabled()) return;
            const nodeId = detail?.node ?? detail?.output?.node;
            if (!nodeId) return;
            for (const graph of [app.graph, ...(app.graph.subgraphs?.values() ?? [])]) {
                const node = graph.getNodeById?.(nodeId);
                if (!node) continue;
                if (node.type?.startsWith("VHS_") && node.widgets?.some(w => w.name === "videopreview")) {
                    debouncedSync();
                }
                break;
            }
        });
    },
});

})();
