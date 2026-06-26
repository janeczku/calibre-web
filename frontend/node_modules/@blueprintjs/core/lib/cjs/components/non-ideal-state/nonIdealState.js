"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NonIdealState = exports.NonIdealStateIconSize = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2025 Palantir Technologies, Inc. All rights reserved.
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const utils_1 = require("../../common/utils");
const html_1 = require("../html/html");
const icon_1 = require("../icon/icon");
var NonIdealStateIconSize;
(function (NonIdealStateIconSize) {
    NonIdealStateIconSize[NonIdealStateIconSize["STANDARD"] = 48] = "STANDARD";
    NonIdealStateIconSize[NonIdealStateIconSize["SMALL"] = 32] = "SMALL";
    NonIdealStateIconSize[NonIdealStateIconSize["EXTRA_SMALL"] = 20] = "EXTRA_SMALL";
})(NonIdealStateIconSize || (exports.NonIdealStateIconSize = NonIdealStateIconSize = {}));
/**
 * Non-ideal state component.
 *
 * @see https://blueprintjs.com/docs/#core/components/non-ideal-state
 */
const NonIdealState = props => {
    const { action, children, className, description, icon, iconMuted = true, iconSize = NonIdealStateIconSize.STANDARD, layout = "vertical", title, } = props;
    return ((0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(common_1.Classes.NON_IDEAL_STATE, `${common_1.Classes.NON_IDEAL_STATE}-${layout}`, className), children: [icon == null ? undefined : ((0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.NON_IDEAL_STATE_VISUAL, style: { fontSize: `${iconSize}px`, lineHeight: `${iconSize}px` }, children: (0, jsx_runtime_1.jsx)(icon_1.Icon, { className: (0, classnames_1.default)({ [common_1.Classes.ICON_MUTED]: iconMuted }), icon: icon, size: iconSize, "aria-hidden": true, tabIndex: -1 }) })), title == null && description == null ? undefined : ((0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.NON_IDEAL_STATE_TEXT, children: [title && (0, jsx_runtime_1.jsx)(html_1.H4, { children: title }), description && (0, utils_1.ensureElement)(description, "div")] })), action, children] }));
};
exports.NonIdealState = NonIdealState;
exports.NonIdealState.displayName = `${common_1.DISPLAYNAME_PREFIX}.NonIdealState`;
//# sourceMappingURL=nonIdealState.js.map