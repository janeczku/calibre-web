"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.EntityTitle = void 0;
const tslib_1 = require("tslib");
const jsx_runtime_1 = require("react/jsx-runtime");
/*
 * Copyright 2024 Palantir Technologies, Inc. All rights reserved.
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
const classnames_1 = tslib_1.__importDefault(require("classnames"));
const react_1 = require("react");
const icons_1 = require("@blueprintjs/icons");
const common_1 = require("../../common");
const html_1 = require("../html/html");
const icon_1 = require("../icon/icon");
const text_1 = require("../text/text");
/**
 * EntityTitle component.
 *
 * @see https://blueprintjs.com/docs/#core/components/entity-title
 */
exports.EntityTitle = (0, react_1.forwardRef)((props, ref) => {
    const { className, ellipsize = false, fill = false, heading = text_1.Text, icon, loading = false, subtitle, tags, title, titleURL, } = props;
    const titleElement = (0, react_1.useMemo)(() => {
        const maybeTitleWithURL = titleURL != null ? ((0, jsx_runtime_1.jsx)("a", { target: "_blank", href: titleURL, rel: "noreferrer", children: title })) : (title);
        return (0, react_1.createElement)(heading, {
            className: (0, classnames_1.default)(common_1.Classes.ENTITY_TITLE_TITLE, {
                [common_1.Classes.SKELETON]: loading,
                [common_1.Classes.TEXT_OVERFLOW_ELLIPSIS]: heading !== text_1.Text && ellipsize,
            }),
            ellipsize: heading === text_1.Text ? ellipsize : undefined,
        }, maybeTitleWithURL);
    }, [titleURL, title, heading, loading, ellipsize]);
    const maybeSubtitle = (0, react_1.useMemo)(() => {
        if (subtitle == null) {
            return null;
        }
        return ((0, jsx_runtime_1.jsx)(text_1.Text, { className: (0, classnames_1.default)(common_1.Classes.TEXT_MUTED, common_1.Classes.ENTITY_TITLE_SUBTITLE, {
                [common_1.Classes.SKELETON]: loading,
            }), ellipsize: ellipsize, children: subtitle }));
    }, [ellipsize, loading, subtitle]);
    return ((0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(className, common_1.Classes.ENTITY_TITLE, getClassNameFromHeading(heading), {
            [common_1.Classes.ENTITY_TITLE_ELLIPSIZE]: ellipsize,
            [common_1.Classes.FILL]: fill,
        }), ref: ref, children: [icon != null && ((0, jsx_runtime_1.jsx)("div", { className: (0, classnames_1.default)(common_1.Classes.ENTITY_TITLE_ICON_CONTAINER, {
                    [common_1.Classes.ENTITY_TITLE_HAS_SUBTITLE]: maybeSubtitle != null,
                }), children: (0, jsx_runtime_1.jsx)(icon_1.Icon, { "aria-hidden": true, className: (0, classnames_1.default)(common_1.Classes.TEXT_MUTED, { [common_1.Classes.SKELETON]: loading }), icon: loading ? icons_1.IconNames.SQUARE : icon, tabIndex: -1 }) })), (0, jsx_runtime_1.jsxs)("div", { className: common_1.Classes.ENTITY_TITLE_TEXT, children: [(0, jsx_runtime_1.jsxs)("div", { className: (0, classnames_1.default)(common_1.Classes.ENTITY_TITLE_TITLE_AND_TAGS, {
                            [common_1.Classes.SKELETON]: loading,
                        }), children: [titleElement, tags != null && (0, jsx_runtime_1.jsx)("div", { className: common_1.Classes.ENTITY_TITLE_TAGS_CONTAINER, children: tags })] }), maybeSubtitle] })] }));
});
exports.EntityTitle.displayName = `${common_1.DISPLAYNAME_PREFIX}.EntityTitle`;
/**
 * Construct header class name from H{*}. Returns `undefined` if `heading` is not a Blueprint heading.
 */
function getClassNameFromHeading(heading) {
    const headerIndex = [html_1.H1, html_1.H2, html_1.H3, html_1.H4, html_1.H5, html_1.H6].findIndex(header => header === heading);
    if (headerIndex < 0) {
        return undefined;
    }
    return [common_1.Classes.getClassNamespace(), "entity-title-heading", `h${headerIndex + 1}`].join("-");
}
//# sourceMappingURL=entityTitle.js.map