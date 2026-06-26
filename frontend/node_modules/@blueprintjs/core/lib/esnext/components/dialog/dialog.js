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
import { useMemo, useRef } from "react";
import { IconSize, SmallCross } from "@blueprintjs/icons";
import { Classes, DISPLAYNAME_PREFIX, mergeRefs } from "../../common";
import * as Errors from "../../common/errors";
import { uniqueId } from "../../common/utils";
import { useValidateProps } from "../../hooks/useValidateProps";
import { Button } from "../button/buttons";
import { H2 } from "../html/html";
import { Icon } from "../icon/icon";
import { Overlay2 } from "../overlay2/overlay2";
/**
 * Dialog component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog
 */
export const Dialog = props => {
    const { canOutsideClickClose = true, children, className, containerRef, icon, isCloseButtonShown, isOpen = false, onClose, role = "dialog", style, title, titleTagName: TitleTagName = H2, ...overlayProps } = props;
    const childRef = useRef(null);
    const titleId = useMemo(() => `title-${uniqueId("bp-dialog")}`, []);
    useValidateProps(() => {
        if (title == null) {
            if (props.icon != null) {
                console.warn(Errors.DIALOG_WARN_NO_HEADER_ICON);
            }
            if (props.isCloseButtonShown != null) {
                console.warn(Errors.DIALOG_WARN_NO_HEADER_CLOSE_BUTTON);
            }
        }
    }, [title, props.icon, props.isCloseButtonShown]);
    return (_jsx(Overlay2, { ...overlayProps, isOpen: isOpen, canOutsideClickClose: canOutsideClickClose, className: Classes.OVERLAY_SCROLL_CONTAINER, childRef: childRef, hasBackdrop: true, onClose: onClose, children: _jsx("div", { className: Classes.DIALOG_CONTAINER, ref: mergeRefs(containerRef, childRef), children: _jsxs("div", { "aria-describedby": overlayProps["aria-describedby"], "aria-labelledby": overlayProps["aria-labelledby"] || (title != null ? titleId : undefined), "aria-modal": overlayProps.enforceFocus ?? true, className: classNames(Classes.DIALOG, className), role: role, style: style, children: [title != null && (_jsxs("div", { className: Classes.DIALOG_HEADER, children: [_jsx(Icon, { icon: icon, size: IconSize.STANDARD, "aria-hidden": true, tabIndex: -1 }), _jsx(TitleTagName, { id: titleId, children: title }), isCloseButtonShown !== false && (_jsx(Button, { "aria-label": "Close", className: Classes.DIALOG_CLOSE_BUTTON, icon: _jsx(SmallCross, { size: IconSize.STANDARD }), onClick: onClose, variant: "minimal" }))] })), children] }) }) }));
};
Dialog.displayName = `${DISPLAYNAME_PREFIX}.Dialog`;
//# sourceMappingURL=dialog.js.map