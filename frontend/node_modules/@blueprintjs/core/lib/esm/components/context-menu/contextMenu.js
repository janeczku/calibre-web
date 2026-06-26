import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
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
import { createElement, forwardRef, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Classes, DISPLAYNAME_PREFIX, mergeRefs, Utils } from "../../common";
import { TooltipContext, TooltipProvider } from "../popover/tooltipContext";
import { ContextMenuPopover } from "./contextMenuPopover";
/**
 * Context menu component.
 *
 * @see https://blueprintjs.com/docs/#core/components/context-menu
 */
export const ContextMenu = forwardRef((props, userRef) => {
    const { className, children, content, disabled = false, onClose, onContextMenu, popoverProps, tagName = "div", ...restProps } = props;
    // ancestor TooltipContext state doesn't affect us since we don't care about parent ContextMenus, we only want to
    // force disable parent Tooltips in certain cases through dispatching actions
    // N.B. any calls to this dispatch function will be no-ops if there is no TooltipProvider ancestor of this component
    const [, tooltipCtxDispatch] = useContext(TooltipContext);
    // click target offset relative to the viewport (e.clientX/clientY), since the target will be rendered in a Portal
    const [targetOffset, setTargetOffset] = useState(undefined);
    // hold a reference to the click mouse event to pass to content/child render functions
    const [mouseEvent, setMouseEvent] = useState();
    const [isOpen, setIsOpen] = useState(false);
    // we need a ref on the child element (or the wrapper we generate) to check for dark theme
    const childRef = useRef(null);
    // If disabled prop is changed, we don't want our old context menu to stick around.
    // If it has just been enabled (disabled = false), then the menu ought to be opened by
    // a new mouse event. Users should not be updating this prop in the onContextMenu callback
    // for this component (that will lead to unpredictable behavior).
    useEffect(() => {
        setIsOpen(false);
        tooltipCtxDispatch({ type: "RESET_DISABLED_STATE" });
    }, [disabled, tooltipCtxDispatch]);
    const handlePopoverClose = useCallback(() => {
        setIsOpen(false);
        setMouseEvent(undefined);
        tooltipCtxDispatch({ type: "RESET_DISABLED_STATE" });
        onClose?.();
    }, [onClose, tooltipCtxDispatch]);
    // if the menu was just opened, we should check for dark theme (but don't do this on every render)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    const isDarkTheme = useMemo(() => Utils.isDarkTheme(childRef.current), [childRef, isOpen]);
    const contentProps = useMemo(() => ({
        isOpen,
        mouseEvent,
        targetOffset,
    }), [isOpen, mouseEvent, targetOffset]);
    // create a memoized function to render the menu so that we can call it if necessary in the "contextmenu" event
    // handler which runs before this render function has a chance to re-run and update the `menu` variable
    const renderMenu = useCallback((menuContentProps) => disabled ? undefined : Utils.isFunction(content) ? content(menuContentProps) : content, [disabled, content]);
    const menuContent = useMemo(() => renderMenu(contentProps), [contentProps, renderMenu]);
    // only render the popover if there is content in the context menu;
    // this avoid doing unnecessary rendering & computation
    const maybePopover = menuContent === undefined ? undefined : (_jsx(ContextMenuPopover, { ...popoverProps, content: menuContent, isDarkTheme: isDarkTheme, isOpen: isOpen, targetOffset: targetOffset, onClose: handlePopoverClose }));
    const handleContextMenu = useCallback((e) => {
        // support nested menus (inner menu target would have called preventDefault())
        if (e.defaultPrevented) {
            return;
        }
        // If disabled, we should avoid the extra work in this event handler.
        // Otherwise: if using the child or content function APIs, we need to make sure contentProps gets updated,
        // so we handle the event regardless of whether the consumer returned an undefined menu.
        const shouldHandleEvent = !disabled && (Utils.isFunction(children) || Utils.isFunction(content) || content !== undefined);
        if (shouldHandleEvent) {
            setIsOpen(true);
            e.persist();
            setMouseEvent(e);
            const newTargetOffset = { left: e.clientX, top: e.clientY };
            setTargetOffset(newTargetOffset);
            tooltipCtxDispatch({ type: "FORCE_DISABLED_STATE" });
            const newMenuContent = renderMenu({ isOpen: true, mouseEvent: e, targetOffset: newTargetOffset });
            if (newMenuContent === undefined) {
                // If there is no menu content, we shouldn't automatically swallow the contextmenu event, since the
                // user probably wants to fall back to default browser behavior. If they still want to disable the
                // native context menu in that case, they can do so with their own `onContextMenu` handler.
            }
            else {
                e.preventDefault();
            }
        }
        onContextMenu?.(e);
    }, [disabled, children, content, onContextMenu, tooltipCtxDispatch, renderMenu]);
    const containerClassName = classNames(className, Classes.CONTEXT_MENU);
    const child = Utils.isFunction(children) ? (children({
        className: containerClassName,
        contentProps,
        onContextMenu: handleContextMenu,
        popover: maybePopover,
        ref: childRef,
    })) : (_jsxs(_Fragment, { children: [maybePopover, createElement(tagName, {
                className: containerClassName,
                onContextMenu: handleContextMenu,
                ref: mergeRefs(childRef, userRef),
                ...restProps,
            }, children)] }));
    // force descendant Tooltips to be disabled when this context menu is open
    return _jsx(TooltipProvider, { forceDisable: isOpen, children: child });
});
ContextMenu.displayName = `${DISPLAYNAME_PREFIX}.ContextMenu`;
//# sourceMappingURL=contextMenu.js.map