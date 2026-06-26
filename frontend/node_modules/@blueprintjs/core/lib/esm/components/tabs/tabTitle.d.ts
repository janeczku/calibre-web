import { AbstractPureComponent } from "../../common";
import type { TabId, TabProps } from "./tab";
export interface TabTitleProps extends TabProps {
    /** Optional contents. */
    children?: React.ReactNode;
    /** Handler invoked when this tab is clicked. */
    onClick: (id: TabId, event: React.MouseEvent<HTMLElement>) => void;
    /** ID of the parent `Tabs` to which this tab belongs. Used to generate ID for ARIA attributes. */
    parentId: TabId;
    /** Whether the tab is currently selected. */
    selected: boolean;
}
export declare class TabTitle extends AbstractPureComponent<TabTitleProps> {
    static displayName: string;
    render(): import("react/jsx-runtime").JSX.Element;
    private handleClick;
}
export declare function generateTabIds(parentId: TabId, tabId: TabId): {
    tabPanelId: string;
    tabTitleId: string;
};
