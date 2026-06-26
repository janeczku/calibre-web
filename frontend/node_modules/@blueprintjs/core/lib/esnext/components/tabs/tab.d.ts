import type { IconName } from "@blueprintjs/icons";
import { AbstractPureComponent } from "../../common";
import { type HTMLDivProps, type MaybeElement, type Props } from "../../common/props";
import type { TagProps } from "../tag/tag";
export type TabId = string | number;
export interface TabIdProps {
    /**
     * `id` prop of the tab title, and the `aria-labelledby` of the `TabPanel`.
     */
    tabTitleId: string;
    /**
     * `id` prop of the `tabpanel`, and the `aria-controls` of the tab title.
     */
    tabPanelId: string;
}
export interface TabProps extends Props, Omit<HTMLDivProps, "id" | "title" | "onClick"> {
    /**
     * Content of tab title, rendered in a list above the active panel.
     * Can also be set via the `title` prop.
     */
    children?: React.ReactNode;
    /**
     * Whether the tab is disabled.
     *
     * @default false
     */
    disabled?: boolean;
    /**
     * Unique identifier used to control which tab is selected
     * and to generate ARIA attributes for accessibility.
     */
    id: TabId;
    /**
     * Panel content, rendered by the parent `Tabs` when this tab is active.
     * If omitted, no panel will be rendered for this tab.
     * Can either be an element or a renderer.
     */
    panel?: React.JSX.Element | ((props: TabIdProps) => React.JSX.Element);
    /**
     * Space-delimited string of class names applied to tab panel container.
     */
    panelClassName?: string;
    /**
     * Content of tab title element, rendered in a list above the active panel.
     * Can also be set via React `children`.
     */
    title?: React.ReactNode;
    /** Name of a Blueprint UI icon (or an icon element) to render before the children. */
    icon?: IconName | MaybeElement;
    /**
     * Content to render inside a `<Tag>` after the children.
     * The tag is `minimal` by default; it can be further modified by using `tagProps`.
     */
    tagContent?: TagProps["children"];
    /**
     * Props to customize the `<Tag>` rendered after the children.
     * This has no effect if `tagContent` is `undefined`.
     */
    tagProps?: Omit<TagProps, "children">;
}
/**
 * Tab component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tabs.tab
 */
export declare class Tab extends AbstractPureComponent<TabProps> {
    static defaultProps: Partial<TabProps>;
    static displayName: string;
    render(): import("react/jsx-runtime").JSX.Element;
}
