"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Drawer = exports.DrawerSize = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const Errors = tslib_1.__importStar(require("../../common/errors"));
const position_1 = require("../../common/position");
const props_1 = require("../../common/props");
const buttons_1 = require("../button/buttons");
const html_1 = require("../html/html");
const icon_1 = require("../icon/icon");
const overlay2_1 = require("../overlay2/overlay2");
var DrawerSize;
(function (DrawerSize) {
    DrawerSize["SMALL"] = "360px";
    DrawerSize["STANDARD"] = "50%";
    DrawerSize["LARGE"] = "90%";
})(DrawerSize || (exports.DrawerSize = DrawerSize = {}));
class Drawer extends common_1.AbstractPureComponent {
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.Drawer`;
    static defaultProps = {
        canOutsideClickClose: true,
        isOpen: false,
        position: "right",
        style: {},
    };
    render() {
        const { hasBackdrop, size, style, position } = this.props;
        const { className, children, ...overlayProps } = this.props;
        const realPosition = (0, position_1.getPositionIgnoreAngles)(position);
        const classes = (0, classnames_1.default)(common_1.Classes.DRAWER, {
            [common_1.Classes.positionClass(realPosition) ?? ""]: true,
        }, className);
        const styleProp = size == null
            ? style
            : {
                ...style,
                [(0, position_1.isPositionHorizontal)(realPosition) ? "height" : "width"]: size,
            };
        return (
        // N.B. the `OVERLAY_CONTAINER` class is a bit of a misnomer since it is only being used by the Drawer
        // component, but we keep it for backwards compatibility.
        (0, jsx_runtime_1.jsx)(overlay2_1.Overlay2, { ...overlayProps, className: (0, classnames_1.default)({ [common_1.Classes.OVERLAY_CONTAINER]: hasBackdrop }), children: (0, jsx_runtime_1.jsxs)("div", { className: classes, style: styleProp, children: [this.maybeRenderHeader(), children] }) }));
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
            if (props.position !== (0, position_1.getPositionIgnoreAngles)(props.position)) {
                console.warn(Errors.DRAWER_ANGLE_POSITIONS_ARE_CASTED);
            }
        }
    }
    maybeRenderCloseButton() {
        // `isCloseButtonShown` can't be defaulted through default props because of props validation
        // so this check actually defaults it to true (fails only if directly set to false)
        if (this.props.isCloseButtonShown !== false) {
            return ((0, jsx_runtime_1.jsx)(buttons_1.Button, { "aria-label": "Close", className: common_1.Classes.DIALOG_CLOSE_BUTTON, icon: (0, jsx_runtime_1.jsx)(icons_1.SmallCross, { size: icons_1.IconSize.LARGE }), onClick: this.props.onClose, variant: "minimal" }));
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
        return ((0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.DRAWER_HEADER, children: [(0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon, size: icons_1.IconSize.LARGE }), (0, jsx_runtime_1.jsx)(html_1.H4, { children: title }), this.maybeRenderCloseButton()] }));
    }
}
exports.Drawer = Drawer;
//# sourceMappingURL=drawer.js.map