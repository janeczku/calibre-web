import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
/*
 * Copyright 2018 Palantir Technologies, Inc. All rights reserved.
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
import { IconSize, SmallCross } from "@blueprintjs/icons";
import { AbstractPureComponent, Classes } from "../../common";
import * as Errors from "../../common/errors";
import { getPositionIgnoreAngles, isPositionHorizontal } from "../../common/position";
import { DISPLAYNAME_PREFIX } from "../../common/props";
import { Button } from "../button/buttons";
import { H4 } from "../html/html";
import { Icon } from "../icon/icon";
import { Overlay2 } from "../overlay2/overlay2";
export var DrawerSize;
(function (DrawerSize) {
    DrawerSize["SMALL"] = "360px";
    DrawerSize["STANDARD"] = "50%";
    DrawerSize["LARGE"] = "90%";
})(DrawerSize || (DrawerSize = {}));
export class Drawer extends AbstractPureComponent {
    static displayName = `${DISPLAYNAME_PREFIX}.Drawer`;
    static defaultProps = {
        canOutsideClickClose: true,
        isOpen: false,
        position: "right",
        style: {},
    };
    render() {
        const { hasBackdrop, size, style, position } = this.props;
        const { className, children, ...overlayProps } = this.props;
        const realPosition = getPositionIgnoreAngles(position);
        const classes = classNames(Classes.DRAWER, {
            [Classes.positionClass(realPosition) ?? ""]: true,
        }, className);
        const styleProp = size == null
            ? style
            : {
                ...style,
                [isPositionHorizontal(realPosition) ? "height" : "width"]: size,
            };
        return (
        // N.B. the `OVERLAY_CONTAINER` class is a bit of a misnomer since it is only being used by the Drawer
        // component, but we keep it for backwards compatibility.
        _jsx(Overlay2, { ...overlayProps, className: classNames({ [Classes.OVERLAY_CONTAINER]: hasBackdrop }), children: _jsxs("div", { className: classes, style: styleProp, children: [this.maybeRenderHeader(), children] }) }));
    }
    validateProps(props) {
        if (props.title == null) {
            if (props.icon != null) {
                console.warn(Errors.DIALOG_WARN_NO_HEADER_ICON);
            }
            if (props.isCloseButtonShown != null) {
                console.warn(Errors.DIALOG_WARN_NO_HEADER_CLOSE_BUTTON);
            }
        }
        if (props.position != null) {
            if (props.position !== getPositionIgnoreAngles(props.position)) {
                console.warn(Errors.DRAWER_ANGLE_POSITIONS_ARE_CASTED);
            }
        }
    }
    maybeRenderCloseButton() {
        // `isCloseButtonShown` can't be defaulted through default props because of props validation
        // so this check actually defaults it to true (fails only if directly set to false)
        if (this.props.isCloseButtonShown !== false) {
            return (_jsx(Button, { "aria-label": "Close", className: Classes.DIALOG_CLOSE_BUTTON, icon: _jsx(SmallCross, { size: IconSize.LARGE }), onClick: this.props.onClose, variant: "minimal" }));
        }
        else {
            return null;
        }
    }
    maybeRenderHeader() {
        const { icon, title } = this.props;
        if (title == null) {
            return null;
        }
        return (_jsxs("div", { className: Classes.DRAWER_HEADER, children: [_jsx(Icon, { icon: icon, size: IconSize.LARGE }), _jsx(H4, { children: title }), this.maybeRenderCloseButton()] }));
    }
}
//# sourceMappingURL=drawer.js.map