"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ContiguousDayRangePicker = void 0;
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
const react_day_picker_1 = require("react-day-picker");
const core_1 = require("@blueprintjs/core");
const dateRangeSelectionStrategy_1 = require("../../common/dateRangeSelectionStrategy");
const monthAndYear_1 = require("../../common/monthAndYear");
const reactDayPickerUtils_1 = require("../../common/reactDayPickerUtils");
const datePickerDropdown_1 = require("../react-day-picker/datePickerDropdown");
const datePickerNavIcons_1 = require("../react-day-picker/datePickerNavIcons");
/**
 * Render a standard day range picker where props.contiguousCalendarMonths is expected to be `true`.
 */
const ContiguousDayRangePicker = ({ allowSingleDayRange, boundaryToModify, dayPickerEventHandlers, dayPickerProps, initialMonthAndYear, locale, maxDate, minDate, onRangeSelect, singleMonthOnly = false, value, }) => {
    const { displayMonth, handleMonthChange } = useContiguousCalendarViews(initialMonthAndYear, singleMonthOnly, value, dayPickerProps?.onMonthChange);
    const handleRangeSelect = (0, react_1.useCallback)((range, selectedDay, activeModifiers, e) => {
        dayPickerProps?.onSelect?.(range, selectedDay, activeModifiers, e);
        if (activeModifiers.disabled) {
            return;
        }
        const { dateRange: nextValue, boundary } = dateRangeSelectionStrategy_1.DateRangeSelectionStrategy.getNextState(value, selectedDay, allowSingleDayRange, boundaryToModify);
        onRangeSelect(nextValue, selectedDay, boundary);
    }, [allowSingleDayRange, boundaryToModify, dayPickerProps, onRangeSelect, value]);
    return ((0, jsx_runtime_1.jsx)(react_day_picker_1.DayPicker, { showOutsideDays: true, ...dayPickerEventHandlers, ...dayPickerProps, captionLayout: "dropdown-buttons", components: {
            Dropdown: datePickerDropdown_1.DatePickerDropdown,
            IconLeft: datePickerNavIcons_1.IconLeft,
            IconRight: datePickerNavIcons_1.IconRight,
            ...dayPickerProps?.components,
        }, fromDate: minDate, locale: locale, mode: "range", month: displayMonth.getFullDate(), numberOfMonths: singleMonthOnly ? 1 : 2, onMonthChange: handleMonthChange, onSelect: handleRangeSelect, selected: (0, reactDayPickerUtils_1.dateRangeToDayPickerRange)(value), toDate: maxDate }));
};
exports.ContiguousDayRangePicker = ContiguousDayRangePicker;
exports.ContiguousDayRangePicker.displayName = `${core_1.DISPLAYNAME_PREFIX}.ContiguousDayRangePicker`;
/**
 * State management and navigation event handlers for a single calendar or two contiguous calendar views.
 *
 * @param initialMonthAndYear initial month and year to display in the left calendar
 * @param singleMonthOnly whether we are only displaying a single month instead of two
 * @param selectedRange currently selected date range
 * @param userOnMonthChange custom `dayPickerProps.onMonthChange` handler supplied by users of `DateRangePicker`
 */
