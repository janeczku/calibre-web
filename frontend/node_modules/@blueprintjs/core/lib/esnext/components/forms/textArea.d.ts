import { AbstractPureComponent } from "../../common";
import { type IntentProps, type Props } from "../../common/props";
import type { Size } from "../../common/size";
export interface TextAreaProps extends IntentProps, Props, React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    /**
     * Set this to `true` if you will be controlling the `value` of this input with asynchronous updates.
     * These may occur if you do not immediately call setState in a parent component with the value from
     * the `onChange` handler, or if working with certain libraries like __redux-form__.
     *
     * @default false
     */
    asyncControl?: boolean;
    /**
     * Whether the component should automatically resize vertically as a user types in the text input.
     * This will disable manual resizing in the vertical dimension.
     *
     * @default false
     */
    autoResize?: boolean;
    /**
     * Whether the text area should take up the full width of its container.
     *
     * @default false
     */
    fill?: boolean;
    /**
     * Ref handler that receives HTML `<textarea>` element backing this component.
     */
    inputRef?: React.Ref<HTMLTextAreaElement>;
    /**
     * Whether the text area should appear with large styling.
     *
     * @deprecated use `size="large"` instead.
     * @default false
     */
    large?: boolean;
    /**
     * Whether the text area should appear with small styling.
     *
     * @deprecated use `size="small"` instead.
     * @default false
     */
    small?: boolean;
    /**
     * The size styling of the text area.
     *
     * @default "medium"
     */
    size?: Size;
}
export interface TextAreaState {
    height?: number;
}
/**
 * Text area component.
 *
 * @see https://blueprintjs.com/docs/#core/components/text-area
 */
export declare class TextArea extends AbstractPureComponent<TextAreaProps, TextAreaState> {
    static defaultProps: TextAreaProps;
    static displayName: string;
    state: TextAreaState;
    textareaElement: HTMLTextAreaElement | null;
    private handleRef;
    private maybeSyncHeightToScrollHeight;
    componentDidMount(): void;
    componentDidUpdate(prevProps: TextAreaProps): void;
    render(): import("react/jsx-runtime").JSX.Element;
    private handleChange;
}
