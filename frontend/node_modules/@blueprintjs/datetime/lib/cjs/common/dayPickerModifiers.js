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
exports.DISALLOWED_MODIFIERS = exports.SELECTED_RANGE_MODIFIER = exports.SELECTED_MODIFIER = exports.OUTSIDE_MODIFIER = exports.HOVERED_RANGE_MODIFIER = exports.DISABLED_MODIFIER = void 0;
exports.combineModifiers = combineModifiers;
exports.DISABLED_MODIFIER = "disabled";
exports.HOVERED_RANGE_MODIFIER = "hovered-range";
exports.OUTSIDE_MODIFIER = "outside";
exports.SELECTED_MODIFIER = "selected";
exports.SELECTED_RANGE_MODIFIER = "selected-range";
// modifiers the user can't set because they are used by Blueprint or react-day-picker
exports.DISALLOWED_MODIFIERS = [
    exports.DISABLED_MODIFIER,
    exports.HOVERED_RANGE_MODIFIER,
    exports.OUTSIDE_MODIFIER,
    exports.SELECTED_MODIFIER,
    exports.SELECTED_RANGE_MODIFIER,
];
function combineModifiers(baseModifiers, userModifiers) {
    let modifiers = baseModifiers;
    if (userModifiers !== undefined) {
        modifiers = {};
        for (const key of Object.keys(userModifiers)) {
            if (exports.DISALLOWED_MODIFIERS.indexOf(key) === -1) {
                modifiers[key] = userModifiers[key];
            }
        }
        for (const key of Object.keys(baseModifiers)) {
            modifiers[key] = baseModifiers[key];
        }
    }
    return modifiers;
}
//# sourceMappingURL=dayPickerModifiers.js.map