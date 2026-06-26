import type { Locale } from "date-fns";
import type { DateInputProps } from "./dateInputProps";
/**
 * Create a date string parser function based on a given locale.
 *
 * Prefer using user-provided `props.parseDate` and `props.dateFnsFormat` if available, otherwise fall back to
 * default formats inferred from time picker props.
 */
export declare function useDateParser(props: DateInputProps, locale: Locale | undefined): (dateString: string) => Date | null;
