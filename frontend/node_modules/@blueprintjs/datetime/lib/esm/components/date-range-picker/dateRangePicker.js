import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
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
import classNames from "classnames";
import { addDays, format } from "date-fns";
import { Boundary, DISPLAYNAME_PREFIX, Divider } from "@blueprintjs/core";
import { Classes, DateUtils, Errors, TimePrecision } from "../../common";
import { dayPickerClassNameOverrides } from "../../common/classes";
import { DateRangeSelectionStrategy } from "../../common/dateRangeSelectionStrategy";
import { combineModifiers, HOVERED_RANGE_MODIFIER } from "../../common/dayPickerModifiers";
import { MonthAndYear } from "../../common/monthAndYear";
import { DatePickerProvider } from "../date-picker/datePickerContext";
import { LOCALE, MAX_DATE, MIN_DATE } from "../dateConstants";
import { DateFnsLocalizedComponent } from "../dateFnsLocalizedComponent";
import { DatePickerShortcutMenu } from "../shortcuts/shortcuts";
import { TimePicker } from "../time-picker/timePicker";
import { ContiguousDayRangePicker } from "./contiguousDayRangePicker";
import { NonContiguousDayRangePicker } from "./nonContiguousDayRangePicker";
const NULL_RANGE = [null, null];
/**
 * Date range picker component.
 *
 * @see https://blueprintjs.com/docs/#datetime/date-range-picker
 */
