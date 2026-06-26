"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DatePickerShortcutMenu = void 0;
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
const react_1 = require("react");
const core_1 = require("@blueprintjs/core");
const common_1 = require("../../common");
const dateUtils_1 = require("../../common/dateUtils");
/**
 * Menu of {@link DateRangeShortcut} items, typically displayed in the UI to the left of a day picker calendar.
 *
 * This component may be used for single date pickers as well as range pickers by toggling the
 * `useSingleDateShortcuts` option.
 */
const DatePickerShortcutMenu = props => {
    const { allowSingleDayRange = false, maxDate, minDate, onShortcutClick, selectedShortcutIndex = -1, timePrecision, useSingleDateShortcuts = false, } = props;
    const shortcuts = props.shortcuts === true
        ? createDefaultShortcuts(allowSingleDayRange, timePrecision != null, useSingleDateShortcuts)
        : props.shortcuts;
    return ((0, jsx_runtime_1.jsx)(core_1.Menu, { "aria-label": "Date picker shortcuts", className: common_1.Classes.DATERANGEPICKER_SHORTCUTS, tabIndex: 0, children: shortcuts.map((shortcut, index) => ((0, jsx_runtime_1.jsx)(ShortcutMenuItem, { active: selectedShortcutIndex === index, index: index, maxDate: maxDate, minDate: minDate, onShortcutClick: onShortcutClick, shortcut: shortcut }, index))) }));
};
exports.DatePickerShortcutMenu = DatePickerShortcutMenu;
const ShortcutMenuItem = props => {
    const { active, index, maxDate, minDate, onShortcutClick, shortcut } = props;
    const isShortcutInRange = (0, dateUtils_1.isDayRangeInRange)(shortcut.dateRange, [minDate, maxDate]);
    const handleClick = (0, react_1.useCallback)(() => onShortcutClick(shortcut, index), [index, onShortcutClick, shortcut]);
    return ((0, jsx_runtime_1.jsx)(core_1.MenuItem, { active: active, disabled: !isShortcutInRange, onClick: handleClick, shouldDismissPopover: false, text: shortcut.label }));
};
function createShortcut(label, dateRange) {
    return { dateRange, label };
}
function createDefaultShortcuts(allowSingleDayRange, hasTimePrecision, useSingleDateShortcuts) {
    const today = new Date();
    const makeDate = (action) => {
        const returnVal = (0, dateUtils_1.clone)(today);
        action(returnVal);
        returnVal.setDate(returnVal.getDate() + 1);
        return returnVal;
    };
    const tomorrow = makeDate(() => null);
    const yesterday = makeDate(d => d.setDate(d.getDate() - 2));
    const oneWeekAgo = makeDate(d => d.setDate(d.getDate() - 7));
    const oneMonthAgo = makeDate(d => d.setMonth(d.getMonth() - 1));
    const threeMonthsAgo = makeDate(d => d.setMonth(d.getMonth() - 3));
    const sixMonthsAgo = makeDate(d => d.setMonth(d.getMonth() - 6));
    const oneYearAgo = makeDate(d => d.setFullYear(d.getFullYear() - 1));
    const twoYearsAgo = makeDate(d => d.setFullYear(d.getFullYear() - 2));
    const singleDayShortcuts = allowSingleDayRange || useSingleDateShortcuts
        ? [
            createShortcut("Today", [today, hasTimePrecision ? tomorrow : today]),
            createShortcut("Yesterday", [yesterday, hasTimePrecision ? today : yesterday]),
        ]
        : [];
    return [
        ...singleDayShortcuts,
        createShortcut(useSingleDateShortcuts ? "1 week ago" : "Past week", [oneWeekAgo, today]),
        createShortcut(useSingleDateShortcuts ? "1 month ago" : "Past month", [oneMonthAgo, today]),
        createShortcut(useSingleDateShortcuts ? "3 months ago" : "Past 3 months", [threeMonthsAgo, today]),
        // Don't include a couple of these for the single date shortcut
        ...(useSingleDateShortcuts ? [] : [createShortcut("Past 6 months", [sixMonthsAgo, today])]),
        createShortcut(useSingleDateShortcuts ? "1 year ago" : "Past year", [oneYearAgo, today]),
        ...(useSingleDateShortcuts ? [] : [createShortcut("Past 2 years", [twoYearsAgo, today])]),
    ];
}
//# sourceMappingURL=shortcuts.js.map