import type { DatePickerBaseProps } from "../../common";
import type { DatePickerState } from "./datePickerState";
export type DatePickerContextState = Pick<DatePickerBaseProps, "reverseMonthAndYearMenus"> & Pick<DatePickerState, "locale">;
/**
 * Context used to pass DatePicker & DateRangePicker props and state down to custom react-day-picker components
 * like DatePickerCaption.
 */
export declare const DatePickerContext: import("react").Context<DatePickerContextState>;
export declare const DatePickerProvider: (props: React.PropsWithChildren<DatePickerContextState>) => import("react/jsx-runtime").JSX.Element;
