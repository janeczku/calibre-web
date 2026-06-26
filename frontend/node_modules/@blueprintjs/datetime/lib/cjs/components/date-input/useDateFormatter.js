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
exports.useDateFormatter = useDateFormatter;
const react_1 = require("react");
const common_1 = require("../../common");
const dateFnsFormatUtils_1 = require("../../common/dateFnsFormatUtils");
const dateFnsLocaleProps_1 = require("../../common/dateFnsLocaleProps");
const dateConstants_1 = require("../dateConstants");
/**
 * Create a date string parser function based on a given locale.
 *
 * Prefer using user-provided `props.formatDate` and `props.dateFnsFormat` if available, otherwise fall back to
 * default formats inferred from time picker props.
 */
function useDateFormatter(props, locale) {
    const { dateFnsFormat, locale: localeFromProps, formatDate, invalidDateMessage = dateConstants_1.INVALID_DATE_MESSAGE, maxDate = dateConstants_1.MAX_DATE, minDate = dateConstants_1.MIN_DATE, outOfRangeMessage = dateConstants_1.OUT_OF_RANGE_MESSAGE, timePickerProps, timePrecision, } = props;
    return (0, react_1.useCallback)((date) => {
        if (date === undefined) {
            return "";
        }
        if (!common_1.DateUtils.isDateValid(date)) {
            return invalidDateMessage;
        }
        else if (common_1.DateUtils.isDayInRange(date, [minDate, maxDate])) {
            if (formatDate !== undefined) {
                // user-provided date formatter
                return formatDate(date, locale?.code ?? (0, dateFnsLocaleProps_1.getLocaleCodeFromProps)(localeFromProps));
            }
            else {
                // use user-provided date-fns format or one of the default formats inferred from time picker props
                const format = dateFnsFormat ?? (0, dateFnsFormatUtils_1.getDefaultDateFnsFormat)({ timePickerProps, timePrecision });
                return (0, dateFnsFormatUtils_1.getDateFnsFormatter)(format, locale)(date);
            }
        }
        else {
            return outOfRangeMessage;
        }
    }, [
        dateFnsFormat,
        formatDate,
        invalidDateMessage,
        locale,
        localeFromProps,
        maxDate,
        minDate,
        outOfRangeMessage,
        timePickerProps,
        timePrecision,
    ]);
}
//# sourceMappingURL=useDateFormatter.js.map