"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NonContiguousDayRangePicker = void 0;
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
const common_1 = require("../../common");
const dateRangeSelectionStrategy_1 = require("../../common/dateRangeSelectionStrategy");
const monthAndYear_1 = require("../../common/monthAndYear");
const reactDayPickerUtils_1 = require("../../common/reactDayPickerUtils");
const datePickerCaption_1 = require("../react-day-picker/datePickerCaption");
/**
 * Date range picker with two calendars which can move independently of each other.
 */
const NonContiguousDayRangePicker = ({ allowSingleDayRange, boundaryToModify, dayPickerEventHandlers, dayPickerProps, initialMonthAndYear, locale, maxDate, minDate, onRangeSelect, value, }) => {
    const { displayMonths, handleLeftMonthChange, handleRightMonthChange } = useNonContiguousCalendarViews(initialMonthAndYear, value, dayPickerProps?.onMonthChange, minDate, maxDate);
    const handleDaySelect = (0, react_1.useCallback)((range, selectedDay, activeModifiers, e) => {
        dayPickerProps?.onSelect?.(range, selectedDay, activeModifiers, e);
        if (activeModifiers.disabled) {
            return;
        }
        const { dateRange: nextValue, boundary } = dateRangeSelectionStrategy_1.DateRangeSelectionStrategy.getNextState(value, selectedDay, allowSingleDayRange, boundaryToModify);
        onRangeSelect(nextValue, selectedDay, boundary);
    }, [allowSingleDayRange, boundaryToModify, dayPickerProps, onRangeSelect, value]);
    // props applied to both the left and right calendars
    const commonDayPickerProps = {
        locale,
        mode: "range",
        showOutsideDays: true,
        ...dayPickerProps,
        ...dayPickerEventHandlers,
        components: {
            Caption: datePickerCaption_1.DatePickerCaption,
            ...dayPickerProps?.components,
        },
        onSelect: handleDaySelect,
        selected: (0, reactDayPickerUtils_1.dateRangeToDayPickerRange)(value),
    };
    return ((0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.DATERANGEPICKER_CALENDARS, children: [(0, jsx_runtime_1.jsx)(react_day_picker_1.DayPicker, { ...commonDayPickerProps, fromDate: minDate, month: displayMonths.left.getFullDate(), numberOfMonths: 1, onMonthChange: handleLeftMonthChange, toMonth: common_1.DateUtils.getDatePreviousMonth(maxDate) }, "left"), (0, jsx_runtime_1.jsx)(react_day_picker_1.DayPicker, { ...commonDayPickerProps, fromMonth: common_1.DateUtils.getDateNextMonth(minDate), month: displayMonths.right.getFullDate(), numberOfMonths: 1, onMonthChange: handleRightMonthChange, toDate: maxDate }, "right")] }));
};
exports.NonContiguousDayRangePicker = NonContiguousDayRangePicker;
exports.NonContiguousDayRangePicker.displayName = `${core_1.DISPLAYNAME_PREFIX}.NonContiguousDayRangePicker`;
/**
 * State management and navigation event handlers for two (left and right) non-contiguous calendar views.
 *
 * @param initialMonthAndYear initial month and year to display in the left calendar
 * @param selectedRange currently selected date range
 * @param userOnMonthChange custom `dayPickerProps.onMonthChange` handler supplied by users of `DateRangePicker`
 */
