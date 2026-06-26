"use strict";
/*
 * Copyright 2022 Palantir Technologies, Inc. All rights reserved.
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
exports.UTC_TIME = exports.getCurrentTimezone = void 0;
exports.getIsoEquivalentWithUpdatedTimezone = getIsoEquivalentWithUpdatedTimezone;
exports.getDateObjectFromIsoString = getDateObjectFromIsoString;
exports.convertLocalDateToTimezoneTime = convertLocalDateToTimezoneTime;
exports.convertDateToLocalEquivalentOfTimezoneTime = convertDateToLocalEquivalentOfTimezoneTime;
const date_fns_tz_1 = require("date-fns-tz");
const getTimezone_1 = require("./getTimezone");
Object.defineProperty(exports, "getCurrentTimezone", { enumerable: true, get: function () { return getTimezone_1.getCurrentTimezone; } });
const timePrecision_1 = require("./timePrecision");
const timezoneItems_1 = require("./timezoneItems");
Object.defineProperty(exports, "UTC_TIME", { enumerable: true, get: function () { return timezoneItems_1.UTC_TIME; } });
const NO_TIME_PRECISION = "date";
const TIME_FORMAT_TO_ISO_FORMAT = {
    [timePrecision_1.TimePrecision.MILLISECOND]: "yyyy-MM-dd'T'HH:mm:ss.SSSxxx",
    [timePrecision_1.TimePrecision.SECOND]: "yyyy-MM-dd'T'HH:mm:ssxxx",
    [timePrecision_1.TimePrecision.MINUTE]: "yyyy-MM-dd'T'HH:mmxxx",
    [NO_TIME_PRECISION]: "yyyy-MM-dd",
};
/**
 * @see https://github.com/marnusw/date-fns-tz#formatintimezone
 * @returns a string of tokens which tell date-fns-tz's formatInTimeZone how to render a datetime
 */
function getFormatStr(timePrecision) {
    return TIME_FORMAT_TO_ISO_FORMAT[timePrecision ?? NO_TIME_PRECISION];
}
function getIsoEquivalentWithUpdatedTimezone(date, timezone, timePrecision) {
    const convertedDate = convertDateToLocalEquivalentOfTimezoneTime(date, timezone);
    return (0, date_fns_tz_1.formatInTimeZone)(convertedDate, timezone, getFormatStr(timePrecision));
}
function getDateObjectFromIsoString(value, timezone) {
    if (value === undefined) {
        return undefined;
    }
    // This function previously used lodash.isEmpty to check for empty values, which returns true for e.g. numbers and Dates.
    // Be extra defensive and avoid breakage in case a consumer is incorrectly passing in such a value.
    if (value === null || value === "" || typeof value !== "string") {
        return null;
    }
    const date = new Date(value);
    // If the value is just a date format then we convert it to midnight in local time to avoid weird things happening
    if (value.length === 10) {
        // If it's just a date, we know it's interpreted as midnight UTC so we convert it to local time of that UTC time
        return convertLocalDateToTimezoneTime(date, timezoneItems_1.UTC_TIME.ianaCode);
    }
    return convertLocalDateToTimezoneTime(date, timezone);
}
/**
 * Converts a date in local timezone to represent better the passed through timezone
 * representation for the user, meaning if 8 AM local time is currently the date, and local time is Oslo
 * and the user has a default of UTC in selection, the new date should represent 7 AM.
 *
 * @param date the current existing date object
 * @param newTimezone the new timezone that we need to update the date to represent
 * @returns The date converted to match the new timezone
 */
function convertLocalDateToTimezoneTime(date, newTimezone) {
    const nowUtc = (0, date_fns_tz_1.zonedTimeToUtc)(date, (0, getTimezone_1.getCurrentTimezone)());
    return (0, date_fns_tz_1.utcToZonedTime)(nowUtc, newTimezone);
}
/**
 * Converts a date to match a new timezone selection. The date is the internal local time
 * representation for the user, meaning if 8 AM local time is currently selected, and local time is Oslo
 * and the user switches timezone to UTC, the new date should represent 9 AM in Oslo time.
 *
 * @param date the current existing date object
 * @param newTimezone the new timezone that the date should be converted to represent
 * @returns The date converted to match the new timezone
 */
function convertDateToLocalEquivalentOfTimezoneTime(date, newTimezone) {
    const nowUtc = (0, date_fns_tz_1.zonedTimeToUtc)(date, newTimezone);
    return (0, date_fns_tz_1.utcToZonedTime)(nowUtc, (0, getTimezone_1.getCurrentTimezone)());
}
//# sourceMappingURL=timezoneUtils.js.map