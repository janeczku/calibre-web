/*
 * Copyright 2022 Palantir Technologies, Inc. All rights reserved.
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
import { useCallback, useContext, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { PortalContext } from "../../context/portal/portalProvider";
/**
 * Portal component.
 *
 * This component detaches its contents and re-attaches them to document.body.
 * Use it when you need to circumvent DOM z-stacking (for dialogs, popovers, etc.).
 * Any class names passed to this element will be propagated to the new container element on document.body.
 *
 * @see https://blueprintjs.com/docs/#core/components/portal
 */
export function Portal(
// eslint-disable-next-line @typescript-eslint/no-deprecated
{ className, stopPropagationEvents, container, onChildrenMount, children }) {
    const context = useContext(PortalContext);
    const portalContainer = container ?? context.portalContainer ?? (typeof document !== "undefined" ? document.body : undefined);
    const [portalElement, setPortalElement] = useState();
    const createPortalElement = useCallback(() => {
        const newPortalElement = document.createElement("div");
        newPortalElement.classList.add(Classes.PORTAL);
        maybeAddClass(newPortalElement.classList, className); // directly added to this portal element
        maybeAddClass(newPortalElement.classList, context.portalClassName); // added via PortalProvider context
        addStopPropagationListeners(newPortalElement, stopPropagationEvents);
        return newPortalElement;
    }, [className, context.portalClassName, stopPropagationEvents]);
    // create the container element & attach it to the DOM
    useEffect(() => {
        if (portalContainer == null) {
            return;
        }
        const newPortalElement = createPortalElement();
        portalContainer.appendChild(newPortalElement);
        setPortalElement(newPortalElement);
        return () => {
            removeStopPropagationListeners(newPortalElement, stopPropagationEvents);
            newPortalElement.remove();
            setPortalElement(undefined);
        };
    }, [portalContainer, createPortalElement, stopPropagationEvents]);
    // wait until next successful render to invoke onChildrenMount callback
    useEffect(() => {
        if (portalElement != null) {
            onChildrenMount?.();
        }
    }, [portalElement, onChildrenMount]);
    useEffect(() => {
        if (portalElement != null) {
            maybeAddClass(portalElement.classList, className);
            return () => maybeRemoveClass(portalElement.classList, className);
        }
        return undefined;
    }, [className, portalElement]);
    useEffect(() => {
        if (portalElement != null) {
            addStopPropagationListeners(portalElement, stopPropagationEvents);
            return () => removeStopPropagationListeners(portalElement, stopPropagationEvents);
        }
        return undefined;
    }, [portalElement, stopPropagationEvents]);
    // Only render `children` once this component has mounted in a browser environment, so they are
    // immediately attached to the DOM tree and can do DOM things like measuring or `autoFocus`.
    // See long comment on componentDidMount in https://reactjs.org/docs/portals.html#event-bubbling-through-portals
    if (typeof document === "undefined" || portalElement == null) {
        return null;
    }
    else {
        return createPortal(children, portalElement);
    }
}
Portal.displayName = `${DISPLAYNAME_PREFIX}.Portal`;
function maybeRemoveClass(classList, className) {
    if (className != null && className !== "") {
        classList.remove(...className.split(" "));
    }
}
function maybeAddClass(classList, className) {
    if (className != null && className !== "") {
        classList.add(...className.split(" "));
    }
}
function addStopPropagationListeners(portalElement, eventNames) {
    eventNames?.forEach(event => portalElement.addEventListener(event, handleStopProgation));
}
function removeStopPropagationListeners(portalElement, events) {
    events?.forEach(event => portalElement.removeEventListener(event, handleStopProgation));
}
function handleStopProgation(e) {
    e.stopPropagation();
}
//# sourceMappingURL=portal.js.map