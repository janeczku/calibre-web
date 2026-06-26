/*
 * Copyright 2018 Palantir Technologies, Inc. All rights reserved.
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
import { isDateValid, isDayInRange } from "./dateUtils";
export function getFormattedDateString(date, props, ignoreRange = false) {
    if (date == null) {
        return "";
    }
    else if (!isDateValid(date)) {
        return props.invalidDateMessage;
    }
    else if (ignoreRange || isDayInRange(date, [props.minDate ?? null, props.maxDate ?? null])) {
        return props.formatDate(date, props.locale);
    }
    else {
        return props.outOfRangeMessage;
    }
}
//# sourceMappingURL=dateFormatProps.js.map