function useNonContiguousCalendarViews(initialMonthAndYear, selectedRange, userOnMonthChange, minDate, maxDate) {
    // show the selected end date's encompassing month in the right view if
    // the calendars don't have to be contiguous.
    // if left view and right view months are the same, show next month in the right view.
    const [views, setViews] = (0, react_1.useState)({
        left: initialMonthAndYear,
        right: getInitialRightView(selectedRange[1], initialMonthAndYear),
    });
    (0, react_1.useEffect)(() => {
        if (selectedRange == null) {
            return;
        }
        setViews(({ left, right }) => {
            let newLeftView = left.clone();
            let newRightView = right.clone();
            const nextValueStartView = monthAndYear_1.MonthAndYear.fromDate(selectedRange[0]);
            const nextValueEndView = monthAndYear_1.MonthAndYear.fromDate(selectedRange[1]);
            if (nextValueStartView == null && nextValueEndView != null) {
                // Only end date selected.
                // If the newly selected end date isn't in either of the displayed months, then
                //   - set the right DayPicker to the month of the selected end date
                //   - ensure the left DayPicker is before the right, changing if needed
                if (!nextValueEndView.isSame(newLeftView) && !nextValueEndView.isSame(newRightView)) {
                    newRightView = nextValueEndView;
                    if (!newLeftView.isBefore(newRightView)) {
                        newLeftView = newRightView.getPreviousMonth();
                    }
                }
            }
            else if (nextValueStartView != null && nextValueEndView == null) {
                // Only start date selected.
                // If the newly selected start date isn't in either of the displayed months, then
                //   - set the left DayPicker to the month of the selected start date
                //   - ensure the right DayPicker is before the left, changing if needed
                if (!nextValueStartView.isSame(newLeftView) && !nextValueStartView.isSame(newRightView)) {
                    newLeftView = nextValueStartView;
                    if (!newRightView.isAfter(newLeftView)) {
                        newRightView = newLeftView.getNextMonth();
                    }
                }
            }
            else if (nextValueStartView != null && nextValueEndView != null) {
                // Both start and end date months are identical
                // If the selected month isn't in either of the displayed months, then
                //   - set the left DayPicker to be the selected month
                //   - set the right DayPicker to +1
                if (nextValueStartView.isSame(nextValueEndView)) {
                    if (newLeftView.isSame(nextValueStartView) || newRightView.isSame(nextValueStartView)) {
                        // do nothing
                    }
                    else {
                        newLeftView = nextValueStartView;
                        newRightView = nextValueStartView.getNextMonth();
                    }
                }
                else {
                    // Different start and end date months, adjust display months.
                    if (!newLeftView.isSame(nextValueStartView)) {
                        newLeftView = nextValueStartView;
                        newRightView = nextValueStartView.getNextMonth();
                    }
                    if (!newRightView.isSame(nextValueEndView)) {
                        newRightView = nextValueEndView;
                    }
                }
            }
            return { left: newLeftView, right: newRightView };
        });
    }, [setViews, selectedRange]);
    const handleLeftMonthChange = (0, react_1.useCallback)((newDate) => {
        const newLeftView = monthAndYear_1.MonthAndYear.fromDate(newDate);
        if (newLeftView == null) {
            return;
        }
        setViews(({ right }) => {
            let newRightView = right.clone();
            if (!newLeftView.isBefore(newRightView)) {
                newRightView = newLeftView.getNextMonth();
            }
            const [leftView, rightView] = getBoundedViews(newLeftView, newRightView, minDate, maxDate);
            userOnMonthChange?.(newLeftView.getFullDate());
            return { left: leftView, right: rightView };
        });
    }, [minDate, maxDate, setViews, userOnMonthChange]);
    const handleRightMonthChange = (0, react_1.useCallback)((newDate) => {
        const newRightView = monthAndYear_1.MonthAndYear.fromDate(newDate);
        if (newRightView == null) {
            return;
        }
        setViews(({ left }) => {
            let newLeftView = left.clone();
            if (!newRightView.isAfter(newLeftView)) {
                newLeftView = newRightView.getPreviousMonth();
            }
            const [leftView, rightView] = getBoundedViews(newLeftView, newRightView, minDate, maxDate);
            userOnMonthChange?.(newRightView.getFullDate());
            return { left: leftView, right: rightView };
        });
    }, [minDate, maxDate, setViews, userOnMonthChange]);
    return {
        displayMonths: views,
        handleLeftMonthChange,
        handleRightMonthChange,
    };
}
function getBoundedViews(leftView, rightView, minDate, maxDate) {
    const minView = monthAndYear_1.MonthAndYear.fromDate(minDate ?? null);
    if (minView != null && leftView.isBefore(minView)) {
        return [minView, minView.getNextMonth()];
    }
    const maxView = monthAndYear_1.MonthAndYear.fromDate(maxDate ?? null);
    if (maxView != null && rightView.isAfter(maxView)) {
        return [maxView.getPreviousMonth(), maxView];
    }
    return [leftView, rightView];
}
function getInitialRightView(selectedRangeEnd, leftView) {
    const rightView = monthAndYear_1.MonthAndYear.fromDate(selectedRangeEnd);
    if (rightView === undefined || rightView.isSameMonth(leftView)) {
        return leftView.getNextMonth();
    }
    return rightView;
}
//# sourceMappingURL=nonContiguousDayRangePicker.js.map