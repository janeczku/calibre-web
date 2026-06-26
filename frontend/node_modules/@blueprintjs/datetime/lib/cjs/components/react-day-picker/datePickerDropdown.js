"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DatePickerDropdown = DatePickerDropdown;
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2023 Palantir Technologies, Inc. All rights reserved.
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
const react_1 = require("react");
const core_1 = require("@blueprintjs/core");
const useMonthSelectRightOffset_1 = require("../../common/useMonthSelectRightOffset");
/**
 * Custom react-day-picker dropdown component which implements Blueprint's datepicker design
 * for month and year dropdowns.
 *
 * @see https://daypicker.dev/guides/custom-components
 */
function DatePickerDropdown({ caption, children, ...props }) {
    const containerElement = (0, react_1.useRef)(null);
    const selectElement = (0, react_1.useRef)(null);
    // Use a custom hook to adjust the position of the position of the HTMLSelect icon to appear right next to
    // the month name. N.B. we expect props.caption to be a simple string representing the month name.
    const displayedMonthText = typeof caption === "string" ? caption : "";
    const monthSelectRightOffset = (0, useMonthSelectRightOffset_1.useMonthSelectRightOffset)(selectElement, containerElement, displayedMonthText);
    const iconProps = (0, react_1.useMemo)(() => (props.name === "months" ? { style: { right: monthSelectRightOffset } } : {}), [props.name, monthSelectRightOffset]);
    return ((0, jsx_runtime_1.jsx)("div", { ref: containerElement, children: (0, jsx_runtime_1.jsx)(core_1.HTMLSelect, { iconProps: iconProps, minimal: true, ref: selectElement, ...props, children: children }) }));
}
//# sourceMappingURL=datePickerDropdown.js.map