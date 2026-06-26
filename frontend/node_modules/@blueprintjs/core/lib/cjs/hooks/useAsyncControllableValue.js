"use strict";
/* !
 * (c) Copyright 2023 Palantir Technologies Inc. All rights reserved.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ASYNC_CONTROLLABLE_VALUE_COMPOSITION_END_DELAY = void 0;
exports.useAsyncControllableValue = useAsyncControllableValue;
const react_1 = require("react");
/**
 * The amount of time (in milliseconds) which the input will wait after a compositionEnd event before
 * unlocking its state value for external updates via props. See `handleCompositionEnd` for more details.
 */
exports.ASYNC_CONTROLLABLE_VALUE_COMPOSITION_END_DELAY = 10;
/**
 * A hook to workaround the following [React bug](https://github.com/facebook/react/issues/3926).
 * This bug is reproduced when an input receives CompositionEvents
 * (for example, through IME composition) and has its value prop updated asychronously.
 * This might happen if a component chooses to do async validation of a value
 * returned by the input's `onChange` callback.
 */
function useAsyncControllableValue(props) {
    const { onCompositionStart, onCompositionEnd, value: propValue, onChange } = props;
    // The source of truth for the input value. This is not updated during IME composition.
    // It may be updated by a parent component.
    const [value, setValue] = (0, react_1.useState)(propValue);
    // The latest input value, which updates during IME composition.
    const [nextValue, setNextValue] = (0, react_1.useState)(propValue);
    // Whether we are in the middle of a composition event.
    const [isComposing, setIsComposing] = (0, react_1.useState)(false);
    // Whether there is a pending update we are expecting from a parent component.
    const [hasPendingUpdate, setHasPendingUpdate] = (0, react_1.useState)(false);
    const cancelPendingCompositionEnd = (0, react_1.useRef)();
    const handleCompositionStart = (0, react_1.useCallback)(event => {
        cancelPendingCompositionEnd.current?.();
        setIsComposing(true);
        onCompositionStart?.(event);
    }, [onCompositionStart]);
    // creates a timeout which will set `isComposing` to false after a delay
    // returns a function which will cancel the timeout if called before it fires
    const createOnCancelPendingCompositionEnd = (0, react_1.useCallback)(() => {
        const timeoutId = window.setTimeout(() => setIsComposing(false), exports.ASYNC_CONTROLLABLE_VALUE_COMPOSITION_END_DELAY);
        return () => window.clearTimeout(timeoutId);
    }, []);
    const handleCompositionEnd = (0, react_1.useCallback)(event => {
        // In some non-latin languages, a keystroke can end a composition event and immediately afterwards start another.
        // This can lead to unexpected characters showing up in the text input. In order to circumvent this problem, we
        // use a timeout which creates a delay which merges the two composition events, creating a more natural and predictable UX.
        // `this.state.nextValue` will become "locked" (it cannot be overwritten by the `value` prop) until a delay (10ms) has
        // passed without a new composition event starting.
        cancelPendingCompositionEnd.current = createOnCancelPendingCompositionEnd();
        onCompositionEnd?.(event);
    }, [createOnCancelPendingCompositionEnd, onCompositionEnd]);
    const handleChange = (0, react_1.useCallback)(event => {
        const { value: targetValue } = event.target;
        setNextValue(targetValue);
        onChange?.(event);
    }, [onChange]);
    // don't derive anything from props if:
    // - in uncontrolled mode, OR
    // - currently composing, since we'll do that after composition ends
    const shouldDeriveFromProps = !(isComposing || propValue === undefined);
    if (shouldDeriveFromProps) {
        const userTriggeredUpdate = nextValue !== value;
        if (userTriggeredUpdate && propValue === nextValue) {
            // parent has processed and accepted our update
            setValue(propValue);
            setHasPendingUpdate(false);
        }
        else if (userTriggeredUpdate && propValue === value) {
            // we have sent the update to our parent, but it has not been processed yet. just wait.
            // DO NOT set nextValue here, since that will temporarily render a potentially stale controlled value,
            // causing the cursor to jump once the new value is accepted
            if (!hasPendingUpdate) {
                // make sure to setState only when necessary to avoid infinite loops
                setHasPendingUpdate(true);
            }
        }
        else if (userTriggeredUpdate && propValue !== value) {
            // accept controlled update overriding user action
            setValue(propValue);
            setNextValue(propValue);
            setHasPendingUpdate(false);
        }
        else if (!userTriggeredUpdate) {
            // accept controlled update, could be confirming or denying user action
            if (value !== propValue || hasPendingUpdate) {
                // make sure to setState only when necessary to avoid infinite loops
                setValue(propValue);
                setNextValue(propValue);
                setHasPendingUpdate(false);
            }
        }
    }
    return {
        onChange: handleChange,
        onCompositionEnd: handleCompositionEnd,
        onCompositionStart: handleCompositionStart,
        // render the pending value even if it is not confirmed by a parent's async controlled update
        // so that the cursor does not jump to the end of input as reported in
        // https://github.com/palantir/blueprint/issues/4298
        value: isComposing || hasPendingUpdate ? nextValue : value,
    };
}
//# sourceMappingURL=useAsyncControllableValue.js.map