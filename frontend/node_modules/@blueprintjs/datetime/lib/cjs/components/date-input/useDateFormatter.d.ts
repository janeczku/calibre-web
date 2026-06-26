import type { Locale } from "date-fns";
import type { DateInputProps } from "./dateInputProps";
/**
 * Create a date string parser function based on a given locale.
 *
 * Prefer using user-provided `props.formatDate` and `props.dateFnsFormat` if available, otherwise fall back to
 * default formats inferred from time picker props.
 */
export declare function useDateFormatter(props: DateInputProps, locale: Locale | undefined): (date: Date | undefined) => string;
