"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.FormGroup = void 0;
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
const common_1 = require("../../common");
const props_1 = require("../../common/props");
/**
 * Form group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/form-group
 */
const FormGroup = props => {
    const { children, className, contentClassName, disabled, fill, helperText, inline, intent, label, labelFor, labelInfo, style, subLabel, ...htmlProps } = props;
    const classes = (0, classnames_1.default)(common_1.Classes.FORM_GROUP, common_1.Classes.intentClass(intent), {
        [common_1.Classes.DISABLED]: disabled,
        [common_1.Classes.FILL]: fill,
        [common_1.Classes.INLINE]: inline,
    }, className);
    return ((0, jsx_runtime_1.jsxs)("div", { className: classes, style: style, ...htmlProps, children: [label && ((0, jsx_runtime_1.jsxs)("label", { className: common_1.Classes.LABEL, htmlFor: labelFor, children: [label, " ", (0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.TEXT_MUTED, children: labelInfo })] })), subLabel && (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.FORM_GROUP_SUB_LABEL, children: subLabel }), (0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(common_1.Classes.FORM_CONTENT, contentClassName), children: [children, helperText && (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.FORM_HELPER_TEXT, children: helperText })] })] }));
};
exports.FormGroup = FormGroup;
exports.FormGroup.displayName = `${props_1.DISPLAYNAME_PREFIX}.FormGroup`;
//# sourceMappingURL=formGroup.js.map