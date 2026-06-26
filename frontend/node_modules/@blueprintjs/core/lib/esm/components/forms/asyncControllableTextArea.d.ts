export type AsyncControllableTextAreaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;
/**
 * A wrapper around the low-level <textarea> component which works around a React bug
 * the same way <AsyncControllableInput> does.
 */
export declare const AsyncControllableTextArea: import("react").ForwardRefExoticComponent<AsyncControllableTextAreaProps & import("react").RefAttributes<HTMLTextAreaElement>>;
