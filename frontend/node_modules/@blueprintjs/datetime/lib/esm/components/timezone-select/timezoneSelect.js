import { jsx as _jsx } from "react/jsx-runtime";
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
import classNames from "classnames";
import { AbstractPureComponent, Button, Classes as CoreClasses, DISPLAYNAME_PREFIX, MenuItem, } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";
import { Classes } from "../../common";
import { formatTimezone, TimezoneDisplayFormat } from "../../common/timezoneDisplayFormat";
import { TIMEZONE_ITEMS } from "../../common/timezoneItems";
import { getInitialTimezoneItems, mapTimezonesWithNames } from "../../common/timezoneNameUtils";
/**
 * Timezone select component.
 *
 * @see https://blueprintjs.com/docs/#datetime/timezone-select
 */
export class TimezoneSelect extends AbstractPureComponent {
    static displayName = `${DISPLAYNAME_PREFIX}.TimezoneSelect`;
    static defaultProps = {
        date: new Date(),
        disabled: false,
        fill: false,
        inputProps: {},
        placeholder: "Select timezone...",
        popoverProps: {},
        showLocalTimezone: false,
    };
    timezoneItems;
    initialTimezoneItems;
    constructor(props) {
        super(props);
        const { showLocalTimezone, inputProps = {}, date } = props;
        this.state = { query: inputProps.value || "" };
        this.timezoneItems = mapTimezonesWithNames(date, TIMEZONE_ITEMS);
        this.initialTimezoneItems = getInitialTimezoneItems(date, showLocalTimezone);
    }
    render() {
        const { children, className, disabled, fill, inputProps, popoverProps } = this.props;
        const { query } = this.state;
        return (_jsx(Select, { className: classNames(Classes.TIMEZONE_SELECT, className), disabled: disabled, fill: fill, inputProps: {
                placeholder: "Search for timezones...",
                ...inputProps,
            }, itemListPredicate: this.filterItems, itemRenderer: this.renderItem, items: query ? this.timezoneItems : this.initialTimezoneItems, noResults: _jsx(MenuItem, { disabled: true, roleStructure: "listoption", text: "No matching timezones." }), onItemSelect: this.handleItemSelect, onQueryChange: this.handleQueryChange, popoverProps: {
                ...popoverProps,
                popoverClassName: classNames(Classes.TIMEZONE_SELECT_POPOVER, popoverProps?.popoverClassName),
            }, popoverTargetProps: { "aria-label": "timezone" }, resetOnClose: true, resetOnSelect: true, children: children ?? this.renderButton() }));
    }
    componentDidUpdate(prevProps, prevState) {
        super.componentDidUpdate(prevProps, prevState);
        const { date: nextDate } = this.props;
        if (this.props.showLocalTimezone !== prevProps.showLocalTimezone) {
            this.initialTimezoneItems = getInitialTimezoneItems(nextDate, this.props.showLocalTimezone);
        }
        if (nextDate != null && nextDate.getTime() !== prevProps.date?.getTime()) {
            this.initialTimezoneItems = mapTimezonesWithNames(nextDate, this.initialTimezoneItems);
            this.timezoneItems = mapTimezonesWithNames(nextDate, this.timezoneItems);
        }
    }
    renderButton() {
        const { buttonProps = {}, disabled, fill, placeholder, value, valueDisplayFormat } = this.props;
        const selectedTimezone = this.timezoneItems.find(tz => tz.ianaCode === value);
        const buttonContent = selectedTimezone !== undefined ? (formatTimezone(selectedTimezone, valueDisplayFormat ?? TimezoneDisplayFormat.COMPOSITE)) : (_jsx("span", { className: CoreClasses.TEXT_MUTED, children: placeholder }));
        return _jsx(Button, { endIcon: "caret-down", disabled: disabled, text: buttonContent, fill: fill, ...buttonProps });
    }
    filterItems = (query, items) => {
        // using list predicate so only one RegExp instance is needed
        // escape bad regex characters, let spaces act as any separator
        const expr = new RegExp(query.replace(/([[()+*?])/g, "\\$1").replace(" ", "[ _/\\(\\)]+"), "i");
        return items.filter(item => expr.test(item.ianaCode) ||
            expr.test(item.label) ||
            expr.test(item.longName) ||
            expr.test(item.shortName));
    };
    renderItem = (item, { handleClick, modifiers }) => {
        if (!modifiers.matchesPredicate) {
            return null;
        }
        return (_jsx(MenuItem, { selected: modifiers.active, text: `${item.label}, ${item.longName}`, onClick: handleClick, label: item.shortName }, item.ianaCode));
    };
    handleItemSelect = (timezone) => this.props.onChange?.(timezone.ianaCode);
    handleQueryChange = (query) => this.setState({ query });
}
//# sourceMappingURL=timezoneSelect.js.map