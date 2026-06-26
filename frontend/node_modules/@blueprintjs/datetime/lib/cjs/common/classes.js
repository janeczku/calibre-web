"use strict";
/*
 * Copyright 2015 Palantir Technologies, Inc. All rights reserved.
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.DATERANGEPICKER3_HOVERED_RANGE = exports.DateRangePickerClasses = exports.DATEPICKER3_REVERSE_MONTH_AND_YEAR = exports.DATEPICKER3_HIGHLIGHT_CURRENT_DAY = exports.DATEPICKER3_DAY_SELECTED = exports.DATEPICKER3_DAY_OUTSIDE = exports.DATEPICKER3_DAY_IS_TODAY = exports.DATEPICKER3_DAY_DISABLED = exports.DATEPICKER3_DAY = exports.DatePickerClasses = exports.DATEPICKER3_NAV_BUTTON_PREVIOUS = exports.DATEPICKER3_NAV_BUTTON_NEXT = exports.DATEPICKER3_NAV_BUTTON = exports.DATEPICKER3_DROPDOWN_YEAR = exports.DATEPICKER3_DROPDOWN_MONTH = exports.DATEPICKER3_CAPTION = exports.DatePickerCaptionClasses = exports.ReactDayPickerClasses = exports.TIMEZONE_SELECT_POPOVER = exports.TIMEZONE_SELECT = exports.TIMEPICKER_AMPM_SELECT = exports.TIMEPICKER_SECOND = exports.TIMEPICKER_MINUTE = exports.TIMEPICKER_MILLISECOND = exports.TIMEPICKER_INPUT_ROW = exports.TIMEPICKER_INPUT = exports.TIMEPICKER_HOUR = exports.TIMEPICKER_DIVIDER_TEXT = exports.TIMEPICKER_ARROW_ROW = exports.TIMEPICKER_ARROW_BUTTON = exports.TIMEPICKER = exports.DATE_RANGE_INPUT_POPOVER = exports.DATE_RANGE_INPUT = exports.DATERANGEPICKER_TIMEPICKERS = exports.DATERANGEPICKER_SHORTCUTS = exports.DATERANGEPICKER_SINGLE_MONTH = exports.DATERANGEPICKER_CONTIGUOUS = exports.DATERANGEPICKER_CALENDARS = exports.DATERANGEPICKER = exports.DATEPICKER_TIMEPICKER_WRAPPER = exports.DATEPICKER_YEAR_SELECT = exports.DATEPICKER_MONTH_SELECT = exports.DATEPICKER_FOOTER = exports.DATEPICKER_CONTENT = exports.DATEPICKER_CAPTION_MEASURE = exports.DATEPICKER_CAPTION = exports.DATEPICKER = exports.DATE_INPUT_TIMEZONE_SELECT = exports.DATE_INPUT_POPOVER = exports.DATE_INPUT = void 0;
exports.dayPickerClassNameOverrides = exports.DATERANGEPICKER3_TIMEPICKERS_STACKED = exports.DATERANGEPICKER3_SELECTED_RANGE_START = exports.DATERANGEPICKER3_SELECTED_RANGE_MIDDLE = exports.DATERANGEPICKER3_SELECTED_RANGE_END = exports.DATERANGEPICKER3_REVERSE_MONTH_AND_YEAR = exports.DATERANGEPICKER3_HOVERED_RANGE_START = exports.DATERANGEPICKER3_HOVERED_RANGE_END = void 0;
const tslib_1 = require("tslib");
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const core_1 = require("@blueprintjs/core");
const NS = core_1.Classes.getClassNamespace();
exports.DATE_INPUT = `${NS}-date-input`;
exports.DATE_INPUT_POPOVER = `${NS}-date-input-popover`;
exports.DATE_INPUT_TIMEZONE_SELECT = `${NS}-date-input-timezone-select`;
exports.DATEPICKER = `${NS}-datepicker`;
exports.DATEPICKER_CAPTION = `${exports.DATEPICKER}-caption`;
exports.DATEPICKER_CAPTION_MEASURE = `${exports.DATEPICKER_CAPTION}-measure`;
exports.DATEPICKER_CONTENT = `${exports.DATEPICKER}-content`;
exports.DATEPICKER_FOOTER = `${exports.DATEPICKER}-footer`;
exports.DATEPICKER_MONTH_SELECT = `${exports.DATEPICKER}-month-select`;
exports.DATEPICKER_YEAR_SELECT = `${exports.DATEPICKER}-year-select`;
exports.DATEPICKER_TIMEPICKER_WRAPPER = `${exports.DATEPICKER}-timepicker-wrapper`;
exports.DATERANGEPICKER = `${NS}-daterangepicker`;
exports.DATERANGEPICKER_CALENDARS = `${exports.DATERANGEPICKER}-calendars`;
exports.DATERANGEPICKER_CONTIGUOUS = `${exports.DATERANGEPICKER}-contiguous`;
exports.DATERANGEPICKER_SINGLE_MONTH = `${exports.DATERANGEPICKER}-single-month`;
exports.DATERANGEPICKER_SHORTCUTS = `${exports.DATERANGEPICKER}-shortcuts`;
exports.DATERANGEPICKER_TIMEPICKERS = `${exports.DATERANGEPICKER}-timepickers`;
exports.DATE_RANGE_INPUT = `${NS}-date-range-input`;
exports.DATE_RANGE_INPUT_POPOVER = `${NS}-date-range-input-popover`;
exports.TIMEPICKER = `${NS}-timepicker`;
exports.TIMEPICKER_ARROW_BUTTON = `${exports.TIMEPICKER}-arrow-button`;
exports.TIMEPICKER_ARROW_ROW = `${exports.TIMEPICKER}-arrow-row`;
exports.TIMEPICKER_DIVIDER_TEXT = `${exports.TIMEPICKER}-divider-text`;
exports.TIMEPICKER_HOUR = `${exports.TIMEPICKER}-hour`;
exports.TIMEPICKER_INPUT = `${exports.TIMEPICKER}-input`;
exports.TIMEPICKER_INPUT_ROW = `${exports.TIMEPICKER}-input-row`;
exports.TIMEPICKER_MILLISECOND = `${exports.TIMEPICKER}-millisecond`;
exports.TIMEPICKER_MINUTE = `${exports.TIMEPICKER}-minute`;
exports.TIMEPICKER_SECOND = `${exports.TIMEPICKER}-second`;
exports.TIMEPICKER_AMPM_SELECT = `${exports.TIMEPICKER}-ampm-select`;
exports.TIMEZONE_SELECT = `${NS}-timezone-select`;
exports.TIMEZONE_SELECT_POPOVER = `${exports.TIMEZONE_SELECT}-popover`;
const RDP = "rdp";
const RDP_DAY = `${RDP}-day`;
/** Class names applied by react-day-picker v8.x */
exports.ReactDayPickerClasses = {
    RDP,
    RDP_CAPTION: `${RDP}-caption`,
    RDP_CAPTION_DROPDOWNS: `${RDP}-caption_dropdowns`,
    RDP_CAPTION_LABEL: `${RDP}-caption_label`,
    RDP_DAY,
    RDP_DAY_DISABLED: `${RDP_DAY}_disabled`,
    RDP_DAY_HOVERED_RANGE: `${RDP_DAY}_hovered`,
    RDP_DAY_HOVERED_RANGE_END: `${RDP_DAY}_hovered_end`,
    RDP_DAY_HOVERED_RANGE_START: `${RDP_DAY}_hovered_start`,
    RDP_DAY_OUTSIDE: `${RDP_DAY}_outside`,
    RDP_DAY_RANGE_END: `${RDP_DAY}_range_end`,
    RDP_DAY_RANGE_MIDDLE: `${RDP_DAY}_range_middle`,
    RDP_DAY_RANGE_START: `${RDP_DAY}_range_start`,
    RDP_DAY_SELECTED: `${RDP_DAY}_selected`,
    RDP_DAY_TODAY: `${RDP_DAY}_today`,
    RDP_MONTH: `${RDP}-month`,
    RDP_NAV: `${RDP}-nav`,
    RDP_TABLE: `${RDP}-table`,
    RDP_VHIDDEN: `${RDP}-vhidden`,
};
exports.DatePickerCaptionClasses = {
    DATEPICKER3_CAPTION: exports.DATEPICKER_CAPTION,
    DATEPICKER3_DROPDOWN_MONTH: exports.DATEPICKER_MONTH_SELECT,
    DATEPICKER3_DROPDOWN_YEAR: exports.DATEPICKER_YEAR_SELECT,
    DATEPICKER3_NAV_BUTTON: `${exports.DATEPICKER}-nav-button`,
    DATEPICKER3_NAV_BUTTON_NEXT: `${exports.DATEPICKER}-nav-button-next`,
    DATEPICKER3_NAV_BUTTON_PREVIOUS: `${exports.DATEPICKER}-nav-button-previous`,
};
exports.DATEPICKER3_CAPTION = exports.DatePickerCaptionClasses.DATEPICKER3_CAPTION, exports.DATEPICKER3_DROPDOWN_MONTH = exports.DatePickerCaptionClasses.DATEPICKER3_DROPDOWN_MONTH, exports.DATEPICKER3_DROPDOWN_YEAR = exports.DatePickerCaptionClasses.DATEPICKER3_DROPDOWN_YEAR, exports.DATEPICKER3_NAV_BUTTON = exports.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON, exports.DATEPICKER3_NAV_BUTTON_NEXT = exports.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON_NEXT, exports.DATEPICKER3_NAV_BUTTON_PREVIOUS = exports.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON_PREVIOUS;
exports.DatePickerClasses = {
    DATEPICKER3_DAY: RDP_DAY,
    DATEPICKER3_DAY_DISABLED: exports.ReactDayPickerClasses.RDP_DAY_DISABLED,
    DATEPICKER3_DAY_IS_TODAY: exports.ReactDayPickerClasses.RDP_DAY_TODAY,
    DATEPICKER3_DAY_OUTSIDE: exports.ReactDayPickerClasses.RDP_DAY_OUTSIDE,
    DATEPICKER3_DAY_SELECTED: exports.ReactDayPickerClasses.RDP_DAY_SELECTED,
    DATEPICKER3_HIGHLIGHT_CURRENT_DAY: `${exports.DATEPICKER}-highlight-current-day`,
    DATEPICKER3_REVERSE_MONTH_AND_YEAR: `${exports.DATEPICKER}-reverse-month-and-year`,
};
exports.DATEPICKER3_DAY = exports.DatePickerClasses.DATEPICKER3_DAY, exports.DATEPICKER3_DAY_DISABLED = exports.DatePickerClasses.DATEPICKER3_DAY_DISABLED, exports.DATEPICKER3_DAY_IS_TODAY = exports.DatePickerClasses.DATEPICKER3_DAY_IS_TODAY, exports.DATEPICKER3_DAY_OUTSIDE = exports.DatePickerClasses.DATEPICKER3_DAY_OUTSIDE, exports.DATEPICKER3_DAY_SELECTED = exports.DatePickerClasses.DATEPICKER3_DAY_SELECTED, exports.DATEPICKER3_HIGHLIGHT_CURRENT_DAY = exports.DatePickerClasses.DATEPICKER3_HIGHLIGHT_CURRENT_DAY, exports.DATEPICKER3_REVERSE_MONTH_AND_YEAR = exports.DatePickerClasses.DATEPICKER3_REVERSE_MONTH_AND_YEAR;
exports.DateRangePickerClasses = {
    DATERANGEPICKER3_HOVERED_RANGE: exports.ReactDayPickerClasses.RDP_DAY_HOVERED_RANGE,
    DATERANGEPICKER3_HOVERED_RANGE_END: exports.ReactDayPickerClasses.RDP_DAY_HOVERED_RANGE_END,
    DATERANGEPICKER3_HOVERED_RANGE_START: exports.ReactDayPickerClasses.RDP_DAY_HOVERED_RANGE_START,
    DATERANGEPICKER3_REVERSE_MONTH_AND_YEAR: `${exports.DATERANGEPICKER}-reverse-month-and-year`,
    DATERANGEPICKER3_SELECTED_RANGE_END: exports.ReactDayPickerClasses.RDP_DAY_RANGE_END,
    DATERANGEPICKER3_SELECTED_RANGE_MIDDLE: exports.ReactDayPickerClasses.RDP_DAY_RANGE_MIDDLE,
    DATERANGEPICKER3_SELECTED_RANGE_START: exports.ReactDayPickerClasses.RDP_DAY_RANGE_START,
    DATERANGEPICKER3_TIMEPICKERS_STACKED: `${exports.DATERANGEPICKER_TIMEPICKERS}-stacked`,
};
exports.DATERANGEPICKER3_HOVERED_RANGE = exports.DateRangePickerClasses.DATERANGEPICKER3_HOVERED_RANGE, exports.DATERANGEPICKER3_HOVERED_RANGE_END = exports.DateRangePickerClasses.DATERANGEPICKER3_HOVERED_RANGE_END, exports.DATERANGEPICKER3_HOVERED_RANGE_START = exports.DateRangePickerClasses.DATERANGEPICKER3_HOVERED_RANGE_START, exports.DATERANGEPICKER3_REVERSE_MONTH_AND_YEAR = exports.DateRangePickerClasses.DATERANGEPICKER3_REVERSE_MONTH_AND_YEAR, exports.DATERANGEPICKER3_SELECTED_RANGE_END = exports.DateRangePickerClasses.DATERANGEPICKER3_SELECTED_RANGE_END, exports.DATERANGEPICKER3_SELECTED_RANGE_MIDDLE = exports.DateRangePickerClasses.DATERANGEPICKER3_SELECTED_RANGE_MIDDLE, exports.DATERANGEPICKER3_SELECTED_RANGE_START = exports.DateRangePickerClasses.DATERANGEPICKER3_SELECTED_RANGE_START, exports.DATERANGEPICKER3_TIMEPICKERS_STACKED = exports.DateRangePickerClasses.DATERANGEPICKER3_TIMEPICKERS_STACKED;
/**
 * Class name overrides for components rendered by react-day-picker. These offer more predictable and standard
 * DOM selectors in custom styles & tests.
 */
exports.dayPickerClassNameOverrides = {
    /* eslint-disable camelcase */
    button: (0, classnames_1.default)(core_1.Classes.BUTTON, core_1.Classes.MINIMAL),
    // no need for button "reset" styles since the core Button styles handle that for us
    button_reset: undefined,
    dropdown_month: exports.DatePickerCaptionClasses.DATEPICKER3_DROPDOWN_MONTH,
    dropdown_year: exports.DatePickerCaptionClasses.DATEPICKER3_DROPDOWN_YEAR,
    nav_button: exports.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON,
    nav_button_next: exports.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON_NEXT,
    nav_button_previous: exports.DatePickerCaptionClasses.DATEPICKER3_NAV_BUTTON_PREVIOUS,
    /* eslint-enable camelcase */
};
//# sourceMappingURL=classes.js.map