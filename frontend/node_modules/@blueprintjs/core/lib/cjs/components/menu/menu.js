"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Menu = void 0;
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
const props_1 = require("../../common/props");
/**
 * Menu component.
 *
 * @see https://blueprintjs.com/docs/#core/components/menu
 */
const Menu = props => {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const { className, children, large, size = "medium", small, ulRef, ...htmlProps } = props;
    return ((0, jsx_runtime_1.jsx)("ul", { role: "menu", ...htmlProps, className: (0, classnames_1.default)(className, common_1.Classes.MENU, common_1.Classes.sizeClass(size, { large, small })), ref: ulRef, children: children }));
};
exports.Menu = Menu;
exports.Menu.displayName = `${props_1.DISPLAYNAME_PREFIX}.Menu`;
//# sourceMappingURL=menu.js.map