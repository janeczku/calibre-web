import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
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
import { useInteractiveAttributes, } from "../../accessibility/useInteractiveAttributes";
import { Classes, Utils } from "../../common";
import { DISPLAYNAME_PREFIX, removeNonHTMLProps } from "../../common/props";
import { Icon } from "../icon/icon";
import { Spinner, SpinnerSize } from "../spinner/spinner";
import { Text } from "../text/text";
/**
 * Button component.
 *
 * @see https://blueprintjs.com/docs/#core/components/button
 */
export const Button = forwardRef((props, ref) => {
    const commonAttributes = useSharedButtonAttributes(props, ref);
    return (_jsx("button", { type: "button", ...removeNonHTMLProps(props), ...commonAttributes, children: renderButtonContents(props) }));
});
Button.displayName = `${DISPLAYNAME_PREFIX}.Button`;
/**
 * AnchorButton component.
 *
 * @see https://blueprintjs.com/docs/#core/components/button
 */
export const AnchorButton = forwardRef((props, ref) => {
    const { href } = props;
    const commonProps = useSharedButtonAttributes(props, ref, {
        defaultTabIndex: 0,
        disabledTabIndex: -1,
    });
    return (_jsx("a", { role: "button", ...removeNonHTMLProps(props), ...commonProps, "aria-disabled": commonProps.disabled, href: commonProps.disabled ? undefined : href, children: renderButtonContents(props) }));
});
AnchorButton.displayName = `${DISPLAYNAME_PREFIX}.AnchorButton`;
/**
 * Most of the button logic lives in this shared hook.
 */
function useSharedButtonAttributes(props, ref, options) {
    const { alignText, fill, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large, loading = false, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    minimal, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    outlined, size = "medium", 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    small, variant = "solid", } = props;
    const disabled = props.disabled || loading;
    const [active, interactiveProps] = useInteractiveAttributes(!disabled, props, ref, options);
    const className = classNames(Classes.BUTTON, {
        [Classes.ACTIVE]: active,
        [Classes.DISABLED]: disabled,
        [Classes.FILL]: fill,
        [Classes.LOADING]: loading,
    }, Classes.alignmentClass(alignText), Classes.intentClass(props.intent), Classes.sizeClass(size, { large, small }), Classes.variantClass(variant, { minimal, outlined }), props.className);
    return {
        ...interactiveProps,
        className,
        disabled,
    };
}
/**
 * Shared rendering code for button contents.
 */
function renderButtonContents(props) {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const { children, ellipsizeText, endIcon, icon, loading, rightIcon, text, textClassName } = props;
    const hasTextContent = !Utils.isReactNodeEmpty(text) || !Utils.isReactNodeEmpty(children);
    return (_jsxs(_Fragment, { children: [loading && _jsx(Spinner, { className: Classes.BUTTON_SPINNER, size: SpinnerSize.SMALL }), _jsx(Icon, { icon: icon }), hasTextContent && (_jsxs(Text, { className: classNames(Classes.BUTTON_TEXT, textClassName), ellipsize: ellipsizeText, tagName: "span", children: [text, children] })), _jsx(Icon, { icon: endIcon ?? rightIcon })] }));
}
//# sourceMappingURL=buttons.js.map