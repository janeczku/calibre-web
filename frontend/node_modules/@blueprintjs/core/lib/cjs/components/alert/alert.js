"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Alert = void 0;
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
const react_1 = require("react");
const common_1 = require("../../common");
const errors_1 = require("../../common/errors");
const useValidateProps_1 = require("../../hooks/useValidateProps");
const buttons_1 = require("../button/buttons");
const dialog_1 = require("../dialog/dialog");
const icon_1 = require("../icon/icon");
/**
 * Alert component.
 *
 * @see https://blueprintjs.com/docs/#core/components/alert
 */
const Alert = props => {
    const { cancelButtonText, canEscapeKeyCancel = false, canOutsideClickCancel = false, children, className, confirmButtonText = "OK", icon, intent, isOpen = false, loading = false, onCancel, onClose, onConfirm, ...overlayProps } = props;
    (0, useValidateProps_1.useValidateProps)(() => {
        if (onClose == null && (cancelButtonText == null) !== (onCancel == null)) {
            console.warn(errors_1.ALERT_WARN_CANCEL_PROPS);
        }
        const hasCancelHandler = onCancel != null || onClose != null;
        if (canEscapeKeyCancel && !hasCancelHandler) {
            console.warn(errors_1.ALERT_WARN_CANCEL_ESCAPE_KEY);
        }
        if (canOutsideClickCancel && !hasCancelHandler) {
            console.warn(errors_1.ALERT_WARN_CANCEL_OUTSIDE_CLICK);
        }
    }, [canEscapeKeyCancel, canOutsideClickCancel, cancelButtonText, onCancel, onClose]);
    const internalHandleCallbacks = (0, react_1.useCallback)((confirmed, event) => {
        (confirmed ? onConfirm : onCancel)?.(event);
        onClose?.(confirmed, event);
    }, [onCancel, onClose, onConfirm]);
    const handleCancel = (0, react_1.useCallback)((event) => internalHandleCallbacks(false, event), [internalHandleCallbacks]);
    const handleConfirm = (0, react_1.useCallback)((event) => internalHandleCallbacks(true, event), [internalHandleCallbacks]);
    return ((0, jsx_runtime_1.jsxs)(dialog_1.Dialog, { ...overlayProps, role: "alertdialog", className: (0, classnames_1.default)(common_1.Classes.ALERT, className), canEscapeKeyClose: canEscapeKeyCancel, canOutsideClickClose: canOutsideClickCancel, isOpen: isOpen, onClose: handleCancel, children: [(0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.ALERT_BODY, children: [(0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon, size: 40, intent: intent }), (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.ALERT_CONTENTS, children: children })] }), (0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.ALERT_FOOTER, children: [(0, jsx_runtime_1.jsx)(buttons_1.Button, { loading: loading, intent: intent, text: confirmButtonText, onClick: handleConfirm }), cancelButtonText && (0, jsx_runtime_1.jsx)(buttons_1.Button, { text: cancelButtonText, disabled: loading, onClick: handleCancel })] })] }));
};
exports.Alert = Alert;
exports.Alert.displayName = `${common_1.DISPLAYNAME_PREFIX}.Alert`;
//# sourceMappingURL=alert.js.map