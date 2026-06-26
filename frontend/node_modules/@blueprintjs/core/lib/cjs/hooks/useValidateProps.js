"use strict";
/* !
 * (c) Copyright 2025 Palantir Technologies Inc. All rights reserved.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.useValidateProps = useValidateProps;
const react_1 = require("react");
const utils_1 = require("../common/utils");
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
function useValidateProps(validator, dependencies = []) {
    (0, react_1.useEffect)(() => {
        if (!(0, utils_1.isNodeEnv)("production")) {
            validator();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, dependencies);
}
//# sourceMappingURL=useValidateProps.js.map