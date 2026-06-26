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
exports.DATEINPUT_INVALID_TIMEZONE = exports.DATEINPUT_INVALID_DEFAULT_TIMEZONE = exports.DATERANGEINPUT_NULL_VALUE = exports.DATERANGEPICKER_PREFERRED_BOUNDARY_TO_MODIFY_INVALID = exports.DATERANGEPICKER_VALUE_INVALID = exports.DATERANGEPICKER_MAX_DATE_INVALID = exports.DATERANGEPICKER_INITIAL_MONTH_INVALID = exports.DATERANGEPICKER_DEFAULT_VALUE_INVALID = exports.DATEPICKER_VALUE_INVALID = exports.DATEPICKER_MAX_DATE_INVALID = exports.DATEPICKER_INITIAL_MONTH_INVALID = exports.DATEPICKER_DEFAULT_VALUE_INVALID = void 0;
const ns = "[Blueprint]";
exports.DATEPICKER_DEFAULT_VALUE_INVALID = ns + ` <DatePicker> defaultValue must be within minDate and maxDate bounds.`;
exports.DATEPICKER_INITIAL_MONTH_INVALID = ns + ` <DatePicker> initialMonth must be within minDate and maxDate bounds.`;
exports.DATEPICKER_MAX_DATE_INVALID = ns + ` <DatePicker> maxDate must be later than minDate.`;
exports.DATEPICKER_VALUE_INVALID = ns + ` <DatePicker> value prop must be within minDate and maxDate bounds.`;
exports.DATERANGEPICKER_DEFAULT_VALUE_INVALID = exports.DATEPICKER_DEFAULT_VALUE_INVALID.replace("DatePicker", "DateRangePicker");
exports.DATERANGEPICKER_INITIAL_MONTH_INVALID = exports.DATEPICKER_INITIAL_MONTH_INVALID.replace("DatePicker", "DateRangePicker");
exports.DATERANGEPICKER_MAX_DATE_INVALID = exports.DATEPICKER_MAX_DATE_INVALID.replace("DatePicker", "DateRangePicker");
exports.DATERANGEPICKER_VALUE_INVALID = exports.DATEPICKER_VALUE_INVALID.replace("DatePicker", "DateRangePicker");
exports.DATERANGEPICKER_PREFERRED_BOUNDARY_TO_MODIFY_INVALID = "<DateRangePicker> preferredBoundaryToModify must be a valid Boundary if defined.";
exports.DATERANGEINPUT_NULL_VALUE = ns +
    ` <DateRangeInput> value cannot be null. Pass undefined to clear the value and operate in` +
    " uncontrolled mode, or pass [null, null] to clear the value and continue operating in controlled mode.";
exports.DATEINPUT_INVALID_DEFAULT_TIMEZONE = `${ns} <DateInput> was provided an invalid defaultTimezone, defaulting to Etc/UTC instead`;
exports.DATEINPUT_INVALID_TIMEZONE = `${ns} <DateInput> was provided an invalid timezone, defaulting to Etc/UTC instead`;
//# sourceMappingURL=errors.js.map