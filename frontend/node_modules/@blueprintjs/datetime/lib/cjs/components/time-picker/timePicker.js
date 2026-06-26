"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TimePicker = void 0;
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const core_1 = require("@blueprintjs/core");
const common_1 = require("../../common");
const timeUnit_1 = require("../../common/timeUnit");
const Utils = tslib_1.__importStar(require("../../common/utils"));
/**
 * Time picker component.
 *
 * @see https://blueprintjs.com/docs/#datetime/timepicker
 */
class TimePicker extends react_1.Component {
    static defaultProps = {
        autoFocus: false,
        disabled: false,
        maxTime: (0, timeUnit_1.getDefaultMaxTime)(),
        minTime: (0, timeUnit_1.getDefaultMinTime)(),
        precision: common_1.TimePrecision.MINUTE,
        selectAllOnFocus: false,
        showArrowButtons: false,
        useAmPm: false,
    };
    static displayName = `${core_1.DISPLAYNAME_PREFIX}.TimePicker`;
    constructor(props) {
        super(props);
        this.state = this.getFullStateFromValue(this.getInitialValue(), props.useAmPm);
    }
    timeInputIds = {
        [timeUnit_1.TimeUnit.HOUR_24]: core_1.Utils.uniqueId(timeUnit_1.TimeUnit.HOUR_24 + "-input"),
        [timeUnit_1.TimeUnit.HOUR_12]: core_1.Utils.uniqueId(timeUnit_1.TimeUnit.HOUR_12 + "-input"),
        [timeUnit_1.TimeUnit.MINUTE]: core_1.Utils.uniqueId(timeUnit_1.TimeUnit.MINUTE + "-input"),
        [timeUnit_1.TimeUnit.SECOND]: core_1.Utils.uniqueId(timeUnit_1.TimeUnit.SECOND + "-input"),
        [timeUnit_1.TimeUnit.MS]: core_1.Utils.uniqueId(timeUnit_1.TimeUnit.MS + "-input"),
    };
    render() {
        const shouldRenderMilliseconds = this.props.precision === common_1.TimePrecision.MILLISECOND;
        const shouldRenderSeconds = shouldRenderMilliseconds || this.props.precision === common_1.TimePrecision.SECOND;
        const hourUnit = this.props.useAmPm ? timeUnit_1.TimeUnit.HOUR_12 : timeUnit_1.TimeUnit.HOUR_24;
        const classes = (0, classnames_1.default)(common_1.Classes.TIMEPICKER, this.props.className, {
            [core_1.Classes.DISABLED]: this.props.disabled,
        });
        return ((0, jsx_runtime_1.jsxs)("div", { className: classes, children: [(0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.TIMEPICKER_ARROW_ROW, children: [this.maybeRenderArrowButton(true, hourUnit), this.maybeRenderArrowButton(true, timeUnit_1.TimeUnit.MINUTE), shouldRenderSeconds && this.maybeRenderArrowButton(true, timeUnit_1.TimeUnit.SECOND), shouldRenderMilliseconds && this.maybeRenderArrowButton(true, timeUnit_1.TimeUnit.MS)] }), (0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.TIMEPICKER_INPUT_ROW, children: [this.renderInput(common_1.Classes.TIMEPICKER_HOUR, hourUnit, this.state.hourText), this.renderDivider(), this.renderInput(common_1.Classes.TIMEPICKER_MINUTE, timeUnit_1.TimeUnit.MINUTE, this.state.minuteText), shouldRenderSeconds && this.renderDivider(), shouldRenderSeconds &&
                            this.renderInput(common_1.Classes.TIMEPICKER_SECOND, timeUnit_1.TimeUnit.SECOND, this.state.secondText), shouldRenderMilliseconds && this.renderDivider("."), shouldRenderMilliseconds &&
                            this.renderInput(common_1.Classes.TIMEPICKER_MILLISECOND, timeUnit_1.TimeUnit.MS, this.state.millisecondText)] }), this.maybeRenderAmPm(), (0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.TIMEPICKER_ARROW_ROW, children: [this.maybeRenderArrowButton(false, hourUnit), this.maybeRenderArrowButton(false, timeUnit_1.TimeUnit.MINUTE), shouldRenderSeconds && this.maybeRenderArrowButton(false, timeUnit_1.TimeUnit.SECOND), shouldRenderMilliseconds && this.maybeRenderArrowButton(false, timeUnit_1.TimeUnit.MS)] })] }));
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
            value = common_1.DateUtils.getTimeInRange(this.state.value ?? this.getInitialValue(), this.props.minTime ?? (0, timeUnit_1.getDefaultMinTime)(), this.props.maxTime ?? (0, timeUnit_1.getDefaultMaxTime)());
        }
        if (this.props.value != null && !common_1.DateUtils.isSameTime(this.props.value, prevProps.value ?? null)) {
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
        const classes = (0, classnames_1.default)(common_1.Classes.TIMEPICKER_ARROW_BUTTON, (0, timeUnit_1.getTimeUnitClassName)(timeUnit));
        const onClick = () => (isDirectionUp ? this.incrementTime : this.decrementTime)(timeUnit);
        const label = `${isDirectionUp ? "Increase" : "Decrease"} ${(0, timeUnit_1.getTimeUnitPrintStr)(timeUnit)}`;
        // set tabIndex=-1 to ensure a valid FocusEvent relatedTarget when focused
        return (
        // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
        (0, jsx_runtime_1.jsx)("span", { "aria-controls": this.timeInputIds[timeUnit], "aria-label": label, tabIndex: -1, className: classes, onClick: onClick, children: (0, jsx_runtime_1.jsx)(core_1.Icon, { icon: isDirectionUp ? "chevron-up" : "chevron-down", title: label }) }));
    }
    renderDivider(text = ":") {
        return (0, jsx_runtime_1.jsx)("span", { className: common_1.Classes.TIMEPICKER_DIVIDER_TEXT, children: text });
    }
    renderInput(className, unit, value) {
        const isValid = value != null ? (0, timeUnit_1.isTimeUnitValid)(unit, parseInt(value, 10)) : false;
        const isHour = unit === timeUnit_1.TimeUnit.HOUR_12 || unit === timeUnit_1.TimeUnit.HOUR_24;
        return ((0, jsx_runtime_1.jsx)("input", { "aria-label": (0, timeUnit_1.getTimeUnitPrintStr)(unit), className: (0, classnames_1.default)(common_1.Classes.TIMEPICKER_INPUT, { [core_1.Classes.intentClass(core_1.Intent.DANGER)]: !isValid }, className), id: this.timeInputIds[unit], min: 0, max: (0, timeUnit_1.getTimeUnitMax)(unit), onBlur: this.getInputBlurHandler(unit), onChange: this.getInputChangeHandler(unit), onFocus: this.getInputFocusHandler(unit), onKeyDown: this.getInputKeyDownHandler(unit), onKeyUp: this.getInputKeyUpHandler(unit), role: this.props.showArrowButtons ? "spinbutton" : undefined, type: "number", value: value, disabled: this.props.disabled, 
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus: isHour && this.props.autoFocus }));
    }
    maybeRenderAmPm() {
        if (!this.props.useAmPm) {
            return null;
        }
        return ((0, jsx_runtime_1.jsxs)(core_1.HTMLSelect, { className: common_1.Classes.TIMEPICKER_AMPM_SELECT, disabled: this.props.disabled, onChange: this.handleAmPmChange, value: this.state.isPm ? "pm" : "am", children: [(0, jsx_runtime_1.jsx)("option", { value: "am", children: "AM" }), (0, jsx_runtime_1.jsx)("option", { value: "pm", children: "PM" })] }));
    }
    // begin method definitions: event handlers
    getInputChangeHandler = (unit) => (e) => {
        const text = getStringValueFromInputEvent(e);
        switch (unit) {
            case timeUnit_1.TimeUnit.HOUR_12:
            case timeUnit_1.TimeUnit.HOUR_24:
                this.setState({ hourText: text });
                break;
            case timeUnit_1.TimeUnit.MINUTE:
                this.setState({ minuteText: text });
                break;
            case timeUnit_1.TimeUnit.SECOND:
                this.setState({ secondText: text });
                break;
            case timeUnit_1.TimeUnit.MS:
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
            const hour = common_1.DateUtils.convert24HourMeridiem(value.getHours(), isNextPm);
            this.setState({ isPm: isNextPm }, () => this.updateTime(hour, timeUnit_1.TimeUnit.HOUR_24));
        }
    };
    // begin method definitions: state modification
    /**
     * Generates a full TimePickerState object with all text fields set to formatted strings based on value
     */
    getFullStateFromValue(value, useAmPm = false) {
        value = value ?? this.getInitialValue();
        const timeInRange = common_1.DateUtils.getTimeInRange(value, this.props.minTime ?? (0, timeUnit_1.getDefaultMinTime)(), this.props.maxTime ?? (0, timeUnit_1.getDefaultMaxTime)());
        const hourUnit = useAmPm ? timeUnit_1.TimeUnit.HOUR_12 : timeUnit_1.TimeUnit.HOUR_24;
        /* eslint-disable sort-keys */
        return {
            hourText: formatTime(timeInRange.getHours(), hourUnit),
            minuteText: formatTime(timeInRange.getMinutes(), timeUnit_1.TimeUnit.MINUTE),
            secondText: formatTime(timeInRange.getSeconds(), timeUnit_1.TimeUnit.SECOND),
            millisecondText: formatTime(timeInRange.getMilliseconds(), timeUnit_1.TimeUnit.MS),
            value: timeInRange,
            isPm: common_1.DateUtils.getIsPmFrom24Hour(timeInRange.getHours()),
        };
        /* eslint-enable sort-keys */
    }
    incrementTime = (unit) => this.shiftTime(unit, 1);
    decrementTime = (unit) => this.shiftTime(unit, -1);
    shiftTime(unit, amount) {
        if (this.props.disabled) {
            return;
        }
        const newTime = (0, timeUnit_1.getTimeUnit)(unit, this.state.value ?? this.getInitialValue()) + amount;
        this.updateTime((0, timeUnit_1.wrapTimeAtUnit)(unit, newTime), unit);
    }
    updateTime(time, unit) {
        const value = this.state.value ?? this.getInitialValue();
        const newValue = common_1.DateUtils.clone(value);
        if ((0, timeUnit_1.isTimeUnitValid)(unit, time)) {
            (0, timeUnit_1.setTimeUnit)(unit, time, newValue, this.state.isPm);
            if (common_1.DateUtils.isTimeInRange(newValue, this.props.minTime ?? (0, timeUnit_1.getDefaultMinTime)(), this.props.maxTime ?? (0, timeUnit_1.getDefaultMaxTime)())) {
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
        const hasNewValue = newState.value != null && !common_1.DateUtils.isSameTime(newState.value, this.state.value ?? null);
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
                    value: this.state.value != null ? common_1.DateUtils.clone(this.state.value) : undefined,
                });
            }
        }
        if (hasNewValue && newState.value != null) {
            this.props.onChange?.(newState.value);
        }
    }
    getInitialValue() {
        const minTime = this.props.minTime ?? (0, timeUnit_1.getDefaultMinTime)();
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
exports.TimePicker = TimePicker;
function formatTime(time, unit) {
    switch (unit) {
        case timeUnit_1.TimeUnit.HOUR_24:
            return time.toString();
        case timeUnit_1.TimeUnit.HOUR_12:
            return common_1.DateUtils.get12HourFrom24Hour(time).toString();
        case timeUnit_1.TimeUnit.MINUTE:
        case timeUnit_1.TimeUnit.SECOND:
            return Utils.padWithZeroes(time.toString(), 2);
        case timeUnit_1.TimeUnit.MS:
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