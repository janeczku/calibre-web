"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Overlay = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
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
/**
 * @fileoverview This component is DEPRECATED, and the code is frozen.
 * All changes & bugfixes should be made to Overlay2 instead.
 */
/* eslint-disable @typescript-eslint/no-deprecated */
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const react_transition_group_1 = require("react-transition-group");
const common_1 = require("../../common");
const props_1 = require("../../common/props");
const utils_1 = require("../../common/utils");
const portal_1 = require("../portal/portal");
const overlayUtils_1 = require("./overlayUtils");
/**
 * Overlay component.
 *
 * @deprecated use `Overlay2` instead
 * @see https://blueprintjs.com/docs/#core/components/overlay
 */
class Overlay extends common_1.AbstractPureComponent {
    static displayName = `${props_1.DISPLAYNAME_PREFIX}.Overlay`;
    static defaultProps = {
        autoFocus: true,
        backdropProps: {},
        canEscapeKeyClose: true,
        canOutsideClickClose: true,
        enforceFocus: true,
        hasBackdrop: true,
        isOpen: false,
        lazy: true,
        shouldReturnFocusOnClose: true,
        transitionDuration: 300,
        transitionName: common_1.Classes.OVERLAY,
        usePortal: true,
    };
    static getDerivedStateFromProps({ isOpen: hasEverOpened }) {
        if (hasEverOpened) {
            return { hasEverOpened };
        }
        return null;
    }
    static openStack = [];
    static getLastOpened = () => Overlay.openStack[Overlay.openStack.length - 1];
    isAutoFocusing = false;
    lastActiveElementBeforeOpened;
    state = {
        hasEverOpened: this.props.isOpen,
    };
    /** Ref for container element, containing all children and the backdrop */
    containerElement = (0, react_1.createRef)();
    // An empty, keyboard-focusable div at the beginning of the Overlay content
    startFocusTrapElement = (0, react_1.createRef)();
    // An empty, keyboard-focusable div at the end of the Overlay content
    endFocusTrapElement = (0, react_1.createRef)();
    render() {
        // oh snap! no reason to render anything at all if we're being truly lazy
        if (this.props.lazy && !this.state.hasEverOpened) {
            return null;
        }
        const { autoFocus, children, className, enforceFocus, usePortal, isOpen } = this.props;
        // TransitionGroup types require single array of children; does not support nested arrays.
        // So we must collapse backdrop and children into one array, and every item must be wrapped in a
        // Transition element (no ReactText allowed).
        const childrenWithTransitions = isOpen ? (react_1.Children.map(children, this.maybeRenderChild) ?? []) : [];
        const maybeBackdrop = this.maybeRenderBackdrop();
        if (maybeBackdrop !== null) {
            childrenWithTransitions.unshift(maybeBackdrop);
        }
        if (isOpen && (autoFocus || enforceFocus) && childrenWithTransitions.length > 0) {
            childrenWithTransitions.unshift(this.renderDummyElement("__start", {
                className: common_1.Classes.OVERLAY_START_FOCUS_TRAP,
                onFocus: this.handleStartFocusTrapElementFocus,
                onKeyDown: this.handleStartFocusTrapElementKeyDown,
                ref: this.startFocusTrapElement,
            }));
            if (enforceFocus) {
                childrenWithTransitions.push(this.renderDummyElement("__end", {
                    className: common_1.Classes.OVERLAY_END_FOCUS_TRAP,
                    onFocus: this.handleEndFocusTrapElementFocus,
                    ref: this.endFocusTrapElement,
                }));
            }
        }
        const containerClasses = (0, classnames_1.default)(common_1.Classes.OVERLAY, {
            [common_1.Classes.OVERLAY_OPEN]: isOpen,
            [common_1.Classes.OVERLAY_INLINE]: !usePortal,
        }, className);
        const transitionGroup = (
        // eslint-disable-next-line jsx-a11y/no-static-element-interactions
        (0, jsx_runtime_1.jsx)("div", { "aria-live": "polite", className: containerClasses, onKeyDown: this.handleKeyDown, ref: this.containerElement, children: (0, jsx_runtime_1.jsx)(react_transition_group_1.TransitionGroup, { appear: true, component: null, children: childrenWithTransitions }) }));
        if (usePortal) {
            return ((0, jsx_runtime_1.jsx)(portal_1.Portal, { className: this.props.portalClassName, container: this.props.portalContainer, stopPropagationEvents: this.props.portalStopPropagationEvents, children: transitionGroup }));
        }
        else {
            return transitionGroup;
        }
    }
    componentDidMount() {
        if (this.props.isOpen) {
            this.overlayWillOpen();
        }
    }
    componentDidUpdate(prevProps) {
        if (prevProps.isOpen && !this.props.isOpen) {
            this.overlayWillClose();
        }
        else if (!prevProps.isOpen && this.props.isOpen) {
            this.overlayWillOpen();
        }
    }
    componentWillUnmount() {
        this.overlayWillClose();
    }
    /**
     * @public for testing
     * @internal
     */
    bringFocusInsideOverlay() {
        // always delay focus manipulation to just before repaint to prevent scroll jumping
        return this.requestAnimationFrame(() => {
            // container element may be undefined between component mounting and Portal rendering
            // activeElement may be undefined in some rare cases in IE
            const activeElement = (0, utils_1.getActiveElement)(this.containerElement.current);
            if (this.containerElement.current == null || activeElement == null || !this.props.isOpen) {
                return;
            }
            const container = this.containerElement.current;
            const isFocusOutsideModal = !container.contains(activeElement);
            if (isFocusOutsideModal) {
                this.startFocusTrapElement.current?.focus({ preventScroll: true });
                this.isAutoFocusing = false;
            }
        });
    }
    maybeRenderChild = (child) => {
        if ((0, utils_1.isFunction)(child)) {
            child = child();
        }
        if (child == null) {
            return null;
        }
        // decorate the child with a few injected props
        const tabIndex = this.props.enforceFocus || this.props.autoFocus ? 0 : undefined;
        const decoratedChild = typeof child === "object" ? ((0, react_1.cloneElement)(child, {
            className: (0, classnames_1.default)(child.props.className, common_1.Classes.OVERLAY_CONTENT),
            tabIndex,
        })) : ((0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.OVERLAY_CONTENT, tabIndex: tabIndex, children: child }));
        const { onOpening, onOpened, onClosing, transitionDuration, transitionName } = this.props;
        return ((0, jsx_runtime_1.jsx)(react_transition_group_1.CSSTransition, { classNames: transitionName, onEntering: onOpening, onEntered: onOpened, onExiting: onClosing, onExited: this.handleTransitionExited, timeout: transitionDuration, addEndListener: this.handleTransitionAddEnd, children: decoratedChild }));
    };
    maybeRenderBackdrop() {
        const { backdropClassName, backdropProps, hasBackdrop, isOpen, transitionDuration, transitionName } = this.props;
        if (hasBackdrop && isOpen) {
            return ((0, jsx_runtime_1.jsx)(react_transition_group_1.CSSTransition, { classNames: transitionName, timeout: transitionDuration, addEndListener: this.handleTransitionAddEnd, children: (0, jsx_runtime_1.jsx)("div", { ...backdropProps, className: (0, classnames_1.default)(common_1.Classes.OVERLAY_BACKDROP, backdropClassName, backdropProps?.className), onMouseDown: this.handleBackdropMouseDown }) }, "__backdrop"));
        }
        else {
            return null;
        }
    }
    renderDummyElement(key, props) {
        const { transitionDuration, transitionName } = this.props;
        return ((0, jsx_runtime_1.jsx)(react_transition_group_1.CSSTransition, { classNames: transitionName, addEndListener: this.handleTransitionAddEnd, timeout: transitionDuration, unmountOnExit: true, children: (0, jsx_runtime_1.jsx)("div", { tabIndex: 0, ...props }) }, key));
    }
    /**
     * Ensures repeatedly pressing shift+tab keeps focus inside the Overlay. Moves focus to
     * the `endFocusTrapElement` or the first keyboard-focusable element in the Overlay (excluding
     * the `startFocusTrapElement`), depending on whether the element losing focus is inside the
     * Overlay.
     */
    handleStartFocusTrapElementFocus = (e) => {
        if (!this.props.enforceFocus || this.isAutoFocusing) {
            return;
        }
        // e.relatedTarget will not be defined if this was a programmatic focus event, as is the
        // case when we call this.bringFocusInsideOverlay() after a user clicked on the backdrop.
        // Otherwise, we're handling a user interaction, and we should wrap around to the last
        // element in this transition group.
        if (e.relatedTarget != null &&
            this.containerElement.current?.contains(e.relatedTarget) &&
            e.relatedTarget !== this.endFocusTrapElement.current) {
            this.endFocusTrapElement.current?.focus({ preventScroll: true });
        }
    };
    /**
     * Wrap around to the end of the dialog if `enforceFocus` is enabled.
     */
    handleStartFocusTrapElementKeyDown = (e) => {
        if (!this.props.enforceFocus) {
            return;
        }
        if (e.shiftKey && e.key === "Tab") {
            const lastFocusableElement = (0, overlayUtils_1.getKeyboardFocusableElements)(this.containerElement).pop();
            if (lastFocusableElement != null) {
                lastFocusableElement.focus();
            }
            else {
                this.endFocusTrapElement.current?.focus({ preventScroll: true });
            }
        }
    };
    /**
     * Ensures repeatedly pressing tab keeps focus inside the Overlay. Moves focus to the
     * `startFocusTrapElement` or the last keyboard-focusable element in the Overlay (excluding the
     * `startFocusTrapElement`), depending on whether the element losing focus is inside the
     * Overlay.
     */
    handleEndFocusTrapElementFocus = (e) => {
        // No need for this.props.enforceFocus check here because this element is only rendered
        // when that prop is true.
        // During user interactions, e.relatedTarget will be defined, and we should wrap around to the
        // "start focus trap" element.
        // Otherwise, we're handling a programmatic focus event, which can only happen after a user
        // presses shift+tab from the first focusable element in the overlay.
        if (e.relatedTarget != null &&
            this.containerElement.current?.contains(e.relatedTarget) &&
            e.relatedTarget !== this.startFocusTrapElement.current) {
            const firstFocusableElement = (0, overlayUtils_1.getKeyboardFocusableElements)(this.containerElement).shift();
            // ensure we don't re-focus an already active element by comparing against e.relatedTarget
            if (!this.isAutoFocusing && firstFocusableElement != null && firstFocusableElement !== e.relatedTarget) {
                firstFocusableElement.focus();
            }
            else {
                this.startFocusTrapElement.current?.focus({ preventScroll: true });
            }
        }
        else {
            const lastFocusableElement = (0, overlayUtils_1.getKeyboardFocusableElements)(this.containerElement).pop();
            if (lastFocusableElement != null) {
                lastFocusableElement.focus();
            }
            else {
                // Keeps focus within Overlay even if there are no keyboard-focusable children
                this.startFocusTrapElement.current?.focus({ preventScroll: true });
            }
        }
    };
    overlayWillClose() {
        document.removeEventListener("focus", this.handleDocumentFocus, /* useCapture */ true);
        document.removeEventListener("mousedown", this.handleDocumentClick);
        const { openStack } = Overlay;
        const stackIndex = openStack.indexOf(this);
        if (stackIndex !== -1) {
            openStack.splice(stackIndex, 1);
            if (openStack.length > 0) {
                const lastOpenedOverlay = Overlay.getLastOpened();
                // Only bring focus back to last overlay if it had autoFocus _and_ enforceFocus enabled.
                // If `autoFocus={false}`, it's likely that the overlay never received focus in the first place,
                // so it would be surprising for us to send it there. See https://github.com/palantir/blueprint/issues/4921
                if (lastOpenedOverlay.props.autoFocus && lastOpenedOverlay.props.enforceFocus) {
                    lastOpenedOverlay.bringFocusInsideOverlay();
                    document.addEventListener("focus", lastOpenedOverlay.handleDocumentFocus, /* useCapture */ true);
                }
            }
            if (openStack.filter(o => o.props.usePortal && o.props.hasBackdrop).length === 0) {
                document.body.classList.remove(common_1.Classes.OVERLAY_OPEN);
            }
        }
    }
    overlayWillOpen() {
        const { getLastOpened, openStack } = Overlay;
        if (openStack.length > 0) {
            document.removeEventListener("focus", getLastOpened().handleDocumentFocus, /* useCapture */ true);
        }
        openStack.push(this);
        if (this.props.autoFocus) {
            this.isAutoFocusing = true;
            this.bringFocusInsideOverlay();
        }
        if (this.props.enforceFocus) {
            // Focus events do not bubble, but setting useCapture allows us to listen in and execute
            // our handler before all others
            document.addEventListener("focus", this.handleDocumentFocus, /* useCapture */ true);
        }
        if (this.props.canOutsideClickClose && !this.props.hasBackdrop) {
            document.addEventListener("mousedown", this.handleDocumentClick);
        }
        if (this.props.hasBackdrop && this.props.usePortal) {
            // add a class to the body to prevent scrolling of content below the overlay
            document.body.classList.add(common_1.Classes.OVERLAY_OPEN);
        }
        this.lastActiveElementBeforeOpened = (0, utils_1.getActiveElement)(this.containerElement.current);
    }
    handleTransitionExited = (node) => {
        if (this.props.shouldReturnFocusOnClose && this.lastActiveElementBeforeOpened instanceof HTMLElement) {
            this.lastActiveElementBeforeOpened.focus();
        }
        this.props.onClosed?.(node);
    };
    handleBackdropMouseDown = (e) => {
        const { backdropProps, canOutsideClickClose, enforceFocus, onClose } = this.props;
        if (canOutsideClickClose) {
            onClose?.(e);
        }
        if (enforceFocus) {
            this.bringFocusInsideOverlay();
        }
        backdropProps?.onMouseDown?.(e);
    };
    handleDocumentClick = (e) => {
        const { canOutsideClickClose, isOpen, onClose } = this.props;
        // get the actual target even in the Shadow DOM
        // see https://github.com/palantir/blueprint/issues/4220
        const eventTarget = (e.composed ? e.composedPath()[0] : e.target);
        const stackIndex = Overlay.openStack.indexOf(this);
        const isClickInThisOverlayOrDescendant = Overlay.openStack
            .slice(stackIndex)
            .some(({ containerElement: elem }) => {
            // `elem` is the container of backdrop & content, so clicking directly on that container
            // should not count as being "inside" the overlay.
            return elem.current?.contains(eventTarget) && !elem.current.isSameNode(eventTarget);
        });
        if (isOpen && !isClickInThisOverlayOrDescendant && canOutsideClickClose) {
            // casting to any because this is a native event
            onClose?.(e);
        }
    };
    /**
     * When multiple Overlays are open, this event handler is only active for the most recently
     * opened one to avoid Overlays competing with each other for focus.
     */
    handleDocumentFocus = (e) => {
        // get the actual target even in the Shadow DOM
        // see https://github.com/palantir/blueprint/issues/4220
        const eventTarget = e.composed ? e.composedPath()[0] : e.target;
        if (this.props.enforceFocus &&
            this.containerElement.current != null &&
            eventTarget instanceof Node &&
            !this.containerElement.current.contains(eventTarget)) {
            // prevent default focus behavior (sometimes auto-scrolls the page)
            e.preventDefault();
            e.stopImmediatePropagation();
            this.bringFocusInsideOverlay();
        }
    };
    handleKeyDown = (e) => {
        const { canEscapeKeyClose, onClose } = this.props;
        if (e.key === "Escape" && canEscapeKeyClose) {
            onClose?.(e);
            // prevent other overlays from closing
            e.stopPropagation();
            // prevent browser-specific escape key behavior (Safari exits fullscreen)
            e.preventDefault();
        }
    };
    handleTransitionAddEnd = () => {
        // no-op
    };
}
exports.Overlay = Overlay;
//# sourceMappingURL=overlay.js.map