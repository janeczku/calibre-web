import { jsx as _jsx } from "react/jsx-runtime";
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
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { H6 } from "../html/html";
/**
 * Menu divider component.
 *
 * @see https://blueprintjs.com/docs/#core/components/menu.menu-divider
 */
export const MenuDivider = ({ className, title, titleId }) => {
    const dividerClasses = classNames(title ? Classes.MENU_HEADER : Classes.MENU_DIVIDER, className);
    return (_jsx("li", { className: dividerClasses, role: "separator", children: title && _jsx(H6, { id: titleId, children: title }) }));
};
MenuDivider.displayName = `${DISPLAYNAME_PREFIX}.MenuDivider`;
//# sourceMappingURL=menuDivider.js.map