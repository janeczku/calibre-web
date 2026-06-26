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
exports.DatePickerUtils = void 0;
exports.getDefaultMaxDate = getDefaultMaxDate;
exports.getDefaultMinDate = getDefaultMinDate;
const common_1 = require("../../common");
const dateFormatProps_1 = require("../../common/dateFormatProps");
const utils_1 = require("../../common/utils");
function getDefaultMaxDate() {
    const date = new Date();
    date.setMonth(date.getMonth() + 6);
    return date;
}
function getDefaultMinDate() {
    const date = new Date();
    date.setFullYear(date.getFullYear() - 20);
    date.setMonth(common_1.Months.JANUARY, 1);
    return date;
}
/**
 * DatePicker-related utility functions which may be useful outside this package to
 * build date/time components.
 */
exports.DatePickerUtils = {
    getDefaultMaxDate,
    getDefaultMinDate,
    getFormattedDateString: dateFormatProps_1.getFormattedDateString,
    measureTextWidth: utils_1.measureTextWidth,
};
//# sourceMappingURL=datePickerUtils.js.map