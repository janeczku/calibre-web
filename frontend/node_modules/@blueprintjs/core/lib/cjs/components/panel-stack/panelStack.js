"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PanelStack2 = exports.PanelStack = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const react_transition_group_1 = require("react-transition-group");
const common_1 = require("../../common");
const hooks_1 = require("../../hooks");
const panelView_1 = require("./panelView");
/**
 * Panel stack component.
 *
 * @see https://blueprintjs.com/docs/#core/components/panel-stack
 * @template T type union of all possible panels in this stack
 */
const PanelStack = (props) => {
    const { initialPanel, onClose, onOpen, renderActivePanelOnly = true, showPanelHeader = true, stack: propsStack, } = props;
    const isControlled = propsStack != null;
    const [localStack, setLocalStack] = (0, react_1.useState)(initialPanel !== undefined ? [initialPanel] : []);
    const stack = (0, react_1.useMemo)(() => (isControlled ? propsStack.slice().reverse() : localStack), [localStack, isControlled, propsStack]);
    const prevStackLength = (0, hooks_1.usePrevious)(stack.length) ?? stack.length;
    const direction = stack.length - prevStackLength < 0 ? "pop" : "push";
    // Map of CSSTransition key -> PanelNodeEntry for each PanelView root DOM node.
    // Each CSSTransition needs its own nodeRef to avoid ReactDOM.findDOMNode() usage.
    const panelNodes = (0, react_1.useRef)(new Map());
    const getOrCreatePanelNode = (0, react_1.useCallback)((key) => {
        let entry = panelNodes.current.get(key);
        if (entry == null) {
            entry = {
                onExited: () => panelNodes.current.delete(key),
                ref: (0, react_1.createRef)(),
            };
            panelNodes.current.set(key, entry);
        }
        return entry;
    }, []);
    const handlePanelOpen = (0, react_1.useCallback)((panel) => {
        onOpen?.(panel);
        if (!isControlled) {
            setLocalStack(prevStack => [panel, ...prevStack]);
        }
    }, [onOpen, isControlled]);
    const handlePanelClose = (0, react_1.useCallback)((panel) => {
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
        return ((0, jsx_runtime_1.jsx)(react_transition_group_1.CSSTransition, { classNames: common_1.Classes.PANEL_STACK, nodeRef: panelRef, onExited: onExited, timeout: 400, children: (0, jsx_runtime_1.jsx)(panelView_1.PanelView, { onClose: handlePanelClose, onOpen: handlePanelOpen, panel: panel, panelNodeRef: panelRef, previousPanel: stack[index + 1], showHeader: showPanelHeader }) }, key));
    })
        .reverse();
    const classes = (0, classnames_1.default)(common_1.Classes.PANEL_STACK, `${common_1.Classes.PANEL_STACK}-${direction}`, props.className);
    return ((0, jsx_runtime_1.jsx)(react_transition_group_1.TransitionGroup, { className: classes, component: "div", children: panels }));
};
exports.PanelStack = PanelStack;
exports.PanelStack.displayName = `${common_1.DISPLAYNAME_PREFIX}.PanelStack`;
/** @deprecated Use `PanelStack` instead */
exports.PanelStack2 = exports.PanelStack;
//# sourceMappingURL=panelStack.js.map