export class DateRangePicker extends DateFnsLocalizedComponent {
    static defaultProps = {
        allowSingleDayRange: false,
        contiguousCalendarMonths: true,
        dayPickerProps: {},
        locale: LOCALE,
        maxDate: MAX_DATE,
        minDate: MIN_DATE,
        reverseMonthAndYearMenus: false,
        shortcuts: true,
        singleMonthOnly: false,
        timePickerProps: {},
    };
    static displayName = `${DISPLAYNAME_PREFIX}.DateRangePicker`;
    // these will get merged with the user's own
    modifiers = {
        [HOVERED_RANGE_MODIFIER]: day => {
            const { hoverValue, value: [selectedStart, selectedEnd], } = this.state;
            if (selectedStart == null && selectedEnd == null) {
                return false;
            }
            if (hoverValue == null || hoverValue[0] == null || hoverValue[1] == null) {
                return false;
            }
            return DateUtils.isDayInRange(day, hoverValue, true);
        },
        [`${HOVERED_RANGE_MODIFIER}-start`]: day => {
            const { hoverValue } = this.state;
            if (hoverValue == null || hoverValue[0] == null) {
                return false;
            }
            return DateUtils.isSameDay(hoverValue[0], day);
        },
        [`${HOVERED_RANGE_MODIFIER}-end`]: day => {
            const { hoverValue } = this.state;
            if (hoverValue == null || hoverValue[1] == null) {
                return false;
            }
            return DateUtils.isSameDay(hoverValue[1], day);
        },
    };
    modifiersClassNames = {
        [HOVERED_RANGE_MODIFIER]: Classes.DATERANGEPICKER3_HOVERED_RANGE,
        [`${HOVERED_RANGE_MODIFIER}-start`]: Classes.DATERANGEPICKER3_HOVERED_RANGE_START,
        [`${HOVERED_RANGE_MODIFIER}-end`]: Classes.DATERANGEPICKER3_HOVERED_RANGE_END,
    };
    initialMonthAndYear = MonthAndYear.fromDate(new Date()) ?? new MonthAndYear(new Date().getMonth(), new Date().getFullYear());
    constructor(props) {
        super(props);
        const value = getInitialValue(props);
        const time = value;
        const initialMonth = getInitialMonth(props, value);
        this.initialMonthAndYear = new MonthAndYear(initialMonth.getMonth(), initialMonth.getFullYear());
        this.state = {
            hoverValue: NULL_RANGE,
            locale: undefined,
            selectedShortcutIndex: this.props.selectedShortcutIndex !== undefined ? this.props.selectedShortcutIndex : -1,
            time,
            value,
        };
    }
    render() {
        const { className, contiguousCalendarMonths, footerElement } = this.props;
        const isSingleMonthOnly = getIsSingleMonthOnly(this.props);
        const classes = classNames(Classes.DATEPICKER, Classes.DATERANGEPICKER, className, {
            [Classes.DATEPICKER3_HIGHLIGHT_CURRENT_DAY]: this.props.highlightCurrentDay,
            [Classes.DATERANGEPICKER_CONTIGUOUS]: contiguousCalendarMonths,
            [Classes.DATERANGEPICKER_SINGLE_MONTH]: isSingleMonthOnly,
            [Classes.DATERANGEPICKER3_REVERSE_MONTH_AND_YEAR]: this.props.reverseMonthAndYearMenus,
        });
        // use the left DayPicker when we only need one
        return (_jsxs("div", { className: classes, children: [this.maybeRenderShortcuts(), _jsx("div", { className: Classes.DATEPICKER_CONTENT, children: _jsxs(DatePickerProvider, { ...this.props, ...this.state, children: [contiguousCalendarMonths || isSingleMonthOnly
                                ? this.renderContiguousDayRangePicker(isSingleMonthOnly)
                                : this.renderNonContiguousDayRangePicker(), this.maybeRenderTimePickers(isSingleMonthOnly), footerElement] }) })] }));
    }
    async componentDidMount() {
        await super.componentDidMount();
    }
    async componentDidUpdate(prevProps) {
        super.componentDidUpdate(prevProps);
        const isControlled = prevProps.value !== undefined && this.props.value !== undefined;
        if (prevProps.contiguousCalendarMonths !== this.props.contiguousCalendarMonths) {
            const initialMonth = getInitialMonth(this.props, getInitialValue(this.props));
            this.initialMonthAndYear = new MonthAndYear(initialMonth.getMonth(), initialMonth.getFullYear());
        }
        if (isControlled &&
            (!DateUtils.areRangesEqual(prevProps.value, this.props.value) ||
                prevProps.contiguousCalendarMonths !== this.props.contiguousCalendarMonths)) {
            this.setState({ value: this.props.value ?? NULL_RANGE });
        }
        if (this.props.selectedShortcutIndex !== prevProps.selectedShortcutIndex) {
            this.setState({ selectedShortcutIndex: this.props.selectedShortcutIndex });
        }
    }
    validateProps(props) {
        const { defaultValue, initialMonth, maxDate, minDate, boundaryToModify, value } = props;
        const dateRange = [minDate, maxDate];
        if (defaultValue != null && !DateUtils.isDayRangeInRange(defaultValue, dateRange)) {
            console.error(Errors.DATERANGEPICKER_DEFAULT_VALUE_INVALID);
        }
        if (initialMonth != null && !DateUtils.isMonthInRange(initialMonth, dateRange)) {
            console.error(Errors.DATERANGEPICKER_INITIAL_MONTH_INVALID);
        }
        if (maxDate != null && minDate != null && maxDate < minDate && !DateUtils.isSameDay(maxDate, minDate)) {
            console.error(Errors.DATERANGEPICKER_MAX_DATE_INVALID);
        }
        if (value != null && !DateUtils.isDayRangeInRange(value, dateRange)) {
            console.error(Errors.DATERANGEPICKER_VALUE_INVALID);
        }
        if (boundaryToModify != null && boundaryToModify !== Boundary.START && boundaryToModify !== Boundary.END) {
            console.error(Errors.DATERANGEPICKER_PREFERRED_BOUNDARY_TO_MODIFY_INVALID);
        }
    }
    maybeRenderShortcuts() {
        const { shortcuts } = this.props;
        if (shortcuts == null || shortcuts === false) {
            return null;
        }
        const { selectedShortcutIndex } = this.state;
        const { allowSingleDayRange, maxDate = MAX_DATE, minDate = MIN_DATE, timePrecision } = this.props;
        return [
            _jsx(DatePickerShortcutMenu, { allowSingleDayRange: allowSingleDayRange, maxDate: maxDate, minDate: minDate, onShortcutClick: this.handleShortcutClick, selectedShortcutIndex: selectedShortcutIndex, shortcuts: shortcuts, timePrecision: timePrecision }, "shortcuts"),
            _jsx(Divider, {}, "div"),
        ];
    }
    maybeRenderTimePickers(isShowingOneMonth) {
        // timePrecision may be set as a root prop or as a property inside timePickerProps, so we need to check both
        const { timePickerProps, timePrecision = timePickerProps?.precision } = this.props;
        if (timePrecision == null && timePickerProps === DateRangePicker.defaultProps.timePickerProps) {
            return null;
        }
        const isLongTimePicker = timePickerProps?.useAmPm ||
            timePrecision === TimePrecision.SECOND ||
            timePrecision === TimePrecision.MILLISECOND;
        return (_jsxs("div", { className: classNames(Classes.DATERANGEPICKER_TIMEPICKERS, {
                [Classes.DATERANGEPICKER3_TIMEPICKERS_STACKED]: isShowingOneMonth && isLongTimePicker,
            }), children: [_jsx(TimePicker, { precision: timePrecision, ...timePickerProps, onChange: this.handleTimeChangeLeftCalendar, value: this.state.time[0] }), _jsx(TimePicker, { precision: timePrecision, ...timePickerProps, onChange: this.handleTimeChangeRightCalendar, value: this.state.time[1] })] }));
    }
    handleTimeChange = (newTime, dateIndex) => {
        this.props.timePickerProps?.onChange?.(newTime);
        const { value, time } = this.state;
        const newValue = DateUtils.getDateTime(value[dateIndex] != null ? DateUtils.clone(value[dateIndex]) : this.getDefaultDate(dateIndex), newTime);
        const newDateRange = [value[0], value[1]];
        newDateRange[dateIndex] = newValue;
        const newTimeRange = [time[0], time[1]];
        newTimeRange[dateIndex] = newTime;
        this.props.onChange?.(newDateRange);
        this.setState({ time: newTimeRange, value: newDateRange });
    };
    // When a user sets the time value before choosing a date, we need to pick a date for them
    // The default depends on the value of the other date since there's an invariant
    // that the left/0 date is always less than the right/1 date
    getDefaultDate = (dateIndex) => {
        const { value } = this.state;
        const otherIndex = dateIndex === 0 ? 1 : 0;
        const otherDate = value[otherIndex];
        if (otherDate == null) {
            return new Date();
        }
        const { allowSingleDayRange } = this.props;
        if (!allowSingleDayRange) {
            const dateDiff = dateIndex === 0 ? -1 : 1;
            return addDays(otherDate, dateDiff);
        }
        return otherDate;
    };
    handleTimeChangeLeftCalendar = (time) => {
        this.handleTimeChange(time, 0);
    };
    handleTimeChangeRightCalendar = (time) => {
        this.handleTimeChange(time, 1);
    };
    /**
     * Render a standard day range picker where props.contiguousCalendarMonths is expected to be `true`.
     */
    renderContiguousDayRangePicker(singleMonthOnly) {
        const { dayPickerProps, ...props } = this.props;
        return (_jsx(ContiguousDayRangePicker, { ...props, contiguousCalendarMonths: true, dayPickerEventHandlers: {
                onDayMouseEnter: this.handleDayMouseEnter,
                onDayMouseLeave: this.handleDayMouseLeave,
            }, dayPickerProps: this.resolvedDayPickerProps, initialMonthAndYear: this.initialMonthAndYear, locale: this.state.locale, onRangeSelect: this.handleDayRangeSelect, singleMonthOnly: singleMonthOnly, value: this.state.value }));
    }
    /**
     * react-day-picker doesn't have built-in support for non-contiguous calendar months in its range picker,
     * so we have to implement this ourselves.
     */
    renderNonContiguousDayRangePicker() {
        const { dayPickerProps, ...props } = this.props;
        return (_jsx(NonContiguousDayRangePicker, { ...props, dayPickerProps: this.resolvedDayPickerProps, dayPickerEventHandlers: {
                onDayMouseEnter: this.handleDayMouseEnter,
                onDayMouseLeave: this.handleDayMouseLeave,
            }, initialMonthAndYear: this.initialMonthAndYear, locale: this.state.locale, onRangeSelect: this.handleDayRangeSelect, value: this.state.value }));
    }
    get resolvedDayPickerProps() {
        const { dayPickerProps = {} } = this.props;
        return {
            ...dayPickerProps,
            classNames: {
                ...dayPickerClassNameOverrides,
                ...dayPickerProps.classNames,
            },
            formatters: {
                formatWeekdayName: this.formatWeekdayName,
                ...dayPickerProps.formatters,
            },
            modifiers: combineModifiers(this.modifiers, dayPickerProps.modifiers),
            modifiersClassNames: {
                ...this.modifiersClassNames,
                ...dayPickerProps.modifiersClassNames,
            },
        };
    }
    /**
     * Custom formatter to render weekday names in the calendar header. The default formatter generally works fine,
     * but it was returning CAPITALIZED strings for some reason, while we prefer Title Case.
     */
    formatWeekdayName = date => format(date, "EEEEEE", { locale: this.state.locale });
    handleDayMouseEnter = (day, activeModifiers, e) => {
        this.props.dayPickerProps?.onDayMouseEnter?.(day, activeModifiers, e);
        if (activeModifiers.disabled) {
            return;
        }
        const { dateRange, boundary } = DateRangeSelectionStrategy.getNextState(this.state.value, day, this.props.allowSingleDayRange, this.props.boundaryToModify);
        this.setState({ hoverValue: dateRange });
        this.props.onHoverChange?.(dateRange, day, boundary);
    };
    handleDayMouseLeave = (day, activeModifiers, e) => {
        this.props.dayPickerProps?.onDayMouseLeave?.(day, activeModifiers, e);
        if (activeModifiers.disabled) {
            return;
        }
        this.setState({ hoverValue: undefined });
        this.props.onHoverChange?.(undefined, day, undefined);
    };
    handleDayRangeSelect = (nextValue, selectedDay, boundary) => {
        // update the hovered date range after click to show the newly selected
        // state, at leasts until the mouse moves again
        this.setState({ hoverValue: nextValue });
        this.props.onHoverChange?.(nextValue, selectedDay, boundary);
        this.updateSelectedRange(nextValue);
    };
    handleShortcutClick = (shortcut, selectedShortcutIndex) => {
        const { dateRange, includeTime } = shortcut;
        if (includeTime) {
            this.updateSelectedRange(dateRange, [dateRange[0], dateRange[1]]);
        }
        else {
            this.updateSelectedRange(dateRange);
        }
        if (this.props.selectedShortcutIndex === undefined) {
            // uncontrolled shorcut selection
            this.setState({ selectedShortcutIndex });
        }
        this.props.onShortcutChange?.(shortcut, selectedShortcutIndex);
    };
    updateSelectedRange = (selectedRange, selectedTimeRange = this.state.time) => {
        selectedRange[0] = DateUtils.getDateTime(selectedRange[0], selectedTimeRange[0]);
        selectedRange[1] = DateUtils.getDateTime(selectedRange[1], selectedTimeRange[1]);
        if (this.props.value == null) {
            // uncontrolled range selection
            this.setState({ time: selectedTimeRange, value: selectedRange });
        }
        this.props.onChange?.(selectedRange);
    };
}
function getIsSingleMonthOnly(props) {
    return props.singleMonthOnly || DateUtils.isSameMonth(props.minDate, props.maxDate);
}
function getInitialValue(props) {
    if (props.value != null) {
        return props.value;
    }
    if (props.defaultValue != null) {
        return props.defaultValue;
    }
    return NULL_RANGE;
}
function getInitialMonth(props, value) {
    const today = new Date();
    const isSingleMonthOnly = getIsSingleMonthOnly(props);
    if (props.initialMonth != null) {
        if (!isSingleMonthOnly && DateUtils.isSameMonth(props.initialMonth, props.maxDate)) {
            // special case: if initial month is same as maxDate month, display it on the right calendar
            return DateUtils.getDatePreviousMonth(props.initialMonth);
        }
        return props.initialMonth;
    }
    else if (value[0] != null) {
        if (!isSingleMonthOnly && DateUtils.isSameMonth(value[0], props.maxDate)) {
            // special case: if start of range is selected and that date is in the maxDate month, display it on the right calendar
            return DateUtils.getDatePreviousMonth(value[0]);
        }
        return DateUtils.clone(value[0]);
    }
    else if (value[1] != null) {
        const month = DateUtils.clone(value[1]);
        if (!DateUtils.isSameMonth(month, props.minDate)) {
            month.setMonth(month.getMonth() - 1);
        }
        return month;
    }
    else if (DateUtils.isDayInRange(today, [props.minDate, props.maxDate])) {
        if (!isSingleMonthOnly && DateUtils.isSameMonth(today, props.maxDate)) {
            // special case: if today is in the maxDate month, display it on the right calendar
            today.setMonth(today.getMonth() - 1);
        }
        return today;
    }
    else {
        const betweenDate = DateUtils.getDateBetween([props.minDate, props.maxDate]);
        if (!isSingleMonthOnly && DateUtils.isSameMonth(betweenDate, props.maxDate)) {
            // special case: if betweenDate is in the maxDate month, display it on the right calendar
            betweenDate.setMonth(betweenDate.getMonth() - 1);
        }
        return betweenDate;
    }
}
//# sourceMappingURL=dateRangePicker.js.map