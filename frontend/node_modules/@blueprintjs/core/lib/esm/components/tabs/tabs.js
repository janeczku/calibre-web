import { createElement as _createElement } from "react";
import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/*
 * Copyright 2015 Palantir Technologies, Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import classNames from "classnames";
import { Children } from "react";
import { AbstractPureComponent, Classes, DISPLAYNAME_PREFIX, Utils } from "../../common";
import { Tab } from "./tab";
import { TabPanel } from "./tabPanel";
import { TabTitle } from "./tabTitle";
/**
 * Component that may be inserted between any two children of `<Tabs>` to right-align all subsequent children.
 */
export const TabsExpander = () => _jsx("div", { className: Classes.FLEX_EXPANDER });
const TAB_SELECTOR = `.${Classes.TAB}`;
/**
 * Tabs component.
 *
 * @see https://blueprintjs.com/docs/#core/components/tabs
 */
export class Tabs extends AbstractPureComponent {
    /**
     * @deprecated Use the `Tab` component directly instead
     *
     * @see https://blueprintjs.com/docs/#core/components/tabs.tab
     */
    static Tab = Tab;
    static defaultProps = {
        animate: true,
        fill: false,
        large: false,
        renderActiveTabPanelOnly: false,
        size: "medium",
        vertical: false,
    };
    static displayName = `${DISPLAYNAME_PREFIX}.Tabs`;
    static getDerivedStateFromProps({ selectedTabId }) {
        if (selectedTabId !== undefined) {
            // keep state in sync with controlled prop, so state is canonical source of truth
            return { selectedTabId };
        }
        return null;
    }
    tablistElement = null;
    refHandlers = {
        tablist: (tabElement) => (this.tablistElement = tabElement),
    };
    constructor(props) {
        super(props);
        const selectedTabId = this.getInitialSelectedTabId();
        this.state = { selectedTabId };
    }
    render() {
        const { animate, children, className, fill, 
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        large, renderActiveTabPanelOnly, size = "medium", vertical, } = this.props;
        const { indicatorWrapperStyle, selectedTabId } = this.state;
        const tabTitles = Children.map(children, this.renderTabTitle);
        const tabPanels = this.getTabChildren()
            .filter(renderActiveTabPanelOnly ? tab => tab.props.id === selectedTabId : () => true)
            .map(this.renderTabPanel);
        const tabIndicator = animate ? (_jsx("div", { className: Classes.TAB_INDICATOR_WRAPPER, style: indicatorWrapperStyle, children: _jsx("div", { className: Classes.TAB_INDICATOR }) })) : null;
        const classes = classNames(Classes.TABS, className, {
            [Classes.VERTICAL]: vertical,
            [Classes.FILL]: fill,
        });
        const tabListClasses = classNames(Classes.TAB_LIST, Classes.sizeClass(size, { large }));
        return (_jsxs("div", { className: classes, children: [_jsxs("div", { className: tabListClasses, onKeyDown: this.handleKeyDown, 
                    // eslint-disable-next-line @typescript-eslint/no-deprecated
                    onKeyPress: this.handleKeyPress, ref: this.refHandlers.tablist, role: "tablist", children: [tabIndicator, tabTitles] }), tabPanels] }));
    }
    componentDidMount() {
        this.moveSelectionIndicator(false);
    }
    componentDidUpdate(prevProps, prevState) {
        if (this.state.selectedTabId !== prevState.selectedTabId) {
            this.moveSelectionIndicator();
        }
        else if (prevState.selectedTabId != null) {
            // comparing React nodes is difficult to do with simple logic, so
            // shallowly compare just their props as a workaround.
            const didChildrenChange = !Utils.arraysEqual(this.getTabChildrenProps(prevProps), this.getTabChildrenProps(), Utils.shallowCompareKeys);
            if (didChildrenChange) {
                this.moveSelectionIndicator();
            }
        }
    }
    getInitialSelectedTabId() {
        // NOTE: providing an unknown ID will hide the selection
        const { defaultSelectedTabId, selectedTabId } = this.props;
        if (selectedTabId !== undefined) {
            return selectedTabId;
        }
        else if (defaultSelectedTabId !== undefined) {
            return defaultSelectedTabId;
        }
        else {
            // select first tab in absence of user input
            const tabs = this.getTabChildren();
            return tabs.length === 0 ? undefined : tabs[0].props.id;
        }
    }
    getTabChildrenProps(props = this.props) {
        return this.getTabChildren(props).map(child => child.props);
    }
    /** Filters children to only `<Tab>`s */
    getTabChildren(props = this.props) {
        return Children.toArray(props.children).filter(isTabElement);
    }
    /** Queries root HTML element for all tabs with optional filter selector */
    getTabElements(subselector = "") {
        if (this.tablistElement == null) {
            return [];
        }
        return Array.from(this.tablistElement.querySelectorAll(TAB_SELECTOR + subselector));
    }
    handleKeyDown = (e) => {
        const direction = Utils.getArrowKeyDirection(e, ["ArrowLeft", "ArrowUp"], ["ArrowRight", "ArrowDown"]);
        if (direction === undefined)
            return;
        const focusedElement = Utils.getActiveElement(this.tablistElement)?.closest(TAB_SELECTOR);
        // rest of this is potentially expensive and futile, so bail if no tab is focused
        if (!focusedElement)
            return;
        // must rely on DOM state because we have no way of mapping `focusedElement` to a React.JSX.Element
        const enabledTabElements = this.getTabElements('[aria-disabled="false"]');
        const focusedIndex = enabledTabElements.indexOf(focusedElement);
        if (focusedIndex < 0)
            return;
        e.preventDefault();
        const { length } = enabledTabElements;
        // auto-wrapping at 0 and `length`
        const nextFocusedIndex = (focusedIndex + direction + length) % length;
        enabledTabElements[nextFocusedIndex].focus();
    };
    handleKeyPress = (e) => {
        const targetTabElement = e.target.closest(TAB_SELECTOR);
        if (targetTabElement != null && Utils.isKeyboardClick(e)) {
            e.preventDefault();
            targetTabElement.click();
        }
    };
    handleTabClick = (newTabId, event) => {
        this.props.onChange?.(newTabId, this.state.selectedTabId, event);
        if (this.props.selectedTabId === undefined) {
            this.setState({ selectedTabId: newTabId });
        }
    };
    /**
     * Calculate the new height, width, and position of the tab indicator.
     * Store the CSS values so the transition animation can start.
     */
    moveSelectionIndicator(animate = true) {
        if (this.tablistElement == null || !this.props.animate) {
            return;
        }
        const tabIdSelector = `${TAB_SELECTOR}[data-tab-id="${this.state.selectedTabId}"]`;
        const selectedTabElement = this.tablistElement.querySelector(tabIdSelector);
        let indicatorWrapperStyle = { display: "none" };
        if (selectedTabElement != null) {
            const { clientHeight, clientWidth, offsetLeft, offsetTop } = selectedTabElement;
            indicatorWrapperStyle = {
                height: clientHeight,
                transform: `translateX(${Math.floor(offsetLeft)}px) translateY(${Math.floor(offsetTop)}px)`,
                width: clientWidth,
            };
            if (!animate) {
                indicatorWrapperStyle.transition = "none";
            }
        }
        this.setState({ indicatorWrapperStyle });
    }
    renderTabPanel = (tab) => {
        const { className, panel, id, panelClassName } = tab.props;
        if (panel === undefined) {
            return undefined;
        }
        return (_createElement(TabPanel, { ...tab.props, key: id, className: classNames(className, panelClassName), parentId: this.props.id, selectedTabId: this.state.selectedTabId }));
    };
    renderTabTitle = (child) => {
        if (isTabElement(child)) {
            const { id } = child.props;
            return (_jsx(TabTitle, { ...child.props, parentId: this.props.id, onClick: this.handleTabClick, selected: id === this.state.selectedTabId }));
        }
        return child;
    };
}
function isTabElement(child) {
    return Utils.isElementOfType(child, Tab);
}
//# sourceMappingURL=tabs.js.map