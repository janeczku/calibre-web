import { type CaptionProps } from "react-day-picker";
/**
 * Custom react-day-picker caption component used in non-contiguous two-month date range pickers.
 *
 * We need to override the whole caption instead of its lower-level components because react-day-picker
 * does not have built-in support for non-contiguous range pickers.
 *
 * @see https://daypicker.dev/guides/custom-components
 */
export declare const DatePickerCaption: {
    (props: CaptionProps): import("react/jsx-runtime").JSX.Element;
    displayName: string;
};
