import { type DateRange, type TimePrecision } from "../../common";
export interface DateShortcutBase {
    /** Shortcut label that appears in the list. */
    label: string;
    /**
     * Set this prop to `true` to allow this shortcut to change the selected
     * times as well as the dates. By default, time components of a shortcut are
     * ignored; clicking a shortcut takes the date components of the `dateRange`
     * and combines them with the currently selected time.
     *
     * @default false
     */
    includeTime?: boolean;
}
export interface DateRangeShortcut extends DateShortcutBase {
    /**
     * Date range represented by this shortcut. Note that time components of a
     * shortcut are ignored by default; set `includeTime: true` to respect them.
     */
    dateRange: DateRange;
}
export interface DatePickerShortcut extends DateShortcutBase {
    /**
     * Date represented by this shortcut. Note that time components of a
     * shortcut are ignored by default; set `includeTime: true` to respect them.
     */
    date: Date;
}
export interface DatePickerShortcutMenuProps {
    allowSingleDayRange?: boolean;
    minDate: Date;
    maxDate: Date;
    shortcuts: DateRangeShortcut[] | true;
    timePrecision: TimePrecision | undefined;
    selectedShortcutIndex?: number;
    onShortcutClick: (shortcut: DateRangeShortcut, index: number) => void;
    /**
     * The DatePicker component reuses this component for a single date.
     * This changes the default shortcut labels and affects which shortcuts are used.
     *
     * @default false
     */
    useSingleDateShortcuts?: boolean;
}
/**
 * Menu of {@link DateRangeShortcut} items, typically displayed in the UI to the left of a day picker calendar.
 *
 * This component may be used for single date pickers as well as range pickers by toggling the
 * `useSingleDateShortcuts` option.
 */
export declare const DatePickerShortcutMenu: React.FC<DatePickerShortcutMenuProps>;
