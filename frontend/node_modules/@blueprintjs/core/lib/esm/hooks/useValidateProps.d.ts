import { type DependencyList } from "react";
/**
 * Custom hook for validating component props during development.
 * This hook runs validation checks only in non-production environments,
 * following the same pattern as AbstractComponent.
 *
 * @param validator - Function that performs the validation checks
 * @param dependencies - Optional array of dependencies that trigger validation when changed
 *
 * @example
 * useValidateProps(() => {
 *     if (value < 0) console.warn("Value must be positive");
 * }, [value]);
 */
export declare function useValidateProps(validator: () => void, dependencies?: DependencyList): void;
