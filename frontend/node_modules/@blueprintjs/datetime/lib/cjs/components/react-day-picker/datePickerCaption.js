"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DatePickerCaption = void 0;
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
const react_1 = require("react");
const react_day_picker_1 = require("react-day-picker");
const react_innertext_1 = tslib_1.__importDefault(require("react-innertext"));
const core_1 = require("@blueprintjs/core");
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const classes_1 = require("../../common/classes");
const useMonthSelectRightOffset_1 = require("../../common/useMonthSelectRightOffset");
const datePickerContext_1 = require("../date-picker/datePickerContext");
/**
 * Custom react-day-picker caption component used in non-contiguous two-month date range pickers.
 *
 * We need to override the whole caption instead of its lower-level components because react-day-picker
 * does not have built-in support for non-contiguous range pickers.
 *
 * @see https://daypicker.dev/guides/custom-components
 */
const DatePickerCaption = (props) => {
    const { classNames: rdpClassNames, formatters, fromDate, toDate, labels } = (0, react_day_picker_1.useDayPicker)();
    const { locale, reverseMonthAndYearMenus } = (0, react_1.useContext)(datePickerContext_1.DatePickerContext);
    // non-null assertion because we define these values in defaultProps
    const minYear = fromDate.getFullYear();
    const maxYear = toDate.getFullYear();
    const displayMonth = props.displayMonth.getMonth();
    const displayYear = props.displayMonth.getFullYear();
    const containerElement = (0, react_1.useRef)(null);
    const monthSelectElement = (0, react_1.useRef)(null);
    const { currentMonth, goToMonth, nextMonth, previousMonth } = (0, react_day_picker_1.useNavigation)();
    const handlePreviousClick = (0, react_1.useCallback)(() => previousMonth && goToMonth(previousMonth), [previousMonth, goToMonth]);
    const handleNextClick = (0, react_1.useCallback)(() => nextMonth && goToMonth(nextMonth), [nextMonth, goToMonth]);
    const prevButton = ((0, jsx_runtime_1.jsx)(core_1.Button, { "aria-label": labels.labelPrevious(previousMonth, { locale }), className: (0, classnames_1.default)(classes_1.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON, classes_1.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON_PREVIOUS), disabled: !previousMonth, icon: (0, jsx_runtime_1.jsx)(icons_1.ChevronLeft, {}), onClick: handlePreviousClick, variant: "minimal" }));
    const nextButton = ((0, jsx_runtime_1.jsx)(core_1.Button, { "aria-label": labels.labelNext(nextMonth, { locale }), className: (0, classnames_1.default)(classes_1.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON, classes_1.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON_NEXT), disabled: !nextMonth, icon: (0, jsx_runtime_1.jsx)(icons_1.ChevronRight, {}), onClick: handleNextClick, variant: "minimal" }));
    // build the list of available years, relying on react-day-picker's default date-fns formatter or a
    // user-provided formatter to localize the year "names"
    const { formatYearCaption } = formatters;
    const allYearOptions = (0, react_1.useMemo)(() => {
        const years = [];
        for (let year = minYear; year <= maxYear; year++) {
            const yearDate = new Date(year, 0);
            const yearCaption = formatYearCaption(yearDate, { locale });
            years.push({ label: (0, react_innertext_1.default)(yearCaption), value: year });
        }
        return years;
    }, [formatYearCaption, maxYear, minYear, locale]);
    // allow out-of-bounds years but disable the option.
    // this handles the Dec 2016 case in https://github.com/palantir/blueprint/issues/391
    if (displayYear > maxYear) {
        const displayYearDate = new Date(displayYear, 0);
        const displayYearCaption = formatYearCaption(displayYearDate, { locale });
        allYearOptions.push({ disabled: true, label: (0, react_innertext_1.default)(displayYearCaption), value: displayYear });
    }
    const handleMonthSelectChange = (0, react_1.useCallback)((e) => {
        const newMonth = parseInt(e.target.value, 10);
        // ignore change events with invalid values to prevent crash on iOS Safari (#4178)
        if (isNaN(newMonth)) {
            return;
        }
        const newDate = common_1.DateUtils.clone(currentMonth);
        newDate.setMonth(newMonth);
        goToMonth(newDate);
    }, [currentMonth, goToMonth]);
    const startMonth = displayYear === minYear ? fromDate.getMonth() : 0;
    const endMonth = displayYear === maxYear ? toDate.getMonth() + 1 : 12;
    // build the list of available months, relying on react-day-picker's default date-fns formatter or a
    // user-provided formatter to localize the month names
    const { formatMonthCaption } = formatters;
    const allMonths = (0, react_1.useMemo)(() => {
        const months = [];
        for (let i = common_1.Months.JANUARY; i <= common_1.Months.DECEMBER; i++) {
            const monthDate = new Date(displayYear, i);
            const formattedMonth = formatMonthCaption(monthDate, { locale });
            months.push((0, react_innertext_1.default)(formattedMonth));
        }
        return months;
    }, [displayYear, formatMonthCaption, locale]);
    const allMonthOptions = allMonths.map((month, i) => ({ label: month, value: i }));
    const availableMonthOptions = allMonthOptions.slice(startMonth, endMonth);
    const displayedMonthText = allMonths[displayMonth];
    const monthSelectRightOffset = (0, useMonthSelectRightOffset_1.useMonthSelectRightOffset)(monthSelectElement, containerElement, displayedMonthText);
    const monthSelect = ((0, jsx_runtime_1.jsx)(core_1.HTMLSelect, { "aria-label": labels.labelMonthDropdown(), iconProps: { style: { right: monthSelectRightOffset } }, className: (0, classnames_1.default)(classes_1.DatePickerCaptionClasses.DATEPICKER3_DROPDOWN_MONTH, rdpClassNames.dropdown_month), minimal: true, onChange: handleMonthSelectChange, ref: monthSelectElement, value: displayMonth, options: availableMonthOptions }, "month"));
    const handleYearSelectChange = (0, react_1.useCallback)((e) => {
        const newYear = parseInt(e.target.value, 10);
        // ignore change events with invalid values to prevent crash on iOS Safari (#4178)
        if (isNaN(newYear)) {
            return;
        }
        const newDate = common_1.DateUtils.clone(currentMonth);
        newDate.setFullYear(newYear);
        goToMonth(newDate);
    }, [currentMonth, goToMonth]);
    const yearSelect = ((0, jsx_runtime_1.jsx)(core_1.HTMLSelect, { "aria-label": labels.labelYearDropdown(), className: (0, classnames_1.default)(classes_1.DatePickerCaptionClasses.DATEPICKER3_DROPDOWN_YEAR, rdpClassNames.dropdown_year), minimal: true, onChange: handleYearSelectChange, value: displayYear, options: allYearOptions }, "year"));
    const orderedSelects = reverseMonthAndYearMenus ? [yearSelect, monthSelect] : [monthSelect, yearSelect];
    const hiddenCaptionLabel = ((0, jsx_runtime_1.jsx)("div", { className: classes_1.ReactDayPickerClasses.RDP_VHIDDEN, children: (0, jsx_runtime_1.jsx)(react_day_picker_1.CaptionLabel, { displayMonth: props.displayMonth, id: props.id }) }));
    return ((0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(classes_1.DatePickerCaptionClasses.DATEPICKER3_CAPTION, rdpClassNames.caption), ref: containerElement, children: [hiddenCaptionLabel, prevButton, orderedSelects, nextButton] }));
};
exports.DatePickerCaption = DatePickerCaption;
exports.DatePickerCaption.displayName = `${core_1.DISPLAYNAME_PREFIX}.DatePickerCaption`;
//# sourceMappingURL=datePickerCaption.js.map