import { jsx as _jsx } from "react/jsx-runtime";
import { createElement as _createElement } from "react";
/*
 * Copyright 2023 Palantir Technologies, Inc. All rights reserved.
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
import { forwardRef, useCallback, useRef, useState } from "react";
import { Classes, Intent, mergeRefs, Utils } from "../../common";
import { DISPLAYNAME_PREFIX, removeNonHTMLProps, } from "../../common/props";
import { Button } from "../button/buttons";
/**
 * Segmented control component.
 *
 * @see https://blueprintjs.com/docs/#core/components/segmented-control
 */
export const SegmentedControl = forwardRef((props, ref) => {
    const { className, defaultValue, disabled, fill, inline, intent = Intent.NONE, 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    large, onValueChange, options, role = "radiogroup", size = "medium", 
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    small, value: controlledValue, ...htmlProps } = props;
    const [localValue, setLocalValue] = useState(defaultValue);
    const selectedValue = controlledValue ?? localValue;
    const outerRef = useRef(null);
    const handleOptionClick = useCallback((newSelectedValue, targetElement) => {
        setLocalValue(newSelectedValue);
        onValueChange?.(newSelectedValue, targetElement);
    }, [onValueChange]);
    const handleKeyDown = useCallback((e) => {
        if (role === "radiogroup" || role === "menu") {
            // in a `radiogroup`, arrow keys select next item, not tab key.
            const direction = Utils.getArrowKeyDirection(e, ["ArrowLeft", "ArrowUp"], ["ArrowRight", "ArrowDown"]);
            const outerElement = outerRef.current;
            if (direction === undefined || !outerElement)
                return;
            const focusedElement = Utils.getActiveElement(outerElement)?.closest("button");
            if (!focusedElement)
                return;
            // must rely on DOM state because we have no way of mapping `focusedElement` to a React.JSX.Element
            const enabledOptionElements = Array.from(outerElement.querySelectorAll("button:not(:disabled)"));
            const focusedIndex = enabledOptionElements.indexOf(focusedElement);
            if (focusedIndex < 0)
                return;
            e.preventDefault();
            // auto-wrapping at 0 and `length`
            const newIndex = (focusedIndex + direction + enabledOptionElements.length) % enabledOptionElements.length;
            const newOption = enabledOptionElements[newIndex];
            newOption.click();
            newOption.focus();
        }
    }, [outerRef, role]);
    const classes = classNames(Classes.SEGMENTED_CONTROL, className, {
        [Classes.FILL]: fill,
        [Classes.INLINE]: inline,
    });
    const isAnySelected = options.some(option => selectedValue === option.value);
    const buttonRole = {
        /* eslint-disable sort-keys */
        radiogroup: "radio",
        menu: "menuitemradio",
        group: undefined,
        toolbar: undefined,
        /* eslint-enable sort-keys */
    }[role];
    return (_jsx("div", { ...removeNonHTMLProps(htmlProps), role: role, onKeyDown: handleKeyDown, className: classes, ref: mergeRefs(ref, outerRef), children: options.map((option, index) => {
            const isSelected = selectedValue === option.value;
            return (_createElement(SegmentedControlOption, { ...option, disabled: option.disabled || disabled, intent: intent, isSelected: isSelected, key: option.value, 
                // eslint-disable-next-line @typescript-eslint/no-deprecated
                large: large, onClick: handleOptionClick, size: size, 
                // eslint-disable-next-line @typescript-eslint/no-deprecated
                small: small, role: buttonRole, ...(role === "radiogroup" || role === "menu"
                    ? {
                        "aria-checked": isSelected,
                        // "roving tabIndex" on a radiogroup: https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/#kbd_roving_tabindex
                        // `!isAnySelected` accounts for case where no value is currently selected
                        // (passed value/defaultValue is not one of the values of the passed options.)
                        // In this case, set first item to be tabbable even though it's unselected.
                        tabIndex: isSelected || (index === 0 && !isAnySelected) ? 0 : -1,
                    }
                    : {
                        "aria-pressed": isSelected,
                    }) }));
        }) }));
});
SegmentedControl.displayName = `${DISPLAYNAME_PREFIX}.SegmentedControl`;
function SegmentedControlOption({ isSelected, label, onClick, value, ...buttonProps }) {
    const handleClick = useCallback((event) => onClick?.(value, event.currentTarget), [onClick, value]);
    return (_jsx(Button, { ...buttonProps, onClick: handleClick, text: label ?? value, variant: !isSelected ? "minimal" : undefined }));
}
SegmentedControlOption.displayName = `${DISPLAYNAME_PREFIX}.SegmentedControlOption`;
//# sourceMappingURL=segmentedControl.js.map