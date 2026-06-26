"use strict";
/*
 * Copyright 2023 Palantir Technologies, Inc. All rights reserved.
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
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.loadDateFnsLocale = loadDateFnsLocale;
exports.useDateFnsLocale = useDateFnsLocale;
const react_1 = require("react");
const core_1 = require("@blueprintjs/core");
/**
 * Lazy-loads a date-fns locale for use in a datetime class component.
 */
async function loadDateFnsLocale(localeCode) {
    try {
        const localeModule = await Promise.resolve(`${
        /* @vite-ignore */
        /* webpackChunkName: "date-fns-locale-[request]" */
        `date-fns/locale/${localeCode}/index.js`}`).then(s => __importStar(require(s)));
        return localeModule.default;
    }
    catch {
        if (!core_1.Utils.isNodeEnv("production")) {
            console.error(`[Blueprint] Could not load "${localeCode}" date-fns locale, please check that this locale code is supported: https://github.com/date-fns/date-fns/tree/main/src/locale`);
        }
        return undefined;
    }
}
/**
 * Lazy-loads a date-fns locale for use in a datetime function component.
 */
function useDateFnsLocale(localeOrCode, dateFnsLocaleLoader = loadDateFnsLocale) {
    // make sure to set the locale correctly on first render if it is available
    const [locale, setLocale] = (0, react_1.useState)(typeof localeOrCode === "object" ? localeOrCode : undefined);
    (0, react_1.useEffect)(() => {
        setLocale(prevLocale => {
            if (typeof localeOrCode === "string") {
                dateFnsLocaleLoader(localeOrCode).then(setLocale);
                // keep the current locale for now, it will be updated async
                return prevLocale;
            }
            else {
                return localeOrCode;
            }
        });
    }, [dateFnsLocaleLoader, localeOrCode]);
    return locale;
}
//# sourceMappingURL=dateFnsLocaleUtils.js.map