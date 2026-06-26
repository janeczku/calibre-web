"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DatePicker = void 0;
const tslib_1 = require("tslib");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const date_fns_1 = require("date-fns");
const react_day_picker_1 = require("react-day-picker");
const core_1 = require("@blueprintjs/core");
const common_1 = require("../../common");
const classes_1 = require("../../common/classes");
const dateConstants_1 = require("../dateConstants");
const dateFnsLocalizedComponent_1 = require("../dateFnsLocalizedComponent");
const datePickerDropdown_1 = require("../react-day-picker/datePickerDropdown");
const datePickerNavIcons_1 = require("../react-day-picker/datePickerNavIcons");
const shortcuts_1 = require("../shortcuts/shortcuts");
const timePicker_1 = require("../time-picker/timePicker");
const datePickerContext_1 = require("./datePickerContext");
/**
 * Date picker component.
 *
 * @see https://blueprintjs.com/docs/#datetime/date-picker
 */
class DatePicker extends dateFnsLocalizedComponent_1.DateFnsLocalizedComponent {
    static defaultProps = {
        canClearSelection: true,
        clearButtonText: "Clear",
        dayPickerProps: {},
        highlightCurrentDay: false,
        locale: dateConstants_1.LOCALE,
        maxDate: dateConstants_1.MAX_DATE,
        minDate: dateConstants_1.MIN_DATE,
        reverseMonthAndYearMenus: false,
        shortcuts: false,
        showActionsBar: false,
        todayButtonText: "Today",
    };
    static displayName = `${core_1.DISPLAYNAME_PREFIX}.DatePicker`;
    ignoreNextMonthChange = false;
    constructor(props) {
        super(props);
        const value = getInitialValue(props);
        const initialMonth = getInitialMonth(props, value);
        this.state = {
            displayMonth: initialMonth.getMonth(),
            displayYear: initialMonth.getFullYear(),
            locale: undefined,
            selectedDay: value == null ? null : value.getDate(),
            selectedShortcutIndex: this.props.selectedShortcutIndex !== undefined ? this.props.selectedShortcutIndex : -1,
            value,
        };
    }
    render() {
        const { className, dayPickerProps, footerElement, maxDate, minDate, showActionsBar } = this.props;
        const { displayMonth, displayYear, locale } = this.state;
        return ((0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(common_1.Classes.DATEPICKER, className, {
                [common_1.Classes.DATEPICKER3_HIGHLIGHT_CURRENT_DAY]: this.props.highlightCurrentDay,
                [common_1.Classes.DATEPICKER3_REVERSE_MONTH_AND_YEAR]: this.props.reverseMonthAndYearMenus,
            }), children: [this.maybeRenderShortcuts(), (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.DATEPICKER_CONTENT, children: (0, jsx_runtime_1.jsxs)(datePickerContext_1.DatePickerProvider, { ...this.props, ...this.state, children: [(0, jsx_runtime_1.jsx)(react_day_picker_1.DayPicker, { locale: locale, showOutsideDays: true, ...dayPickerProps, captionLayout: "dropdown-buttons", classNames: {
                                    ...classes_1.dayPickerClassNameOverrides,
                                    ...dayPickerProps?.classNames,
                                }, components: {
                                    Dropdown: datePickerDropdown_1.DatePickerDropdown,
                                    IconLeft: datePickerNavIcons_1.IconLeft,
                                    IconRight: datePickerNavIcons_1.IconRight,
                                    ...dayPickerProps?.components,
                                }, formatters: {
                                    formatWeekdayName: this.renderWeekdayName,
                                    ...dayPickerProps?.formatters,
                                }, fromDate: minDate, mode: "single", month: new Date(displayYear, displayMonth), onMonthChange: this.handleMonthChange, onSelect: this.handleDaySelect, required: !this.props.canClearSelection, selected: this.state.value ?? undefined, toDate: maxDate }), this.maybeRenderTimePicker(), showActionsBar && this.renderOptionsBar(), footerElement] }) })] }));
    }
    async componentDidMount() {
        await super.componentDidMount();
    }
    async componentDidUpdate(prevProps) {
        super.componentDidUpdate(prevProps);
        if (this.props.value !== prevProps.value) {
            if (this.props.value == null) {
                // clear the value
                this.setState({ value: null });
            }
            else {
                this.setState({
                    displayMonth: this.props.value.getMonth(),
                    displayYear: this.props.value.getFullYear(),
                    selectedDay: this.props.value.getDate(),
                    value: this.props.value,
                });
            }
        }
        if (this.props.selectedShortcutIndex !== prevProps.selectedShortcutIndex) {
            this.setState({ selectedShortcutIndex: this.props.selectedShortcutIndex });
        }
    }
    validateProps(props) {
        const { defaultValue, initialMonth, maxDate, minDate, value } = props;
        if (defaultValue != null && !common_1.DateUtils.isDayInRange(defaultValue, [minDate, maxDate])) {
            console.error(common_1.Errors.DATEPICKER_DEFAULT_VALUE_INVALID);
        }
        if (initialMonth != null && !common_1.DateUtils.isMonthInRange(initialMonth, [minDate, maxDate])) {
            console.error(common_1.Errors.DATEPICKER_INITIAL_MONTH_INVALID);
        }
        if (maxDate != null && minDate != null && maxDate < minDate && !common_1.DateUtils.isSameDay(maxDate, minDate)) {
            console.error(common_1.Errors.DATEPICKER_MAX_DATE_INVALID);
        }
        if (value != null && !common_1.DateUtils.isDayInRange(value, [minDate, maxDate])) {
            console.error(common_1.Errors.DATEPICKER_VALUE_INVALID);
        }
    }
    /**
     * Custom formatter to render weekday names in the calendar header. The default formatter generally works fine,
     * but it was returning CAPITALIZED strings for some reason, while we prefer Title Case.
     */
    renderWeekdayName = date => {
        return (0, date_fns_1.format)(date, "EEEEEE", { locale: this.state.locale });
    };
    renderOptionsBar() {
        const { clearButtonText, todayButtonText, minDate, maxDate, canClearSelection } = this.props;
        const todayEnabled = isTodayEnabled(minDate, maxDate);
        return [
            (0, jsx_runtime_1.jsx)(core_1.Divider, {}, "div"),
            (0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.DATEPICKER_FOOTER, children: [(0, jsx_runtime_1.jsx)(core_1.Button, { disabled: !todayEnabled, onClick: this.handleTodayClick, text: todayButtonText, variant: "minimal" }), (0, jsx_runtime_1.jsx)(core_1.Button, { disabled: !canClearSelection, onClick: this.handleClearClick, text: clearButtonText, variant: "minimal" })] }, "footer"),
        ];
    }
    maybeRenderTimePicker() {
        const { timePrecision, timePickerProps, minDate, maxDate } = this.props;
        if (timePrecision == null && timePickerProps === undefined) {
            return null;
        }
        const applyMin = this.state.value != null && common_1.DateUtils.isSameDay(this.state.value, minDate);
        const applyMax = this.state.value != null && common_1.DateUtils.isSameDay(this.state.value, maxDate);
        return ((0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.DATEPICKER_TIMEPICKER_WRAPPER, children: (0, jsx_runtime_1.jsx)(timePicker_1.TimePicker, { precision: timePrecision, minTime: applyMin ? minDate : undefined, maxTime: applyMax ? maxDate : undefined, ...timePickerProps, onChange: this.handleTimeChange, value: this.state.value }) }));
    }
    maybeRenderShortcuts() {
        const { shortcuts } = this.props;
        if (shortcuts == null || shortcuts === false) {
            return null;
        }
        const { selectedShortcutIndex } = this.state;
        const { maxDate = dateConstants_1.MAX_DATE, minDate = dateConstants_1.MIN_DATE, timePrecision } = this.props;
        // Reuse the existing date range shortcuts and only care about start date
        const dateRangeShortcuts = shortcuts === true
            ? true
            : shortcuts.map(shortcut => ({
                ...shortcut,
                // TODO: Remove cast after setting "strictNullChecks: true"
                dateRange: [shortcut.date, null],
            }));
        return [
            (0, jsx_runtime_1.jsx)(shortcuts_1.DatePickerShortcutMenu, { allowSingleDayRange: true, maxDate: maxDate, minDate: minDate, selectedShortcutIndex: selectedShortcutIndex, shortcuts: dateRangeShortcuts, timePrecision: timePrecision, onShortcutClick: this.handleShortcutClick, useSingleDateShortcuts: true }, "shortcuts"),
            (0, jsx_runtime_1.jsx)(core_1.Divider, {}, "div"),
        ];
    }
    handleDaySelect = (day, selectedDay, activeModifiers, e) => {
        if (activeModifiers.disabled) {
            return;
        }
        else if (day === undefined) {
            this.handleClearClick();
            return;
        }
        this.updateDay(day);
        this.props.dayPickerProps?.onSelect?.(day, selectedDay, activeModifiers, e);
        // allow toggling selected date by clicking it again (if prop enabled)
        const newValue = this.props.canClearSelection && activeModifiers.selected
            ? null
            : common_1.DateUtils.getDateTime(day, this.state.value);
        this.updateValue(newValue, true);
    };
    handleShortcutClick = (shortcut, selectedShortcutIndex) => {
        const { onShortcutChange, selectedShortcutIndex: currentShortcutIndex } = this.props;
        const { dateRange, includeTime } = shortcut;
        const newDate = dateRange[0];
        const newValue = includeTime ? newDate : common_1.DateUtils.getDateTime(newDate, this.state.value);
        if (newDate == null) {
            return;
        }
        this.updateDay(newDate);
        this.updateValue(newValue, true);
        if (currentShortcutIndex === undefined) {
            this.setState({ selectedShortcutIndex });
        }
        const datePickerShortcut = { ...shortcut, date: newDate };
        onShortcutChange?.(datePickerShortcut, selectedShortcutIndex);
    };
    updateDay = (day) => {
        if (this.props.value === undefined) {
            // set now if uncontrolled, otherwise they'll be updated in `componentDidUpdate`
            this.setState({
                displayMonth: day.getMonth(),
                displayYear: day.getFullYear(),
                selectedDay: day.getDate(),
            });
        }
        if (this.state.value != null && this.state.value.getMonth() !== day.getMonth()) {
            this.ignoreNextMonthChange = true;
        }
    };
    computeValidDateInSpecifiedMonthYear(displayYear, displayMonth) {
        const { minDate, maxDate } = this.props;
        const { selectedDay } = this.state;
        // month is 0-based, date is 1-based. date 0 is last day of previous month.
        const maxDaysInMonth = new Date(displayYear, displayMonth + 1, 0).getDate();
        const displayDate = selectedDay == null ? 1 : Math.min(selectedDay, maxDaysInMonth);
        // 12:00 matches the underlying react-day-picker timestamp behavior
        const value = common_1.DateUtils.getDateTime(new Date(displayYear, displayMonth, displayDate, 12), this.state.value);
        // clamp between min and max dates
        if (value != null && value < minDate) {
            return minDate;
        }
        else if (value != null && value > maxDate) {
            return maxDate;
        }
        return value;
    }
    handleClearClick = () => this.updateValue(null, true);
    handleMonthChange = (newDate) => {
        const date = this.computeValidDateInSpecifiedMonthYear(newDate.getFullYear(), newDate.getMonth());
        if (date != null) {
            this.setState({ displayMonth: date.getMonth(), displayYear: date.getFullYear() });
            this.props.dayPickerProps?.onMonthChange?.(date);
        }
        if (this.state.value !== null) {
            // if handleDayClick just got run (so this flag is set), then the
            // user selected a date in a new month, so don't invoke onChange a
            // second time
            this.updateValue(date, false, this.ignoreNextMonthChange);
            this.ignoreNextMonthChange = false;
        }
    };
    handleTodayClick = () => {
        const { timezone } = this.props;
        const today = new Date();
        const value = timezone != null ? common_1.TimezoneUtils.convertLocalDateToTimezoneTime(today, timezone) : today;
        const displayMonth = value.getMonth();
        const displayYear = value.getFullYear();
        const selectedDay = value.getDate();
        this.setState({ displayMonth, displayYear, selectedDay });
        this.updateValue(value, true);
    };
    handleTimeChange = (time) => {
        this.props.timePickerProps?.onChange?.(time);
        const { value } = this.state;
        const newValue = common_1.DateUtils.getDateTime(value != null ? value : new Date(), time);
        this.updateValue(newValue, true);
    };
    /**
     * Update `value` by invoking `onChange` (always) and setting state (if uncontrolled).
     */
    updateValue(value, isUserChange, skipOnChange = false) {
        if (!skipOnChange) {
            this.props.onChange?.(value, isUserChange);
        }
        if (this.props.value === undefined) {
            this.setState({ value });
        }
    }
}
exports.DatePicker = DatePicker;
function getInitialValue(props) {
    // !== because `null` is a valid value (no date)
    if (props.value !== undefined) {
        return props.value;
    }
    if (props.defaultValue !== undefined) {
        return props.defaultValue;
    }
    return null;
}
function getInitialMonth(props, value) {
    const rangeFromProps = [props.minDate ?? null, props.maxDate ?? null];
    const today = new Date();
    // != because we must have a real `Date` to begin the calendar on.
    if (props.initialMonth != null) {
        return props.initialMonth;
    }
    else if (value != null) {
        return value;
    }
    else if (common_1.DateUtils.isDayInRange(today, rangeFromProps)) {
        return today;
    }
    else {
        return common_1.DateUtils.getDateBetween(rangeFromProps);
    }
}
function isTodayEnabled(minDate, maxDate) {
    const today = new Date();
    return common_1.DateUtils.isDayInRange(today, [minDate, maxDate]);
}
//# sourceMappingURL=datePicker.js.map