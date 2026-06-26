"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ContextMenu = void 0;
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
const common_1 = require("../../common");
const tooltipContext_1 = require("../popover/tooltipContext");
const contextMenuPopover_1 = require("./contextMenuPopover");
/**
 * Context menu component.
 *
 * @see https://blueprintjs.com/docs/#core/components/context-menu
 */
exports.ContextMenu = (0, react_1.forwardRef)((props, userRef) => {
    const { className, children, content, disabled = false, onClose, onContextMenu, popoverProps, tagName = "div", ...restProps } = props;
    // ancestor TooltipContext state doesn't affect us since we don't care about parent ContextMenus, we only want to
    // force disable parent Tooltips in certain cases through dispatching actions
    // N.B. any calls to this dispatch function will be no-ops if there is no TooltipProvider ancestor of this component
    const [, tooltipCtxDispatch] = (0, react_1.useContext)(tooltipContext_1.TooltipContext);
    // click target offset relative to the viewport (e.clientX/clientY), since the target will be rendered in a Portal
    const [targetOffset, setTargetOffset] = (0, react_1.useState)(undefined);
    // hold a reference to the click mouse event to pass to content/child render functions
    const [mouseEvent, setMouseEvent] = (0, react_1.useState)();
    const [isOpen, setIsOpen] = (0, react_1.useState)(false);
    // we need a ref on the child element (or the wrapper we generate) to check for dark theme
    const childRef = (0, react_1.useRef)(null);
    // If disabled prop is changed, we don't want our old context menu to stick around.
    // If it has just been enabled (disabled = false), then the menu ought to be opened by
    // a new mouse event. Users should not be updating this prop in the onContextMenu callback
    // for this component (that will lead to unpredictable behavior).
    (0, react_1.useEffect)(() => {
        setIsOpen(false);
        tooltipCtxDispatch({ type: "RESET_DISABLED_STATE" });
    }, [disabled, tooltipCtxDispatch]);
    const handlePopoverClose = (0, react_1.useCallback)(() => {
        setIsOpen(false);
        setMouseEvent(undefined);
        tooltipCtxDispatch({ type: "RESET_DISABLED_STATE" });
        onClose?.();
    }, [onClose, tooltipCtxDispatch]);
    // if the menu was just opened, we should check for dark theme (but don't do this on every render)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    const isDarkTheme = (0, react_1.useMemo)(() => common_1.Utils.isDarkTheme(childRef.current), [childRef, isOpen]);
    const contentProps = (0, react_1.useMemo)(() => ({
        isOpen,
        mouseEvent,
        targetOffset,
    }), [isOpen, mouseEvent, targetOffset]);
    // create a memoized function to render the menu so that we can call it if necessary in the "contextmenu" event
    // handler which runs before this render function has a chance to re-run and update the `menu` variable
    const renderMenu = (0, react_1.useCallback)((menuContentProps) => disabled ? undefined : common_1.Utils.isFunction(content) ? content(menuContentProps) : content, [disabled, content]);
    const menuContent = (0, react_1.useMemo)(() => renderMenu(contentProps), [contentProps, renderMenu]);
    // only render the popover if there is content in the context menu;
    // this avoid doing unnecessary rendering & computation
    const maybePopover = menuContent === undefined ? undefined : ((0, jsx_runtime_1.jsx)(contextMenuPopover_1.ContextMenuPopover, { ...popoverProps, content: menuContent, isDarkTheme: isDarkTheme, isOpen: isOpen, targetOffset: targetOffset, onClose: handlePopoverClose }));
    const handleContextMenu = (0, react_1.useCallback)((e) => {
        // support nested menus (inner menu target would have called preventDefault())
        if (e.defaultPrevented) {
            return;
        }
        // If disabled, we should avoid the extra work in this event handler.
        // Otherwise: if using the child or content function APIs, we need to make sure contentProps gets updated,
        // so we handle the event regardless of whether the consumer returned an undefined menu.
        const shouldHandleEvent = !disabled && (common_1.Utils.isFunction(children) || common_1.Utils.isFunction(content) || content !== undefined);
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
    const containerClassName = (0, classnames_1.default)(className, common_1.Classes.CONTEXT_MENU);
    const child = common_1.Utils.isFunction(children) ? (children({
        className: containerClassName,
        contentProps,
        onContextMenu: handleContextMenu,
        popover: maybePopover,
        ref: childRef,
    })) : ((0, jsx_runtime_1.jsxs)(jsx_runtime_1.Fragment, { children: [maybePopover, (0, react_1.createElement)(tagName, {
                className: containerClassName,
                onContextMenu: handleContextMenu,
                ref: (0, common_1.mergeRefs)(childRef, userRef),
                ...restProps,
            }, children)] }));
    // force descendant Tooltips to be disabled when this context menu is open
    return (0, jsx_runtime_1.jsx)(tooltipContext_1.TooltipProvider, { forceDisable: isOpen, children: child });
});
exports.ContextMenu.displayName = `${common_1.DISPLAYNAME_PREFIX}.ContextMenu`;
//# sourceMappingURL=contextMenu.js.map