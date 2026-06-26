"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Callout = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2017 Palantir Technologies, Inc. All rights reserved.
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
const html_1 = require("../html/html");
const icon_1 = require("../icon/icon");
/**
 * Callout component.
 *
 * @see https://blueprintjs.com/docs/#core/components/callout
 */
const Callout = props => {
    const { className, children, icon, intent, title, compact, minimal = false, ...htmlProps } = props;
    const iconElement = renderIcon(icon, intent);
    const classes = (0, classnames_1.default)(common_1.Classes.CALLOUT, common_1.Classes.intentClass(intent), className, {
        [common_1.Classes.CALLOUT_HAS_BODY_CONTENT]: !common_1.Utils.isReactNodeEmpty(children),
        [common_1.Classes.CALLOUT_ICON]: iconElement != null,
        [common_1.Classes.COMPACT]: compact,
        [common_1.Classes.MINIMAL]: minimal,
    });
    return ((0, jsx_runtime_1.jsxs)("div", { className: classes, ...htmlProps, children: [iconElement, title && (0, jsx_runtime_1.jsx)(html_1.H5, { children: title }), children] }));
};
exports.Callout = Callout;
exports.Callout.displayName = `${common_1.DISPLAYNAME_PREFIX}.Callout`;
const renderIcon = (icon, intent) => {
    // 1. no icon
    if (icon === null || icon === false) {
        return undefined;
    }
    const iconProps = {
        "aria-hidden": true,
        tabIndex: -1,
    };
    // 2. icon specified by name or as a custom SVG element
    if (icon !== undefined) {
        return (0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon, ...iconProps });
    }
    // 3. icon specified by intent prop
    switch (intent) {
        case common_1.Intent.DANGER:
            return (0, jsx_runtime_1.jsx)(icons_1.Error, { ...iconProps });
        case common_1.Intent.PRIMARY:
            return (0, jsx_runtime_1.jsx)(icons_1.InfoSign, { ...iconProps });
        case common_1.Intent.WARNING:
            return (0, jsx_runtime_1.jsx)(icons_1.WarningSign, { ...iconProps });
        case common_1.Intent.SUCCESS:
            return (0, jsx_runtime_1.jsx)(icons_1.Tick, { ...iconProps });
        default:
            return undefined;
    }
};
//# sourceMappingURL=callout.js.map