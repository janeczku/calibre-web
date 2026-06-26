"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Checkbox = exports.Radio = exports.Switch = void 0;
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
const common_1 = require("../../common");
const props_1 = require("../../common/props");
/**
 * Renders common control elements, with additional props to customize appearance.
 * This component is not exported and is only used within this module for `Checkbox`, `Radio`, and `Switch` below.
 */
const ControlInternal = (0, react_1.forwardRef)((props, ref) => {
    const { alignIndicator, children, className, indicatorChildren, inline, inputRef, label, labelElement, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large, size = "medium", style, type, typeClassName, tagName = "label", ...htmlProps } = props;
    const classes = (0, classnames_1.default)(common_1.Classes.CONTROL, typeClassName, {
        [common_1.Classes.DISABLED]: htmlProps.disabled,
        [common_1.Classes.INLINE]: inline,
    }, common_1.Classes.alignmentClass(alignIndicator), common_1.Classes.sizeClass(size, { large }), className);
    return (0, react_1.createElement)(tagName, { className: classes, ref, style }, (0, jsx_runtime_1.jsx)("input", { className: common_1.Classes.CONTROL_INPUT, ...htmlProps, ref: inputRef, type: type }), (0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.CONTROL_INDICATOR, children: indicatorChildren }), label, labelElement, children);
});
ControlInternal.displayName = `${props_1.DISPLAYNAME_PREFIX}.Control`;
/**
 * Switch component.
 *
 * @see https://blueprintjs.com/docs/#core/components/switch
 */
exports.Switch = (0, react_1.forwardRef)((props, ref) => {
    const { innerLabelChecked, innerLabel, ...controlProps } = props;
    const switchLabels = innerLabel || innerLabelChecked
        ? [
            (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.CONTROL_INDICATOR_CHILD, children: (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.SWITCH_INNER_TEXT, children: innerLabelChecked ? innerLabelChecked : innerLabel }) }, "checked"),
            (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.CONTROL_INDICATOR_CHILD, children: (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.SWITCH_INNER_TEXT, children: innerLabel }) }, "unchecked"),
        ]
        : null;
    return ((0, jsx_runtime_1.jsx)(ControlInternal, { ...controlProps, indicatorChildren: switchLabels, ref: ref, type: "checkbox", typeClassName: common_1.Classes.SWITCH }));
});
exports.Switch.displayName = `${props_1.DISPLAYNAME_PREFIX}.Switch`;
/**
 * Radio component.
 *
 * @see https://blueprintjs.com/docs/#core/components/radio
 */
exports.Radio = (0, react_1.forwardRef)((props, ref) => {
    return (0, jsx_runtime_1.jsx)(ControlInternal, { ...props, ref: ref, type: "radio", typeClassName: common_1.Classes.RADIO });
});
exports.Radio.displayName = `${props_1.DISPLAYNAME_PREFIX}.Radio`;
/**
 * Checkbox component.
 *
 * @see https://blueprintjs.com/docs/#core/components/checkbox
 */
exports.Checkbox = (0, react_1.forwardRef)((props, ref) => {
    const { defaultIndeterminate, indeterminate, onChange, ...controlProps } = props;
    const [isIndeterminate, setIsIndeterminate] = (0, react_1.useState)(indeterminate || defaultIndeterminate || false);
    const localInputRef = (0, react_1.useRef)(null);
    const inputRef = (0, common_1.mergeRefs)(props.inputRef, localInputRef);
    const handleChange = (0, react_1.useCallback)((evt) => {
        // update state immediately only if uncontrolled
        if (indeterminate === undefined) {
            setIsIndeterminate(evt.target.indeterminate);
        }
        // otherwise wait for props change. always invoke handler.
        onChange?.(evt);
    }, [indeterminate, onChange]);
    (0, react_1.useEffect)(() => {
        if (indeterminate !== undefined) {
            setIsIndeterminate(indeterminate);
        }
    }, [indeterminate]);
    (0, react_1.useEffect)(() => {
        if (localInputRef.current != null) {
            localInputRef.current.indeterminate = isIndeterminate;
        }
    }, [localInputRef, isIndeterminate]);
    return ((0, jsx_runtime_1.jsx)(ControlInternal, { ...controlProps, inputRef: inputRef, onChange: handleChange, ref: ref, type: "checkbox", typeClassName: common_1.Classes.CHECKBOX }));
});
exports.Checkbox.displayName = `${props_1.DISPLAYNAME_PREFIX}.Checkbox`;
//# sourceMappingURL=controls.js.map