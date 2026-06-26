import type { IconName } from "@blueprintjs/icons";
import type { IntentProps, MaybeElement, NonSmallSize, Props } from "../../common";
export interface TagSharedProps extends Props, IntentProps {
    /**
     * Whether the tag should appear in an active state.
     *
     * @default false
     */
    active?: boolean;
    /**
     * Name of a Blueprint UI icon (or an icon element) to render on the left side of the tag,
     * before any content.
     */
    icon?: IconName | MaybeElement;
    /**
     * Name of a Blueprint UI icon (or an icon element) to render at the end of the tag, after the child
     * node(s).
     */
    endIcon?: IconName | MaybeElement;
    /**
     * Whether the tag should take up the full width of its container.
     *
     * @default false
     */
    fill?: boolean;
    /**
     * Whether the tag should visually respond to user interactions. If set to `true`, hovering over the
     * tag will change its color and mouse cursor.
     *
     * Recommended when `onClick` is also defined.
     *
     * @default false
     */
    interactive?: boolean;
    /**
     * Whether this tag should use large styles.
     *
     * @deprecated use size="large" instead
     * @default false
     */
    large?: boolean;
    /**
     * Whether this tag should use minimal styles.
     *
     * @default false
     */
    minimal?: boolean;
    /**
     * Callback invoked when the tag is clicked.
     * Recommended when `interactive` is `true`.
     */
    onClick?: (e: React.MouseEvent<HTMLSpanElement>) => void;
    /**
     * Name of a Blueprint UI icon (or an icon element) to render on the right side of the tag,
     * after the child node(s).
     *
     * @deprecated Use `endIcon` instead
     */
    rightIcon?: IconName | MaybeElement;
    /**
     * Whether this tag should have rounded ends.
     *
     * @default false
     */
    round?: boolean;
    /**
     * The size of the tag.
     *
     * @default "medium"
     */
    size?: NonSmallSize;
}
