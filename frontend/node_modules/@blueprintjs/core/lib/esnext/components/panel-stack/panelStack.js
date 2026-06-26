import { jsx as _jsx } from "react/jsx-runtime";
/*
 * Copyright 2021 Palantir Technologies, Inc. All rights reserved.
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
import { createRef, useCallback, useMemo, useRef, useState } from "react";
import { CSSTransition, TransitionGroup } from "react-transition-group";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { usePrevious } from "../../hooks";
import { PanelView } from "./panelView";
/**
 * Panel stack component.
 *
 * @see https://blueprintjs.com/docs/#core/components/panel-stack
 * @template T type union of all possible panels in this stack
 */
export const PanelStack = (props) => {
    const { initialPanel, onClose, onOpen, renderActivePanelOnly = true, showPanelHeader = true, stack: propsStack, } = props;
    const isControlled = propsStack != null;
    const [localStack, setLocalStack] = useState(initialPanel !== undefined ? [initialPanel] : []);
    const stack = useMemo(() => (isControlled ? propsStack.slice().reverse() : localStack), [localStack, isControlled, propsStack]);
    const prevStackLength = usePrevious(stack.length) ?? stack.length;
    const direction = stack.length - prevStackLength < 0 ? "pop" : "push";
    // Map of CSSTransition key -> PanelNodeEntry for each PanelView root DOM node.
    // Each CSSTransition needs its own nodeRef to avoid ReactDOM.findDOMNode() usage.
    const panelNodes = useRef(new Map());
    const getOrCreatePanelNode = useCallback((key) => {
        let entry = panelNodes.current.get(key);
        if (entry == null) {
            entry = {
                onExited: () => panelNodes.current.delete(key),
                ref: createRef(),
            };
            panelNodes.current.set(key, entry);
        }
        return entry;
    }, []);
    const handlePanelOpen = useCallback((panel) => {
        onOpen?.(panel);
        if (!isControlled) {
            setLocalStack(prevStack => [panel, ...prevStack]);
        }
    }, [onOpen, isControlled]);
    const handlePanelClose = useCallback((panel) => {
        onClose?.(panel);
        if (!isControlled) {
            setLocalStack(prevStack => prevStack.slice(1));
        }
    }, [onClose, isControlled]);
    // early return, after all hooks are called
    if (stack.length === 0) {
        return null;
    }
    const panelsToRender = renderActivePanelOnly ? [stack[0]] : stack;
    const panels = panelsToRender
        .map((panel, index) => {
        // With renderActivePanelOnly={false} we would keep all the CSSTransitions rendered,
        // therefore they would not trigger the "enter" transition event as they were entered.
        // To force the enter event, we want to change the key, but stack.length is not enough
        // and a single panel should not rerender as long as it's hidden.
        // This key contains two parts: first one, stack.length - index is constant (and unique) for each panel,
        // second one, active changes only when the panel becomes or stops being active.
        const layer = stack.length - index;
        const key = renderActivePanelOnly ? stack.length : layer;
        const { onExited, ref: panelRef } = getOrCreatePanelNode(key);
        return (_jsx(CSSTransition, { classNames: Classes.PANEL_STACK, nodeRef: panelRef, onExited: onExited, timeout: 400, children: _jsx(PanelView, { onClose: handlePanelClose, onOpen: handlePanelOpen, panel: panel, panelNodeRef: panelRef, previousPanel: stack[index + 1], showHeader: showPanelHeader }) }, key));
    })
        .reverse();
    const classes = classNames(Classes.PANEL_STACK, `${Classes.PANEL_STACK}-${direction}`, props.className);
    return (_jsx(TransitionGroup, { className: classes, component: "div", children: panels }));
};
PanelStack.displayName = `${DISPLAYNAME_PREFIX}.PanelStack`;
/** @deprecated Use `PanelStack` instead */
export const PanelStack2 = PanelStack;
//# sourceMappingURL=panelStack.js.map