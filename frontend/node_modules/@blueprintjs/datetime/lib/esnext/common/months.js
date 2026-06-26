/*
 * Copyright 2017 Palantir Technologies, Inc. All rights reserved.
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
/**
 * Enumeration of calendar months.
 *
 * Note that the enum values are numbers (with January as `0`) so they can be
 * easily compared to `date.getMonth()`.
 */
export var Months;
(function (Months) {
    Months[Months["JANUARY"] = 0] = "JANUARY";
    Months[Months["FEBRUARY"] = 1] = "FEBRUARY";
    Months[Months["MARCH"] = 2] = "MARCH";
    Months[Months["APRIL"] = 3] = "APRIL";
    Months[Months["MAY"] = 4] = "MAY";
    Months[Months["JUNE"] = 5] = "JUNE";
    Months[Months["JULY"] = 6] = "JULY";
    Months[Months["AUGUST"] = 7] = "AUGUST";
    Months[Months["SEPTEMBER"] = 8] = "SEPTEMBER";
    Months[Months["OCTOBER"] = 9] = "OCTOBER";
    Months[Months["NOVEMBER"] = 10] = "NOVEMBER";
    Months[Months["DECEMBER"] = 11] = "DECEMBER";
})(Months || (Months = {}));
//# sourceMappingURL=months.js.map