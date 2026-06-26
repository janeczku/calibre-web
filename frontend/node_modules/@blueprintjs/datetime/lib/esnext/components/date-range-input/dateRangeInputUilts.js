/* !
 * (c) Copyright 2024 Palantir Technologies Inc. All rights reserved.
 */
const DAY_IN_MILLIS = 1000 * 60 * 60 * 24;
const WEEK_IN_MILLIS = 7 * DAY_IN_MILLIS;
export function getTodayAtMidnight() {
    return new Date(new Date().setHours(0, 0, 0, 0));
}
export function shiftDateByDays(date, days) {
    return new Date(date.valueOf() + days * DAY_IN_MILLIS);
}
export function shiftDateByWeeks(date, weeks) {
    return new Date(date.valueOf() + weeks * WEEK_IN_MILLIS);
}
export function shiftDateByArrowKey(date, key) {
    switch (key) {
        case "ArrowUp":
            return shiftDateByWeeks(date, -1);
        case "ArrowDown":
            return shiftDateByWeeks(date, 1);
        case "ArrowLeft":
            return shiftDateByDays(date, -1);
        case "ArrowRight":
            return shiftDateByDays(date, 1);
        default:
            return date;
    }
}
export function clampDate(date, minDate, maxDate) {
    let result = date;
    if (minDate != null && date < minDate) {
        result = minDate;
    }
    if (maxDate != null && date > maxDate) {
        result = maxDate;
    }
    return result;
}
export function isEntireInputSelected(element) {
    if (element == null) {
        return false;
    }
    return element.selectionStart === 0 && element.selectionEnd === element.value.length;
}
//# sourceMappingURL=dateRangeInputUilts.js.map