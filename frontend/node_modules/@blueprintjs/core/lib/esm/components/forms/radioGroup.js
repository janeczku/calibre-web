import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { createElement as _createElement } from "react";
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
import { Children, cloneElement, useCallback, useMemo } from "react";
import { Classes, DISPLAYNAME_PREFIX, removeNonHTMLProps, } from "../../common";
import * as Errors from "../../common/errors";
import { isElementOfType, uniqueId } from "../../common/utils";
import { useValidateProps } from "../../hooks/useValidateProps";
import { RadioCard } from "../control-card/radioCard";
import { Radio } from "./controls";
/**
 * Radio group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/radio.radiogroup
 */
export const RadioGroup = props => {
    const { children, className, disabled, inline, label, name, onChange, options, selectedValue, ...htmlProps } = props;
    // a unique name for this group, which can be overridden by `name` prop.
    const autoGroupName = useMemo(() => nextName(), []);
    const labelId = useMemo(() => uniqueId("label"), []);
    useValidateProps(() => {
        if (children != null && options != null) {
            console.warn(Errors.RADIOGROUP_WARN_CHILDREN_OPTIONS_MUTEX);
        }
    }, [children, options]);
    const getRadioProps = useCallback((optionProps) => {
        const { className: optionClassName, disabled: optionDisabled, value } = optionProps;
        return {
            checked: value === selectedValue,
            className: optionClassName,
            disabled: optionDisabled || disabled,
            inline,
            name: name == null ? autoGroupName : name,
            onChange,
            value,
        };
    }, [autoGroupName, disabled, inline, name, onChange, selectedValue]);
    const renderChildren = () => {
        return Children.map(children, child => {
            if (isElementOfType(child, Radio) || isElementOfType(child, RadioCard)) {
                return cloneElement(
                // Need this cast here to suppress a TS error caused by differing `ref` types for the Radio and
                // RadioCard components. We aren't injecting a ref, so we don't need to be strict about that
                // incompatibility.
                child, getRadioProps(child.props));
            }
            return child;
        });
    };
    const renderOptions = () => {
        return options?.map(option => (_createElement(Radio, { ...getRadioProps(option), key: option.value, labelElement: option.label || option.value })));
    };
    return (_jsxs("div", { role: "radiogroup", "aria-labelledby": label ? labelId : undefined, ...removeNonHTMLProps(htmlProps), className: classNames(Classes.RADIO_GROUP, className), children: [label && (_jsx("label", { className: Classes.LABEL, id: labelId, children: label })), Array.isArray(options) ? renderOptions() : renderChildren()] }));
};
RadioGroup.displayName = `${DISPLAYNAME_PREFIX}.RadioGroup`;
let counter = 0;
function nextName() {
    return `${RadioGroup.displayName}-${counter++}`;
}
//# sourceMappingURL=radioGroup.js.map