/*
 * Copyright 2021 Palantir Technologies, Inc. All rights reserved.
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
/**
 * Specifies the popup kind for [aria-haspopup](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Attributes/aria-haspopup).
 */
export var PopupKind;
(function (PopupKind) {
    /** The popup is a menu. */
    PopupKind["MENU"] = "menu";
    /** The popup is a listbox. */
    PopupKind["LISTBOX"] = "listbox";
    /** The popup is a tree. */
    PopupKind["TREE"] = "tree";
    /** The popup is a grid. */
    PopupKind["GRID"] = "grid";
    /** The popup is a dialog. */
    PopupKind["DIALOG"] = "dialog";
})(PopupKind || (PopupKind = {}));
//# sourceMappingURL=popupKind.js.map