"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Overlay2 = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2024 Palantir Technologies, Inc. All rights reserved.
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
const errors_1 = require("../../common/errors");
const props_1 = require("../../common/props");
const utils_1 = require("../../common/utils");
const domUtils_1 = require("../../common/utils/domUtils");
const useOverlayStack_1 = require("../../hooks/overlays/useOverlayStack");
const usePrevious_1 = require("../../hooks/usePrevious");
const overlayUtils_1 = require("../overlay/overlayUtils");
const portal_1 = require("../portal/portal");
/**
 * Overlay2 component.
 *
 * @see https://blueprintjs.com/docs/#core/components/overlay2
 */
exports.Overlay2 = (0, react_1.forwardRef)((props, forwardedRef) => {
    const { autoFocus = true, backdropClassName, backdropProps = {}, canEscapeKeyClose = true, canOutsideClickClose = true, childRef, childRefs, children, className, enforceFocus = true, hasBackdrop = true, isOpen = false, lazy = (0, domUtils_1.hasDOMEnvironment)(), onClose, onClosed, onClosing, onOpened, onOpening, portalClassName, portalContainer, shouldReturnFocusOnClose = true, transitionDuration = 300, transitionName = common_1.Classes.OVERLAY, usePortal = true, } = props;
    useOverlay2Validation(props);
    const { closeOverlay, getLastOpened, getThisOverlayAndDescendants, openOverlay } = (0, useOverlayStack_1.useOverlayStack)();
    const [isAutoFocusing, setIsAutoFocusing] = (0, react_1.useState)(false);
    const [hasEverOpened, setHasEverOpened] = (0, react_1.useState)(false);
    const [shouldFocusOnContainerMount, setShouldFocusOnContainerMount] = (0, react_1.useState)(false);
    const lastActiveElementBeforeOpened = (0, react_1.useRef)(null);
    /** Ref for container element, containing all children and the backdrop */
    const containerElement = (0, react_1.useRef)(null);
    /** Ref for backdrop element */
    const backdropElement = (0, react_1.useRef)(null);
    /* An empty, keyboard-focusable div at the beginning of the Overlay content */
    const startFocusTrapElement = (0, react_1.useRef)(null);
    /* An empty, keyboard-focusable div at the end of the Overlay content */
    const endFocusTrapElement = (0, react_1.useRef)(null);
    /**
     * Locally-generated DOM ref for a singleton child element.
     * This is only used iff the user does not specify the `childRef` or `childRefs` props.
     */
    const localChildRef = (0, react_1.useRef)(null);
    const bringFocusInsideOverlay = (0, react_1.useCallback)((containerOverride) => {
        // always delay focus manipulation to just before repaint to prevent scroll jumping
        return requestAnimationFrame(() => {
            // container element may be undefined between component mounting and Portal rendering
            // activeElement may be undefined in some rare cases in IE
            const container = containerOverride ?? (0, utils_1.getRef)(containerElement);
            const activeElement = (0, utils_1.getActiveElement)(container);
            if (container == null || activeElement == null) {
                return;
            }
            // Overlay2 is guaranteed to be mounted here
            const isFocusOutsideModal = !container.contains(activeElement);
            if (isFocusOutsideModal) {
                (0, utils_1.getRef)(startFocusTrapElement)?.focus({ preventScroll: true });
                setIsAutoFocusing(false);
            }
        });
    }, []);
    /**
     * Callback for when the container element is mounted in the DOM.
     * This handles a race condition where autoFocus is requested before Portal renders a container.
     */
    const handleContainerMount = (0, react_1.useCallback)((node) => {
        // If we have a pending focus request and the container is now available, apply focus
        if (node != null && shouldFocusOnContainerMount) {
            setShouldFocusOnContainerMount(false);
            setIsAutoFocusing(true);
            bringFocusInsideOverlay(node);
        }
    }, [bringFocusInsideOverlay, shouldFocusOnContainerMount]);
    /**
     * Combined ref that both stores the container element and triggers mount logic
     */
    const mergedContainerRef = (0, react_1.useMemo)(() => (0, common_1.mergeRefs)(containerElement, handleContainerMount), [handleContainerMount]);
    /** Unique ID for this overlay in the global stack */
    const id = useOverlay2ID();
    // N.B. use `null` here and not simply `undefined` because `useImperativeHandle` will set `null` on unmount,
    // and we need the following code to be resilient to that value.
    const instance = (0, react_1.useRef)(null);
    /**
     * When multiple `enforceFocus` Overlays are open, this event handler is only active for the most
     * recently opened one to avoid Overlays competing with each other for focus.
     */
    const handleDocumentFocus = (0, react_1.useCallback)((e) => {
        // get the actual target even in the Shadow DOM
        // see https://github.com/palantir/blueprint/issues/4220
        const eventTarget = e.composed ? e.composedPath()[0] : e.target;
        const container = (0, utils_1.getRef)(containerElement);
        if (container != null && eventTarget instanceof Node && !container.contains(eventTarget)) {
            // prevent default focus behavior (sometimes auto-scrolls the page)
            e.preventDefault();
            e.stopImmediatePropagation();
            bringFocusInsideOverlay();
        }
    }, [bringFocusInsideOverlay]);
    // N.B. this listener is only kept attached when `isOpen={true}` and `canOutsideClickClose={true}`
    const handleDocumentMousedown = (0, react_1.useCallback)((e) => {
        // get the actual target even in the Shadow DOM
        // see https://github.com/palantir/blueprint/issues/4220
        const eventTarget = (e.composed ? e.composedPath()[0] : e.target);
        const thisOverlayAndDescendants = getThisOverlayAndDescendants(id);
        const isClickInThisOverlayOrDescendant = thisOverlayAndDescendants.some(({ containerElement: containerRef }) => {
            // `elem` is the container of backdrop & content, so clicking directly on that container
            // should not count as being "inside" the overlay.
            const elem = (0, utils_1.getRef)(containerRef);
            return elem?.contains(eventTarget) && !elem.isSameNode(eventTarget);
        });
        if (!isClickInThisOverlayOrDescendant) {
            // casting to any because this is a native event
            onClose?.(e);
        }
    }, [getThisOverlayAndDescendants, id, onClose]);
    // N.B. this listener allows Escape key to close overlays that don't have focus (e.g., hover-triggered tooltips)
    // It's only attached when `autoFocus={false}` (indicating a hover interaction) and `canEscapeKeyClose={true}`
    const handleDocumentKeyDown = (0, react_1.useCallback)((e) => {
        if (e.key === "Escape" && canEscapeKeyClose) {
            // Only close if this is the topmost overlay to avoid closing multiple overlays at once
            const lastOpened = getLastOpened();
            if (lastOpened?.id === id) {
                onClose?.(e);
                e.stopPropagation();
                e.preventDefault();
            }
        }
    }, [canEscapeKeyClose, getLastOpened, id, onClose]);
    // send this instance's imperative handle to the the forwarded ref as well as our local ref
    const ref = (0, react_1.useMemo)(() => (0, common_1.mergeRefs)(forwardedRef, instance), [forwardedRef]);
    (0, react_1.useImperativeHandle)(ref, () => ({
        bringFocusInsideOverlay,
        containerElement,
        handleDocumentFocus,
        handleDocumentMousedown,
        id,
        props: {
            autoFocus,
            enforceFocus,
            hasBackdrop,
            usePortal,
        },
    }), [
        autoFocus,
        bringFocusInsideOverlay,
        enforceFocus,
        handleDocumentFocus,
        handleDocumentMousedown,
        hasBackdrop,
        id,
        usePortal,
    ]);
    const handleContainerKeyDown = (0, react_1.useCallback)((e) => {
        if (e.key === "Escape" && canEscapeKeyClose) {
            onClose?.(e);
            // prevent other overlays from closing
            e.stopPropagation();
            // prevent browser-specific escape key behavior (Safari exits fullscreen)
            e.preventDefault();
        }
    }, [canEscapeKeyClose, onClose]);
    const overlayWillOpen = (0, react_1.useCallback)(() => {
        if (instance.current == null) {
            return;
        }
        const lastOpenedOverlay = getLastOpened();
        if (lastOpenedOverlay?.handleDocumentFocus !== undefined) {
            document.removeEventListener("focus", lastOpenedOverlay.handleDocumentFocus, /* useCapture */ true);
        }
        openOverlay(instance.current);
        if (autoFocus) {
            const container = (0, utils_1.getRef)(containerElement);
            if (container != null) {
                setIsAutoFocusing(true);
                bringFocusInsideOverlay();
            }
            else {
                setShouldFocusOnContainerMount(true);
            }
        }
        (0, utils_1.setRef)(lastActiveElementBeforeOpened, (0, utils_1.getActiveElement)((0, utils_1.getRef)(containerElement)));
    }, [autoFocus, bringFocusInsideOverlay, getLastOpened, openOverlay]);
    const overlayWillClose = (0, react_1.useCallback)(() => {
        document.removeEventListener("focus", handleDocumentFocus, /* useCapture */ true);
        document.removeEventListener("mousedown", handleDocumentMousedown);
        // N.B. `instance.current` may be null at this point if we are cleaning up an open overlay during the unmount phase
        // (this is common, for example, with context menu's singleton `showContextMenu` / `hideContextMenu` imperative APIs).
        closeOverlay(id);
        const lastOpenedOverlay = getLastOpened();
        if (lastOpenedOverlay !== undefined) {
            // Only bring focus back to last overlay if it had autoFocus _and_ enforceFocus enabled.
            // If `autoFocus={false}`, it's likely that the overlay never received focus in the first place,
            // so it would be surprising for us to send it there. See https://github.com/palantir/blueprint/issues/4921
            if (lastOpenedOverlay.props.autoFocus && lastOpenedOverlay.props.enforceFocus) {
                lastOpenedOverlay.bringFocusInsideOverlay?.();
                if (lastOpenedOverlay.handleDocumentFocus !== undefined) {
                    document.addEventListener("focus", lastOpenedOverlay.handleDocumentFocus, /* useCapture */ true);
                }
            }
        }
    }, [closeOverlay, getLastOpened, handleDocumentFocus, handleDocumentMousedown, id]);
    const prevIsOpen = (0, usePrevious_1.usePrevious)(isOpen) ?? false;
    (0, react_1.useEffect)(() => {
        if (isOpen) {
            setHasEverOpened(true);
        }
        if (!prevIsOpen && isOpen) {
            // just opened
            overlayWillOpen();
        }
        if (prevIsOpen && !isOpen) {
            // just closed
            overlayWillClose();
        }
    }, [isOpen, overlayWillOpen, overlayWillClose, prevIsOpen]);
    // Important: clean up old document-level event listeners if their memoized values change (this is rare, but
    // may happen, for example, if a user forgets to use `useCallback` in the `props.onClose` value).
    // Otherwise, we will lose the reference to those values and create a memory leak since we won't be able
    // to successfully detach them inside overlayWillClose.
    (0, react_1.useEffect)(() => {
        if (!isOpen || !(canOutsideClickClose && !hasBackdrop)) {
            return;
        }
        document.addEventListener("mousedown", handleDocumentMousedown);
        return () => {
            document.removeEventListener("mousedown", handleDocumentMousedown);
        };
    }, [handleDocumentMousedown, isOpen, canOutsideClickClose, hasBackdrop]);
    (0, react_1.useEffect)(() => {
        // Attach document-level keydown listener for overlays that don't receive focus (like hover tooltips)
        // This enables Escape key dismissal without stealing focus on hover
        if (!isOpen || autoFocus !== false || !canEscapeKeyClose) {
            return;
        }
        document.addEventListener("keydown", handleDocumentKeyDown);
        return () => {
            document.removeEventListener("keydown", handleDocumentKeyDown);
        };
    }, [handleDocumentKeyDown, isOpen, autoFocus, canEscapeKeyClose]);
    (0, react_1.useEffect)(() => {
        if (!isOpen || !enforceFocus) {
            return;
        }
        // Only add listener if this overlay is the most recent one
        const lastOpened = getLastOpened();
        const isTopOverlay = lastOpened?.id === id;
        if (!isTopOverlay) {
            return;
        }
        // Focus events do not bubble, but setting useCapture allows us to listen in and execute
        // our handler before all others
        document.addEventListener("focus", handleDocumentFocus, /* useCapture */ true);
        return () => {
            document.removeEventListener("focus", handleDocumentFocus, /* useCapture */ true);
        };
    }, [handleDocumentFocus, enforceFocus, isOpen, getLastOpened, id]);
    const overlayWillCloseRef = (0, react_1.useRef)(overlayWillClose);
    overlayWillCloseRef.current = overlayWillClose;
    (0, react_1.useEffect)(() => {
        // run cleanup code once on unmount, ensuring we call the most recent overlayWillClose callback
        // by storing in a ref and keeping up to date
        return () => {
            overlayWillCloseRef.current();
        };
    }, []);
    const handleTransitionExited = (0, react_1.useCallback)((node) => {
        const lastActiveElement = (0, utils_1.getRef)(lastActiveElementBeforeOpened);
        if (shouldReturnFocusOnClose && lastActiveElement instanceof HTMLElement) {
            lastActiveElement.focus();
        }
        onClosed?.(node);
    }, [onClosed, shouldReturnFocusOnClose]);
    // N.B. CSSTransition requires this callback to be defined, even if it's unused.
    const handleTransitionAddEnd = (0, react_1.useCallback)(() => {
        // no-op
    }, []);
    /**
     * Gets the relevant DOM ref for a child element using the `childRef` or `childRefs` props (if possible).
     * This ref is necessary for `CSSTransition` to work in React 18 without relying on `ReactDOM.findDOMNode`.
     *
     * Returns `undefined` if the user did not specify either of those props. In those cases, we use the ref we
     * have locally generated and expect that the user _did not_ specify their own `ref` on the child element
     * (it will get clobbered / overriden).
     *
     * @see https://reactcommunity.org/react-transition-group/css-transition
     */
    const getUserChildRef = (0, react_1.useCallback)((child) => {
        if (childRef != null) {
            return childRef;
        }
        else if (childRefs != null) {
            const key = child.key;
            if (key == null) {
                if (!(0, utils_1.isNodeEnv)("production")) {
                    console.error(errors_1.OVERLAY_CHILD_REQUIRES_KEY);
                }
                return undefined;
            }
            return childRefs[key];
        }
        return undefined;
    }, [childRef, childRefs]);
    const maybeRenderChild = (0, react_1.useCallback)((child) => {
        if (child == null || (0, utils_1.isEmptyString)(child)) {
            return null;
        }
        // decorate the child with a few injected props
        const userChildRef = getUserChildRef(child);
        const childProps = (0, utils_1.isReactElement)(child) ? child.props : {};
        // if the child is a string, number, or fragment, it will be wrapped in a <span> element
        const decoratedChild = (0, utils_1.ensureElement)(child, "span", {
            className: (0, classnames_1.default)(childProps.className, common_1.Classes.OVERLAY_CONTENT),
            // IMPORTANT: only inject our ref if the user didn't specify childRef or childRefs already. Otherwise,
            // we risk clobbering the user's ref (which we cannot inspect here while cloning/decorating the child).
            ref: userChildRef === undefined ? localChildRef : undefined,
            tabIndex: enforceFocus || autoFocus ? 0 : undefined,
        });
        const resolvedChildRef = userChildRef ?? localChildRef;
        return ((0, jsx_runtime_1.jsx)(react_transition_group_1.CSSTransition, { addEndListener: handleTransitionAddEnd, classNames: transitionName, 
            // HACKHACK: CSSTransition types are slightly incompatible with React types here.
            // React prefers `| null` but not `| undefined` for the ref value, while
            // CSSTransition _demands_ that `| undefined` be part of the element type.
            nodeRef: resolvedChildRef, onEntered: getLifecycleCallbackWithChildRef(onOpened, resolvedChildRef), onEntering: getLifecycleCallbackWithChildRef(onOpening, resolvedChildRef), onExited: getLifecycleCallbackWithChildRef(handleTransitionExited, resolvedChildRef), onExiting: getLifecycleCallbackWithChildRef(onClosing, resolvedChildRef), timeout: transitionDuration, children: decoratedChild }));
    }, [
        autoFocus,
        enforceFocus,
        getUserChildRef,
        handleTransitionAddEnd,
        handleTransitionExited,
        onClosing,
        onOpened,
        onOpening,
        transitionDuration,
        transitionName,
    ]);
    const handleBackdropMouseDown = (0, react_1.useCallback)((e) => {
        if (canOutsideClickClose) {
            onClose?.(e);
        }
        if (enforceFocus) {
            bringFocusInsideOverlay();
        }
        backdropProps?.onMouseDown?.(e);
    }, [backdropProps, bringFocusInsideOverlay, canOutsideClickClose, enforceFocus, onClose]);
    const renderDummyElement = (0, react_1.useCallback)((key, dummyElementProps) => ((0, jsx_runtime_1.jsx)(react_transition_group_1.CSSTransition, { addEndListener: handleTransitionAddEnd, classNames: transitionName, nodeRef: dummyElementProps.ref, timeout: transitionDuration, unmountOnExit: true, children: (0, jsx_runtime_1.jsx)("div", { tabIndex: 0, ...dummyElementProps }) }, key)), [handleTransitionAddEnd, transitionDuration, transitionName]);
    /**
     * Ensures repeatedly pressing shift+tab keeps focus inside the Overlay. Moves focus to
     * the `endFocusTrapElement` or the first keyboard-focusable element in the Overlay (excluding
     * the `startFocusTrapElement`), depending on whether the element losing focus is inside the
     * Overlay.
     */
    const handleStartFocusTrapElementFocus = (0, react_1.useCallback)((e) => {
        if (!enforceFocus || isAutoFocusing) {
            return;
        }
        // e.relatedTarget will not be defined if this was a programmatic focus event, as is the
        // case when we call this.bringFocusInsideOverlay() after a user clicked on the backdrop.
        // Otherwise, we're handling a user interaction, and we should wrap around to the last
        // element in this transition group.
        const container = (0, utils_1.getRef)(containerElement);
        const endFocusTrap = (0, utils_1.getRef)(endFocusTrapElement);
        if (e.relatedTarget != null &&
            container?.contains(e.relatedTarget) &&
            e.relatedTarget !== endFocusTrap) {
            endFocusTrap?.focus({ preventScroll: true });
        }
    }, [enforceFocus, isAutoFocusing]);
    /**
     * Wrap around to the end of the dialog if `enforceFocus` is enabled.
     */
    const handleStartFocusTrapElementKeyDown = (0, react_1.useCallback)((e) => {
        if (!enforceFocus) {
            return;
        }
        if (e.shiftKey && e.key === "Tab") {
            const lastFocusableElement = (0, overlayUtils_1.getKeyboardFocusableElements)(containerElement).pop();
            if (lastFocusableElement != null) {
                lastFocusableElement.focus();
            }
            else {
                (0, utils_1.getRef)(endFocusTrapElement)?.focus({ preventScroll: true });
            }
        }
    }, [enforceFocus]);
    /**
     * Ensures repeatedly pressing tab keeps focus inside the Overlay. Moves focus to the
     * `startFocusTrapElement` or the last keyboard-focusable element in the Overlay (excluding the
     * `startFocusTrapElement`), depending on whether the element losing focus is inside the
     * Overlay.
     */
    const handleEndFocusTrapElementFocus = (0, react_1.useCallback)((e) => {
        // No need for this.props.enforceFocus check here because this element is only rendered
        // when that prop is true.
        // During user interactions, e.relatedTarget will be defined, and we should wrap around to the
        // "start focus trap" element.
        // Otherwise, we're handling a programmatic focus event, which can only happen after a user
        // presses shift+tab from the first focusable element in the overlay.
        const startFocusTrap = (0, utils_1.getRef)(startFocusTrapElement);
        if (e.relatedTarget != null &&
            (0, utils_1.getRef)(containerElement)?.contains(e.relatedTarget) &&
            e.relatedTarget !== startFocusTrap) {
            const firstFocusableElement = (0, overlayUtils_1.getKeyboardFocusableElements)(containerElement).shift();
            // ensure we don't re-focus an already active element by comparing against e.relatedTarget
            if (!isAutoFocusing && firstFocusableElement != null && firstFocusableElement !== e.relatedTarget) {
                firstFocusableElement.focus();
            }
            else {
                startFocusTrap?.focus({ preventScroll: true });
            }
        }
        else {
            const lastFocusableElement = (0, overlayUtils_1.getKeyboardFocusableElements)(containerElement).pop();
            if (lastFocusableElement != null) {
                lastFocusableElement.focus();
            }
            else {
                // Keeps focus within Overlay even if there are no keyboard-focusable children
                startFocusTrap?.focus({ preventScroll: true });
            }
        }
    }, [isAutoFocusing]);
    const maybeBackdrop = (0, react_1.useMemo)(() => hasBackdrop && isOpen ? ((0, jsx_runtime_1.jsx)(react_transition_group_1.CSSTransition, { classNames: transitionName, nodeRef: backdropElement, timeout: transitionDuration, addEndListener: handleTransitionAddEnd, children: (0, jsx_runtime_1.jsx)("div", { ...backdropProps, className: (0, classnames_1.default)(common_1.Classes.OVERLAY_BACKDROP, backdropClassName, backdropProps?.className), onMouseDown: handleBackdropMouseDown, ref: backdropElement }) }, "__backdrop")) : null, [
        backdropClassName,
        backdropProps,
        handleBackdropMouseDown,
        handleTransitionAddEnd,
        hasBackdrop,
        isOpen,
        transitionDuration,
        transitionName,
    ]);
    // no reason to render anything at all if we're being truly lazy
    if (lazy && !hasEverOpened) {
        return null;
    }
    // TransitionGroup types require single array of children; does not support nested arrays.
    // So we must collapse backdrop and children into one array, and every item must be wrapped in a
    // Transition element (no ReactText allowed).
    const childrenWithTransitions = isOpen ? (react_1.Children.map(children, maybeRenderChild) ?? []) : [];
    // const maybeBackdrop = maybeRenderBackdrop();
    if (maybeBackdrop !== null) {
        childrenWithTransitions.unshift(maybeBackdrop);
    }
    if (isOpen && (autoFocus || enforceFocus) && childrenWithTransitions.length > 0) {
        childrenWithTransitions.unshift(renderDummyElement("__start", {
            className: common_1.Classes.OVERLAY_START_FOCUS_TRAP,
            onFocus: handleStartFocusTrapElementFocus,
            onKeyDown: handleStartFocusTrapElementKeyDown,
            ref: startFocusTrapElement,
        }));
        if (enforceFocus) {
            childrenWithTransitions.push(renderDummyElement("__end", {
                className: common_1.Classes.OVERLAY_END_FOCUS_TRAP,
                onFocus: handleEndFocusTrapElementFocus,
                ref: endFocusTrapElement,
            }));
        }
    }
    const transitionGroup = (
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions
    (0, jsx_runtime_1.jsx)("div", { "aria-live": "polite", className: (0, classnames_1.default)(common_1.Classes.OVERLAY, {
            [common_1.Classes.OVERLAY_OPEN]: isOpen,
            [common_1.Classes.OVERLAY_INLINE]: !usePortal,
        }, className), onKeyDown: handleContainerKeyDown, ref: mergedContainerRef, children: (0, jsx_runtime_1.jsx)(react_transition_group_1.TransitionGroup, { appear: true, component: null, children: childrenWithTransitions }) }));
    if (usePortal) {
        return ((0, jsx_runtime_1.jsx)(portal_1.Portal, { className: portalClassName, container: portalContainer, children: transitionGroup }));
    }
    else {
        return transitionGroup;
    }
});
exports.Overlay2.displayName = `${props_1.DISPLAYNAME_PREFIX}.Overlay2`;
function useOverlay2Validation({ childRef, childRefs, children }) {
    const numChildren = react_1.Children.count(children);
    (0, react_1.useEffect)(() => {
        if ((0, utils_1.isNodeEnv)("production")) {
            return;
        }
        if (childRef != null && childRefs != null) {
            console.error(errors_1.OVERLAY_CHILD_REF_AND_REFS_MUTEX);
        }
        if (numChildren > 1 && childRefs == null) {
            console.error(errors_1.OVERLAY_WITH_MULTIPLE_CHILDREN_REQUIRES_CHILD_REFS);
        }
    }, [childRef, childRefs, numChildren]);
}
/**
 * Generates a unique ID for a given Overlay which persists across the component's lifecycle.
 */
function useOverlay2ID() {
    const id = (0, react_1.useId)();
    return `${exports.Overlay2.displayName}-${id}`;
}
// N.B. the `onExiting` callback is not provided with the `node` argument as suggested in CSSTransition types since
// we are using the `nodeRef` prop, so we must inject it dynamically.
function getLifecycleCallbackWithChildRef(callback, childRef) {
    return () => {
        if (childRef?.current != null) {
            callback?.(childRef.current);
        }
    };
}
//# sourceMappingURL=overlay2.js.map