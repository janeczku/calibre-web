import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/*
 * Copyright 2024 Palantir Technologies, Inc. All rights reserved.
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
import { Classes, DISPLAYNAME_PREFIX, Utils } from "../../common";
import { isReactNodeEmpty } from "../../common/utils";
import { Icon } from "../icon/icon";
import { Text } from "../text/text";
import { TagRemoveButton } from "./tagRemoveButton";
/**
 * Compound tag component.
 *
 * @see https://blueprintjs.com/docs/#core/components/compound-tag
 */
export const CompoundTag = forwardRef((props, ref) => {
    const { active = false, children, className, endIcon, fill = false, icon, intent, interactive = false, leftContent, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large = false, minimal = false, onRemove, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    rightIcon, round = false, size = "medium", tabIndex = 0, ...htmlProps } = props;
    const isRemovable = Utils.isFunction(onRemove);
    const tagClasses = classNames(Classes.TAG, Classes.COMPOUND_TAG, Classes.intentClass(intent), Classes.sizeClass(size, { large }), {
        [Classes.ACTIVE]: active,
        [Classes.FILL]: fill,
        [Classes.INTERACTIVE]: interactive,
        [Classes.MINIMAL]: minimal,
        [Classes.ROUND]: round,
    }, className);
    return (_jsxs("span", { ...htmlProps, className: tagClasses, tabIndex: interactive ? tabIndex : undefined, ref: ref, children: [_jsxs("span", { className: Classes.COMPOUND_TAG_LEFT, children: [_jsx(Icon, { icon: icon }), _jsx(Text, { className: classNames(Classes.COMPOUND_TAG_LEFT_CONTENT, Classes.FILL), tagName: "span", children: leftContent })] }), _jsxs("span", { className: Classes.COMPOUND_TAG_RIGHT, children: [!isReactNodeEmpty(children) && (_jsx(Text, { className: classNames(Classes.COMPOUND_TAG_RIGHT_CONTENT, Classes.FILL), tagName: "span", children: children })), _jsx(Icon, { icon: endIcon ?? rightIcon }), isRemovable && _jsx(TagRemoveButton, { ...props })] })] }));
});
CompoundTag.displayName = `${DISPLAYNAME_PREFIX}.CompoundTag`;
//# sourceMappingURL=compoundTag.js.map