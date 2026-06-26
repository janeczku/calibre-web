import { type Alignment, type ButtonVariant, type Size } from "../../common";
import { type HTMLDivProps, type Props } from "../../common/props";
export interface ButtonGroupProps extends Props, HTMLDivProps, React.RefAttributes<HTMLDivElement> {
    /**
     * Text alignment within button. By default, icons and text will be centered
     * within the button. Passing `"start"` or `"end"` will align the button
     * text to that side and push `icon` and `endIcon` to either edge. Passing
     * `"center"` will center the text and icons together.
     */
    alignText?: Alignment;
    /** Buttons in this group. */
    children: React.ReactNode;
    /**
     * Whether the button group should take up the full width of its container.
     *
     * @default false
     */
    fill?: boolean;
    /**
     * Whether the child buttons should appear with minimal styling.
     *
     * @deprecated use `variant="minimal"` instead
     * @default false
     */
    minimal?: boolean;
    /**
     * Whether the child buttons should use outlined styles.
     *
     * @deprecated use `variant="outlined"` instead
     * @default false
     */
    outlined?: boolean;
    /**
     * Visual style variant for the child buttons.
     *
     * @default "solid"
     */
    variant?: ButtonVariant;
    /**
     * Whether the child buttons should appear with large styling.
     *
     * @deprecated use `size="large"` instead.
     * @default false
     */
    large?: boolean;
    /**
     * The size of the child buttons.
     *
     * @default "medium"
     */
    size?: Size;
    /**
     * Whether the button group should appear with vertical styling.
     *
     * @default false
     */
    vertical?: boolean;
}
/**
 * Button group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/button-group
 */
export declare const ButtonGroup: React.FC<ButtonGroupProps>;
