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
exports.isTimeEqualOrSmallerThan = exports.isTimeEqualOrGreaterThan = exports.isSameDay = void 0;
exports.clone = clone;
exports.isDateValid = isDateValid;
exports.isEqual = isEqual;
exports.areRangesEqual = areRangesEqual;
exports.isSameMonth = isSameMonth;
exports.isSameTime = isSameTime;
exports.isDayInRange = isDayInRange;
exports.isDayRangeInRange = isDayRangeInRange;
exports.isMonthInRange = isMonthInRange;
exports.isTimeInRange = isTimeInRange;
exports.getTimeInRange = getTimeInRange;
exports.isTimeSameOrAfter = isTimeSameOrAfter;
exports.getDateBetween = getDateBetween;
exports.getDateTime = getDateTime;
exports.getDateOnlyWithTime = getDateOnlyWithTime;
exports.getDatePreviousMonth = getDatePreviousMonth;
exports.getDateNextMonth = getDateNextMonth;
exports.convert24HourMeridiem = convert24HourMeridiem;
exports.getIsPmFrom24Hour = getIsPmFrom24Hour;
exports.get12HourFrom24Hour = get12HourFrom24Hour;
exports.get24HourFrom12Hour = get24HourFrom12Hour;
exports.isToday = isToday;
exports.hasMonthChanged = hasMonthChanged;
exports.hasTimeChanged = hasTimeChanged;
const date_fns_1 = require("date-fns");
Object.defineProperty(exports, "isSameDay", { enumerable: true, get: function () { return date_fns_1.isSameDay; } });
const dateRange_1 = require("./dateRange");
const months_1 = require("./months");
function clone(d) {
    return new Date(d.getTime());
}
function isDateValid(date) {
    return date instanceof Date && !isNaN(date.valueOf());
}
function isEqual(date1, date2) {
    if (date1 == null && date2 == null) {
        return true;
    }
    else if (date1 == null || date2 == null) {
        return false;
    }
    else {
        return date1.getTime() === date2.getTime();
    }
}
function areRangesEqual(dateRange1, dateRange2) {
    if (dateRange1 == null && dateRange2 == null) {
        return true;
    }
    else if (dateRange1 == null || dateRange2 == null) {
        return false;
    }
    else {
        const [start1, end1] = dateRange1;
        const [start2, end2] = dateRange2;
        const areStartsEqual = (start1 == null && start2 == null) || (start1 != null && start2 != null && (0, date_fns_1.isSameDay)(start1, start2));
        const areEndsEqual = (end1 == null && end2 == null) || (end1 != null && end2 != null && (0, date_fns_1.isSameDay)(end1, end2));
        return areStartsEqual && areEndsEqual;
    }
}
function isSameMonth(date1, date2) {
    return (date1 != null &&
        date2 != null &&
        date1.getMonth() === date2.getMonth() &&
        date1.getFullYear() === date2.getFullYear());
}
function isSameTime(d1, d2) {
    // N.B. do not use date-fns helper fns here, since we don't want to return false when the month/day/year is different
    return (d1 != null &&
        d2 != null &&
        d1.getHours() === d2.getHours() &&
        d1.getMinutes() === d2.getMinutes() &&
        d1.getSeconds() === d2.getSeconds() &&
        d1.getMilliseconds() === d2.getMilliseconds());
}
function isDayInRange(date, dateRange, exclusive = false) {
    if (date == null || !(0, dateRange_1.isNonNullRange)(dateRange)) {
        return false;
    }
    const day = clone(date);
    const start = clone(dateRange[0]);
    const end = clone(dateRange[1]);
    day.setHours(0, 0, 0, 0);
    start.setHours(0, 0, 0, 0);
    end.setHours(0, 0, 0, 0);
    return start <= day && day <= end && (!exclusive || (!(0, date_fns_1.isSameDay)(start, day) && !(0, date_fns_1.isSameDay)(day, end)));
}
function isDayRangeInRange(innerRange, outerRange) {
    return ((innerRange[0] == null || isDayInRange(innerRange[0], outerRange)) &&
        (innerRange[1] == null || isDayInRange(innerRange[1], outerRange)));
}
function isMonthInRange(date, dateRange) {
    if (date == null) {
        return false;
    }
    if (!(0, dateRange_1.isNonNullRange)(dateRange)) {
        return false;
    }
    const day = clone(date);
    const start = clone(dateRange[0]);
    const end = clone(dateRange[1]);
    day.setDate(1);
    start.setDate(1);
    end.setDate(1);
    day.setHours(0, 0, 0, 0);
    start.setHours(0, 0, 0, 0);
    end.setHours(0, 0, 0, 0);
    return start <= day && day <= end;
}
const isTimeEqualOrGreaterThan = (time, timeToCompare) => time.getTime() >= timeToCompare.getTime();
exports.isTimeEqualOrGreaterThan = isTimeEqualOrGreaterThan;
const isTimeEqualOrSmallerThan = (time, timeToCompare) => time.getTime() <= timeToCompare.getTime();
exports.isTimeEqualOrSmallerThan = isTimeEqualOrSmallerThan;
function isTimeInRange(date, minDate, maxDate) {
    const time = getDateOnlyWithTime(date);
    const minTime = getDateOnlyWithTime(minDate);
    const maxTime = getDateOnlyWithTime(maxDate);
    const isTimeGreaterThanMinTime = (0, exports.isTimeEqualOrGreaterThan)(time, minTime);
    const isTimeSmallerThanMaxTime = (0, exports.isTimeEqualOrSmallerThan)(time, maxTime);
    if ((0, exports.isTimeEqualOrSmallerThan)(maxTime, minTime)) {
        return isTimeGreaterThanMinTime || isTimeSmallerThanMaxTime;
    }
    return isTimeGreaterThanMinTime && isTimeSmallerThanMaxTime;
}
function getTimeInRange(time, minTime, maxTime) {
    if (isSameTime(minTime, maxTime)) {
        return maxTime;
    }
    else if (isTimeInRange(time, minTime, maxTime)) {
        return time;
    }
    else if (isTimeSameOrAfter(time, maxTime)) {
        return maxTime;
    }
    return minTime;
}
/**
 * Returns true if the time part of `date` is later than or equal to the time
 * part of `dateToCompare`. The day, month, and year parts will not be compared.
 */
