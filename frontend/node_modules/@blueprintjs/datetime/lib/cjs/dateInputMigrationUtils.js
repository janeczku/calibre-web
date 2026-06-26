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
exports.onChangeAdapter = onChangeAdapter;
exports.valueAdapter = valueAdapter;
exports.defaultValueAdapter = defaultValueAdapter;
const date_fns_1 = require("date-fns");
const common_1 = require("./common");
/**
 * `onChange` prop adapter for automated DateInput -> DateInput2 migration in @blueprintjs/datetime2 v0.x.
 *
 * Note that we exclude `undefined` from the input & output types since we expect the callback to be defined
 * if this adapter is used.
 *
 * @param handler DateInput onChange handler
 * @returns DateInput2 onChange handler
 */
function onChangeAdapter(handler) {
    if (handler === undefined) {
        return noOp;
    }
    const tz = common_1.TimezoneUtils.getCurrentTimezone();
    return (newDate, isUserChange) => handler(common_1.TimezoneUtils.getDateObjectFromIsoString(newDate, tz) ?? null, isUserChange);
}
/**
 * `value` prop adapter for automated DateInput -> DateInput2 migration in @blueprintjs/datetime2 v0.x.
 *
 * @param value DateInput value
 * @param timePrecision (optional) DateInput timePrecision
 * @returns DateInput2 value
 */
function valueAdapter(value, timePrecision) {
    if (value == null || !(0, date_fns_1.isValid)(value)) {
        return null;
    }
    return convertDateToDateString(value, timePrecision);
}
/**
 * Adapter for automated DateInput -> DateInput2 migration in @blueprintjs/datetime2 v0.x.
 *
 * @param defaultValue DateInput value
 * @param timePrecision (optional) DateInput timePrecision
 * @returns DateInput2 value
 */
function defaultValueAdapter(defaultValue, timePrecision) {
    if (defaultValue === undefined || !(0, date_fns_1.isValid)(defaultValue)) {
        return undefined;
    }
    return convertDateToDateString(defaultValue, timePrecision);
}
function convertDateToDateString(date, timePrecision) {
    const tz = common_1.TimezoneUtils.getCurrentTimezone();
    const inferredTimePrecision = date.getMilliseconds() !== 0
        ? common_1.TimePrecision.MILLISECOND
        : date.getSeconds() !== 0
            ? common_1.TimePrecision.SECOND
            : date.getMinutes() !== 0
                ? common_1.TimePrecision.MINUTE
                : undefined;
    return common_1.TimezoneUtils.getIsoEquivalentWithUpdatedTimezone(date, tz, timePrecision ?? inferredTimePrecision);
}
function noOp() {
    // nothing
}
//# sourceMappingURL=dateInputMigrationUtils.js.map