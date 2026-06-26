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
import { AbstractPureComponent, DISPLAYNAME_PREFIX, Intent } from "../../common";
import * as Errors from "../../common/errors";
import { MultiSlider, MultiSliderHandle } from "./multiSlider";
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
export class RangeSlider extends AbstractPureComponent {
    static defaultProps = {
        ...MultiSlider.defaultSliderProps,
        intent: Intent.PRIMARY,
        value: [0, 10],
    };
    static displayName = `${DISPLAYNAME_PREFIX}.RangeSlider`;
    render() {
        const { value, handleHtmlProps, ...props } = this.props;
        return (_jsxs(MultiSlider, { ...props, children: [_jsx(MultiSliderHandle, { value: value[RangeIndex.START], type: "start", intentAfter: props.intent, htmlProps: handleHtmlProps?.start }), _jsx(MultiSliderHandle, { value: value[RangeIndex.END], type: "end", htmlProps: handleHtmlProps?.end })] }));
    }
    validateProps(props) {
        const { value } = props;
        if (value == null || value[RangeIndex.START] == null || value[RangeIndex.END] == null) {
            throw new Error(Errors.RANGESLIDER_NULL_VALUE);
        }
    }
}
//# sourceMappingURL=rangeSlider.js.map