function useContiguousCalendarViews(initialMonthAndYear, singleMonthOnly, selectedRange, userOnMonthChange) {
    const [displayMonth, setDisplayMonth] = (0, react_1.useState)(initialMonthAndYear);
    const prevSelectedRange = (0, react_1.useRef)(selectedRange);
    const isInitialRender = (0, react_1.useRef)(true);
    // use an effect to react to external value updates (such as shortcut item selections)
    (0, react_1.useEffect)(() => {
        // upon first render, we shouldn't update the display month; instead just use the initially computed value.
        // this is important in cases where the user sets `initialMonth` and a controlled `value`.
        if (isInitialRender.current) {
            isInitialRender.current = false;
            return;
        }
        if (selectedRange == null) {
            return;
        }
        setDisplayMonth(prevDisplayMonth => {
            let newDisplayMonth = prevDisplayMonth.clone();
            if (selectedRange[0] == null || selectedRange[1] == null) {
                // special case: if only one boundary of the range is selected and it is already displayed in one of the
                // months, don't update the display month. this prevents the picker from shifting around when a user is in
                // the middle of a selection.
                if (isDateDisplayed(selectedRange[0], prevDisplayMonth, singleMonthOnly) ||
                    isDateDisplayed(selectedRange[1], prevDisplayMonth, singleMonthOnly)) {
                    return newDisplayMonth;
                }
            }
            const nextRangeStart = monthAndYear_1.MonthAndYear.fromDate(selectedRange[0]);
            const nextRangeEnd = monthAndYear_1.MonthAndYear.fromDate(selectedRange[1]);
            const hasSelectionEndChanged = prevSelectedRange.current[0]?.valueOf() === selectedRange[0]?.valueOf();
            if (nextRangeStart == null && nextRangeEnd != null) {
                // Only end date selected.
                // If the newly selected end date isn't in either of the displayed months, then
                //   - set the right DayPicker to the month of the selected end date
                //   - ensure the left DayPicker is before the right, changing if needed
                if (!nextRangeEnd.isSame(newDisplayMonth.getNextMonth())) {
                    newDisplayMonth = nextRangeEnd.getPreviousMonth();
                }
            }
            else if (nextRangeStart != null && nextRangeEnd == null) {
                // Only start date selected.
                // If the newly selected start date isn't in either of the displayed months, then
                //   - set the left DayPicker to the month of the selected start date
                //   - ensure the right DayPicker is before the left, changing if needed
                if (!nextRangeStart.isSame(newDisplayMonth)) {
                    newDisplayMonth = nextRangeStart;
                }
            }
            else if (nextRangeStart != null && nextRangeEnd != null) {
                if (nextRangeStart.isSame(nextRangeEnd)) {
                    // Both start and end date months are identical
                    if (newDisplayMonth.isSame(nextRangeStart) ||
                        (!singleMonthOnly && newDisplayMonth.getNextMonth().isSame(nextRangeEnd))) {
                        // do nothing
                    }
                    else {
                        newDisplayMonth = nextRangeStart;
                    }
                }
                else if (hasSelectionEndChanged) {
                    // If the selection end has changed, adjust the view to show the new end date
                    newDisplayMonth = singleMonthOnly ? nextRangeEnd : nextRangeEnd.getPreviousMonth();
                }
                else {
                    // Otherwise, the selection start must have changed, show that
                    newDisplayMonth = nextRangeStart;
                }
            }
            return newDisplayMonth;
        });
    }, [setDisplayMonth, selectedRange, singleMonthOnly]);
    (0, react_1.useEffect)(() => {
        prevSelectedRange.current = selectedRange;
    }, [selectedRange]);
    const handleMonthChange = (0, react_1.useCallback)(newMonth => {
        const newDisplayMonth = monthAndYear_1.MonthAndYear.fromDate(newMonth);
        if (newDisplayMonth) {
            setDisplayMonth(newDisplayMonth);
        }
        userOnMonthChange?.(newMonth);
    }, [userOnMonthChange, setDisplayMonth]);
    return {
        displayMonth,
        handleMonthChange,
    };
}
/**
 * Determines whether a given date is displayed in a contiguous single- or double-calendar view.
 */
function isDateDisplayed(date, displayMonth, singleMonthOnly) {
    if (date == null) {
        return false;
    }
    const month = monthAndYear_1.MonthAndYear.fromDate(date);
    if (month == null) {
        return false;
    }
    return singleMonthOnly
        ? displayMonth.isSameMonth(month)
        : displayMonth.isSameMonth(month) || displayMonth.getNextMonth().isSameMonth(month);
}
//# sourceMappingURL=contiguousDayRangePicker.js.map