function isTimeSameOrAfter(date, dateToCompare) {
    const time = getDateOnlyWithTime(date);
    const timeToCompare = getDateOnlyWithTime(dateToCompare);
    return (0, exports.isTimeEqualOrGreaterThan)(time, timeToCompare);
}
/**
 * @returns a Date at the exact time-wise midpoint between startDate and endDate
 *
 *  TODO: Convert `dateRange` argument to a NonNullDateRange to avoid non-null assertions
 *  see: https://github.com/palantir/blueprint/pull/7337#discussion_r1990189512
 */
function getDateBetween(dateRange) {
    const start = dateRange[0].getTime();
    const end = dateRange[1].getTime();
    const middle = start + (end - start) * 0.5;
    return new Date(middle);
}
function getDateTime(date, time) {
    if (date == null) {
        return null;
    }
    else if (time == null) {
        // cannot use default argument because `null` is a common value in this package.
        return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
    }
    else {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate(), time.getHours(), time.getMinutes(), time.getSeconds(), time.getMilliseconds());
    }
}
function getDateOnlyWithTime(date) {
    return new Date(0, 0, 0, date.getHours(), date.getMinutes(), date.getSeconds(), date.getMilliseconds());
}
function getDatePreviousMonth(date) {
    if (date.getMonth() === months_1.Months.JANUARY) {
        return new Date(date.getFullYear() - 1, months_1.Months.DECEMBER);
    }
    else {
        return new Date(date.getFullYear(), date.getMonth() - 1);
    }
}
function getDateNextMonth(date) {
    if (date.getMonth() === months_1.Months.DECEMBER) {
        return new Date(date.getFullYear() + 1, months_1.Months.JANUARY);
    }
    else {
        return new Date(date.getFullYear(), date.getMonth() + 1);
    }
}
function convert24HourMeridiem(hour, toPm) {
    if (hour < 0 || hour > 23) {
        throw new Error(`hour must be between [0,23] inclusive: got ${hour}`);
    }
    return toPm ? (hour % 12) + 12 : hour % 12;
}
function getIsPmFrom24Hour(hour) {
    if (hour < 0 || hour > 23) {
        throw new Error(`hour must be between [0,23] inclusive: got ${hour}`);
    }
    return hour >= 12;
}
function get12HourFrom24Hour(hour) {
    if (hour < 0 || hour > 23) {
        throw new Error(`hour must be between [0,23] inclusive: got ${hour}`);
    }
    const newHour = hour % 12;
    return newHour === 0 ? 12 : newHour;
}
function get24HourFrom12Hour(hour, isPm) {
    if (hour < 1 || hour > 12) {
        throw new Error(`hour must be between [1,12] inclusive: got ${hour}`);
    }
    const newHour = hour === 12 ? 0 : hour;
    return isPm ? newHour + 12 : newHour;
}
function isToday(date) {
    return (0, date_fns_1.isSameDay)(date, new Date());
}
function hasMonthChanged(prevDate, nextDate) {
    return (prevDate == null) !== (nextDate == null) || nextDate?.getMonth() !== prevDate?.getMonth();
}
function hasTimeChanged(prevDate, nextDate) {
    return ((prevDate == null) !== (nextDate == null) ||
        nextDate?.getHours() !== prevDate?.getHours() ||
        nextDate?.getMinutes() !== prevDate?.getMinutes() ||
        nextDate?.getSeconds() !== prevDate?.getSeconds() ||
        nextDate?.getMilliseconds() !== prevDate?.getMilliseconds());
}
//# sourceMappingURL=dateUtils.js.map