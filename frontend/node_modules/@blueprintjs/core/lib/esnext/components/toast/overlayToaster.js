import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import { Children, createRef } from "react";
import { createRoot } from "react-dom/client";
import { AbstractPureComponent, Classes, Position } from "../../common";
import { TOASTER_CREATE_NULL, TOASTER_MAX_TOASTS_INVALID, TOASTER_WARN_INLINE } from "../../common/errors";
import { DISPLAYNAME_PREFIX } from "../../common/props";
import { isNodeEnv } from "../../common/utils";
import { Overlay2 } from "../overlay2/overlay2";
import { Toast } from "./toast";
const defaultDomRenderer = (element, container) => {
    createRoot(container).render(element);
};
export const OVERLAY_TOASTER_DELAY_MS = 50;
/**
 * OverlayToaster component.
 *
 * @see https://blueprintjs.com/docs/#core/components/toast
 */
export class OverlayToaster extends AbstractPureComponent {
    static displayName = `${DISPLAYNAME_PREFIX}.OverlayToaster`;
    static defaultProps = {
        autoFocus: false,
        canEscapeKeyClear: true,
        position: Position.TOP,
        usePortal: true,
    };
    /**
     * Create a new `Toaster` instance that can be shared around your application.
     * The `Toaster` will be rendered into a new element appended to the given container.
     */
    static create(props, options = {}) {
        if (props != null && props.usePortal != null && !isNodeEnv("production")) {
            console.warn(TOASTER_WARN_INLINE);
        }
        const { container = document.body, domRenderer = defaultDomRenderer } = options;
        const toasterComponentRoot = document.createElement("div");
        container.appendChild(toasterComponentRoot);
        return new Promise((resolve, reject) => {
            try {
                domRenderer(_jsx(OverlayToaster, { ...props, ref: handleRef, usePortal: false }), toasterComponentRoot);
            }
            catch (error) {
                // Note that we're catching errors from the domRenderer function
                // call, but not errors when rendering <OverlayToaster>, which
                // happens in a separate scheduled tick. Wrapping the
                // OverlayToaster in an error boundary would be necessary to
                // capture rendering errors, but that's still a bit unreliable
                // and would only catch errors rendering the initial mount.
                reject(error);
            }
            // We can get a rough guarantee that the OverlayToaster has been
            // mounted to the DOM by waiting until the ref callback here has
            // been fired.
            //
            // This is the approach suggested under "What about the render
            // callback?" at https://github.com/reactwg/react-18/discussions/5.
            function handleRef(ref) {
                if (ref == null) {
                    reject(new Error(TOASTER_CREATE_NULL));
                    return;
                }
                resolve(ref);
            }
        });
    }
    /**
     * This is an alias for `OverlayToaster.create`, exposed for backwards compatibility with the 5.x API.
     *
     * @deprecated Use `OverlayToaster.create` instead.
     */
    static createAsync(props, options) {
        return OverlayToaster.create(props, options);
    }
    state = {
        toastRefs: {},
        toasts: [],
    };
    // Queue of toasts to be displayed. If toasts are shown too quickly back to back, it can result in cut off toasts.
    // The queue ensures that toasts are only displayed in QUEUE_TIMEOUT_MS increments.
    queue = {
        cancel: undefined,
        isRunning: false,
        toasts: [],
    };
    // auto-incrementing identifier for un-keyed toasts
    toastId = 0;
    toastRefs = {};
    /** Compute a new collection of toast refs (usually after updating toasts) */
    getToastRefs = (toasts) => {
        return toasts.reduce((refs, toast) => {
            refs[toast.key] = createRef();
            return refs;
        }, {});
    };
    show(props, key) {
        const options = this.createToastOptions(props, key);
        const wasExistingToastUpdated = this.maybeUpdateExistingToast(options, key);
        if (wasExistingToastUpdated) {
            return options.key;
        }
        if (this.queue.isRunning) {
            // If a toast has been shown recently, push to the queued toasts to prevent toasts from being shown too
            // quickly for the animations to keep up
            this.queue.toasts.push(options);
        }
        else {
            // If we have not recently shown a toast, we can immediately show the given toast
            this.immediatelyShowToast(options);
            this.startQueueTimeout();
        }
        return options.key;
    }
    maybeUpdateExistingToast(options, key) {
        if (key == null) {
            return false;
        }
        const isExistingQueuedToast = this.queue.toasts.some(toast => toast.key === key);
        if (isExistingQueuedToast) {
            this.queue.toasts = this.queue.toasts.map(t => (t.key === key ? options : t));
            return true;
        }
        const isExistingShownToast = this.state.toasts.some(toast => toast.key === key);
        if (isExistingShownToast) {
            this.updateToastsInState(toasts => toasts.map(t => (t.key === key ? options : t)));
            return true;
        }
        return false;
    }
    immediatelyShowToast(options) {
        if (this.props.maxToasts) {
            // check if active number of toasts are at the maxToasts limit
            this.dismissIfAtLimit();
        }
        this.updateToastsInState(toasts => [options, ...toasts]);
    }
    startQueueTimeout() {
        this.queue.isRunning = true;
        this.queue.cancel = this.setTimeout(this.handleQueueTimeout, OVERLAY_TOASTER_DELAY_MS);
    }
    handleQueueTimeout = () => {
        const nextToast = this.queue.toasts.shift();
        if (nextToast != null) {
            this.immediatelyShowToast(nextToast);
            this.startQueueTimeout();
        }
        else {
            this.queue.isRunning = false;
        }
    };
    updateToastsInState(getNewToasts) {
        this.setState(prevState => {
            const toasts = getNewToasts(prevState.toasts);
            return { toastRefs: this.getToastRefs(toasts), toasts };
        });
    }
    dismiss(key, timeoutExpired = false) {
        this.setState(prevState => {
            const toasts = prevState.toasts.filter(t => {
                const matchesKey = t.key === key;
                if (matchesKey) {
                    t.onDismiss?.(timeoutExpired);
                }
                return !matchesKey;
            });
            return { toastRefs: this.getToastRefs(toasts), toasts };
        });
    }
    clear() {
        this.queue.cancel?.();
        this.queue = { cancel: undefined, isRunning: false, toasts: [] };
        this.state.toasts.forEach(t => t.onDismiss?.(false));
        this.setState({ toastRefs: {}, toasts: [] });
    }
    getToasts() {
        return this.state.toasts;
    }
    render() {
        const classes = classNames(Classes.TOAST_CONTAINER, this.getPositionClasses(), this.props.className);
        return (_jsxs(Overlay2
        // eslint-disable-next-line jsx-a11y/no-autofocus
        , { 
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus: this.props.autoFocus, canEscapeKeyClose: this.props.canEscapeKeyClear, canOutsideClickClose: false, className: classes, childRefs: this.toastRefs, enforceFocus: false, hasBackdrop: false, isOpen: this.state.toasts.length > 0 || Children.count(this.props.children) > 0, onClose: this.handleClose, shouldReturnFocusOnClose: false, 
            // $pt-transition-duration * 3 + $pt-transition-duration / 2
            transitionDuration: 350, transitionName: Classes.TOAST, usePortal: this.props.usePortal, children: [this.state.toasts.map(this.renderToast, this), this.props.children] }));
    }
    validateProps({ maxToasts }) {
        // maximum number of toasts should not be a number less than 1
        if (maxToasts !== undefined && maxToasts < 1) {
            throw new Error(TOASTER_MAX_TOASTS_INVALID);
        }
    }
    dismissIfAtLimit() {
        if (this.state.toasts.length === this.props.maxToasts) {
            // dismiss the oldest toast to stay within the maxToasts limit
            this.dismiss(this.state.toasts[this.state.toasts.length - 1].key);
        }
    }
    renderToast = (toast) => {
        const { key, ...toastProps } = toast;
        return _jsx(Toast, { ...toastProps, onDismiss: this.getDismissHandler(toast) }, key);
    };
    createToastOptions(props, key = `toast-${this.toastId++}`) {
        // clone the object before adding the key prop to avoid leaking the mutation
        return { ...props, key };
    }
    getPositionClasses() {
        const positions = this.props.position.split("-");
        // NOTE that there is no -center class because that's the default style
        return [
            ...positions.map(p => `${Classes.TOAST_CONTAINER}-${p.toLowerCase()}`),
            `${Classes.TOAST_CONTAINER}-${this.props.usePortal ? "in-portal" : "inline"}`,
        ];
    }
    getDismissHandler = (toast) => (timeoutExpired) => {
        this.dismiss(toast.key, timeoutExpired);
    };
    handleClose = (e) => {
        // NOTE that `e` isn't always a KeyboardEvent but that's the only type we care about
        if (e.key === "Escape") {
            this.clear();
        }
    };
}
//# sourceMappingURL=overlayToaster.js.map