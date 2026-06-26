import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/*
 * Copyright 2016 Palantir Technologies, Inc. All rights reserved.
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
import { forwardRef } from "react";
import { useInteractiveAttributes } from "../../accessibility/useInteractiveAttributes";
import { Classes, DISPLAYNAME_PREFIX, removeNonHTMLProps, Utils, } from "../../common";
import { isReactNodeEmpty } from "../../common/utils";
import { Icon } from "../icon/icon";
import { Text } from "../text/text";
import { TagRemoveButton } from "./tagRemoveButton";
/**
 * Tag component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tag
 */
export const Tag = forwardRef((props, ref) => {
    const { children, className, endIcon, fill = false, icon, intent, interactive, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large = false, minimal = false, multiline, onRemove, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    rightIcon, round = false, size = "medium", tabIndex = 0, htmlTitle, ...htmlProps } = props;
    const isRemovable = Utils.isFunction(onRemove);
    const isInteractive = interactive ?? htmlProps.onClick != null;
    const [active, interactiveProps] = useInteractiveAttributes(isInteractive, props, ref, {
        defaultTabIndex: 0,
        disabledTabIndex: undefined,
    });
    const tagClasses = classNames(Classes.TAG, Classes.intentClass(intent), Classes.sizeClass(size, { large }), {
        [Classes.ACTIVE]: active,
        [Classes.FILL]: fill,
        [Classes.INTERACTIVE]: isInteractive,
        [Classes.MINIMAL]: minimal,
        [Classes.ROUND]: round,
    }, className);
    return (_jsxs("span", { ...removeNonHTMLProps(htmlProps), ...interactiveProps, className: tagClasses, role: isInteractive ? "button" : undefined, children: [_jsx(Icon, { icon: icon }), !isReactNodeEmpty(children) && (_jsx(Text, { className: Classes.FILL, ellipsize: !multiline, tagName: "span", title: htmlTitle, children: children })), _jsx(Icon, { icon: endIcon ?? rightIcon }), isRemovable && _jsx(TagRemoveButton, { ...props })] }));
});
Tag.displayName = `${DISPLAYNAME_PREFIX}.Tag`;
//# sourceMappingURL=tag.js.map