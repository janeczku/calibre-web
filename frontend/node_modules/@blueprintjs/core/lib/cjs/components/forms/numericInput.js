"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NumericInput = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2017 Palantir Technologies, Inc. All rights reserved.
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
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const Errors = tslib_1.__importStar(require("../../common/errors"));
const buttonGroup_1 = require("../button/buttonGroup");
const buttons_1 = require("../button/buttons");
const controlGroup_1 = require("./controlGroup");
const inputGroup_1 = require("./inputGroup");
const numericInputUtils_1 = require("./numericInputUtils");
var IncrementDirection;
(function (IncrementDirection) {
    IncrementDirection[IncrementDirection["DOWN"] = -1] = "DOWN";
    IncrementDirection[IncrementDirection["UP"] = 1] = "UP";
})(IncrementDirection || (IncrementDirection = {}));
const NON_HTML_PROPS = [
    "allowNumericCharactersOnly",
    "buttonPosition",
    "clampValueOnBlur",
    "className",
    "defaultValue",
    "majorStepSize",
    "minorStepSize",
    "onButtonClick",
    "onValueChange",
    "selectAllOnFocus",
    "selectAllOnIncrement",
    "stepSize",
];
/**
 * Numeric input component.
 *
 * @see https://blueprintjs.com/docs/#core/components/numeric-input
 */
