/*
 * Copyright 2019 Palantir Technologies, Inc. All rights reserved.
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
import { Component } from "react";
import { isNodeEnv } from "./utils";
/**
 * An abstract component that Blueprint components can extend
 * in order to add some common functionality like runtime props validation.
 */
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export class AbstractComponent extends Component {
    // unsafe lifecycle methods
    componentWillUpdate;
    componentWillReceiveProps;
    componentWillMount;
    // this should be static, not an instance method
    getDerivedStateFromProps;
    /** Component displayName should be `public static`. This property exists to prevent incorrect usage. */
    displayName;
    // Not bothering to remove entries when their timeouts finish because clearing invalid ID is a no-op
    timeoutIds = [];
    requestIds = [];
    constructor(props) {
        super(props);
        if (!isNodeEnv("production")) {
            this.validateProps(this.props);
        }
    }
    componentDidUpdate(_prevProps, _prevState, _snapshot) {
        if (!isNodeEnv("production")) {
            this.validateProps(this.props);
        }
    }
    componentWillUnmount() {
        this.clearTimeouts();
        this.cancelAnimationFrames();
    }
    /**
     * Request an animation frame and remember its ID.
     * All pending requests will be canceled when component unmounts.
     *
     * @returns a "cancel" function that will cancel the request when invoked.
     */
    requestAnimationFrame(callback) {
        const handle = window.requestAnimationFrame(callback);
        this.requestIds.push(handle);
        return () => window.cancelAnimationFrame(handle);
    }
    /**
     * Set a timeout and remember its ID.
     * All stored timeouts will be cleared when component unmounts.
     *
     * @returns a "cancel" function that will clear timeout when invoked.
     */
    setTimeout(callback, timeout) {
        const handle = window.setTimeout(callback, timeout);
        this.timeoutIds.push(handle);
        return () => window.clearTimeout(handle);
    }
    /**
     * Clear all known timeouts.
     */
    clearTimeouts = () => {
        if (this.timeoutIds.length > 0) {
            for (const timeoutId of this.timeoutIds) {
                window.clearTimeout(timeoutId);
            }
            this.timeoutIds = [];
        }
    };
    /**
     * Clear all known animation frame requests.
     */
    cancelAnimationFrames = () => {
        if (this.requestIds.length > 0) {
            for (const requestId of this.requestIds) {
                window.cancelAnimationFrame(requestId);
            }
            this.requestIds = [];
        }
    };
    /**
     * Ensures that the props specified for a component are valid.
     * Implementations should check that props are valid and usually throw an Error if they are not.
     * Implementations should not duplicate checks that the type system already guarantees.
     *
     * This method should be used instead of React's
     * [propTypes](https://facebook.github.io/react/docs/reusable-components.html#prop-validation) feature.
     * Like propTypes, these runtime checks run only in development mode.
     */
    validateProps(_props) {
        // implement in subclass
    }
}
//# sourceMappingURL=abstractComponent.js.map