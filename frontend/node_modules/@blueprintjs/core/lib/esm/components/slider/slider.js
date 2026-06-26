import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import { AbstractPureComponent, Intent } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
import { MultiSlider, MultiSliderHandle } from "./multiSlider";
/**
 * Slider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/sliders.slider
 */
export class Slider extends AbstractPureComponent {
    static defaultProps = {
        ...MultiSlider.defaultSliderProps,
        initialValue: 0,
        intent: Intent.PRIMARY,
        value: 0,
    };
    static displayName = `${DISPLAYNAME_PREFIX}.Slider`;
    render() {
        const { initialValue, intent, value, onChange, onRelease, handleHtmlProps, ...props } = this.props;
        return (_jsxs(MultiSlider, { ...props, children: [_jsx(MultiSliderHandle, { value: value, intentAfter: value < initialValue ? intent : undefined, intentBefore: value > initialValue ? intent : undefined, onChange: onChange, onRelease: onRelease, htmlProps: handleHtmlProps }), _jsx(MultiSliderHandle, { value: initialValue, interactionKind: "none" })] }));
    }
}
//# sourceMappingURL=slider.js.map