class NumericInput extends common_1.AbstractPureComponent {
    static displayName = `${common_1.DISPLAYNAME_PREFIX}.NumericInput`;
    static VALUE_EMPTY = "";
    static VALUE_ZERO = "0";
    numericInputId = common_1.Utils.uniqueId("numericInput");
    static defaultProps = {
        allowNumericCharactersOnly: true,
        buttonPosition: common_1.Position.RIGHT,
        clampValueOnBlur: false,
        defaultValue: NumericInput.VALUE_EMPTY,
        large: false,
        majorStepSize: 10,
        minorStepSize: 0.1,
        selectAllOnFocus: false,
        selectAllOnIncrement: false,
        size: "medium",
        small: false,
        stepSize: 1,
    };
    static getDerivedStateFromProps(props, state) {
        const nextState = {
            prevMaxProp: props.max,
            prevMinProp: props.min,
        };
        const didMinChange = props.min !== state.prevMinProp;
        const didMaxChange = props.max !== state.prevMaxProp;
        const didBoundsChange = didMinChange || didMaxChange;
        // in controlled mode, use props.value
        // in uncontrolled mode, if state.value has not been assigned yet (upon initial mount), use props.defaultValue
        const value = props.value?.toString() ?? state.value;
        const stepMaxPrecision = NumericInput.getStepMaxPrecision(props);
        const sanitizedValue = value !== NumericInput.VALUE_EMPTY
            ? NumericInput.roundAndClampValue(value, stepMaxPrecision, props.min, props.max, 0, props.locale)
            : NumericInput.VALUE_EMPTY;
        // if a new min and max were provided that cause the existing value to fall
        // outside of the new bounds, then clamp the value to the new valid range.
        if (didBoundsChange && sanitizedValue !== state.value) {
            return { ...nextState, stepMaxPrecision, value: sanitizedValue };
        }
        return { ...nextState, stepMaxPrecision, value };
    }
    static CONTINUOUS_CHANGE_DELAY = 300;
    static CONTINUOUS_CHANGE_INTERVAL = 100;
    // Value Helpers
    // =============
    static getStepMaxPrecision(props) {
        if (props.minorStepSize != null) {
            return common_1.Utils.countDecimalPlaces(props.minorStepSize);
        }
        else {
            return common_1.Utils.countDecimalPlaces(props.stepSize);
        }
    }
    static roundAndClampValue(value, stepMaxPrecision, min, max, delta = 0, locale) {
        if (!(0, numericInputUtils_1.isValueNumeric)(value, locale)) {
            return NumericInput.VALUE_EMPTY;
        }
        const currentValue = (0, numericInputUtils_1.parseStringToStringNumber)(value, locale);
        const nextValue = (0, numericInputUtils_1.toMaxPrecision)(Number(currentValue) + delta, stepMaxPrecision);
        const clampedValue = (0, numericInputUtils_1.clampValue)(nextValue, min, max);
        return (0, numericInputUtils_1.toLocaleString)(clampedValue, locale);
    }
    state = {
        currentImeInputInvalid: false,
        shouldSelectAfterUpdate: false,
        stepMaxPrecision: NumericInput.getStepMaxPrecision(this.props),
        value: (0, numericInputUtils_1.getValueOrEmptyValue)(this.props.value ?? this.props.defaultValue),
    };
    // updating these flags need not trigger re-renders, so don't include them in this.state.
    didPasteEventJustOccur = false;
    delta = 0;
    inputElement = null;
    inputRef = (0, common_1.refHandler)(this, "inputElement", this.props.inputRef);
    intervalId;
    incrementButtonHandlers = this.getButtonEventHandlers(IncrementDirection.UP);
    decrementButtonHandlers = this.getButtonEventHandlers(IncrementDirection.DOWN);
    getCurrentValueAsNumber = () => Number((0, numericInputUtils_1.parseStringToStringNumber)(this.state.value, this.props.locale));
    render() {
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        const { buttonPosition, className, fill, large, size = "medium", small } = this.props;
        const containerClasses = (0, classnames_1.default)(common_1.Classes.NUMERIC_INPUT, common_1.Classes.sizeClass(size, { large, small }), className);
        const buttons = this.renderButtons();
        return ((0, jsx_runtime_1.jsxs)(controlGroup_1.ControlGroup, { className: containerClasses, fill: fill, children: [buttonPosition === common_1.Position.LEFT && buttons, this.renderInput(), buttonPosition === common_1.Position.RIGHT && buttons] }));
    }
    componentDidUpdate(prevProps, prevState) {
        super.componentDidUpdate(prevProps, prevState);
        if (prevProps.inputRef !== this.props.inputRef) {
            (0, common_1.setRef)(prevProps.inputRef, null);
            this.inputRef = (0, common_1.refHandler)(this, "inputElement", this.props.inputRef);
            (0, common_1.setRef)(this.props.inputRef, this.inputElement);
        }
        if (this.state.shouldSelectAfterUpdate) {
            this.inputElement?.setSelectionRange(0, this.state.value.length);
        }
        const didMinChange = this.props.min !== prevProps.min;
        const didMaxChange = this.props.max !== prevProps.max;
        const didBoundsChange = didMinChange || didMaxChange;
        const didLocaleChange = this.props.locale !== prevProps.locale;
        const didValueChange = this.state.value !== prevState.value;
        if ((didBoundsChange && didValueChange) || (didLocaleChange && prevState.value !== NumericInput.VALUE_EMPTY)) {
            // we clamped the value due to a bounds change, so we should fire the change callback
            const valueToParse = didLocaleChange ? prevState.value : this.state.value;
            const valueAsString = (0, numericInputUtils_1.parseStringToStringNumber)(valueToParse, prevProps.locale);
            const localizedValue = (0, numericInputUtils_1.toLocaleString)(+valueAsString, this.props.locale);
            this.props.onValueChange?.(+valueAsString, localizedValue, this.inputElement);
        }
    }
    validateProps(nextProps) {
        const { majorStepSize, max, min, minorStepSize, stepSize, value } = nextProps;
        if (min != null && max != null && min > max) {
            console.error(Errors.NUMERIC_INPUT_MIN_MAX);
        }
        if (stepSize <= 0) {
            console.error(Errors.NUMERIC_INPUT_STEP_SIZE_NON_POSITIVE);
        }
        if (minorStepSize && minorStepSize <= 0) {
            console.error(Errors.NUMERIC_INPUT_MINOR_STEP_SIZE_NON_POSITIVE);
        }
        if (majorStepSize && majorStepSize <= 0) {
            console.error(Errors.NUMERIC_INPUT_MAJOR_STEP_SIZE_NON_POSITIVE);
        }
        if (minorStepSize && minorStepSize > stepSize) {
            console.error(Errors.NUMERIC_INPUT_MINOR_STEP_SIZE_BOUND);
        }
        if (majorStepSize && majorStepSize < stepSize) {
            console.error(Errors.NUMERIC_INPUT_MAJOR_STEP_SIZE_BOUND);
        }
        // controlled mode
        if (value != null) {
            const stepMaxPrecision = NumericInput.getStepMaxPrecision(nextProps);
            const sanitizedValue = NumericInput.roundAndClampValue(value.toString(), stepMaxPrecision, min, max, 0, this.props.locale);
            const valueDoesNotMatch = sanitizedValue !== value.toString();
            const localizedValue = (0, numericInputUtils_1.toLocaleString)(Number((0, numericInputUtils_1.parseStringToStringNumber)(value, this.props.locale)), this.props.locale);
            const isNotLocalized = sanitizedValue !== localizedValue;
            if (valueDoesNotMatch && isNotLocalized) {
                console.warn(Errors.NUMERIC_INPUT_CONTROLLED_VALUE_INVALID);
            }
        }
    }
    // Render Helpers
    // ==============
    renderButtons() {
        const { intent, max, min, locale } = this.props;
        const value = (0, numericInputUtils_1.parseStringToStringNumber)(this.state.value, locale);
        const disabled = this.props.disabled || this.props.readOnly;
        const isIncrementDisabled = max !== undefined && value !== "" && +value >= max;
        const isDecrementDisabled = min !== undefined && value !== "" && +value <= min;
        return ((0, jsx_runtime_1.jsxs)(buttonGroup_1.ButtonGroup, { className: common_1.Classes.FIXED, vertical: true, children: [(0, jsx_runtime_1.jsx)(buttons_1.Button, { "aria-label": "increment", "aria-controls": this.numericInputId, disabled: disabled || isIncrementDisabled, icon: (0, jsx_runtime_1.jsx)(icons_1.ChevronUp, {}), intent: intent, ...this.incrementButtonHandlers }), (0, jsx_runtime_1.jsx)(buttons_1.Button, { "aria-label": "decrement", "aria-controls": this.numericInputId, disabled: disabled || isDecrementDisabled, icon: (0, jsx_runtime_1.jsx)(icons_1.ChevronDown, {}), intent: intent, ...this.decrementButtonHandlers })] }, "button-group"));
    }
    renderInput() {
        const inputGroupHtmlProps = (0, common_1.removeNonHTMLProps)(this.props, NON_HTML_PROPS, true);
        const valueAsNumber = this.getCurrentValueAsNumber();
        return ((0, jsx_runtime_1.jsx)(inputGroup_1.InputGroup, { asyncControl: this.props.asyncControl, autoComplete: "off", id: this.numericInputId, role: this.props.allowNumericCharactersOnly ? "spinbutton" : undefined, ...inputGroupHtmlProps, "aria-valuemax": this.props.max, "aria-valuemin": this.props.min, "aria-valuenow": valueAsNumber, intent: this.state.currentImeInputInvalid ? common_1.Intent.DANGER : this.props.intent, inputClassName: this.props.inputClassName, inputRef: this.inputRef, inputSize: this.props.inputSize, 
            // eslint-disable-next-line @typescript-eslint/no-deprecated
            large: this.props.large, leftElement: this.props.leftElement, leftIcon: this.props.leftIcon, onFocus: this.handleInputFocus, onBlur: this.handleInputBlur, onCompositionEnd: this.handleCompositionEnd, onCompositionUpdate: this.handleCompositionUpdate, onKeyDown: this.handleInputKeyDown, 
            // eslint-disable-next-line @typescript-eslint/no-deprecated
            onKeyPress: this.handleInputKeyPress, onPaste: this.handleInputPaste, onValueChange: this.handleInputChange, rightElement: this.props.rightElement, size: this.props.size, 
            // eslint-disable-next-line @typescript-eslint/no-deprecated
            small: this.props.small, value: this.state.value }));
    }
    // Callbacks - Buttons
    // ===================
    getButtonEventHandlers(direction) {
        return {
            // keydown is fired repeatedly when held so it's implicitly continuous
            onKeyDown: evt => {
                if (!this.props.disabled && common_1.Utils.isKeyboardClick(evt)) {
                    this.handleButtonClick(evt, direction);
                }
            },
            onMouseDown: evt => {
                if (!this.props.disabled) {
                    this.handleButtonClick(evt, direction);
                    this.startContinuousChange();
                }
            },
        };
    }
    handleButtonClick = (e, direction) => {
        const delta = this.updateDelta(direction, e);
        const nextValue = this.incrementValue(delta);
        this.props.onButtonClick?.(Number((0, numericInputUtils_1.parseStringToStringNumber)(nextValue, this.props.locale)), nextValue);
    };
    startContinuousChange() {
        // The button's onMouseUp event handler doesn't fire if the user
        // releases outside of the button, so we need to watch all the way
        // from the top.
        document.addEventListener("mouseup", this.stopContinuousChange);
        // Initial delay is slightly longer to prevent the user from
        // accidentally triggering the continuous increment/decrement.
        this.setTimeout(() => {
            this.intervalId = window.setInterval(this.handleContinuousChange, NumericInput.CONTINUOUS_CHANGE_INTERVAL);
        }, NumericInput.CONTINUOUS_CHANGE_DELAY);
    }
    stopContinuousChange = () => {
        this.delta = 0;
        this.clearTimeouts();
        clearInterval(this.intervalId);
        document.removeEventListener("mouseup", this.stopContinuousChange);
    };
    handleContinuousChange = () => {
        // If either min or max prop is set, when reaching the limit
        // the button will be disabled and stopContinuousChange will be never fired,
        // hence the need to check on each iteration to properly clear the timeout
        if (this.props.min !== undefined || this.props.max !== undefined) {
            const min = this.props.min ?? -Infinity;
            const max = this.props.max ?? Infinity;
            const valueAsNumber = this.getCurrentValueAsNumber();
            if (valueAsNumber <= min || valueAsNumber >= max) {
                this.stopContinuousChange();
                return;
            }
        }
        const nextValue = this.incrementValue(this.delta);
        this.props.onButtonClick?.(Number((0, numericInputUtils_1.parseStringToStringNumber)(nextValue, this.props.locale)), nextValue);
    };
    // Callbacks - Input
    // =================
    handleInputFocus = (e) => {
        // update this state flag to trigger update for input selection (see componentDidUpdate)
        this.setState({ shouldSelectAfterUpdate: this.props.selectAllOnFocus });
        this.props.onFocus?.(e);
    };
    handleInputBlur = (e) => {
        // always disable this flag on blur so it's ready for next time.
        this.setState({ shouldSelectAfterUpdate: false });
        if (this.props.clampValueOnBlur) {
            const { value } = e.target;
            this.handleNextValue(this.roundAndClampValue(value));
        }
        this.props.onBlur?.(e);
    };
    handleInputKeyDown = (e) => {
        if (this.props.disabled || this.props.readOnly) {
            return;
        }
        const direction = common_1.Utils.getArrowKeyDirection(e, ["ArrowDown"], ["ArrowUp"]);
        if (direction !== undefined) {
            // when the input field has focus, some key combinations will modify
            // the field's selection range. we'll actually want to select all
            // text in the field after we modify the value on the following
            // lines. preventing the default selection behavior lets us do that
            // without interference.
            e.preventDefault();
            const delta = this.updateDelta(direction, e);
            this.incrementValue(delta);
        }
        this.props.onKeyDown?.(e);
    };
    handleCompositionEnd = (e) => {
        if (this.props.allowNumericCharactersOnly) {
            this.handleNextValue((0, numericInputUtils_1.sanitizeNumericInput)(e.data, this.props.locale));
            this.setState({ currentImeInputInvalid: false });
        }
    };
    handleCompositionUpdate = (e) => {
        if (this.props.allowNumericCharactersOnly) {
            const { data } = e;
            const sanitizedValue = (0, numericInputUtils_1.sanitizeNumericInput)(data, this.props.locale);
            if (sanitizedValue.length === 0 && data.length > 0) {
                this.setState({ currentImeInputInvalid: true });
            }
            else {
                this.setState({ currentImeInputInvalid: false });
            }
        }
    };
    handleInputKeyPress = (e) => {
        // we prohibit keystrokes in onKeyPress instead of onKeyDown, because
        // e.key is not trustworthy in onKeyDown in all browsers.
        if (this.props.allowNumericCharactersOnly && !(0, numericInputUtils_1.isValidNumericKeyboardEvent)(e, this.props.locale)) {
            e.preventDefault();
        }
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        this.props.onKeyPress?.(e);
    };
    handleInputPaste = (e) => {
        this.didPasteEventJustOccur = true;
        this.props.onPaste?.(e);
    };
    handleInputChange = (value) => {
        let nextValue = value;
        if (this.props.allowNumericCharactersOnly && this.didPasteEventJustOccur) {
            this.didPasteEventJustOccur = false;
            nextValue = (0, numericInputUtils_1.sanitizeNumericInput)(value, this.props.locale);
        }
        this.handleNextValue(nextValue);
        this.setState({ shouldSelectAfterUpdate: false });
    };
    // Data logic
    // ==========
    handleNextValue(valueAsString) {
        if (this.props.value == null) {
            this.setState({ value: valueAsString });
        }
        this.props.onValueChange?.(Number((0, numericInputUtils_1.parseStringToStringNumber)(valueAsString, this.props.locale)), valueAsString, this.inputElement);
    }
    incrementValue(delta) {
        // pretend we're incrementing from 0 if currValue is empty
        const currValue = this.state.value === NumericInput.VALUE_EMPTY ? NumericInput.VALUE_ZERO : this.state.value;
        const nextValue = this.roundAndClampValue(currValue, delta);
        if (nextValue !== this.state.value) {
            this.handleNextValue(nextValue);
            this.setState({ shouldSelectAfterUpdate: this.props.selectAllOnIncrement });
        }
        // return value used in continuous change updates
        return nextValue;
    }
    getIncrementDelta(direction, isShiftKeyPressed, isAltKeyPressed) {
        const { majorStepSize, minorStepSize, stepSize } = this.props;
        if (isShiftKeyPressed && majorStepSize != null) {
            return direction * majorStepSize;
        }
        else if (isAltKeyPressed && minorStepSize != null) {
            return direction * minorStepSize;
        }
        else {
            return direction * stepSize;
        }
    }
    roundAndClampValue(value, delta = 0) {
        return NumericInput.roundAndClampValue(value, this.state.stepMaxPrecision, this.props.min, this.props.max, delta, this.props.locale);
    }
    updateDelta(direction, e) {
        this.delta = this.getIncrementDelta(direction, e.shiftKey, e.altKey);
        return this.delta;
    }
}
exports.NumericInput = NumericInput;
//# sourceMappingURL=numericInput.js.map