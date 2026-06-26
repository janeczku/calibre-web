import type { Alignment, NonSmallSize } from "../../common";
import type { HTMLInputProps, Props } from "../../common/props";
export interface CheckedControlProps {
    /** Whether the control is checked. */
    checked?: boolean;
    /** Whether the control is initially checked (uncontrolled mode). */
    defaultChecked?: boolean;
    /** Event handler invoked when input value is changed. */
    onChange?: React.ChangeEventHandler<HTMLInputElement>;
}
/**
 * Shared props for form control components like Switch, Checkbox, and Radio.
 */
export interface ControlProps extends CheckedControlProps, Props, Omit<HTMLInputProps, "size">, React.RefAttributes<HTMLLabelElement> {
    /**
     * Alignment of the indicator within container.
     *
     * @default Alignment.START
     */
    alignIndicator?: Alignment;
    /** JSX label for the control. */
    children?: React.ReactNode;
    /** Whether the control is non-interactive. */
    disabled?: boolean;
    /** Whether the control should appear as an inline element. */
    inline?: boolean;
    /** Ref attached to the HTML `<input>` element backing this component. */
    inputRef?: React.Ref<HTMLInputElement>;
    /**
     * Text label for the control.
     *
     * Use `children` or `labelElement` to supply JSX content. This prop actually supports JSX elements,
     * but TypeScript will throw an error because `HTMLAttributes` only allows strings.
     */
    label?: string;
    /**
     * JSX element label for the control.
     *
     * This prop is a workaround for TypeScript consumers as the type definition for `label` only
     * accepts strings. JavaScript consumers can provide a JSX element directly to `label`.
     */
    labelElement?: React.ReactNode;
    /**
     * Whether this control should use large styles.
     *
     * @deprecated use `size="large"` instead
     * @default false
     */
    large?: boolean;
    /**
     * Size of the control.
     *
     * @default "medium"
     */
    size?: NonSmallSize;
    /**
     * Name of the HTML tag that wraps the checkbox.
     *
     * By default a `<label>` is used, which effectively enlarges the click
     * target to include all of its children. Supply a different tag name if
     * this behavior is undesirable or you're listening to click events from a
     * parent element (as the label can register duplicate clicks).
     *
     * @default "label"
     */
    tagName?: keyof React.JSX.IntrinsicElements;
}
