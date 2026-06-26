import { AbstractPureComponent, type ButtonProps, type InputGroupProps, type Props } from "@blueprintjs/core";
import { type SelectPopoverProps } from "@blueprintjs/select";
import { TimezoneDisplayFormat } from "../../common/timezoneDisplayFormat";
export interface TimezoneSelectProps extends Props {
    /**
     * Element which triggers the timezone select popover. If this is undefined,
     * by default the component will render a `<Button>` which shows the currently
     * selected timezone.
     */
    children?: React.ReactNode;
    /**
     * The currently selected timezone UTC identifier, e.g. "Pacific/Honolulu".
     *
     * @see https://www.iana.org/time-zones
     */
    value: string | undefined;
    /**
     * Callback invoked when the user selects a timezone.
     *
     * @param timezone the new timezone's IANA code
     */
    onChange: (timezone: string) => void;
    /**
     * The date to use when formatting timezone offsets.
     * An offset date is necessary to account for DST, but typically the default value of `now` will be sufficient.
     *
     * @default now
     */
    date?: Date;
    /**
     * Whether the component should take up the full width of its container.
     * This overrides `popoverProps.fill` and `buttonProps.fill`.
     *
     * @default false
     */
    fill?: boolean;
    /**
     * Whether this component is non-interactive.
     * This prop will be ignored if `children` is provided.
     *
     * @default false
     */
    disabled?: boolean;
    /**
     * Whether to show the local timezone at the top of the list of initial timezone suggestions.
     *
     * @default false
     */
    showLocalTimezone?: boolean;
    /**
     * Text to show when no timezone has been selected (`value === undefined`).
     * This prop will be ignored if `children` is provided.
     *
     * @default "Select timezone..."
     */
    placeholder?: string;
    /**
     * Props to spread to the target `Button`.
     * This prop will be ignored if `children` is provided.
     */
    buttonProps?: Partial<ButtonProps>;
    /**
     * Props to spread to the filter `InputGroup`.
     * All props are supported except `ref` (use `inputRef` instead).
     * If you want to control the filter input, you can pass `value` and `onChange` here
     * to override `Select`'s own behavior.
     */
    inputProps?: InputGroupProps;
    /** Props to spread to the popover. Note that `content` cannot be changed. */
    popoverProps?: SelectPopoverProps["popoverProps"];
    /**
     * Format to use when displaying the selected (or default) timezone within the target element.
     * This prop will be ignored if `children` is provided.
     *
     * @default TimezoneDisplayFormat.COMPOSITE
     */
    valueDisplayFormat?: TimezoneDisplayFormat;
}
export interface TimezoneSelectState {
    query: string;
}
/**
 * Timezone select component.
 *
 * @see https://blueprintjs.com/docs/#datetime/timezone-select
 */
export declare class TimezoneSelect extends AbstractPureComponent<TimezoneSelectProps, TimezoneSelectState> {
    static displayName: string;
    static defaultProps: Partial<TimezoneSelectProps>;
    private timezoneItems;
    private initialTimezoneItems;
    constructor(props: TimezoneSelectProps);
    render(): import("react/jsx-runtime").JSX.Element;
    componentDidUpdate(prevProps: TimezoneSelectProps, prevState: TimezoneSelectState): void;
    private renderButton;
    private filterItems;
    private renderItem;
    private handleItemSelect;
    private handleQueryChange;
}
