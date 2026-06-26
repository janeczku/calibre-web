import { type IconName } from "@blueprintjs/icons";
import { AbstractPureComponent, type NonSmallSize } from "../../common";
import { type HTMLInputProps, type IntentProps, type MaybeElement, type Props } from "../../common/props";
import { type TagProps } from "../tag/tag";
/**
 * The method in which a `TagInput` value was added.
 * - `"default"` - indicates that a value was added by manual selection.
 * - `"blur"` - indicates that a value was added when the `TagInput` lost focus.
 *   This is only possible when `addOnBlur=true`.
 * - `"paste"` - indicates that a value was added via paste. This is only
 *   possible when `addOnPaste=true`.
 */
export type TagInputAddMethod = "default" | "blur" | "paste";
export interface TagInputProps extends IntentProps, Props {
    /**
     * If true, `onAdd` will be invoked when the input loses focus.
     * Otherwise, `onAdd` is only invoked when `enter` is pressed.
     *
     * @default false
     */
    addOnBlur?: boolean;
    /**
     * If true, `onAdd` will be invoked when the user pastes text containing the `separator`
     * into the input. Otherwise, pasted text will remain in the input.
     *
     * __Note:__ For example, if `addOnPaste=true` and `separator="\n"` (new line), then:
     * - Pasting `"hello"` will _not_ invoke `onAdd`
     * - Pasting `"hello\n"` will invoke `onAdd` with `["hello"]`
     * - Pasting `"hello\nworld"` will invoke `onAdd` with `["hello", "world"]`
     *
     * @default true
     */
    addOnPaste?: boolean;
    /**
     * Whether the component should automatically resize as a user types in the text input.
     * This will have no effect when `fill={true}`.
     *
     * @default false
     */
    autoResize?: boolean;
    /**
     * Optional child elements which will be rendered between the selected tags and
     * the text input. Rendering children is usually unnecessary.
     *
     * @default undefined
     */
    children?: React.ReactNode;
    /**
     * Whether the component is non-interactive.
     * Note that you'll also need to disable the component's `rightElement`,
     * if appropriate.
     *
     * @default false
     */
    disabled?: boolean;
    /** Whether the tag input should take up the full width of its container. */
    fill?: boolean;
    /**
     * React props to pass to the `<input>` element.
     * Note that `ref` and `key` are not supported here; use `inputRef` below.
     * Also note that `inputProps.style.width` will be overriden if `autoResize={true}`.
     */
    inputProps?: HTMLInputProps;
    /** Ref handler for the `<input>` element. */
    inputRef?: React.Ref<HTMLInputElement>;
    /** Controlled value of the `<input>` element. This is shorthand for `inputProps={{ value }}`. */
    inputValue?: string;
    /**
     * Whether the tag input should use a large size.
     *
     * @deprecated use `size="large"` instead.
     * @default false
     */
    large?: boolean;
    /** Name of a Blueprint UI icon (or an icon element) to render on the left side of the input. */
    leftIcon?: IconName | MaybeElement;
    /**
     * Callback invoked when new tags are added by the user pressing `enter` on the input.
     * Receives the current value of the input field split by `separator` into an array.
     * New tags are expected to be appended to the list.
     *
     * The input will be cleared after `onAdd` is invoked _unless_ the callback explicitly
     * returns `false`. This is useful if the provided `value` is somehow invalid and should
     * not be added as a tag.
     */
    onAdd?: (values: string[], method: TagInputAddMethod) => boolean | void;
    /**
     * Callback invoked when new tags are added or removed. Receives the updated list of `values`:
     * new tags are appended to the end of the list, removed tags are removed at their index.
     *
     * Like `onAdd`, the input will be cleared after this handler is invoked _unless_ the callback
     * explicitly returns `false`.
     *
     * This callback essentially implements basic `onAdd` and `onRemove` functionality and merges
     * the two handlers into one to simplify controlled usage.
     * ```
     */
    onChange?: (values: React.ReactNode[]) => boolean | void;
    /**
     * Callback invoked when the value of `<input>` element is changed.
     * This is shorthand for `inputProps={{ onChange }}`.
     */
    onInputChange?: React.ChangeEventHandler<HTMLInputElement>;
    /**
     * Callback invoked when the user depresses a keyboard key.
     * Receives the event and the index of the active tag (or `undefined` if
     * focused in the input).
     */
    onKeyDown?: (event: React.KeyboardEvent<HTMLElement>, index?: number) => void;
    /**
     * Callback invoked when the user releases a keyboard key.
     * Receives the event and the index of the active tag (or `undefined` if
     * focused in the input).
     */
    onKeyUp?: (event: React.KeyboardEvent<HTMLElement>, index?: number) => void;
    /**
     * Callback invoked when the user clicks the X button on a tag.
     * Receives value and index of removed tag.
     */
    onRemove?: (value: React.ReactNode, index: number) => void;
    /**
     * Input placeholder text which will not appear if `values` contains any items
     * (consistent with default HTML input behavior).
     * Use `inputProps.placeholder` if you want the placeholder text to _always_ appear.
     *
     * If you define both `placeholder` and `inputProps.placeholder`, then the former will appear
     * when `values` is empty and the latter at all other times.
     */
    placeholder?: string;
    /**
     * Element to render on right side of input.
     * For best results, use a small spinner or minimal button (button height will adjust if `TagInput` uses large styles).
     * Other elements will likely require custom styles for correct positioning.
     */
    rightElement?: React.JSX.Element;
    /**
     * Separator pattern used to split input text into multiple values. Default value splits on commas and newlines.
     * Explicit `false` value disables splitting (note that `onAdd` will still receive an array of length 1).
     *
     * @default /[,\n\r]/
     */
    separator?: string | RegExp | false;
    /**
     * The size of the tag input.
     *
     * @default "medium"
     */
    size?: NonSmallSize;
    /**
     * React props to pass to each `Tag`. Provide an object to pass the same props to every tag,
     * or a function to customize props per tag.
     *
     * If you define `onRemove` here then you will have to implement your own tag removal
     * handling as `TagInput`'s own `onRemove` handler will never be invoked.
     */
    tagProps?: TagProps | ((value: React.ReactNode, index: number) => TagProps);
    /**
     * Controlled tag values. Each value will be rendered inside a `Tag`, which can be customized
     * using `tagProps`. Therefore, any valid React node can be used as a `TagInput` value; falsy
     * values will not be rendered.
     */
    values: readonly React.ReactNode[];
}
export interface TagInputState {
    activeIndex: number;
    inputValue: string;
    isInputFocused: boolean;
    prevInputValueProp?: string;
}
/**
 * Tag input component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tag-input
 */
export declare class TagInput extends AbstractPureComponent<TagInputProps, TagInputState> {
    static displayName: string;
    static defaultProps: Partial<TagInputProps>;
    static getDerivedStateFromProps(props: Readonly<TagInputProps>, state: Readonly<TagInputState>): Partial<TagInputState> | null;
    state: TagInputState;
    inputElement: HTMLInputElement | null;
    private handleRef;
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidUpdate(prevProps: TagInputProps): void;
    private addTags;
    private maybeRenderTag;
    private getNextActiveIndex;
    private findNextIndex;
    /**
     * Splits inputValue on separator prop,
     * trims whitespace from each new value,
     * and ignores empty values.
     */
    private getValues;
    private handleContainerClick;
    private handleContainerBlur;
    private handleInputFocus;
    private handleInputChange;
    private handleInputKeyDown;
    private handleInputKeyUp;
    private handleInputPaste;
    private handleRemoveTag;
    private handleBackspaceToRemove;
    private handleDeleteToRemove;
    /** Remove the item at the given index by invoking `onRemove` and `onChange` accordingly. */
    private removeIndexFromValues;
    private invokeKeyPressCallback;
    /** Returns whether the given index represents a valid item in `this.props.values`. */
    private isValidIndex;
}
