"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NavbarGroup = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const common_1 = require("../../common");
const errors_1 = require("../../common/errors");
const props_1 = require("../../common/props");
const useValidateProps_1 = require("../../hooks/useValidateProps");
// this component is simple enough that tests would be purely tautological.
/* istanbul ignore next */
const NavbarGroup = ({ align = common_1.Alignment.START, children, className, ...htmlProps }) => {
    const classes = (0, classnames_1.default)(common_1.Classes.NAVBAR_GROUP, common_1.Classes.alignmentClass(align), className);
    (0, useValidateProps_1.useValidateProps)(() => {
        if (align === common_1.Alignment.CENTER) {
            console.warn(errors_1.NAVBAR_GROUP_ALIGN_CENTER);
        }
    }, [align]);
    return ((0, jsx_runtime_1.jsx)("div", { className: classes, ...htmlProps, children: children }));
};
exports.NavbarGroup = NavbarGroup;
exports.NavbarGroup.displayName = `${props_1.DISPLAYNAME_PREFIX}.NavbarGroup`;
//# sourceMappingURL=navbarGroup.js.map