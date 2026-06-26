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
import { Classes } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
/**
 * Menu component.
 *
 * @see https://blueprintjs.com/docs/#core/components/menu
 */
export const Menu = props => {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const { className, children, large, size = "medium", small, ulRef, ...htmlProps } = props;
    return (_jsx("ul", { role: "menu", ...htmlProps, className: classNames(className, Classes.MENU, Classes.sizeClass(size, { large, small })), ref: ulRef, children: children }));
};
Menu.displayName = `${DISPLAYNAME_PREFIX}.Menu`;
//# sourceMappingURL=menu.js.map