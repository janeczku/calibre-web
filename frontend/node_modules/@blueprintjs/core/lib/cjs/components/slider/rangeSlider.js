"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RangeSlider = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2016 Palantir Technologies, Inc. All rights reserved.
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
const common_1 = require("../../common");
const Errors = tslib_1.__importStar(require("../../common/errors"));
const multiSlider_1 = require("./multiSlider");
var RangeIndex;
(function (RangeIndex) {
    RangeIndex[RangeIndex["START"] = 0] = "START";
    RangeIndex[RangeIndex["END"] = 1] = "END";
})(RangeIndex || (RangeIndex = {}));
/**
 * Range slider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/sliders.range-slider
 */
class RangeSlider extends common_1.AbstractPureComponent {
    static defaultProps = {
        ...multiSlider_1.MultiSlider.defaultSliderProps,
        intent: common_1.Intent.PRIMARY,
        value: [0, 10],
    };
    static displayName = `${common_1.DISPLAYNAME_PREFIX}.RangeSlider`;
    render() {
        const { value, handleHtmlProps, ...props } = this.props;
        return ((0, jsx_runtime_1.jsxs)(multiSlider_1.MultiSlider, { ...props, children: [(0, jsx_runtime_1.jsx)(multiSlider_1.MultiSliderHandle, { value: value[RangeIndex.START], type: "start", intentAfter: props.intent, htmlProps: handleHtmlProps?.start }), (0, jsx_runtime_1.jsx)(multiSlider_1.MultiSliderHandle, { value: value[RangeIndex.END], type: "end", htmlProps: handleHtmlProps?.end })] }));
    }
    validateProps(props) {
        const { value } = props;
        if (value == null || value[RangeIndex.START] == null || value[RangeIndex.END] == null) {
            throw new Error(Errors.RANGESLIDER_NULL_VALUE);
        }
    }
}
exports.RangeSlider = RangeSlider;
//# sourceMappingURL=rangeSlider.js.map