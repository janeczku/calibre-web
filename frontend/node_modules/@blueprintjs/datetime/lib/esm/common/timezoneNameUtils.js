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
import { formatInTimeZone } from "date-fns-tz";
import { getCurrentTimezone } from "./getTimezone";
import { MINIMAL_TIMEZONE_ITEMS, TIMEZONE_ITEMS } from "./timezoneItems";
const CURRENT_DATE = Date.now();
const LONG_NAME_FORMAT_STR = "zzzz";
const SHORT_NAME_FORMAT_STR = "zzz";
export function isValidTimezone(timeZone) {
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
export function getTimezoneShortName(tzIanaCode, date) {
    return formatInTimeZone(date ?? CURRENT_DATE, tzIanaCode, SHORT_NAME_FORMAT_STR);
}
/**
 * Augments a simple {@link Timezone} metadata object with long and short names formatted by `date-fns-tz`.
 */
export function getTimezoneNames(tz, date = CURRENT_DATE) {
    return {
        ...tz,
        longName: formatInTimeZone(date, tz.ianaCode, LONG_NAME_FORMAT_STR),
        shortName: formatInTimeZone(date, tz.ianaCode, SHORT_NAME_FORMAT_STR),
    };
}
export const mapTimezonesWithNames = (date, timezones) => timezones.map(tz => getTimezoneNames(tz, date));
export function getInitialTimezoneItems(date, showLocalTimezone) {
    const systemTimezone = getCurrentTimezone();
    const localTimezone = showLocalTimezone
        ? TIMEZONE_ITEMS.find(timezone => timezone.ianaCode === systemTimezone)
        : undefined;
    const localTimezoneItem = localTimezone !== undefined
        ? {
            ...localTimezone,
            longName: "Current timezone",
            shortName: formatInTimeZone(date ?? CURRENT_DATE, localTimezone.ianaCode, SHORT_NAME_FORMAT_STR),
        }
        : undefined;
    const minimalTimezoneItemsWithNames = mapTimezonesWithNames(date, MINIMAL_TIMEZONE_ITEMS).filter(tz => tz.ianaCode !== localTimezoneItem?.ianaCode);
    return localTimezoneItem === undefined
        ? minimalTimezoneItemsWithNames
        : [localTimezoneItem, ...minimalTimezoneItemsWithNames];
}
//# sourceMappingURL=timezoneNameUtils.js.map