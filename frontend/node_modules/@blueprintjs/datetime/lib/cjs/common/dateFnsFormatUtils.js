"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.DefaultDateFnsFormats = void 0;
exports.getDefaultDateFnsFormat = getDefaultDateFnsFormat;
exports.getDateFnsFormatter = getDateFnsFormatter;
exports.getDateFnsParser = getDateFnsParser;
const date_fns_1 = require("date-fns");
const timePrecision_1 = require("./timePrecision");
exports.DefaultDateFnsFormats = {
    DATE_ONLY: "yyyy-MM-dd",
    DATE_TIME_MILLISECONDS: "yyyy-MM-dd HH:mm:ss.SSS",
    DATE_TIME_MINUTES: "yyyy-MM-dd HH:mm",
    DATE_TIME_SECONDS: "yyyy-MM-dd HH:mm:ss",
};
function getDefaultDateFnsFormat(props) {
    const hasTimePickerProps = props.timePickerProps !== undefined && Object.keys(props.timePickerProps).length > 0;
    const precision = props.timePrecision ??
        props.timePickerProps?.precision ??
        // if timePickerProps is non-empty but has no precision defined, use the default value of "minute"
        (hasTimePickerProps ? timePrecision_1.TimePrecision.MINUTE : undefined);
    switch (precision) {
        case timePrecision_1.TimePrecision.MILLISECOND:
            return exports.DefaultDateFnsFormats.DATE_TIME_MILLISECONDS;
        case timePrecision_1.TimePrecision.MINUTE:
            return exports.DefaultDateFnsFormats.DATE_TIME_MINUTES;
        case timePrecision_1.TimePrecision.SECOND:
            return exports.DefaultDateFnsFormats.DATE_TIME_SECONDS;
        default:
            return exports.DefaultDateFnsFormats.DATE_ONLY;
    }
}
function getDateFnsFormatter(formatStr, locale) {
    return (date) => (0, date_fns_1.format)(date, formatStr, { locale });
}
function getDateFnsParser(formatStr, locale) {
    return (str) => (0, date_fns_1.parse)(str, formatStr, new Date(), { locale });
}
//# sourceMappingURL=dateFnsFormatUtils.js.map