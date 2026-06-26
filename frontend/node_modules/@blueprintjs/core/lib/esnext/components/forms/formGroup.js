import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import classNames from "classnames";
import { Classes } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
/**
 * Form group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/form-group
 */
export const FormGroup = props => {
    const { children, className, contentClassName, disabled, fill, helperText, inline, intent, label, labelFor, labelInfo, style, subLabel, ...htmlProps } = props;
    const classes = classNames(Classes.FORM_GROUP, Classes.intentClass(intent), {
        [Classes.DISABLED]: disabled,
        [Classes.FILL]: fill,
        [Classes.INLINE]: inline,
    }, className);
    return (_jsxs("div", { className: classes, style: style, ...htmlProps, children: [label && (_jsxs("label", { className: Classes.LABEL, htmlFor: labelFor, children: [label, " ", _jsx("span", { className: Classes.TEXT_MUTED, children: labelInfo })] })), subLabel && _jsx("div", { className: Classes.FORM_GROUP_SUB_LABEL, children: subLabel }), _jsxs("div", { className: classNames(Classes.FORM_CONTENT, contentClassName), children: [children, helperText && _jsx("div", { className: Classes.FORM_HELPER_TEXT, children: helperText })] })] }));
};
FormGroup.displayName = `${DISPLAYNAME_PREFIX}.FormGroup`;
//# sourceMappingURL=formGroup.js.map