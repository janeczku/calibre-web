"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DialogFooter = void 0;
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
const react_1 = require("react");
const common_1 = require("../../common");
/**
 * Dialog footer component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.dialog-footer-props
 */
exports.DialogFooter = (0, react_1.forwardRef)((props, ref) => {
    const { actions, children, className, minimal = false, ...htmlProps } = props;
    return ((0, jsx_runtime_1.jsxs)("div", { ...htmlProps, className: (0, classnames_1.default)(common_1.Classes.DIALOG_FOOTER, className, {
            [common_1.Classes.DIALOG_FOOTER_FIXED]: !minimal,
        }), ref: ref, children: [(0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.DIALOG_FOOTER_MAIN_SECTION, children: children }), actions != null && (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.DIALOG_FOOTER_ACTIONS, children: actions })] }));
});
exports.DialogFooter.displayName = `${common_1.DISPLAYNAME_PREFIX}.DialogFooter`;
//# sourceMappingURL=dialogFooter.js.map