"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Spinner = exports.SpinnerSize = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2025 Palantir Technologies, Inc. All rights reserved.
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const common_1 = require("../../common");
const errors_1 = require("../../common/errors");
const props_1 = require("../../common/props");
const utils_1 = require("../../common/utils");
const useValidateProps_1 = require("../../hooks/useValidateProps");
var SpinnerSize;
(function (SpinnerSize) {
    SpinnerSize[SpinnerSize["SMALL"] = 20] = "SMALL";
    SpinnerSize[SpinnerSize["STANDARD"] = 50] = "STANDARD";
    SpinnerSize[SpinnerSize["LARGE"] = 100] = "LARGE";
})(SpinnerSize || (exports.SpinnerSize = SpinnerSize = {}));
// see http://stackoverflow.com/a/18473154/3124288 for calculating arc path
const R = 45;
const SPINNER_TRACK = `M 50,50 m 0,-${R} a ${R},${R} 0 1 1 0,${R * 2} a ${R},${R} 0 1 1 0,-${R * 2}`;
// unitless total length of SVG path, to which stroke-dash* properties are relative.
// https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/pathLength
// this value is the result of `<path d={SPINNER_TRACK} />.getTotalLength()` and works in all browsers:
const PATH_LENGTH = 280;
const MIN_SIZE = 10;
const STROKE_WIDTH = 4;
const MIN_STROKE_WIDTH = 16;
/**
 * Spinner component.
 *
 * @see https://blueprintjs.com/docs/#core/components/spinner
 */
const Spinner = props => {
    const { className = "", intent, value, tagName = "div", size, ...htmlProps } = props;
    (0, useValidateProps_1.useValidateProps)(() => {
        const isSizePropSet = size != null;
        const isSizeClassSet = className.indexOf(common_1.Classes.SMALL) >= 0 || className.indexOf(common_1.Classes.LARGE) >= 0;
        if (isSizePropSet && isSizeClassSet) {
            console.warn(errors_1.SPINNER_WARN_CLASSES_SIZE);
        }
    }, [className, size]);
    const sizePx = getSize(size, className);
    // keep spinner track width consistent at all sizes (down to about 10px).
    const strokeWidth = Math.min(MIN_STROKE_WIDTH, (STROKE_WIDTH * SpinnerSize.LARGE) / sizePx);
    const strokeOffset = PATH_LENGTH - PATH_LENGTH * (value == null ? 0.25 : (0, utils_1.clamp)(value, 0, 1));
    const classes = (0, classnames_1.default)(common_1.Classes.SPINNER, common_1.Classes.intentClass(intent), { [common_1.Classes.SPINNER_NO_SPIN]: value != null }, className);
    // multiple DOM elements around SVG are necessary to properly isolate animation:
    // - SVG elements in IE do not support anim/trans so they must be set on a parent HTML element.
    // - SPINNER_ANIMATION isolates svg from parent display and is always centered inside root element.
    return (0, react_1.createElement)(tagName, {
        "aria-label": "loading",
        "aria-valuemax": 100,
        "aria-valuemin": 0,
        "aria-valuenow": value === undefined ? undefined : value * 100,
        className: classes,
        role: "progressbar",
        ...htmlProps,
    }, (0, react_1.createElement)(tagName, { className: common_1.Classes.SPINNER_ANIMATION }, (0, jsx_runtime_1.jsxs)("svg", { width: sizePx, height: sizePx, strokeWidth: strokeWidth.toFixed(2), viewBox: getViewBox(strokeWidth), children: [(0, jsx_runtime_1.jsx)("path", { className: common_1.Classes.SPINNER_TRACK, d: SPINNER_TRACK }), (0, jsx_runtime_1.jsx)("path", { className: common_1.Classes.SPINNER_HEAD, d: SPINNER_TRACK, pathLength: PATH_LENGTH, strokeDasharray: `${PATH_LENGTH} ${PATH_LENGTH}`, strokeDashoffset: strokeOffset })] })));
};
exports.Spinner = Spinner;
exports.Spinner.displayName = `${props_1.DISPLAYNAME_PREFIX}.Spinner`;
/**
 * Resolve size to a pixel value.
 * Size can be set by className, props, default, or minimum constant.
 */
const getSize = (size, className) => {
    if (size == null) {
        if (className.indexOf(common_1.Classes.SMALL) >= 0) {
            return SpinnerSize.SMALL;
        }
        else if (className.indexOf(common_1.Classes.LARGE) >= 0) {
            return SpinnerSize.LARGE;
        }
        return SpinnerSize.STANDARD;
    }
    return Math.max(MIN_SIZE, size);
};
/** Compute viewbox such that stroked track sits exactly at edge of image frame. */
const getViewBox = (strokeWidth) => {
    const radius = R + strokeWidth / 2;
    const viewBoxX = (50 - radius).toFixed(2);
    const viewBoxWidth = (radius * 2).toFixed(2);
    return `${viewBoxX} ${viewBoxX} ${viewBoxWidth} ${viewBoxWidth}`;
};
//# sourceMappingURL=spinner.js.map