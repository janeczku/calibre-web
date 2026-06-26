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
import { Boundary } from "@blueprintjs/core";
import { isSameDay } from "./dateUtils";
/* eslint-disable-next-line @typescript-eslint/no-extraneous-class */
export class DateRangeSelectionStrategy {
    /**
     * Returns the new date-range and the boundary that would be affected if `day` were clicked. The
     * affected boundary may be different from the provided `boundary` in some cases. For example,
     * clicking a particular boundary's selected date will always deselect it regardless of which
     * `boundary` you provide to this function (because it's simply a more intuitive interaction).
     */
    static getNextState(currentRange, day, allowSingleDayRange, boundary) {
        if (boundary != null) {
            return this.getNextStateForBoundary(currentRange, day, allowSingleDayRange, boundary);
        }
        else {
            return this.getDefaultNextState(currentRange, day, allowSingleDayRange);
        }
    }
    static getNextStateForBoundary(currentRange, day, allowSingleDayRange, boundary) {
        const boundaryDate = this.getBoundaryDate(boundary, currentRange);
        const otherBoundary = this.getOtherBoundary(boundary);
        const otherBoundaryDate = this.getBoundaryDate(otherBoundary, currentRange);
        let nextBoundary;
        let nextDateRange;
        if (boundaryDate == null && otherBoundaryDate == null) {
            nextBoundary = boundary;
            nextDateRange = this.createRangeForBoundary(boundary, day, null);
        }
        else if (boundaryDate != null && otherBoundaryDate == null) {
            const nextBoundaryDate = isSameDay(boundaryDate, day) ? null : day;
            nextBoundary = boundary;
            nextDateRange = this.createRangeForBoundary(boundary, nextBoundaryDate, null);
        }
        else if (boundaryDate == null && otherBoundaryDate != null) {
            if (isSameDay(day, otherBoundaryDate)) {
                let nextDate;
                if (allowSingleDayRange) {
                    nextBoundary = boundary;
                    nextDate = otherBoundaryDate;
                }
                else {
                    nextBoundary = otherBoundary;
                    nextDate = null;
                }
                nextDateRange = this.createRangeForBoundary(boundary, nextDate, nextDate);
            }
            else if (this.isOverlappingOtherBoundary(boundary, day, otherBoundaryDate)) {
                nextBoundary = otherBoundary;
                nextDateRange = this.createRangeForBoundary(boundary, otherBoundaryDate, day);
            }
            else {
                nextBoundary = boundary;
                nextDateRange = this.createRangeForBoundary(boundary, day, otherBoundaryDate);
            }
        }
        else {
            // both boundaryDate and otherBoundaryDate are already defined
            if (boundaryDate != null && isSameDay(boundaryDate, day)) {
                const isSingleDayRangeSelected = otherBoundaryDate != null && isSameDay(boundaryDate, otherBoundaryDate);
                const nextOtherBoundaryDate = isSingleDayRangeSelected ? null : otherBoundaryDate;
                nextBoundary = boundary;
                nextDateRange = this.createRangeForBoundary(boundary, null, nextOtherBoundaryDate);
            }
            else if (otherBoundaryDate != null && isSameDay(day, otherBoundaryDate)) {
                const [nextBoundaryDate, nextOtherBoundaryDate] = allowSingleDayRange
                    ? [otherBoundaryDate, otherBoundaryDate]
                    : [boundaryDate, null];
                nextBoundary = allowSingleDayRange ? boundary : otherBoundary;
                nextDateRange = this.createRangeForBoundary(boundary, nextBoundaryDate, nextOtherBoundaryDate);
            }
            else if (otherBoundaryDate != null && this.isOverlappingOtherBoundary(boundary, day, otherBoundaryDate)) {
                nextBoundary = boundary;
                nextDateRange = this.createRangeForBoundary(boundary, day, null);
            }
            else {
                // extend the date range with an earlier boundaryDate date
                nextBoundary = boundary;
                nextDateRange = this.createRangeForBoundary(boundary, day, otherBoundaryDate);
            }
        }
        return { boundary: nextBoundary, dateRange: nextDateRange };
    }
    static getDefaultNextState(selectedRange, day, allowSingleDayRange) {
        const [start, end] = selectedRange;
        let nextDateRange;
        let nextBoundary = Boundary.START;
        if (start == null && end == null) {
            nextDateRange = [day, null];
        }
        else if (start != null && end == null) {
            nextDateRange = this.createRange(day, start, allowSingleDayRange);
            nextBoundary = Boundary.END;
        }
        else if (start == null && end != null) {
            nextDateRange = this.createRange(day, end, allowSingleDayRange);
        }
        else {
            const isStart = start != null && isSameDay(start, day);
            const isEnd = end != null && isSameDay(end, day);
            if (isStart && isEnd) {
                nextDateRange = [null, null];
            }
            else if (isStart) {
                nextDateRange = [null, end];
            }
            else if (isEnd) {
                nextDateRange = [start, null];
                nextBoundary = Boundary.END;
            }
            else {
                nextDateRange = [day, null];
            }
        }
        return { boundary: nextBoundary, dateRange: nextDateRange };
    }
    static getOtherBoundary(boundary) {
        return boundary === Boundary.START ? Boundary.END : Boundary.START;
    }
    static getBoundaryDate(boundary, dateRange) {
        return boundary === Boundary.START ? dateRange[0] : dateRange[1];
    }
    static isOverlappingOtherBoundary(boundary, boundaryDate, otherBoundaryDate) {
        return boundary === Boundary.START ? boundaryDate > otherBoundaryDate : boundaryDate < otherBoundaryDate;
    }
    static createRangeForBoundary(boundary, boundaryDate, otherBoundaryDate) {
        return boundary === Boundary.START
            ? [boundaryDate, otherBoundaryDate]
            : [otherBoundaryDate, boundaryDate];
    }
    static createRange(a, b, allowSingleDayRange) {
        // clicking the same date again will clear it
        if (!allowSingleDayRange && isSameDay(a, b)) {
            return [null, null];
        }
        return a < b ? [a, b] : [b, a];
    }
}
//# sourceMappingURL=dateRangeSelectionStrategy.js.map