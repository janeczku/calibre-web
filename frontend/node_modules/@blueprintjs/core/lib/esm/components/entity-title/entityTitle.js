import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import classNames from "classnames";
import { createElement, forwardRef, useMemo } from "react";
import { IconNames } from "@blueprintjs/icons";
import { Classes, DISPLAYNAME_PREFIX } from "../../common";
import { H1, H2, H3, H4, H5, H6 } from "../html/html";
import { Icon } from "../icon/icon";
import { Text } from "../text/text";
/**
 * EntityTitle component.
 *
 * @see https://blueprintjs.com/docs/#core/components/entity-title
 */
export const EntityTitle = forwardRef((props, ref) => {
    const { className, ellipsize = false, fill = false, heading = Text, icon, loading = false, subtitle, tags, title, titleURL, } = props;
    const titleElement = useMemo(() => {
        const maybeTitleWithURL = titleURL != null ? (_jsx("a", { target: "_blank", href: titleURL, rel: "noreferrer", children: title })) : (title);
        return createElement(heading, {
            className: classNames(Classes.ENTITY_TITLE_TITLE, {
                [Classes.SKELETON]: loading,
                [Classes.TEXT_OVERFLOW_ELLIPSIS]: heading !== Text && ellipsize,
            }),
            ellipsize: heading === Text ? ellipsize : undefined,
        }, maybeTitleWithURL);
    }, [titleURL, title, heading, loading, ellipsize]);
    const maybeSubtitle = useMemo(() => {
        if (subtitle == null) {
            return null;
        }
        return (_jsx(Text, { className: classNames(Classes.TEXT_MUTED, Classes.ENTITY_TITLE_SUBTITLE, {
                [Classes.SKELETON]: loading,
            }), ellipsize: ellipsize, children: subtitle }));
    }, [ellipsize, loading, subtitle]);
    return (_jsxs("div", { className: classNames(className, Classes.ENTITY_TITLE, getClassNameFromHeading(heading), {
            [Classes.ENTITY_TITLE_ELLIPSIZE]: ellipsize,
            [Classes.FILL]: fill,
        }), ref: ref, children: [icon != null && (_jsx("div", { className: classNames(Classes.ENTITY_TITLE_ICON_CONTAINER, {
                    [Classes.ENTITY_TITLE_HAS_SUBTITLE]: maybeSubtitle != null,
                }), children: _jsx(Icon, { "aria-hidden": true, className: classNames(Classes.TEXT_MUTED, { [Classes.SKELETON]: loading }), icon: loading ? IconNames.SQUARE : icon, tabIndex: -1 }) })), _jsxs("div", { className: Classes.ENTITY_TITLE_TEXT, children: [_jsxs("div", { className: classNames(Classes.ENTITY_TITLE_TITLE_AND_TAGS, {
                            [Classes.SKELETON]: loading,
                        }), children: [titleElement, tags != null && _jsx("div", { className: Classes.ENTITY_TITLE_TAGS_CONTAINER, children: tags })] }), maybeSubtitle] })] }));
});
EntityTitle.displayName = `${DISPLAYNAME_PREFIX}.EntityTitle`;
/**
 * Construct header class name from H{*}. Returns `undefined` if `heading` is not a Blueprint heading.
 */
function getClassNameFromHeading(heading) {
    const headerIndex = [H1, H2, H3, H4, H5, H6].findIndex(header => header === heading);
    if (headerIndex < 0) {
        return undefined;
    }
    return [Classes.getClassNamespace(), "entity-title-heading", `h${headerIndex + 1}`].join("-");
}
//# sourceMappingURL=entityTitle.js.map