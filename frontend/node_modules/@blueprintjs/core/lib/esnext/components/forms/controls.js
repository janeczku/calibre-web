import { jsx as _jsx } from "react/jsx-runtime";
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
import { createElement, forwardRef, useCallback, useEffect, useRef, useState } from "react";
import { Classes, mergeRefs } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
/**
 * Renders common control elements, with additional props to customize appearance.
 * This component is not exported and is only used within this module for `Checkbox`, `Radio`, and `Switch` below.
 */
const ControlInternal = forwardRef((props, ref) => {
    const { alignIndicator, children, className, indicatorChildren, inline, inputRef, label, labelElement, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large, size = "medium", style, type, typeClassName, tagName = "label", ...htmlProps } = props;
    const classes = classNames(Classes.CONTROL, typeClassName, {
        [Classes.DISABLED]: htmlProps.disabled,
        [Classes.INLINE]: inline,
    }, Classes.alignmentClass(alignIndicator), Classes.sizeClass(size, { large }), className);
    return createElement(tagName, { className: classes, ref, style }, _jsx("input", { className: Classes.CONTROL_INPUT, ...htmlProps, ref: inputRef, type: type }), _jsx("span", { className: Classes.CONTROL_INDICATOR, children: indicatorChildren }), label, labelElement, children);
});
ControlInternal.displayName = `${DISPLAYNAME_PREFIX}.Control`;
/**
 * Switch component.
 *
 * @see https://blueprintjs.com/docs/#core/components/switch
 */
export const Switch = forwardRef((props, ref) => {
    const { innerLabelChecked, innerLabel, ...controlProps } = props;
    const switchLabels = innerLabel || innerLabelChecked
        ? [
            _jsx("div", { className: Classes.CONTROL_INDICATOR_CHILD, children: _jsx("div", { className: Classes.SWITCH_INNER_TEXT, children: innerLabelChecked ? innerLabelChecked : innerLabel }) }, "checked"),
            _jsx("div", { className: Classes.CONTROL_INDICATOR_CHILD, children: _jsx("div", { className: Classes.SWITCH_INNER_TEXT, children: innerLabel }) }, "unchecked"),
        ]
        : null;
    return (_jsx(ControlInternal, { ...controlProps, indicatorChildren: switchLabels, ref: ref, type: "checkbox", typeClassName: Classes.SWITCH }));
});
Switch.displayName = `${DISPLAYNAME_PREFIX}.Switch`;
/**
 * Radio component.
 *
 * @see https://blueprintjs.com/docs/#core/components/radio
 */
export const Radio = forwardRef((props, ref) => {
    return _jsx(ControlInternal, { ...props, ref: ref, type: "radio", typeClassName: Classes.RADIO });
});
Radio.displayName = `${DISPLAYNAME_PREFIX}.Radio`;
/**
 * Checkbox component.
 *
 * @see https://blueprintjs.com/docs/#core/components/checkbox
 */
export const Checkbox = forwardRef((props, ref) => {
    const { defaultIndeterminate, indeterminate, onChange, ...controlProps } = props;
    const [isIndeterminate, setIsIndeterminate] = useState(indeterminate || defaultIndeterminate || false);
    const localInputRef = useRef(null);
    const inputRef = mergeRefs(props.inputRef, localInputRef);
    const handleChange = useCallback((evt) => {
        // update state immediately only if uncontrolled
        if (indeterminate === undefined) {
            setIsIndeterminate(evt.target.indeterminate);
        }
        // otherwise wait for props change. always invoke handler.
        onChange?.(evt);
    }, [indeterminate, onChange]);
    useEffect(() => {
        if (indeterminate !== undefined) {
            setIsIndeterminate(indeterminate);
        }
    }, [indeterminate]);
    useEffect(() => {
        if (localInputRef.current != null) {
            localInputRef.current.indeterminate = isIndeterminate;
        }
    }, [localInputRef, isIndeterminate]);
    return (_jsx(ControlInternal, { ...controlProps, inputRef: inputRef, onChange: handleChange, ref: ref, type: "checkbox", typeClassName: Classes.CHECKBOX }));
});
Checkbox.displayName = `${DISPLAYNAME_PREFIX}.Checkbox`;
//# sourceMappingURL=controls.js.map