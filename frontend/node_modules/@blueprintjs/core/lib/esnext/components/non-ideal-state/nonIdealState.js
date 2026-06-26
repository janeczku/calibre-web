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
import { IconSize } from "@blueprintjs/icons";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { ensureElement } from "../../common/utils";
import { H4 } from "../html/html";
import { Icon } from "../icon/icon";
export var NonIdealStateIconSize;
(function (NonIdealStateIconSize) {
    NonIdealStateIconSize[NonIdealStateIconSize["STANDARD"] = 48] = "STANDARD";
    NonIdealStateIconSize[NonIdealStateIconSize["SMALL"] = 32] = "SMALL";
    NonIdealStateIconSize[NonIdealStateIconSize["EXTRA_SMALL"] = 20] = "EXTRA_SMALL";
})(NonIdealStateIconSize || (NonIdealStateIconSize = {}));
/**
 * Non-ideal state component.
 *
 * @see https://blueprintjs.com/docs/#core/components/non-ideal-state
 */
export const NonIdealState = props => {
    const { action, children, className, description, icon, iconMuted = true, iconSize = NonIdealStateIconSize.STANDARD, layout = "vertical", title, } = props;
    return (_jsxs("div", { className: classNames(Classes.NON_IDEAL_STATE, `${Classes.NON_IDEAL_STATE}-${layout}`, className), children: [icon == null ? undefined : (_jsx("div", { className: Classes.NON_IDEAL_STATE_VISUAL, style: { fontSize: `${iconSize}px`, lineHeight: `${iconSize}px` }, children: _jsx(Icon, { className: classNames({ [Classes.ICON_MUTED]: iconMuted }), icon: icon, size: iconSize, "aria-hidden": true, tabIndex: -1 }) })), title == null && description == null ? undefined : (_jsxs("div", { className: Classes.NON_IDEAL_STATE_TEXT, children: [title && _jsx(H4, { children: title }), description && ensureElement(description, "div")] })), action, children] }));
};
NonIdealState.displayName = `${DISPLAYNAME_PREFIX}.NonIdealState`;
//# sourceMappingURL=nonIdealState.js.map