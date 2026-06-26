import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import classNames from "classnames";
import { Error, InfoSign, Tick, WarningSign } from "@blueprintjs/icons";
import { Classes, DISPLAYNAME_PREFIX, Intent, Utils, } from "../../common";
import { H5 } from "../html/html";
import { Icon } from "../icon/icon";
/**
 * Callout component.
 *
 * @see https://blueprintjs.com/docs/#core/components/callout
 */
export const Callout = props => {
    const { className, children, icon, intent, title, compact, minimal = false, ...htmlProps } = props;
    const iconElement = renderIcon(icon, intent);
    const classes = classNames(Classes.CALLOUT, Classes.intentClass(intent), className, {
        [Classes.CALLOUT_HAS_BODY_CONTENT]: !Utils.isReactNodeEmpty(children),
        [Classes.CALLOUT_ICON]: iconElement != null,
        [Classes.COMPACT]: compact,
        [Classes.MINIMAL]: minimal,
    });
    return (_jsxs("div", { className: classes, ...htmlProps, children: [iconElement, title && _jsx(H5, { children: title }), children] }));
};
Callout.displayName = `${DISPLAYNAME_PREFIX}.Callout`;
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
        return _jsx(Icon, { icon: icon, ...iconProps });
    }
    // 3. icon specified by intent prop
    switch (intent) {
        case Intent.DANGER:
            return _jsx(Error, { ...iconProps });
        case Intent.PRIMARY:
            return _jsx(InfoSign, { ...iconProps });
        case Intent.WARNING:
            return _jsx(WarningSign, { ...iconProps });
        case Intent.SUCCESS:
            return _jsx(Tick, { ...iconProps });
        default:
            return undefined;
    }
};
//# sourceMappingURL=callout.js.map