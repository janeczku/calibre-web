import { jsx as _jsx } from "react/jsx-runtime";
/*
 * Copyright 2016 Palantir Technologies, Inc. All rights reserved.
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
import { AbstractPureComponent, Classes, Utils } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
import { formatPercentage } from "./sliderUtils";
// props that require number values, for validation
const NUMBER_PROPS = ["max", "min", "stepSize", "tickSize", "value"];
/** Internal component for a Handle with click/drag/keyboard logic to determine a new value. */
export class Handle extends AbstractPureComponent {
    static displayName = `${DISPLAYNAME_PREFIX}.SliderHandle`;
    state = {
        isMoving: false,
    };
    handleElement = null;
    refHandlers = {
        handle: (el) => (this.handleElement = el),
    };
    componentDidMount() {
        // The first time this component renders, it has no ref to the handle and thus incorrectly centers the handle.
        // Therefore, on the first mount, force a re-render to center the handle with the ref'd component.
        this.forceUpdate();
    }
    render() {
        const { className, disabled, label, min, max, value, vertical, htmlProps } = this.props;
        const { isMoving } = this.state;
        return (_jsx("span", { role: "slider", tabIndex: 0, ...htmlProps, className: classNames(Classes.SLIDER_HANDLE, { [Classes.ACTIVE]: isMoving }, className), onKeyDown: disabled ? undefined : this.handleKeyDown, onKeyUp: disabled ? undefined : this.handleKeyUp, onMouseDown: disabled ? undefined : this.beginHandleMovement, onTouchStart: disabled ? undefined : this.beginHandleTouchMovement, ref: this.refHandlers.handle, style: this.getStyleProperties(), "aria-valuemin": min, "aria-valuemax": max, "aria-valuenow": value, "aria-disabled": disabled, "aria-orientation": vertical ? "vertical" : "horizontal", children: label == null ? null : _jsx("span", { className: Classes.SLIDER_LABEL, children: label }) }));
    }
    componentWillUnmount() {
        this.removeDocumentEventListeners();
    }
    /** Convert client pixel to value between min and max. */
    clientToValue(clientPixel) {
        const { stepSize, tickSize, value, vertical } = this.props;
        if (this.handleElement == null) {
            return value;
        }
        // #1769: this logic doesn't work perfectly when the tick size is
        // smaller than the handle size; it may be off by a tick or two.
        const clientPixelNormalized = vertical ? window.innerHeight - clientPixel : clientPixel;
        const handleCenterPixel = this.getHandleElementCenterPixel(this.handleElement);
        const pixelDelta = clientPixelNormalized - handleCenterPixel;
        if (isNaN(pixelDelta)) {
            return value;
        }
        // convert pixels to range value in increments of `stepSize`
        return value + Math.round(pixelDelta / (tickSize * stepSize)) * stepSize;
    }
    mouseEventClientOffset(event) {
        return this.props.vertical ? event.clientY : event.clientX;
    }
    touchEventClientOffset(event) {
        const touch = event.changedTouches[0];
        return this.props.vertical ? touch.clientY : touch.clientX;
    }
    beginHandleMovement = (event) => {
        document.addEventListener("mousemove", this.handleHandleMovement);
        document.addEventListener("mouseup", this.endHandleMovement);
        this.setState({ isMoving: true });
        this.changeValue(this.clientToValue(this.mouseEventClientOffset(event)));
    };
    beginHandleTouchMovement = (event) => {
        document.addEventListener("touchmove", this.handleHandleTouchMovement);
        document.addEventListener("touchend", this.endHandleTouchMovement);
        document.addEventListener("touchcancel", this.endHandleTouchMovement);
        this.setState({ isMoving: true });
        this.changeValue(this.clientToValue(this.touchEventClientOffset(event)));
    };
    validateProps(props) {
        for (const prop of NUMBER_PROPS) {
            if (typeof props[prop] !== "number") {
                throw new Error(`[Blueprint] <Handle> requires number value for ${prop} prop`);
            }
        }
    }
    getStyleProperties = () => {
        if (this.handleElement == null) {
            return {};
        }
        // The handle midpoint of RangeSlider is actually shifted by a margin to
        // be on the edge of the visible handle element. Because the midpoint
        // calculation does not take this margin into account, we instead
        // measure the long side (which is equal to the short side plus the
        // margin).
        const { min = 0, tickSizeRatio, value, vertical } = this.props;
        const { handleMidpoint } = this.getHandleMidpointAndOffset(this.handleElement, true);
        const offsetRatio = (value - min) * tickSizeRatio;
        const offsetCalc = `calc(${formatPercentage(offsetRatio)} - ${handleMidpoint}px)`;
        return vertical ? { bottom: offsetCalc } : { left: offsetCalc };
    };
    endHandleMovement = (event) => {
        this.handleMoveEndedAt(this.mouseEventClientOffset(event));
    };
    endHandleTouchMovement = (event) => {
        this.handleMoveEndedAt(this.touchEventClientOffset(event));
    };
    handleMoveEndedAt = (clientPixel) => {
        this.removeDocumentEventListeners();
        this.setState({ isMoving: false });
        // always invoke onRelease; changeValue may call onChange if value is different
        const finalValue = this.changeValue(this.clientToValue(clientPixel));
        this.props.onRelease?.(finalValue);
    };
    handleHandleMovement = (event) => {
        this.handleMovedTo(this.mouseEventClientOffset(event));
    };
    handleHandleTouchMovement = (event) => {
        this.handleMovedTo(this.touchEventClientOffset(event));
    };
    handleMovedTo = (clientPixel) => {
        if (this.state.isMoving && !this.props.disabled) {
            this.changeValue(this.clientToValue(clientPixel));
        }
    };
    handleKeyDown = (event) => {
        const { stepSize, value } = this.props;
        const direction = Utils.getArrowKeyDirection(event, ["ArrowLeft", "ArrowDown"], ["ArrowRight", "ArrowUp"]);
        if (direction !== undefined) {
            this.changeValue(value + stepSize * direction);
            // this key event has been handled! prevent browser scroll on up/down
            event.preventDefault();
        }
    };
    handleKeyUp = (event) => {
        if (Utils.isArrowKey(event)) {
            this.props.onRelease?.(this.props.value);
        }
    };
    /** Clamp value and invoke callback if it differs from current value */
    changeValue(newValue, callback = this.props.onChange) {
        newValue = this.clamp(newValue);
        if (!isNaN(newValue) && this.props.value !== newValue) {
            callback?.(newValue);
        }
        return newValue;
    }
    /** Clamp value between min and max props */
    clamp(value) {
        return Utils.clamp(value, this.props.min, this.props.max);
    }
    getHandleElementCenterPixel(handleElement) {
        const { handleMidpoint, handleOffset } = this.getHandleMidpointAndOffset(handleElement);
        return handleOffset + handleMidpoint;
    }
    getHandleMidpointAndOffset(handleElement, useOppositeDimension = false) {
        if (handleElement == null) {
            return { handleMidpoint: 0, handleOffset: 0 };
        }
        const { vertical } = this.props;
        // N.B. element.clientHeight does not include border size.
        // Also, element.getBoundingClientRect() is useful to get the top & left position on the page, but
        // it fails to accurately measure element width & height inside absolutely-positioned and CSS-transformed
        // containers like Popovers, so we use element.offsetWidth & offsetHeight instead (see https://github.com/palantir/blueprint/issues/4417).
        const handleRect = handleElement.getBoundingClientRect();
        handleRect.width = handleElement.offsetWidth;
        handleRect.height = handleElement.offsetHeight;
        const sizeKey = vertical
            ? useOppositeDimension
                ? "width"
                : "height"
            : useOppositeDimension
                ? "height"
                : "width";
        // "bottom" value seems to be consistently incorrect, so explicitly
        // calculate it using the window offset instead.
        const handleOffset = vertical ? window.innerHeight - (handleRect.top + handleRect[sizeKey]) : handleRect.left;
        return { handleMidpoint: handleRect[sizeKey] / 2, handleOffset };
    }
    removeDocumentEventListeners() {
        document.removeEventListener("mousemove", this.handleHandleMovement);
        document.removeEventListener("mouseup", this.endHandleMovement);
        document.removeEventListener("touchmove", this.handleHandleTouchMovement);
        document.removeEventListener("touchend", this.endHandleTouchMovement);
        document.removeEventListener("touchcancel", this.endHandleTouchMovement);
    }
}
//# sourceMappingURL=handle.js.map