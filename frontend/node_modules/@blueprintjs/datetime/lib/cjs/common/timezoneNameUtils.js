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
exports.mapTimezonesWithNames = void 0;
exports.isValidTimezone = isValidTimezone;
exports.getTimezoneShortName = getTimezoneShortName;
exports.getTimezoneNames = getTimezoneNames;
exports.getInitialTimezoneItems = getInitialTimezoneItems;
const date_fns_tz_1 = require("date-fns-tz");
const getTimezone_1 = require("./getTimezone");
const timezoneItems_1 = require("./timezoneItems");
const CURRENT_DATE = Date.now();
const LONG_NAME_FORMAT_STR = "zzzz";
const SHORT_NAME_FORMAT_STR = "zzz";
function isValidTimezone(timeZone) {
    if (timeZone === undefined) {
        return false;
    }
    try {
        Intl.DateTimeFormat(undefined, { timeZone });
        return true;
    }
    catch (e) {
        return false;
    }
}
function getTimezoneShortName(tzIanaCode, date) {
    return (0, date_fns_tz_1.formatInTimeZone)(date ?? CURRENT_DATE, tzIanaCode, SHORT_NAME_FORMAT_STR);
}
/**
 * Augments a simple {@link Timezone} metadata object with long and short names formatted by `date-fns-tz`.
 */
function getTimezoneNames(tz, date = CURRENT_DATE) {
    return {
        ...tz,
        longName: (0, date_fns_tz_1.formatInTimeZone)(date, tz.ianaCode, LONG_NAME_FORMAT_STR),
        shortName: (0, date_fns_tz_1.formatInTimeZone)(date, tz.ianaCode, SHORT_NAME_FORMAT_STR),
    };
}
const mapTimezonesWithNames = (date, timezones) => timezones.map(tz => getTimezoneNames(tz, date));
exports.mapTimezonesWithNames = mapTimezonesWithNames;
function getInitialTimezoneItems(date, showLocalTimezone) {
    const systemTimezone = (0, getTimezone_1.getCurrentTimezone)();
    const localTimezone = showLocalTimezone
        ? timezoneItems_1.TIMEZONE_ITEMS.find(timezone => timezone.ianaCode === systemTimezone)
        : undefined;
    const localTimezoneItem = localTimezone !== undefined
        ? {
            ...localTimezone,
            longName: "Current timezone",
            shortName: (0, date_fns_tz_1.formatInTimeZone)(date ?? CURRENT_DATE, localTimezone.ianaCode, SHORT_NAME_FORMAT_STR),
        }
        : undefined;
    const minimalTimezoneItemsWithNames = (0, exports.mapTimezonesWithNames)(date, timezoneItems_1.MINIMAL_TIMEZONE_ITEMS).filter(tz => tz.ianaCode !== localTimezoneItem?.ianaCode);
    return localTimezoneItem === undefined
        ? minimalTimezoneItemsWithNames
        : [localTimezoneItem, ...minimalTimezoneItemsWithNames];
}
//# sourceMappingURL=timezoneNameUtils.js.map