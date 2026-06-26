"use strict";
/*
 * Copyright 2023 Palantir Technologies, Inc. All rights reserved.
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
exports.useMonthSelectRightOffset = useMonthSelectRightOffset;
const react_1 = require("react");
const core_1 = require("@blueprintjs/core");
const icons_1 = require("@blueprintjs/icons");
const datePickerUtils_1 = require("../components/date-picker/datePickerUtils");
const _1 = require(".");
function useMonthSelectRightOffset(monthSelectElement, containerElement, displayedMonthText) {
    const [monthRightOffset, setMonthRightOffset] = (0, react_1.useState)(0);
    (0, core_1.useIsomorphicLayoutEffect)(() => {
        if (containerElement.current == null) {
            return;
        }
        // measure width of text as rendered inside our container element.
        const monthTextWidth = datePickerUtils_1.DatePickerUtils.measureTextWidth(displayedMonthText, _1.Classes.DATEPICKER_CAPTION_MEASURE, containerElement.current);
        const monthSelectWidth = monthSelectElement.current?.clientWidth ?? 0;
        const rightOffset = Math.max(2, monthSelectWidth - monthTextWidth - icons_1.IconSize.STANDARD - 2);
        setMonthRightOffset(rightOffset);
    }, [containerElement, displayedMonthText, monthSelectElement]);
    return monthRightOffset;
}
//# sourceMappingURL=useMonthSelectRightOffset.js.map