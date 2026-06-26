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
import { useCallback } from "react";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { ALERT_WARN_CANCEL_ESCAPE_KEY, ALERT_WARN_CANCEL_OUTSIDE_CLICK, ALERT_WARN_CANCEL_PROPS, } from "../../common/errors";
import { useValidateProps } from "../../hooks/useValidateProps";
import { Button } from "../button/buttons";
import { Dialog } from "../dialog/dialog";
import { Icon } from "../icon/icon";
/**
 * Alert component.
 *
 * @see https://blueprintjs.com/docs/#core/components/alert
 */
export const Alert = props => {
    const { cancelButtonText, canEscapeKeyCancel = false, canOutsideClickCancel = false, children, className, confirmButtonText = "OK", icon, intent, isOpen = false, loading = false, onCancel, onClose, onConfirm, ...overlayProps } = props;
    useValidateProps(() => {
        if (onClose == null && (cancelButtonText == null) !== (onCancel == null)) {
            console.warn(ALERT_WARN_CANCEL_PROPS);
        }
        const hasCancelHandler = onCancel != null || onClose != null;
        if (canEscapeKeyCancel && !hasCancelHandler) {
            console.warn(ALERT_WARN_CANCEL_ESCAPE_KEY);
        }
        if (canOutsideClickCancel && !hasCancelHandler) {
            console.warn(ALERT_WARN_CANCEL_OUTSIDE_CLICK);
        }
    }, [canEscapeKeyCancel, canOutsideClickCancel, cancelButtonText, onCancel, onClose]);
    const internalHandleCallbacks = useCallback((confirmed, event) => {
        (confirmed ? onConfirm : onCancel)?.(event);
        onClose?.(confirmed, event);
    }, [onCancel, onClose, onConfirm]);
    const handleCancel = useCallback((event) => internalHandleCallbacks(false, event), [internalHandleCallbacks]);
    const handleConfirm = useCallback((event) => internalHandleCallbacks(true, event), [internalHandleCallbacks]);
    return (_jsxs(Dialog, { ...overlayProps, role: "alertdialog", className: classNames(Classes.ALERT, className), canEscapeKeyClose: canEscapeKeyCancel, canOutsideClickClose: canOutsideClickCancel, isOpen: isOpen, onClose: handleCancel, children: [_jsxs("div", { className: Classes.ALERT_BODY, children: [_jsx(Icon, { icon: icon, size: 40, intent: intent }), _jsx("div", { className: Classes.ALERT_CONTENTS, children: children })] }), _jsxs("div", { className: Classes.ALERT_FOOTER, children: [_jsx(Button, { loading: loading, intent: intent, text: confirmButtonText, onClick: handleConfirm }), cancelButtonText && _jsx(Button, { text: cancelButtonText, disabled: loading, onClick: handleCancel })] })] }));
};
Alert.displayName = `${DISPLAYNAME_PREFIX}.Alert`;
//# sourceMappingURL=alert.js.map