import { TimePrecision } from "./common";
import type { DateInputProps } from "./components/date-input/dateInputProps";
type DateInputLegacyValue = Date | null | undefined;
type DateInputLegacyDefaultValue = Date | undefined;
type DateInputLegacyChangeHandler = (selectedDate: Date | null, isUserChange: boolean) => void;
/**
 * `onChange` prop adapter for automated DateInput -> DateInput2 migration in @blueprintjs/datetime2 v0.x.
 *
 * Note that we exclude `undefined` from the input & output types since we expect the callback to be defined
 * if this adapter is used.
 *
 * @param handler DateInput onChange handler
 * @returns DateInput2 onChange handler
 */
export declare function onChangeAdapter(handler: DateInputLegacyChangeHandler): NonNullable<DateInputProps["onChange"]>;
/**
 * `value` prop adapter for automated DateInput -> DateInput2 migration in @blueprintjs/datetime2 v0.x.
 *
 * @param value DateInput value
 * @param timePrecision (optional) DateInput timePrecision
 * @returns DateInput2 value
 */
export declare function valueAdapter(value: DateInputLegacyValue, timePrecision?: TimePrecision): DateInputProps["value"];
/**
 * Adapter for automated DateInput -> DateInput2 migration in @blueprintjs/datetime2 v0.x.
 *
 * @param defaultValue DateInput value
 * @param timePrecision (optional) DateInput timePrecision
 * @returns DateInput2 value
 */
export declare function defaultValueAdapter(defaultValue: DateInputLegacyDefaultValue, timePrecision?: TimePrecision): DateInputProps["defaultValue"];
export {};
