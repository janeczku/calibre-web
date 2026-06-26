"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MenuDivider = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2015 Palantir Technologies, Inc. All rights reserved.
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
const common_1 = require("../../common");
const html_1 = require("../html/html");
/**
 * Menu divider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/menu.menu-divider
 */
const MenuDivider = ({ className, title, titleId }) => {
    const dividerClasses = (0, classnames_1.default)(title ? common_1.Classes.MENU_HEADER : common_1.Classes.MENU_DIVIDER, className);
    return ((0, jsx_runtime_1.jsx)("li", { className: dividerClasses, role: "separator", children: title && (0, jsx_runtime_1.jsx)(html_1.H6, { id: titleId, children: title }) }));
};
exports.MenuDivider = MenuDivider;
exports.MenuDivider.displayName = `${common_1.DISPLAYNAME_PREFIX}.MenuDivider`;
//# sourceMappingURL=menuDivider.js.map