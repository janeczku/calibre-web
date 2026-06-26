import { AbstractPureComponent } from "../../common";
export type AsyncControllableInputProps = React.InputHTMLAttributes<HTMLInputElement> & {
    inputRef?: React.Ref<HTMLInputElement>;
};
type InputValue = AsyncControllableInputProps["value"];
export interface AsyncControllableInputState {
    /**
     * Whether we are in the middle of a composition event.
     *
     * @default false
     */
    isComposing: boolean;
    /**
     * The source of truth for the input value. This is not updated during IME composition.
     * It may be updated by a parent component.
     *
     * @default ""
     */
    value: InputValue;
    /**
     * The latest input value, which updates during IME composition. Defaults to props.value.
     */
    nextValue: InputValue;
    /**
     * Whether there is a pending update we are expecting from a parent component.
     *
     * @default false
     */
    hasPendingUpdate: boolean;
}
/**
 * A stateful wrapper around the low-level <input> component which works around a
 * [React bug](https://github.com/facebook/react/issues/3926). This bug is reproduced when an input
 * receives CompositionEvents (for example, through IME composition) and has its value prop updated
 * asychronously. This might happen if a component chooses to do async validation of a value
 * returned by the input's `onChange` callback.
 *
 * Note: this component does not apply any Blueprint-specific styling.
 */
export declare class AsyncControllableInput extends AbstractPureComponent<AsyncControllableInputProps, AsyncControllableInputState> {
    static displayName: string;
    /**
     * The amount of time (in milliseconds) which the input will wait after a compositionEnd event before
     * unlocking its state value for external updates via props. See `handleCompositionEnd` for more details.
     */
    static COMPOSITION_END_DELAY: number;
    state: AsyncControllableInputState;
    private cancelPendingCompositionEnd;
    static getDerivedStateFromProps(nextProps: AsyncControllableInputProps, nextState: AsyncControllableInputState): Partial<AsyncControllableInputState> | null;
    render(): import("react/jsx-runtime").JSX.Element;
    private handleCompositionStart;
    private handleCompositionEnd;
    private handleChange;
}
export {};
