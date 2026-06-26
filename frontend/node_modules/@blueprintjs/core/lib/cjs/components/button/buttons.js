"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AnchorButton = exports.Button = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const useInteractiveAttributes_1 = require("../../accessibility/useInteractiveAttributes");
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const icon_1 = require("../icon/icon");
const spinner_1 = require("../spinner/spinner");
const text_1 = require("../text/text");
/**
 * Button component.
 *
 * @see https://blueprintjs.com/docs/#core/components/button
 */
exports.Button = (0, react_1.forwardRef)((props, ref) => {
    const commonAttributes = useSharedButtonAttributes(props, ref);
    return ((0, jsx_runtime_1.jsx)("button", { type: "button", ...(0, props_1.removeNonHTMLProps)(props), ...commonAttributes, children: renderButtonContents(props) }));
});
exports.Button.displayName = `${props_1.DISPLAYNAME_PREFIX}.Button`;
/**
 * AnchorButton component.
 *
 * @see https://blueprintjs.com/docs/#core/components/button
 */
exports.AnchorButton = (0, react_1.forwardRef)((props, ref) => {
    const { href } = props;
    const commonProps = useSharedButtonAttributes(props, ref, {
        defaultTabIndex: 0,
        disabledTabIndex: -1,
    });
    return ((0, jsx_runtime_1.jsx)("a", { role: "button", ...(0, props_1.removeNonHTMLProps)(props), ...commonProps, "aria-disabled": commonProps.disabled, href: commonProps.disabled ? undefined : href, children: renderButtonContents(props) }));
});
exports.AnchorButton.displayName = `${props_1.DISPLAYNAME_PREFIX}.AnchorButton`;
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
    const [active, interactiveProps] = (0, useInteractiveAttributes_1.useInteractiveAttributes)(!disabled, props, ref, options);
    const className = (0, classnames_1.default)(common_1.Classes.BUTTON, {
        [common_1.Classes.ACTIVE]: active,
        [common_1.Classes.DISABLED]: disabled,
        [common_1.Classes.FILL]: fill,
        [common_1.Classes.LOADING]: loading,
    }, common_1.Classes.alignmentClass(alignText), common_1.Classes.intentClass(props.intent), common_1.Classes.sizeClass(size, { large, small }), common_1.Classes.variantClass(variant, { minimal, outlined }), props.className);
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
    const hasTextContent = !common_1.Utils.isReactNodeEmpty(text) || !common_1.Utils.isReactNodeEmpty(children);
    return ((0, jsx_runtime_1.jsxs)(jsx_runtime_1.Fragment, { children: [loading && (0, jsx_runtime_1.jsx)(spinner_1.Spinner, { className: common_1.Classes.BUTTON_SPINNER, size: spinner_1.SpinnerSize.SMALL }), (0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: icon }), hasTextContent && ((0, jsx_runtime_1.jsxs)(text_1.Text, { className: (0, classnames_1.default)(common_1.Classes.BUTTON_TEXT, textClassName), ellipsize: ellipsizeText, tagName: "span", children: [text, children] })), (0, jsx_runtime_1.jsx)(icon_1.Icon, { icon: endIcon ?? rightIcon })] }));
}
//# sourceMappingURL=buttons.js.map