import { type Intent } from "../../common";
import { type HTMLDivProps, type IntentProps, type Props } from "../../common/props";
export interface FormGroupProps extends IntentProps, Props, HTMLDivProps {
    /** Group contents. */
    children?: React.ReactNode;
    /**
     * A space-delimited list of class names to pass along to the
     * `Classes.FORM_CONTENT` element that contains `children`.
     */
    contentClassName?: string;
    /**
     * Whether form group should appear as non-interactive.
     * Remember that `input` elements must be disabled separately.
     */
    disabled?: boolean;
    /**
     * Whether the component should take up the full width of its container.
     */
    fill?: boolean;
    /**
     * Optional helper text. The given content will be wrapped in
     * `Classes.FORM_HELPER_TEXT` and displayed beneath `children`.
     * Helper text color is determined by the `intent`.
     */
    helperText?: React.ReactNode;
    /** Whether to render the label and children on a single line. */
    inline?: boolean;
    /**
     * Visual intent to apply to helper text and sub label.
     * Note that child form elements need to have their own intents applied independently.
     */
    intent?: Intent;
    /** Label of this form group. */
    label?: React.ReactNode;
    /**
     * `id` attribute of the labelable form element that this `FormGroup` controls,
     * used as `<label for>` attribute.
     */
    labelFor?: string;
    /**
     * Optional secondary text that appears after the label.
     */
    labelInfo?: React.ReactNode;
    /** CSS properties to apply to the root element. */
    style?: React.CSSProperties;
    /**
     * Optional text for `label`. The given content will be wrapped in
     * `Classes.FORM_GROUP_SUB_LABEL` and displayed beneath `label`.
     */
    subLabel?: React.ReactNode;
}
/**
 * Form group component.
 *
 * @see https://blueprintjs.com/docs/#core/components/form-group
 */
export declare const FormGroup: React.FC<FormGroupProps>;
