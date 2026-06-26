/*
 * Copyright 2016 Palantir Technologies, Inc. All rights reserved.
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
import { getDateNextMonth, getDatePreviousMonth } from "./dateUtils";
export class MonthAndYear {
    static fromDate(date) {
        return date == null ? undefined : new MonthAndYear(date.getMonth(), date.getFullYear());
    }
    date;
    constructor(month, year) {
        if (month != null && year != null) {
            this.date = new Date(year, month);
        }
        else {
            this.date = new Date();
        }
    }
    clone() {
        return new MonthAndYear(this.getMonth(), this.getYear());
    }
    getFullDate() {
        return this.date;
    }
    getMonth() {
        return this.date.getMonth();
    }
    getYear() {
        return this.date.getFullYear();
    }
    getPreviousMonth() {
        const previousMonthDate = getDatePreviousMonth(this.date);
        return new MonthAndYear(previousMonthDate.getMonth(), previousMonthDate.getFullYear());
    }
    getNextMonth() {
        const nextMonthDate = getDateNextMonth(this.date);
        return new MonthAndYear(nextMonthDate.getMonth(), nextMonthDate.getFullYear());
    }
    isBefore(monthAndYear) {
        return compareMonthAndYear(this, monthAndYear) < 0;
    }
    isAfter(monthAndYear) {
        return compareMonthAndYear(this, monthAndYear) > 0;
    }
    isSame(monthAndYear) {
        return compareMonthAndYear(this, monthAndYear) === 0;
    }
    isSameMonth(monthAndYear) {
        return this.getMonth() === monthAndYear.getMonth();
    }
}
// returns negative if left < right
// returns positive if left > right
// returns 0 if left === right
function compareMonthAndYear(firstMonthAndYear, secondMonthAndYear) {
    const firstMonth = firstMonthAndYear.getMonth();
    const firstYear = firstMonthAndYear.getYear();
    const secondMonth = secondMonthAndYear.getMonth();
    const secondYear = secondMonthAndYear.getYear();
    if (firstYear === secondYear) {
        return firstMonth - secondMonth;
    }
    else {
        return firstYear - secondYear;
    }
}
//# sourceMappingURL=monthAndYear.js.map