import type { IconName } from "@blueprintjs/icons";
import { type IntentProps, type MaybeElement, type Props } from "../../common";
import type { TagSharedProps } from "./tagSharedProps";
export interface TagProps extends Props, IntentProps, TagSharedProps, React.RefAttributes<HTMLSpanElement>, React.HTMLAttributes<HTMLSpanElement> {
    /**
     * Child nodes which will be rendered inside a `<Text>` element.
     */
    children?: React.ReactNode;
    /**
     * HTML title to be passed to the <Text> component
     */
    htmlTitle?: string;
    /**
     * Whether the tag should visually respond to user interactions. If set to `true`, hovering over the
     * tag will change its color and mouse cursor.
     *
     * Tags will be marked as interactive automatically if an onClick handler is provided and this prop is not.
     *
     * @default false
     */
    interactive?: boolean;
    /**
     * Name of a Blueprint UI icon (or an icon element) to render on the left side of the tag,
     * before the child nodes.
     */
    icon?: IconName | MaybeElement;
    /**
     * Whether tag content should be allowed to occupy multiple lines.
     * If `false`, a single line of text will be truncated with an ellipsis if it overflows.
     * Note that icons will be vertically centered relative to multiline text.
     *
     * @default false
     */
    multiline?: boolean;
    /**
     * Click handler for remove button.
     * The remove button will only be rendered if this prop is defined.
     */
    onRemove?: (e: React.MouseEvent<HTMLButtonElement>, tagProps: TagProps) => void;
}
/**
 * Tag component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tag
 */
export declare const Tag: React.FC<TagProps>;
