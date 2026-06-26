import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
/*
 * Copyright 2020 Palantir Technologies, Inc. All rights reserved.
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
import { Children } from "react";
import { AbstractPureComponent, Classes, Utils } from "../../common";
import { DISPLAYNAME_PREFIX } from "../../common/props";
import { clickElementOnKeyPress } from "../../common/utils";
import { Dialog } from "./dialog";
import { DialogFooter } from "./dialogFooter";
import { DialogStep } from "./dialogStep";
import { DialogStepButton } from "./dialogStepButton";
const PADDING_BOTTOM = 0;
const MIN_WIDTH = 800;
/**
 * Multi-step dialog component.
 *
 * @see https://blueprintjs.com/docs/#core/components/dialog.multistep-dialog
 */
export class MultistepDialog extends AbstractPureComponent {
    static displayName = `${DISPLAYNAME_PREFIX}.MultistepDialog`;
    static defaultProps = {
        canOutsideClickClose: true,
        isOpen: false,
        navigationPosition: "left",
        resetOnClose: true,
        showCloseButtonInFooter: false,
    };
    state = this.getInitialIndexFromProps(this.props);
    render() {
        const { className, navigationPosition, showCloseButtonInFooter, isCloseButtonShown, ...otherProps } = this.props;
        return (_jsx(Dialog, { isCloseButtonShown: isCloseButtonShown, ...otherProps, className: classNames({
                [Classes.MULTISTEP_DIALOG_NAV_RIGHT]: navigationPosition === "right",
                [Classes.MULTISTEP_DIALOG_NAV_TOP]: navigationPosition === "top",
            }, className), style: this.getDialogStyle(), children: _jsxs("div", { className: Classes.MULTISTEP_DIALOG_PANELS, children: [this.renderLeftPanel(), this.maybeRenderRightPanel()] }) }));
    }
    componentDidUpdate(prevProps) {
        if ((prevProps.resetOnClose || prevProps.initialStepIndex !== this.props.initialStepIndex) &&
            !prevProps.isOpen &&
            this.props.isOpen) {
            this.setState(this.getInitialIndexFromProps(this.props));
        }
    }
    getDialogStyle() {
        return { minWidth: MIN_WIDTH, paddingBottom: PADDING_BOTTOM, ...this.props.style };
    }
    renderLeftPanel() {
        return (_jsx("div", { className: Classes.MULTISTEP_DIALOG_LEFT_PANEL, role: "tablist", "aria-label": "steps", children: this.getDialogStepChildren().filter(isDialogStepElement).map(this.renderDialogStep) }));
    }
    renderDialogStep = (step, index) => {
        const stepNumber = index + 1;
        const hasBeenViewed = this.state.lastViewedIndex >= index;
        const currentlySelected = this.state.selectedIndex === index;
        const handleClickDialogStep = index > this.state.lastViewedIndex ? undefined : this.getDialogStepChangeHandler(index);
        return (_jsx("div", { className: classNames(Classes.DIALOG_STEP_CONTAINER, {
                [Classes.ACTIVE]: currentlySelected,
                [Classes.DIALOG_STEP_VIEWED]: hasBeenViewed,
            }), "aria-disabled": !currentlySelected && !hasBeenViewed, "aria-selected": currentlySelected, role: "tab", children: _jsxs("div", { className: Classes.DIALOG_STEP, onClick: handleClickDialogStep, tabIndex: handleClickDialogStep ? 0 : -1, 
                // enable enter key to take effect on the div as if it were a button
                onKeyDown: clickElementOnKeyPress(["Enter", " "]), role: "button", children: [_jsx("div", { className: Classes.DIALOG_STEP_ICON, children: stepNumber }), _jsx("div", { className: Classes.DIALOG_STEP_TITLE, children: step.props.title })] }) }, index));
    };
    maybeRenderRightPanel() {
        const steps = this.getDialogStepChildren();
        if (steps.length <= this.state.selectedIndex) {
            return null;
        }
        const { className, panel, panelClassName } = steps[this.state.selectedIndex].props;
        return (_jsxs("div", { className: classNames(Classes.MULTISTEP_DIALOG_RIGHT_PANEL, className, panelClassName), children: [panel, this.renderFooter()] }));
    }
    renderFooter() {
        const { closeButtonProps, showCloseButtonInFooter, onClose } = this.props;
        const maybeCloseButton = !showCloseButtonInFooter ? undefined : (_jsx(DialogStepButton, { text: "Close", onClick: onClose, ...closeButtonProps }));
        return _jsx(DialogFooter, { actions: this.renderButtons(), children: maybeCloseButton });
    }
    renderButtons() {
        const { selectedIndex } = this.state;
        const steps = this.getDialogStepChildren();
        const buttons = [];
        if (this.state.selectedIndex > 0) {
            const backButtonProps = steps[selectedIndex].props.backButtonProps ?? this.props.backButtonProps;
            buttons.push(_jsx(DialogStepButton, { onClick: this.getDialogStepChangeHandler(selectedIndex - 1), text: "Back", ...backButtonProps }, "back"));
        }
        if (selectedIndex === this.getDialogStepChildren().length - 1) {
            buttons.push(_jsx(DialogStepButton, { intent: "primary", text: "Submit", ...this.props.finalButtonProps }, "final"));
        }
        else {
            const nextButtonProps = steps[selectedIndex].props.nextButtonProps ?? this.props.nextButtonProps;
            buttons.push(_jsx(DialogStepButton, { intent: "primary", onClick: this.getDialogStepChangeHandler(selectedIndex + 1), text: "Next", ...nextButtonProps }, "next"));
        }
        return buttons;
    }
    getDialogStepChangeHandler(index) {
        return (event) => {
            if (this.props.onChange !== undefined) {
                const steps = this.getDialogStepChildren();
                const prevStepId = steps[this.state.selectedIndex].props.id;
                const newStepId = steps[index].props.id;
                this.props.onChange(newStepId, prevStepId, event);
            }
            this.setState({
                lastViewedIndex: Math.max(this.state.lastViewedIndex, index),
                selectedIndex: index,
            });
        };
    }
    /** Filters children to only `<DialogStep>`s */
    getDialogStepChildren(props = this.props) {
        return Children.toArray(props.children).filter(isDialogStepElement);
    }
    getInitialIndexFromProps(props) {
        if (props.initialStepIndex !== undefined) {
            const boundedInitialIndex = Math.max(0, Math.min(props.initialStepIndex, this.getDialogStepChildren(props).length - 1));
            return {
                lastViewedIndex: boundedInitialIndex,
                selectedIndex: boundedInitialIndex,
            };
        }
        else {
            return {
                lastViewedIndex: 0,
                selectedIndex: 0,
            };
        }
    }
}
function isDialogStepElement(child) {
    return Utils.isElementOfType(child, DialogStep);
}
//# sourceMappingURL=multistepDialog.js.map