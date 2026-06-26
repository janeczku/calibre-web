import { type IconName } from "@blueprintjs/icons";
import { type MaybeElement, type Props } from "../../common";
export interface EntityTitleProps extends Props {
    /**
     * Whether the overflowing text content should be ellipsized.
     *
     * @default false
     */
    ellipsize?: boolean;
    /** Whether the component should expand to fill its container. */
    fill?: boolean;
    /**
     * React component to render the main title heading. This defaults to
     * Blueprint's `<Text>` component, * which inherits font size from its
     * containing element(s).
     *
     * To render larger, more prominent titles, Use Blueprint's heading
     * components instead (e.g. `{ H1 } from "@blueprintjs/core"`).
     *
     * @default Text
     */
    heading?: React.FC<any>;
    /**
     * Name of a Blueprint UI icon (or an icon element) to render in the section's header.
     * Note that the header will only be rendered if `title` is provided.
     */
    icon?: IconName | MaybeElement;
    /**
     * Whether to render as loading state.
     *
     * @default false
     */
    loading?: boolean;
    /** The content to render below the title. Defaults to render muted text. */
    subtitle?: React.JSX.Element | string;
    /** The primary title to render. */
    title: React.JSX.Element | string;
    /** If specified, the title will be wrapped in an anchor with this URL. */
    titleURL?: string;
    /**
     * <Tag> components work best - if multiple, wrap in <React.Fragment>
     */
    tags?: React.ReactNode;
}
/**
 * EntityTitle component.
 *
 * @see https://blueprintjs.com/docs/#core/components/entity-title
 */
export declare const EntityTitle: React.FC<EntityTitleProps>;
