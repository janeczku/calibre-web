"use strict";
/*
 * Copyright 2018 Palantir Technologies, Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.mouseUpHorizontal = exports.DRAG_SIZE = void 0;
exports.simulateMovement = simulateMovement;
const vitest_utils_1 = require("@blueprintjs/test-commons/vitest-utils");
const handle_1 = require("./handle");
exports.DRAG_SIZE = 20;
/**
 * Simulates a full move of a slider handle: engage, move, release.
 * Supports touch and vertical events. Use options to configure exact movement.
 */
function simulateMovement(wrapper, options) {
    const { from = 0, handleIndex = 0, touch = false } = options;
    const handle = wrapper.find(handle_1.Handle).at(handleIndex);
    const eventData = options.vertical !== undefined && options.verticalHeight !== undefined
        ? { clientY: options.verticalHeight - from }
        : { clientX: from };
    if (touch) {
        handle.simulate("touchstart", { changedTouches: [eventData] });
    }
    else {
        handle.simulate("mousedown", eventData);
    }
    genericMove(options);
    genericRelease(options);
    return wrapper;
}
/** Release the mouse at the given clientX pixel. Useful for ending a drag interaction. */
const mouseUpHorizontal = (clientX) => genericRelease({ dragTimes: 0, from: clientX });
exports.mouseUpHorizontal = mouseUpHorizontal;
// Private helpers
// ===============
function genericMove(options) {
    const { dragSize = exports.DRAG_SIZE, from = 0, dragTimes = 1, touch } = options;
    const eventName = touch ? "touchmove" : "mousemove";
    for (let i = 0; i < dragTimes; i += 1) {
        const clientPixel = from + i * dragSize;
        dispatchEvent(options, eventName, clientPixel);
    }
}
function genericRelease(options) {
    const { dragSize = exports.DRAG_SIZE, from = 0, dragTimes = 1, touch } = options;
    const eventName = touch ? "touchend" : "mouseup";
    const clientPixel = from + dragTimes * dragSize;
    dispatchEvent(options, eventName, clientPixel);
}
function dispatchEvent(options, eventName, clientPixel) {
    const { touch, vertical, verticalHeight = 0 } = options;
    const dispatchFn = touch ? vitest_utils_1.dispatchTouchEvent : vitest_utils_1.dispatchMouseEvent;
    if (vertical) {
        // vertical sliders go from bottom-up, so everything is backward
        dispatchFn(document, eventName, undefined, verticalHeight - clientPixel);
    }
    else {
        dispatchFn(document, eventName, clientPixel, undefined);
    }
}
//# sourceMappingURL=sliderTestUtils.js.map