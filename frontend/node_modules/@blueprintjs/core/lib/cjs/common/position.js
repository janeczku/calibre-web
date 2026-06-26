"use strict";
/*
 * Copyright 2015 Palantir Technologies, Inc. All rights reserved.
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
exports.Position = void 0;
exports.isPositionHorizontal = isPositionHorizontal;
exports.isPositionVertical = isPositionVertical;
exports.getPositionIgnoreAngles = getPositionIgnoreAngles;
exports.Position = {
    BOTTOM: "bottom",
    BOTTOM_LEFT: "bottom-left",
    BOTTOM_RIGHT: "bottom-right",
    LEFT: "left",
    LEFT_BOTTOM: "left-bottom",
    LEFT_TOP: "left-top",
    RIGHT: "right",
    RIGHT_BOTTOM: "right-bottom",
    RIGHT_TOP: "right-top",
    TOP: "top",
    TOP_LEFT: "top-left",
    TOP_RIGHT: "top-right",
};
function isPositionHorizontal(position) {
    /* istanbul ignore next */
    return (position === exports.Position.TOP ||
        position === exports.Position.TOP_LEFT ||
        position === exports.Position.TOP_RIGHT ||
        position === exports.Position.BOTTOM ||
        position === exports.Position.BOTTOM_LEFT ||
        position === exports.Position.BOTTOM_RIGHT);
}
function isPositionVertical(position) {
    /* istanbul ignore next */
    return (position === exports.Position.LEFT ||
        position === exports.Position.LEFT_TOP ||
        position === exports.Position.LEFT_BOTTOM ||
        position === exports.Position.RIGHT ||
        position === exports.Position.RIGHT_TOP ||
        position === exports.Position.RIGHT_BOTTOM);
}
function getPositionIgnoreAngles(position) {
    if (position === exports.Position.TOP || position === exports.Position.TOP_LEFT || position === exports.Position.TOP_RIGHT) {
        return exports.Position.TOP;
    }
    else if (position === exports.Position.BOTTOM ||
        position === exports.Position.BOTTOM_LEFT ||
        position === exports.Position.BOTTOM_RIGHT) {
        return exports.Position.BOTTOM;
    }
    else if (position === exports.Position.LEFT || position === exports.Position.LEFT_TOP || position === exports.Position.LEFT_BOTTOM) {
        return exports.Position.LEFT;
    }
    else {
        return exports.Position.RIGHT;
    }
}
//# sourceMappingURL=position.js.map