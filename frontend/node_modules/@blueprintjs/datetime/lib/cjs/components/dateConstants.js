"use strict";
/* !
 * (c) Copyright 2025 Palantir Technologies Inc. All rights reserved.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.INVALID_DATE = exports.OVERLAPPING_DATES_MESSAGE = exports.OUT_OF_RANGE_MESSAGE = exports.INVALID_DATE_MESSAGE = exports.MIN_DATE = exports.MAX_DATE = exports.LOCALE = void 0;
const datePickerUtils_1 = require("./date-picker/datePickerUtils");
exports.LOCALE = "en-US";
exports.MAX_DATE = datePickerUtils_1.DatePickerUtils.getDefaultMaxDate();
exports.MIN_DATE = datePickerUtils_1.DatePickerUtils.getDefaultMinDate();
exports.INVALID_DATE_MESSAGE = "Invalid date";
exports.OUT_OF_RANGE_MESSAGE = "Out of range";
exports.OVERLAPPING_DATES_MESSAGE = "Overlapping dates";
exports.INVALID_DATE = new Date(undefined);
//# sourceMappingURL=dateConstants.js.map