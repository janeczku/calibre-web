/* !
 * (c) Copyright 2024 Palantir Technologies Inc. All rights reserved.
 */
import { useCallback, useRef, useState } from "react";
import { mergeRefs, Utils } from "../common";
const DEFAULT_OPTIONS = { defaultTabIndex: undefined, disabledTabIndex: -1 };
export function useInteractiveAttributes(interactive, props, ref, options = DEFAULT_OPTIONS) {
    const { defaultTabIndex, disabledTabIndex } = options;
    const { active, onClick, onFocus, onKeyDown, onKeyUp, onBlur, tabIndex = defaultTabIndex } = props;
    // the current key being pressed
    const [currentKeyPressed, setCurrentKeyPressed] = useState();
    // whether the button is in "active" state
    const [isActive, setIsActive] = useState(false);
    // our local ref for the interactive element, merged with the consumer's own ref in this hook's return value
    const elementRef = useRef(null);
    const handleBlur = useCallback((e) => {
        if (isActive) {
            setIsActive(false);
        }
        onBlur?.(e);
    }, [isActive, onBlur]);
    const handleKeyDown = useCallback((e) => {
        if (Utils.isKeyboardClick(e)) {
            e.preventDefault();
            if (e.key !== currentKeyPressed) {
                setIsActive(true);
            }
        }
        setCurrentKeyPressed(e.key);
        onKeyDown?.(e);
    }, [currentKeyPressed, onKeyDown]);
    const handleKeyUp = useCallback((e) => {
        if (Utils.isKeyboardClick(e)) {
            setIsActive(false);
            elementRef.current?.click();
        }
        setCurrentKeyPressed(undefined);
        onKeyUp?.(e);
    }, [onKeyUp, elementRef]);
    const resolvedActive = interactive && (active || isActive);
    return [
        resolvedActive,
        {
            onBlur: handleBlur,
            onClick: interactive ? onClick : undefined,
            onFocus: interactive ? onFocus : undefined,
            onKeyDown: handleKeyDown,
            onKeyUp: handleKeyUp,
            ref: mergeRefs(elementRef, ref),
            tabIndex: interactive ? tabIndex : disabledTabIndex,
        },
    ];
}
//# sourceMappingURL=useInteractiveAttributes.js.map