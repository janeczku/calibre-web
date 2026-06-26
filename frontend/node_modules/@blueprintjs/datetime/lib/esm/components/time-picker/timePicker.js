import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
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
import { Component } from "react";
import { Classes as CoreClasses, Utils as CoreUtils, DISPLAYNAME_PREFIX, HTMLSelect, Icon, Intent, } from "@blueprintjs/core";
import { Classes, DateUtils, TimePrecision } from "../../common";
import { getDefaultMaxTime, getDefaultMinTime, getTimeUnit, getTimeUnitClassName, getTimeUnitMax, getTimeUnitPrintStr, isTimeUnitValid, setTimeUnit, TimeUnit, wrapTimeAtUnit, } from "../../common/timeUnit";
import * as Utils from "../../common/utils";
/**
 * Time picker component.
 *
 * @see https://blueprintjs.com/docs/#datetime/timepicker
 */
export class TimePicker extends Component {
    static defaultProps = {
        autoFocus: false,
        disabled: false,
        maxTime: getDefaultMaxTime(),
        minTime: getDefaultMinTime(),
        precision: TimePrecision.MINUTE,
        selectAllOnFocus: false,
        showArrowButtons: false,
        useAmPm: false,
    };
    static displayName = `${DISPLAYNAME_PREFIX}.TimePicker`;
    constructor(props) {
        super(props);
        this.state = this.getFullStateFromValue(this.getInitialValue(), props.useAmPm);
    }
    timeInputIds = {
        [TimeUnit.HOUR_24]: CoreUtils.uniqueId(TimeUnit.HOUR_24 + "-input"),
        [TimeUnit.HOUR_12]: CoreUtils.uniqueId(TimeUnit.HOUR_12 + "-input"),
        [TimeUnit.MINUTE]: CoreUtils.uniqueId(TimeUnit.MINUTE + "-input"),
        [TimeUnit.SECOND]: CoreUtils.uniqueId(TimeUnit.SECOND + "-input"),
        [TimeUnit.MS]: CoreUtils.uniqueId(TimeUnit.MS + "-input"),
    };
    render() {
        const shouldRenderMilliseconds = this.props.precision === TimePrecision.MILLISECOND;
        const shouldRenderSeconds = shouldRenderMilliseconds || this.props.precision === TimePrecision.SECOND;
        const hourUnit = this.props.useAmPm ? TimeUnit.HOUR_12 : TimeUnit.HOUR_24;
        const classes = classNames(Classes.TIMEPICKER, this.props.className, {
            [CoreClasses.DISABLED]: this.props.disabled,
        });
        return (_jsxs("div", { className: classes, children: [_jsxs("div", { className: Classes.TIMEPICKER_ARROW_ROW, children: [this.maybeRenderArrowButton(true, hourUnit), this.maybeRenderArrowButton(true, TimeUnit.MINUTE), shouldRenderSeconds && this.maybeRenderArrowButton(true, TimeUnit.SECOND), shouldRenderMilliseconds && this.maybeRenderArrowButton(true, TimeUnit.MS)] }), _jsxs("div", { className: Classes.TIMEPICKER_INPUT_ROW, children: [this.renderInput(Classes.TIMEPICKER_HOUR, hourUnit, this.state.hourText), this.renderDivider(), this.renderInput(Classes.TIMEPICKER_MINUTE, TimeUnit.MINUTE, this.state.minuteText), shouldRenderSeconds && this.renderDivider(), shouldRenderSeconds &&
                            this.renderInput(Classes.TIMEPICKER_SECOND, TimeUnit.SECOND, this.state.secondText), shouldRenderMilliseconds && this.renderDivider("."), shouldRenderMilliseconds &&
                            this.renderInput(Classes.TIMEPICKER_MILLISECOND, TimeUnit.MS, this.state.millisecondText)] }), this.maybeRenderAmPm(), _jsxs("div", { className: Classes.TIMEPICKER_ARROW_ROW, children: [this.maybeRenderArrowButton(false, hourUnit), this.maybeRenderArrowButton(false, TimeUnit.MINUTE), shouldRenderSeconds && this.maybeRenderArrowButton(false, TimeUnit.SECOND), shouldRenderMilliseconds && this.maybeRenderArrowButton(false, TimeUnit.MS)] })] }));
    }
    componentDidUpdate(prevProps) {
        const didMinTimeChange = prevProps.minTime !== this.props.minTime;
        const didMaxTimeChange = prevProps.maxTime !== this.props.maxTime;
        const didBoundsChange = didMinTimeChange || didMaxTimeChange;
        const didPropValueChange = prevProps.value !== this.props.value;
        const shouldStateUpdate = didBoundsChange || didPropValueChange;
        let value = this.state.value;
        if (this.props.value == null) {
            value = this.getInitialValue();
        }
        if (didBoundsChange) {
            value = DateUtils.getTimeInRange(this.state.value ?? this.getInitialValue(), this.props.minTime ?? getDefaultMinTime(), this.props.maxTime ?? getDefaultMaxTime());
        }
        if (this.props.value != null && !DateUtils.isSameTime(this.props.value, prevProps.value ?? null)) {
            value = this.props.value;
        }
        if (shouldStateUpdate) {
            this.setState(this.getFullStateFromValue(value, this.props.useAmPm));
        }
    }
    // begin method definitions: rendering
    maybeRenderArrowButton(isDirectionUp, timeUnit) {
        if (!this.props.showArrowButtons) {
            return null;
        }
        const classes = classNames(Classes.TIMEPICKER_ARROW_BUTTON, getTimeUnitClassName(timeUnit));
        const onClick = () => (isDirectionUp ? this.incrementTime : this.decrementTime)(timeUnit);
        const label = `${isDirectionUp ? "Increase" : "Decrease"} ${getTimeUnitPrintStr(timeUnit)}`;
        // set tabIndex=-1 to ensure a valid FocusEvent relatedTarget when focused
        return (
        // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
        _jsx("span", { "aria-controls": this.timeInputIds[timeUnit], "aria-label": label, tabIndex: -1, className: classes, onClick: onClick, children: _jsx(Icon, { icon: isDirectionUp ? "chevron-up" : "chevron-down", title: label }) }));
    }
    renderDivider(text = ":") {
        return _jsx("span", { className: Classes.TIMEPICKER_DIVIDER_TEXT, children: text });
    }
    renderInput(className, unit, value) {
        const isValid = value != null ? isTimeUnitValid(unit, parseInt(value, 10)) : false;
        const isHour = unit === TimeUnit.HOUR_12 || unit === TimeUnit.HOUR_24;
        return (_jsx("input", { "aria-label": getTimeUnitPrintStr(unit), className: classNames(Classes.TIMEPICKER_INPUT, { [CoreClasses.intentClass(Intent.DANGER)]: !isValid }, className), id: this.timeInputIds[unit], min: 0, max: getTimeUnitMax(unit), onBlur: this.getInputBlurHandler(unit), onChange: this.getInputChangeHandler(unit), onFocus: this.getInputFocusHandler(unit), onKeyDown: this.getInputKeyDownHandler(unit), onKeyUp: this.getInputKeyUpHandler(unit), role: this.props.showArrowButtons ? "spinbutton" : undefined, type: "number", value: value, disabled: this.props.disabled, 
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus: isHour && this.props.autoFocus }));
    }
    maybeRenderAmPm() {
        if (!this.props.useAmPm) {
            return null;
        }
        return (_jsxs(HTMLSelect, { className: Classes.TIMEPICKER_AMPM_SELECT, disabled: this.props.disabled, onChange: this.handleAmPmChange, value: this.state.isPm ? "pm" : "am", children: [_jsx("option", { value: "am", children: "AM" }), _jsx("option", { value: "pm", children: "PM" })] }));
    }
    // begin method definitions: event handlers
    getInputChangeHandler = (unit) => (e) => {
        const text = getStringValueFromInputEvent(e);
        switch (unit) {
            case TimeUnit.HOUR_12:
            case TimeUnit.HOUR_24:
                this.setState({ hourText: text });
                break;
            case TimeUnit.MINUTE:
                this.setState({ minuteText: text });
                break;
            case TimeUnit.SECOND:
                this.setState({ secondText: text });
                break;
            case TimeUnit.MS:
                this.setState({ millisecondText: text });
                break;
        }
    };
    getInputBlurHandler = (unit) => (e) => {
        const text = getStringValueFromInputEvent(e);
        this.updateTime(parseInt(text, 10), unit);
        this.props.onBlur?.(e, unit);
    };
    getInputFocusHandler = (unit) => (e) => {
        if (this.props.selectAllOnFocus) {
            e.currentTarget.select();
        }
        this.props.onFocus?.(e, unit);
    };
    getInputKeyDownHandler = (unit) => (e) => {
        handleKeyEvent(e, {
            ArrowDown: () => this.decrementTime(unit),
            ArrowUp: () => this.incrementTime(unit),
            Enter: () => {
                e.currentTarget.blur();
            },
        });
        this.props.onKeyDown?.(e, unit);
    };
    getInputKeyUpHandler = (unit) => (e) => {
        this.props.onKeyUp?.(e, unit);
    };
    handleAmPmChange = (e) => {
        const isNextPm = e.currentTarget.value === "pm";
        if (isNextPm !== this.state.isPm) {
            const value = this.state.value ?? this.getInitialValue();
            const hour = DateUtils.convert24HourMeridiem(value.getHours(), isNextPm);
            this.setState({ isPm: isNextPm }, () => this.updateTime(hour, TimeUnit.HOUR_24));
        }
    };
    // begin method definitions: state modification
    /**
     * Generates a full TimePickerState object with all text fields set to formatted strings based on value
     */
    getFullStateFromValue(value, useAmPm = false) {
        value = value ?? this.getInitialValue();
        const timeInRange = DateUtils.getTimeInRange(value, this.props.minTime ?? getDefaultMinTime(), this.props.maxTime ?? getDefaultMaxTime());
        const hourUnit = useAmPm ? TimeUnit.HOUR_12 : TimeUnit.HOUR_24;
        /* eslint-disable sort-keys */
        return {
            hourText: formatTime(timeInRange.getHours(), hourUnit),
            minuteText: formatTime(timeInRange.getMinutes(), TimeUnit.MINUTE),
            secondText: formatTime(timeInRange.getSeconds(), TimeUnit.SECOND),
            millisecondText: formatTime(timeInRange.getMilliseconds(), TimeUnit.MS),
            value: timeInRange,
            isPm: DateUtils.getIsPmFrom24Hour(timeInRange.getHours()),
        };
        /* eslint-enable sort-keys */
    }
    incrementTime = (unit) => this.shiftTime(unit, 1);
    decrementTime = (unit) => this.shiftTime(unit, -1);
    shiftTime(unit, amount) {
        if (this.props.disabled) {
            return;
        }
        const newTime = getTimeUnit(unit, this.state.value ?? this.getInitialValue()) + amount;
        this.updateTime(wrapTimeAtUnit(unit, newTime), unit);
    }
    updateTime(time, unit) {
        const value = this.state.value ?? this.getInitialValue();
        const newValue = DateUtils.clone(value);
        if (isTimeUnitValid(unit, time)) {
            setTimeUnit(unit, time, newValue, this.state.isPm);
            if (DateUtils.isTimeInRange(newValue, this.props.minTime ?? getDefaultMinTime(), this.props.maxTime ?? getDefaultMaxTime())) {
                this.updateState({ value: newValue });
            }
            else {
                this.updateState(this.getFullStateFromValue(value, this.props.useAmPm));
            }
        }
        else {
            this.updateState(this.getFullStateFromValue(value, this.props.useAmPm));
        }
    }
    updateState(state) {
        let newState = state;
        const hasNewValue = newState.value != null && !DateUtils.isSameTime(newState.value, this.state.value ?? null);
        if (this.props.value == null) {
            // component is uncontrolled
            if (hasNewValue) {
                newState = this.getFullStateFromValue(newState.value, this.props.useAmPm);
            }
            this.setState(newState);
        }
        else {
            // component is controlled, and there's a new value
            // so set inputs' text based off of _old_ value and later fire onChange with new value
            if (hasNewValue) {
                this.setState(this.getFullStateFromValue(this.state.value, this.props.useAmPm));
            }
            else {
                // no new value, this means only text has changed (from user typing)
                // we want inputs to change, so update state with new text for the inputs
                // but don't change actual value
                this.setState({
                    ...newState,
                    value: this.state.value != null ? DateUtils.clone(this.state.value) : undefined,
                });
            }
        }
        if (hasNewValue && newState.value != null) {
            this.props.onChange?.(newState.value);
        }
    }
    getInitialValue() {
        const minTime = this.props.minTime ?? getDefaultMinTime();
        let value = minTime;
        if (this.props.value != null) {
            value = this.props.value;
        }
        else if (this.props.defaultValue != null) {
            value = this.props.defaultValue;
        }
        return value;
    }
}
function formatTime(time, unit) {
    switch (unit) {
        case TimeUnit.HOUR_24:
            return time.toString();
        case TimeUnit.HOUR_12:
            return DateUtils.get12HourFrom24Hour(time).toString();
        case TimeUnit.MINUTE:
        case TimeUnit.SECOND:
            return Utils.padWithZeroes(time.toString(), 2);
        case TimeUnit.MS:
            return Utils.padWithZeroes(time.toString(), 3);
        default:
            throw Error("Invalid TimeUnit");
    }
}
function getStringValueFromInputEvent(e) {
    return e.target.value;
}
function handleKeyEvent(e, actions, preventDefault = true) {
    for (const key of Object.keys(actions)) {
        if (e.key === key) {
            if (preventDefault) {
                e.preventDefault();
            }
            actions[key]();
        }
    }
}
//# sourceMappingURL=timePicker.js.map