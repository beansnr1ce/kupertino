// Cupertino Snap — Rectangle.app-compatible default shortcuts for KWin (Plasma 6)
// KDE-side chords assume the keyd layer: Meta+Alt = physical Ctrl+Super = mac ⌃⌥,
// Meta+Alt+Ctrl = physical Ctrl+Super+Alt = mac ⌃⌥⌘.
"use strict";

const RESIZE_STEP = 30;
const saved = new Map();

function activeWin() {
    const w = workspace.activeWindow;
    if (!w || !w.moveable || !w.resizeable) {
        return null;
    }
    return w;
}

function screenArea(w) {
    return workspace.clientArea(KWin.MaximizeArea, w);
}

function remember(w) {
    const id = w.internalId.toString();
    if (!saved.has(id)) {
        const g = w.frameGeometry;
        saved.set(id, { x: g.x, y: g.y, width: g.width, height: g.height });
    }
}

function setGeometry(w, x, y, width, height) {
    if (w.fullScreen) {
        w.fullScreen = false;
    }
    w.setMaximize(false, false);
    // Qt.rect() is unavailable in KWin's pure-JS environment; KWin converts
    // a plain {x,y,width,height} object to QRectF on assignment
    w.frameGeometry = { x: Math.round(x), y: Math.round(y),
                        width: Math.round(width), height: Math.round(height) };
}

function place(fx, fy, fw, fh) {
    return () => {
        const w = activeWin();
        if (!w) return;
        const a = screenArea(w);
        remember(w);
        setGeometry(w, a.x + a.width * fx, a.y + a.height * fy,
                    a.width * fw, a.height * fh);
    };
}

function maximize() {
    const w = activeWin();
    if (!w) return;
    remember(w);
    if (w.fullScreen) {
        w.fullScreen = false;
    }
    w.setMaximize(true, true);
}

function maximizeHeight() {
    const w = activeWin();
    if (!w) return;
    const a = screenArea(w);
    remember(w);
    const g = w.frameGeometry;
    setGeometry(w, g.x, a.y, g.width, a.height);
}

function resizeBy(delta) {
    return () => {
        const w = activeWin();
        if (!w) return;
        const a = screenArea(w);
        remember(w);
        const g = w.frameGeometry;
        let width = Math.min(g.width + delta, a.width);
        let height = Math.min(g.height + delta, a.height);
        if (width < w.minSize.width) width = w.minSize.width;
        if (height < w.minSize.height) height = w.minSize.height;
        let x = g.x - (width - g.width) / 2;
        let y = g.y - (height - g.height) / 2;
        x = Math.max(a.x, Math.min(x, a.x + a.width - width));
        y = Math.max(a.y, Math.min(y, a.y + a.height - height));
        setGeometry(w, x, y, width, height);
    };
}

function center() {
    const w = activeWin();
    if (!w) return;
    const a = screenArea(w);
    remember(w);
    const g = w.frameGeometry;
    setGeometry(w, a.x + (a.width - g.width) / 2,
                a.y + (a.height - g.height) / 2, g.width, g.height);
}

function restore() {
    const w = activeWin();
    if (!w) return;
    const id = w.internalId.toString();
    const g = saved.get(id);
    if (!g) return;
    saved.delete(id);
    setGeometry(w, g.x, g.y, g.width, g.height);
}

function moveToDisplay(offset) {
    return () => {
        const w = activeWin();
        if (!w) return;
        const screens = workspace.screens;
        if (screens.length < 2) return;
        const idx = screens.indexOf(w.output);
        const target = screens[(idx + offset + screens.length) % screens.length];
        const from = screenArea(w);
        const to = workspace.clientArea(KWin.MaximizeArea, target,
                                        workspace.currentDesktop);
        remember(w);
        const g = w.frameGeometry;
        setGeometry(w,
            to.x + ((g.x - from.x) / from.width) * to.width,
            to.y + ((g.y - from.y) / from.height) * to.height,
            (g.width / from.width) * to.width,
            (g.height / from.height) * to.height);
    };
}

workspace.windowRemoved.connect(w => saved.delete(w.internalId.toString()));

const T = 1 / 3;
// Internal action names keep the original Rectangle* ids: they are the keys in
// kglobalshortcutsrc, so changing them would orphan existing registrations.
registerShortcut("RectangleLeftHalf", "Snap: Left Half", "Meta+Alt+Left", place(0, 0, 0.5, 1));
registerShortcut("RectangleRightHalf", "Snap: Right Half", "Meta+Alt+Right", place(0.5, 0, 0.5, 1));
registerShortcut("RectangleTopHalf", "Snap: Top Half", "Meta+Alt+Up", place(0, 0, 1, 0.5));
registerShortcut("RectangleBottomHalf", "Snap: Bottom Half", "Meta+Alt+Down", place(0, 0.5, 1, 0.5));
registerShortcut("RectangleTopLeft", "Snap: Top Left", "Meta+Alt+U", place(0, 0, 0.5, 0.5));
registerShortcut("RectangleTopRight", "Snap: Top Right", "Meta+Alt+I", place(0.5, 0, 0.5, 0.5));
registerShortcut("RectangleBottomLeft", "Snap: Bottom Left", "Meta+Alt+J", place(0, 0.5, 0.5, 0.5));
registerShortcut("RectangleBottomRight", "Snap: Bottom Right", "Meta+Alt+K", place(0.5, 0.5, 0.5, 0.5));
registerShortcut("RectangleFirstThird", "Snap: First Third", "Meta+Alt+D", place(0, 0, T, 1));
registerShortcut("RectangleCenterThird", "Snap: Center Third", "Meta+Alt+F", place(T, 0, T, 1));
registerShortcut("RectangleLastThird", "Snap: Last Third", "Meta+Alt+G", place(2 * T, 0, T, 1));
registerShortcut("RectangleFirstTwoThirds", "Snap: First Two Thirds", "Meta+Alt+E", place(0, 0, 2 * T, 1));
registerShortcut("RectangleCenterTwoThirds", "Snap: Center Two Thirds", "Meta+Alt+R", place(1 / 6, 0, 2 * T, 1));
registerShortcut("RectangleLastTwoThirds", "Snap: Last Two Thirds", "Meta+Alt+T", place(T, 0, 2 * T, 1));
registerShortcut("RectangleMaximize", "Snap: Maximize", "Meta+Alt+Return", maximize);
registerShortcut("RectangleMaximizeHeight", "Snap: Maximize Height", "Meta+Alt+Shift+Up", maximizeHeight);
registerShortcut("RectangleSmaller", "Snap: Make Smaller", "Meta+Alt+-", resizeBy(-RESIZE_STEP));
registerShortcut("RectangleLarger", "Snap: Make Larger", "Meta+Alt+=", resizeBy(RESIZE_STEP));
registerShortcut("RectangleCenter", "Snap: Center", "Meta+Alt+C", center);
registerShortcut("RectangleRestore", "Snap: Restore", "Meta+Alt+Backspace", restore);
registerShortcut("RectangleNextDisplay", "Snap: Next Display", "Meta+Alt+Ctrl+Right", moveToDisplay(1));
registerShortcut("RectanglePrevDisplay", "Snap: Previous Display", "Meta+Alt+Ctrl+Left", moveToDisplay(-1));
