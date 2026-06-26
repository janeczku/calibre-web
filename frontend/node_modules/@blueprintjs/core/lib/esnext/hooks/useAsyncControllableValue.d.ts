interface UseAsyncControllableValueProps<E extends HTMLInputElement | HTMLTextAreaElement> {
    value?: React.InputHTMLAttributes<E>["value"];
    onChange?: React.ChangeEventHandler<E>;
    onCompositionStart?: React.CompositionEventHandler<E>;
    onCompositionEnd?: React.CompositionEventHandler<E>;
}
/**
 * The amount of time (in milliseconds) which the input will wait after a compositionEnd event before
 * unlocking its state value for external updates via props. See `handleCompositionEnd` for more details.
 */
export declare const ASYNC_CONTROLLABLE_VALUE_COMPOSITION_END_DELAY = 10;
/**
 * A hook to workaround the following [React bug](https://github.com/facebook/react/issues/3926).
 * This bug is reproduced when an input receives CompositionEvents
 * (for example, through IME composition) and has its value prop updated asychronously.
 * This might happen if a component chooses to do async validation of a value
 * returned by the input's `onChange` callback.
 */
export declare function useAsyncControllableValue<E extends HTMLInputElement | HTMLTextAreaElement>(props: UseAsyncControllableValueProps<E>): {
    onChange: import("react").ChangeEventHandler<E>;
    onCompositionEnd: import("react").CompositionEventHandler<E>;
    onCompositionStart: import("react").CompositionEventHandler<E>;
    value: string | number | readonly string[] | undefined;
};
export {};
