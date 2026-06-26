"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Dialog = void 0;
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
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const Errors = tslib_1.__importStar(require("../../common/errors"));
const utils_1 = require("../../common/utils");
const useValidateProps_1 = require("../../hooks/useValidateProps");
const buttons_1 = require("../button/buttons");
const html_1 = require("../html/html");
const icon_1 = require("../icon/icon");
const overlay2_1 = require("../overlay2/overlay2");
/**
 * Dialog component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog
 */
const Dialog = props => {
    const { canOutsideClickClose = true, children, className, containerRef, icon, isCloseButtonShown, isOpen = false, onClose, role = "dialog", style, title, titleTagName: TitleTagName = html_1.H2, ...overlayProps } = props;
    const childRef = (0, react_1.useRef)(null);
    const titleId = (0, react_1.useMemo)(() => `title-${(0, utils_1.uniqueId)("bp-dialog")}`, []);
    (0, useValidateProps_1.useValidateProps)(() => {
        if (title == null) {
            if (props.icon != null) {
                console.warn(Errors.DIALOG_WARN_NO_HEADER_ICON);
            }
            if (props.isCloseButtonShown != null) {
                console.warn(Errors.DIALOG_WARN_NO_HEADER_CLOSE_BUTTON);
            }
        }
    }, [title, props.icon, props.isCloseButtonShown]);
    return ((0, jsx_runtime_1.jsx)(overlay2_1.Overlay2, { ...overlayProps, isOpen: isOpen, canOutsideClickClose: canOutsideClickClose, className: common_1.Classes.OVERLAY_SCROLL_CONTAINER, childRef: childRef, hasBackdrop: true, onClose: onClose, children: (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.DIALOG_CONTAINER, ref: (0, common_1.mergeRefs)(containerRef, childRef), children: (0, jsx_runtime_1.jsxs)("div", { "aria-describedby": overlayProps["aria-describedby"], "aria-labelledby": overlayProps["aria-labelledby"] || (title != null ? titleId : undefined), "aria-modal": overlayProps.enforceFocus ?? true, className: (0, classnames_1.default)(common_1.Classes.DIALOG, className), role: role, style: style, children: [title != null && ((0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.DIALOG_HEADER, children: [(0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon, size: icons_1.IconSize.STANDARD, "aria-hidden": true, tabIndex: -1 }), (0, jsx_runtime_1.jsx)(TitleTagName, { id: titleId, children: title }), isCloseButtonShown !== false && ((0, jsx_runtime_1.jsx)(buttons_1.Button, { "aria-label": "Close", className: common_1.Classes.DIALOG_CLOSE_BUTTON, icon: (0, jsx_runtime_1.jsx)(icons_1.SmallCross, { size: icons_1.IconSize.STANDARD }), onClick: onClose, variant: "minimal" }))] })), children] }) }) }));
};
exports.Dialog = Dialog;
exports.Dialog.displayName = `${common_1.DISPLAYNAME_PREFIX}.Dialog`;
//# sourceMappingURL=dialog.js.map