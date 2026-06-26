"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Slider = void 0;
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
const props_1 = require("../../common/props");
const multiSlider_1 = require("./multiSlider");
/**
 * Slider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/sliders.slider
 */
class Slider extends common_1.AbstractPureComponent {
    static defaultProps = {
        ...multiSlider_1.MultiSlider.defaultSliderProps,
        initialValue: 0,
        intent: common_1.Intent.PRIMARY,
        value: 0,
    };
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.Slider`;
    render() {
        const { initialValue, intent, value, onChange, onRelease, handleHtmlProps, ...props } = this.props;
        return ((0, jsx_runtime_1.jsxs)(multiSlider_1.MultiSlider, { ...props, children: [(0, jsx_runtime_1.jsx)(multiSlider_1.MultiSliderHandle, { value: value, intentAfter: value < initialValue ? intent : undefined, intentBefore: value > initialValue ? intent : undefined, onChange: onChange, onRelease: onRelease, htmlProps: handleHtmlProps }), (0, jsx_runtime_1.jsx)(multiSlider_1.MultiSliderHandle, { value: initialValue, interactionKind: "none" })] }));
    }
}
exports.Slider = Slider;
//# sourceMappingURL=slider.js.map