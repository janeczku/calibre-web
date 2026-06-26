import { AbstractPureComponent } from "../../common";
import { type TabId, type TabProps } from "./tab";
import type { TabsProps } from "./tabs";
import { type TabTitleProps } from "./tabTitle";
export interface TabPanelProps extends Pick<TabProps, "className" | "id" | "panel">, Pick<TabsProps, "renderActiveTabPanelOnly" | "selectedTabId">, Pick<TabTitleProps, "parentId"> {
    /**
     * Used for setting visibility. This `TabPanel` will be visibile when `selectedTabId === id`, with proper accessibility attributes set.
     */
    selectedTabId: TabId | undefined;
}
/**
 * Wraps the passed `panel`.
 */
export declare class TabPanel extends AbstractPureComponent<TabPanelProps> {
    render(): import("react/jsx-runtime").JSX.Element | undefined;
}
