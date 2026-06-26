import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import classNames from "classnames";
import { forwardRef } from "react";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
/**
 * Dialog footer component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.dialog-footer-props
 */
export const DialogFooter = forwardRef((props, ref) => {
    const { actions, children, className, minimal = false, ...htmlProps } = props;
    return (_jsxs("div", { ...htmlProps, className: classNames(Classes.DIALOG_FOOTER, className, {
            [Classes.DIALOG_FOOTER_FIXED]: !minimal,
        }), ref: ref, children: [_jsx("div", { className: Classes.DIALOG_FOOTER_MAIN_SECTION, children: children }), actions != null && _jsx("div", { className: Classes.DIALOG_FOOTER_ACTIONS, children: actions })] }));
});
DialogFooter.displayName = `${DISPLAYNAME_PREFIX}.DialogFooter`;
//# sourceMappingURL=dialogFooter.js.map