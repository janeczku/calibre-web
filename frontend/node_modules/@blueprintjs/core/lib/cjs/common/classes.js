"use strict";
/*
 * Copyright 2015 Palantir Technologies, Inc. All rights reserved.
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.LIST = exports.HEADING = exports.CODE_BLOCK = exports.CODE = exports.BLOCKQUOTE = exports.TEXT_OVERFLOW_ELLIPSIS = exports.TEXT_DISABLED = exports.TEXT_MUTED = exports.TEXT_SMALL = exports.TEXT_LARGE = exports.MONOSPACE_TEXT = exports.RUNNING_TEXT = exports.UI_TEXT = exports.FOCUS_STYLE_MANAGER_IGNORE = exports.FOCUS_DISABLED = exports.INTENT_DANGER = exports.INTENT_WARNING = exports.INTENT_SUCCESS = exports.INTENT_PRIMARY = exports.ELEVATION_4 = exports.ELEVATION_3 = exports.ELEVATION_2 = exports.ELEVATION_1 = exports.ELEVATION_0 = exports.POSITION_RIGHT = exports.POSITION_LEFT = exports.POSITION_BOTTOM = exports.POSITION_TOP = exports.VERTICAL = exports.SMALL = exports.SELECTED = exports.ROUND = exports.READ_ONLY = exports.MULTILINE = exports.PADDED = exports.OUTLINED = exports.MINIMAL = exports.LOADING = exports.LARGE = exports.INTERACTIVE = exports.INLINE = exports.FIXED_TOP = exports.FIXED = exports.FILL = exports.DISABLED = exports.DARK = exports.COMPACT = exports.ALIGN_RIGHT = exports.ALIGN_LEFT = exports.ACTIVE = void 0;
exports.DRAWER_BODY = exports.DRAWER = exports.DIVIDER = exports.DIALOG_STEP_VIEWED = exports.DIALOG_STEP_ICON = exports.DIALOG_STEP_TITLE = exports.DIALOG_STEP_CONTAINER = exports.DIALOG_STEP = exports.DIALOG_FOOTER_ACTIONS = exports.DIALOG_FOOTER_MAIN_SECTION = exports.DIALOG_FOOTER_FIXED = exports.DIALOG_FOOTER = exports.DIALOG_CLOSE_BUTTON = exports.DIALOG_BODY_SCROLL_CONTAINER = exports.DIALOG_BODY = exports.DIALOG_HEADER = exports.DIALOG_CONTAINER = exports.DIALOG = exports.CONTROL_GROUP = exports.CONTEXT_MENU_BACKDROP = exports.CONTEXT_MENU_POPOVER = exports.CONTEXT_MENU_VIRTUAL_TARGET = exports.CONTEXT_MENU = exports.COLLAPSE_BODY = exports.COLLAPSE = exports.CARD_LIST_BORDERED = exports.CARD_LIST = exports.RADIO_CONTROL_CARD = exports.CHECKBOX_CONTROL_CARD = exports.SWITCH_CONTROL_CARD = exports.CONTROL_CARD_LABEL = exports.CONTROL_CARD = exports.CARD = exports.CALLOUT_ICON = exports.CALLOUT_HAS_BODY_CONTENT = exports.CALLOUT = exports.BUTTON_TEXT = exports.BUTTON_SPINNER = exports.BUTTON_GROUP = exports.BUTTON = exports.BREADCRUMBS_COLLAPSED = exports.BREADCRUMBS = exports.BREADCRUMB_CURRENT = exports.BREADCRUMB = exports.ALERT_FOOTER = exports.ALERT_CONTENTS = exports.ALERT_BODY = exports.ALERT = exports.RTL = exports.LIST_UNSTYLED = void 0;
exports.LABEL = exports.HOTKEY_DIALOG = exports.HOTKEY_COLUMN = exports.HOTKEY_LABEL = exports.HOTKEY = exports.MODIFIER_KEY = exports.KEY_COMBO = exports.KEY = exports.FILE_UPLOAD_INPUT_CUSTOM_TEXT = exports.FILE_UPLOAD_INPUT = exports.FILE_INPUT_HAS_SELECTION = exports.FILE_INPUT = exports.SWITCH_INNER_TEXT = exports.SWITCH = exports.RADIO_GROUP = exports.RADIO = exports.CHECKBOX = exports.CONTROL_INDICATOR_CHILD = exports.CONTROL_INDICATOR = exports.CONTROL_INPUT = exports.CONTROL = exports.TEXT_AREA_AUTO_RESIZE = exports.TEXT_AREA = exports.RESIZABLE_INPUT_SPAN = exports.INPUT_ACTION = exports.INPUT_LEFT_CONTAINER = exports.INPUT_GROUP = exports.INPUT_GHOST = exports.INPUT = exports.HTML_TABLE_STRIPED = exports.HTML_TABLE_BORDERED = exports.HTML_TABLE = exports.HTML_SELECT = exports.FLEX_EXPANDER = exports.ENTITY_TITLE_TITLE_AND_TAGS = exports.ENTITY_TITLE_TITLE = exports.ENTITY_TITLE_TEXT = exports.ENTITY_TITLE_TAGS_CONTAINER = exports.ENTITY_TITLE_SUBTITLE = exports.ENTITY_TITLE_ICON_CONTAINER = exports.ENTITY_TITLE_HAS_SUBTITLE = exports.ENTITY_TITLE_ELLIPSIZE = exports.ENTITY_TITLE = exports.EDITABLE_TEXT_PLACEHOLDER = exports.EDITABLE_TEXT_INPUT = exports.EDITABLE_TEXT_EDITING = exports.EDITABLE_TEXT_CONTENT = exports.EDITABLE_TEXT = exports.DRAWER_HEADER = exports.DRAWER_FOOTER = void 0;
exports.OVERLAY_CONTENT = exports.OVERLAY_CONTAINER = exports.OVERLAY_BACKDROP = exports.OVERLAY = exports.OVERFLOW_LIST_SPACER = exports.OVERFLOW_LIST = exports.NUMERIC_INPUT = exports.NON_IDEAL_STATE_TEXT = exports.NON_IDEAL_STATE_VISUAL = exports.NON_IDEAL_STATE = exports.NAVBAR_DIVIDER = exports.NAVBAR_HEADING = exports.NAVBAR_GROUP = exports.NAVBAR = exports.SECTION_CARD = exports.SECTION_HEADER_COLLAPSE_CARET = exports.SECTION_HEADER_RIGHT = exports.SECTION_HEADER_TABS = exports.SECTION_HEADER_DIVIDER = exports.SECTION_HEADER_SUB_TITLE = exports.SECTION_HEADER_TITLE = exports.SECTION_HEADER_LEFT = exports.SECTION_HEADER = exports.SECTION_COLLAPSED = exports.SECTION = exports.MULTISTEP_DIALOG_NAV_RIGHT = exports.MULTISTEP_DIALOG_NAV_TOP = exports.MULTISTEP_DIALOG_RIGHT_PANEL = exports.MULTISTEP_DIALOG_LEFT_PANEL = exports.MULTISTEP_DIALOG_PANELS = exports.MULTISTEP_DIALOG = exports.MENU_HEADER = exports.MENU_DIVIDER = exports.MENU_SUBMENU_ICON = exports.MENU_SUBMENU = exports.MENU_ITEM_LABEL = exports.MENU_ITEM_ICON = exports.MENU_ITEM_SELECTED_ICON = exports.MENU_ITEM_IS_SELECTABLE = exports.MENU_ITEM = exports.MENU = exports.LINK_COLOR_INHERIT = exports.LINK_UNDERLINE_NONE = exports.LINK_UNDERLINE_HOVER = exports.LINK_UNDERLINE_ALWAYS = exports.LINK = exports.FORM_GROUP_SUB_LABEL = exports.FORM_HELPER_TEXT = exports.FORM_CONTENT = exports.FORM_GROUP = void 0;
exports.SEGMENTED_CONTROL = exports.SPINNER_TRACK = exports.SPINNER_NO_SPIN = exports.SPINNER_HEAD = exports.SPINNER_ANIMATION = exports.SPINNER = exports.END = exports.START = exports.SLIDER_PROGRESS = exports.SLIDER_TRACK = exports.SLIDER_LABEL = exports.SLIDER_HANDLE = exports.SLIDER_AXIS = exports.SLIDER = exports.SKELETON = exports.PORTAL = exports.PROGRESS_NO_ANIMATION = exports.PROGRESS_NO_STRIPES = exports.PROGRESS_METER = exports.PROGRESS_BAR = exports.POPOVER_WRAPPER = exports.POPOVER_MINIMAL_ANIMATION = exports.POPOVER_TRANSITION_CONTAINER = exports.POPOVER_TARGET = exports.POPOVER_REFERENCE_HIDDEN = exports.POPOVER_POPPER_ESCAPED = exports.POPOVER_OPEN = exports.POPOVER_MATCH_TARGET_WIDTH = exports.POPOVER_DISMISS_OVERRIDE = exports.POPOVER_DISMISS = exports.POPOVER_CONTENT_SIZING = exports.POPOVER_CONTENT_PLACEMENT = exports.POPOVER_CONTENT = exports.POPOVER_CAPTURING_DISMISS = exports.POPOVER_BACKDROP = exports.POPOVER_ARROW = exports.POPOVER = exports.PANEL_STACK2_VIEW = exports.PANEL_STACK2_HEADER_BACK = exports.PANEL_STACK2_HEADER = exports.PANEL_STACK2 = exports.PANEL_STACK_VIEW = exports.PANEL_STACK_HEADER_BACK = exports.PANEL_STACK_HEADER = exports.PANEL_STACK = exports.OVERLAY_END_FOCUS_TRAP = exports.OVERLAY_START_FOCUS_TRAP = exports.OVERLAY_SCROLL_CONTAINER = exports.OVERLAY_OPEN = exports.OVERLAY_INLINE = void 0;
exports.ICON_MUTED = exports.ICON_LARGE = exports.ICON_STANDARD = exports.ICON = exports.TREE_ROOT = exports.TREE_NODE_SELECTED = exports.TREE_NODE_SECONDARY_LABEL = exports.TREE_NODE_LIST = exports.TREE_NODE_LABEL = exports.TREE_NODE_ICON = exports.TREE_NODE_EXPANDED = exports.TREE_NODE_CONTENT = exports.TREE_NODE_CARET_OPEN = exports.TREE_NODE_CARET_NONE = exports.TREE_NODE_CARET_CLOSED = exports.TREE_NODE_CARET = exports.TREE_NODE = exports.TREE = exports.TOOLTIP_INDICATOR = exports.TOOLTIP = exports.TOAST_MESSAGE = exports.TOAST_CONTAINER = exports.TOAST = exports.TAG_INPUT_VALUES = exports.TAG_INPUT_ICON = exports.TAG_INPUT = exports.COMPOUND_TAG_RIGHT_CONTENT = exports.COMPOUND_TAG_RIGHT = exports.COMPOUND_TAG_LEFT_CONTENT = exports.COMPOUND_TAG_LEFT = exports.COMPOUND_TAG = exports.TAG_REMOVE = exports.TAG = exports.TABS = exports.TAB_PANEL = exports.TAB_LIST = exports.TAB_INDICATOR_WRAPPER = exports.TAB_INDICATOR = exports.TAB_TAG = exports.TAB_ICON = exports.TAB = void 0;
exports.getClassNamespace = getClassNamespace;
exports.alignmentClass = alignmentClass;
exports.elevationClass = elevationClass;
exports.iconClass = iconClass;
exports.intentClass = intentClass;
exports.positionClass = positionClass;
exports.sizeClass = sizeClass;
exports.variantClass = variantClass;
const alignment_1 = require("./alignment");
const elevation_1 = require("./elevation");
const intent_1 = require("./intent");
const position_1 = require("./position");
let NS = "bp6";
if (typeof BLUEPRINT_NAMESPACE !== "undefined") {
    NS = BLUEPRINT_NAMESPACE;
}
else if (typeof REACT_APP_BLUEPRINT_NAMESPACE !== "undefined") {
    NS = REACT_APP_BLUEPRINT_NAMESPACE;
}
// modifiers
exports.ACTIVE = `${NS}-active`;
exports.ALIGN_LEFT = `${NS}-align-left`;
exports.ALIGN_RIGHT = `${NS}-align-right`;
exports.COMPACT = `${NS}-compact`;
exports.DARK = `${NS}-dark`;
exports.DISABLED = `${NS}-disabled`;
exports.FILL = `${NS}-fill`;
exports.FIXED = `${NS}-fixed`;
exports.FIXED_TOP = `${NS}-fixed-top`;
exports.INLINE = `${NS}-inline`;
exports.INTERACTIVE = `${NS}-interactive`;
exports.LARGE = `${NS}-large`;
exports.LOADING = `${NS}-loading`;
exports.MINIMAL = `${NS}-minimal`;
exports.OUTLINED = `${NS}-outlined`;
exports.PADDED = `${NS}-padded`;
exports.MULTILINE = `${NS}-multiline`;
exports.READ_ONLY = `${NS}-read-only`;
exports.ROUND = `${NS}-round`;
exports.SELECTED = `${NS}-selected`;
exports.SMALL = `${NS}-small`;
exports.VERTICAL = `${NS}-vertical`;
exports.POSITION_TOP = positionClass(position_1.Position.TOP);
exports.POSITION_BOTTOM = positionClass(position_1.Position.BOTTOM);
exports.POSITION_LEFT = positionClass(position_1.Position.LEFT);
exports.POSITION_RIGHT = positionClass(position_1.Position.RIGHT);
exports.ELEVATION_0 = elevationClass(elevation_1.Elevation.ZERO);
exports.ELEVATION_1 = elevationClass(elevation_1.Elevation.ONE);
exports.ELEVATION_2 = elevationClass(elevation_1.Elevation.TWO);
exports.ELEVATION_3 = elevationClass(elevation_1.Elevation.THREE);
exports.ELEVATION_4 = elevationClass(elevation_1.Elevation.FOUR);
exports.INTENT_PRIMARY = intentClass(intent_1.Intent.PRIMARY);
exports.INTENT_SUCCESS = intentClass(intent_1.Intent.SUCCESS);
exports.INTENT_WARNING = intentClass(intent_1.Intent.WARNING);
exports.INTENT_DANGER = intentClass(intent_1.Intent.DANGER);
exports.FOCUS_DISABLED = `${NS}-focus-disabled`;
exports.FOCUS_STYLE_MANAGER_IGNORE = `${NS}-focus-style-manager-ignore`;
// text utilities
exports.UI_TEXT = `${NS}-ui-text`;
exports.RUNNING_TEXT = `${NS}-running-text`;
exports.MONOSPACE_TEXT = `${NS}-monospace-text`;
exports.TEXT_LARGE = `${NS}-text-large`;
exports.TEXT_SMALL = `${NS}-text-small`;
exports.TEXT_MUTED = `${NS}-text-muted`;
exports.TEXT_DISABLED = `${NS}-text-disabled`;
exports.TEXT_OVERFLOW_ELLIPSIS = `${NS}-text-overflow-ellipsis`;
// textual elements
exports.BLOCKQUOTE = `${NS}-blockquote`;
exports.CODE = `${NS}-code`;
exports.CODE_BLOCK = `${NS}-code-block`;
exports.HEADING = `${NS}-heading`;
exports.LIST = `${NS}-list`;
exports.LIST_UNSTYLED = `${NS}-list-unstyled`;
exports.RTL = `${NS}-rtl`;
// components
exports.ALERT = `${NS}-alert`;
exports.ALERT_BODY = `${exports.ALERT}-body`;
exports.ALERT_CONTENTS = `${exports.ALERT}-contents`;
exports.ALERT_FOOTER = `${exports.ALERT}-footer`;
exports.BREADCRUMB = `${NS}-breadcrumb`;
exports.BREADCRUMB_CURRENT = `${exports.BREADCRUMB}-current`;
exports.BREADCRUMBS = `${exports.BREADCRUMB}s`;
exports.BREADCRUMBS_COLLAPSED = `${exports.BREADCRUMB}s-collapsed`;
exports.BUTTON = `${NS}-button`;
exports.BUTTON_GROUP = `${exports.BUTTON}-group`;
exports.BUTTON_SPINNER = `${exports.BUTTON}-spinner`;
exports.BUTTON_TEXT = `${exports.BUTTON}-text`;
exports.CALLOUT = `${NS}-callout`;
exports.CALLOUT_HAS_BODY_CONTENT = `${exports.CALLOUT}-has-body-content`;
exports.CALLOUT_ICON = `${exports.CALLOUT}-icon`;
exports.CARD = `${NS}-card`;
exports.CONTROL_CARD = `${NS}-control-card`;
exports.CONTROL_CARD_LABEL = `${exports.CONTROL_CARD}-label`;
exports.SWITCH_CONTROL_CARD = `${NS}-switch-control-card`;
exports.CHECKBOX_CONTROL_CARD = `${NS}-checkbox-control-card`;
exports.RADIO_CONTROL_CARD = `${NS}-radio-control-card`;
exports.CARD_LIST = `${NS}-card-list`;
exports.CARD_LIST_BORDERED = `${exports.CARD_LIST}-bordered`;
exports.COLLAPSE = `${NS}-collapse`;
exports.COLLAPSE_BODY = `${exports.COLLAPSE}-body`;
exports.CONTEXT_MENU = `${NS}-context-menu`;
exports.CONTEXT_MENU_VIRTUAL_TARGET = `${exports.CONTEXT_MENU}-virtual-target`;
exports.CONTEXT_MENU_POPOVER = `${exports.CONTEXT_MENU}-popover`;
exports.CONTEXT_MENU_BACKDROP = `${exports.CONTEXT_MENU}-backdrop`;
exports.CONTROL_GROUP = `${NS}-control-group`;
exports.DIALOG = `${NS}-dialog`;
exports.DIALOG_CONTAINER = `${exports.DIALOG}-container`;
exports.DIALOG_HEADER = `${exports.DIALOG}-header`;
exports.DIALOG_BODY = `${exports.DIALOG}-body`;
exports.DIALOG_BODY_SCROLL_CONTAINER = `${exports.DIALOG}-body-scroll-container`;
exports.DIALOG_CLOSE_BUTTON = `${exports.DIALOG}-close-button`;
exports.DIALOG_FOOTER = `${exports.DIALOG}-footer`;
exports.DIALOG_FOOTER_FIXED = `${exports.DIALOG}-footer-fixed`;
exports.DIALOG_FOOTER_MAIN_SECTION = `${exports.DIALOG}-footer-main-section`;
exports.DIALOG_FOOTER_ACTIONS = `${exports.DIALOG}-footer-actions`;
exports.DIALOG_STEP = `${NS}-dialog-step`;
exports.DIALOG_STEP_CONTAINER = `${exports.DIALOG_STEP}-container`;
exports.DIALOG_STEP_TITLE = `${exports.DIALOG_STEP}-title`;
exports.DIALOG_STEP_ICON = `${exports.DIALOG_STEP}-icon`;
exports.DIALOG_STEP_VIEWED = `${exports.DIALOG_STEP}-viewed`;
exports.DIVIDER = `${NS}-divider`;
exports.DRAWER = `${NS}-drawer`;
exports.DRAWER_BODY = `${exports.DRAWER}-body`;
exports.DRAWER_FOOTER = `${exports.DRAWER}-footer`;
exports.DRAWER_HEADER = `${exports.DRAWER}-header`;
exports.EDITABLE_TEXT = `${NS}-editable-text`;
exports.EDITABLE_TEXT_CONTENT = `${exports.EDITABLE_TEXT}-content`;
exports.EDITABLE_TEXT_EDITING = `${exports.EDITABLE_TEXT}-editing`;
exports.EDITABLE_TEXT_INPUT = `${exports.EDITABLE_TEXT}-input`;
exports.EDITABLE_TEXT_PLACEHOLDER = `${exports.EDITABLE_TEXT}-placeholder`;
exports.ENTITY_TITLE = `${NS}-entity-title`;
exports.ENTITY_TITLE_ELLIPSIZE = `${NS}-entity-title-ellipsize`;
exports.ENTITY_TITLE_HAS_SUBTITLE = `${exports.ENTITY_TITLE}-has-subtitle`;
exports.ENTITY_TITLE_ICON_CONTAINER = `${exports.ENTITY_TITLE}-icon-container`;
exports.ENTITY_TITLE_SUBTITLE = `${exports.ENTITY_TITLE}-subtitle`;
exports.ENTITY_TITLE_TAGS_CONTAINER = `${exports.ENTITY_TITLE}-tags-container`;
exports.ENTITY_TITLE_TEXT = `${exports.ENTITY_TITLE}-text`;
exports.ENTITY_TITLE_TITLE = `${exports.ENTITY_TITLE}-title`;
exports.ENTITY_TITLE_TITLE_AND_TAGS = `${exports.ENTITY_TITLE}-title-and-tags`;
exports.FLEX_EXPANDER = `${NS}-flex-expander`;
exports.HTML_SELECT = `${NS}-html-select`;
exports.HTML_TABLE = `${NS}-html-table`;
exports.HTML_TABLE_BORDERED = `${exports.HTML_TABLE}-bordered`;
exports.HTML_TABLE_STRIPED = `${exports.HTML_TABLE}-striped`;
exports.INPUT = `${NS}-input`;
exports.INPUT_GHOST = `${exports.INPUT}-ghost`;
exports.INPUT_GROUP = `${exports.INPUT}-group`;
exports.INPUT_LEFT_CONTAINER = `${exports.INPUT}-left-container`;
exports.INPUT_ACTION = `${exports.INPUT}-action`;
exports.RESIZABLE_INPUT_SPAN = `${NS}-resizable-input-span`;
exports.TEXT_AREA = `${NS}-text-area`;
exports.TEXT_AREA_AUTO_RESIZE = `${exports.TEXT_AREA}-auto-resize`;
exports.CONTROL = `${NS}-control`;
exports.CONTROL_INPUT = `${exports.CONTROL}-input`;
exports.CONTROL_INDICATOR = `${exports.CONTROL}-indicator`;
exports.CONTROL_INDICATOR_CHILD = `${exports.CONTROL_INDICATOR}-child`;
exports.CHECKBOX = `${NS}-checkbox`;
exports.RADIO = `${NS}-radio`;
exports.RADIO_GROUP = `${NS}-radio-group`;
exports.SWITCH = `${NS}-switch`;
exports.SWITCH_INNER_TEXT = `${exports.SWITCH}-inner-text`;
exports.FILE_INPUT = `${NS}-file-input`;
exports.FILE_INPUT_HAS_SELECTION = `${NS}-file-input-has-selection`;
exports.FILE_UPLOAD_INPUT = `${NS}-file-upload-input`;
exports.FILE_UPLOAD_INPUT_CUSTOM_TEXT = `${NS}-file-upload-input-custom-text`;
exports.KEY = `${NS}-key`;
exports.KEY_COMBO = `${exports.KEY}-combo`;
exports.MODIFIER_KEY = `${NS}-modifier-key`;
exports.HOTKEY = `${NS}-hotkey`;
exports.HOTKEY_LABEL = `${exports.HOTKEY}-label`;
exports.HOTKEY_COLUMN = `${exports.HOTKEY}-column`;
exports.HOTKEY_DIALOG = `${exports.HOTKEY}-dialog`;
exports.LABEL = `${NS}-label`;
exports.FORM_GROUP = `${NS}-form-group`;
exports.FORM_CONTENT = `${NS}-form-content`;
exports.FORM_HELPER_TEXT = `${NS}-form-helper-text`;
exports.FORM_GROUP_SUB_LABEL = `${NS}-form-group-sub-label`;
exports.LINK = `${NS}-link`;
exports.LINK_UNDERLINE_ALWAYS = `${exports.LINK}-underline-always`;
exports.LINK_UNDERLINE_HOVER = `${exports.LINK}-underline-hover`;
exports.LINK_UNDERLINE_NONE = `${exports.LINK}-underline-none`;
exports.LINK_COLOR_INHERIT = `${exports.LINK}-color-inherit`;
exports.MENU = `${NS}-menu`;
exports.MENU_ITEM = `${exports.MENU}-item`;
exports.MENU_ITEM_IS_SELECTABLE = `${exports.MENU_ITEM}-is-selectable`;
exports.MENU_ITEM_SELECTED_ICON = `${exports.MENU_ITEM}-selected-icon`;
exports.MENU_ITEM_ICON = `${exports.MENU_ITEM}-icon`;
exports.MENU_ITEM_LABEL = `${exports.MENU_ITEM}-label`;
exports.MENU_SUBMENU = `${NS}-submenu`;
exports.MENU_SUBMENU_ICON = `${exports.MENU_SUBMENU}-icon`;
exports.MENU_DIVIDER = `${exports.MENU}-divider`;
exports.MENU_HEADER = `${exports.MENU}-header`;
exports.MULTISTEP_DIALOG = `${NS}-multistep-dialog`;
exports.MULTISTEP_DIALOG_PANELS = `${exports.MULTISTEP_DIALOG}-panels`;
exports.MULTISTEP_DIALOG_LEFT_PANEL = `${exports.MULTISTEP_DIALOG}-left-panel`;
exports.MULTISTEP_DIALOG_RIGHT_PANEL = `${exports.MULTISTEP_DIALOG}-right-panel`;
exports.MULTISTEP_DIALOG_NAV_TOP = `${exports.MULTISTEP_DIALOG}-nav-top`;
exports.MULTISTEP_DIALOG_NAV_RIGHT = `${exports.MULTISTEP_DIALOG}-nav-right`;
exports.SECTION = `${NS}-section`;
exports.SECTION_COLLAPSED = `${exports.SECTION}-collapsed`;
exports.SECTION_HEADER = `${exports.SECTION}-header`;
exports.SECTION_HEADER_LEFT = `${exports.SECTION_HEADER}-left`;
exports.SECTION_HEADER_TITLE = `${exports.SECTION_HEADER}-title`;
exports.SECTION_HEADER_SUB_TITLE = `${exports.SECTION_HEADER}-sub-title`;
exports.SECTION_HEADER_DIVIDER = `${exports.SECTION_HEADER}-divider`;
exports.SECTION_HEADER_TABS = `${exports.SECTION_HEADER}-tabs`;
exports.SECTION_HEADER_RIGHT = `${exports.SECTION_HEADER}-right`;
exports.SECTION_HEADER_COLLAPSE_CARET = `${exports.SECTION_HEADER}-collapse-caret`;
exports.SECTION_CARD = `${exports.SECTION}-card`;
exports.NAVBAR = `${NS}-navbar`;
exports.NAVBAR_GROUP = `${exports.NAVBAR}-group`;
exports.NAVBAR_HEADING = `${exports.NAVBAR}-heading`;
exports.NAVBAR_DIVIDER = `${exports.NAVBAR}-divider`;
exports.NON_IDEAL_STATE = `${NS}-non-ideal-state`;
exports.NON_IDEAL_STATE_VISUAL = `${exports.NON_IDEAL_STATE}-visual`;
exports.NON_IDEAL_STATE_TEXT = `${exports.NON_IDEAL_STATE}-text`;
exports.NUMERIC_INPUT = `${NS}-numeric-input`;
exports.OVERFLOW_LIST = `${NS}-overflow-list`;
exports.OVERFLOW_LIST_SPACER = `${exports.OVERFLOW_LIST}-spacer`;
exports.OVERLAY = `${NS}-overlay`;
exports.OVERLAY_BACKDROP = `${exports.OVERLAY}-backdrop`;
exports.OVERLAY_CONTAINER = `${exports.OVERLAY}-container`;
exports.OVERLAY_CONTENT = `${exports.OVERLAY}-content`;
exports.OVERLAY_INLINE = `${exports.OVERLAY}-inline`;
exports.OVERLAY_OPEN = `${exports.OVERLAY}-open`;
exports.OVERLAY_SCROLL_CONTAINER = `${exports.OVERLAY}-scroll-container`;
exports.OVERLAY_START_FOCUS_TRAP = `${exports.OVERLAY}-start-focus-trap`;
exports.OVERLAY_END_FOCUS_TRAP = `${exports.OVERLAY}-end-focus-trap`;
exports.PANEL_STACK = `${NS}-panel-stack2`;
exports.PANEL_STACK_HEADER = `${exports.PANEL_STACK}-header`;
exports.PANEL_STACK_HEADER_BACK = `${exports.PANEL_STACK}-header-back`;
exports.PANEL_STACK_VIEW = `${exports.PANEL_STACK}-view`;
/** @deprecated Use `PANEL_STACK` instead */
exports.PANEL_STACK2 = exports.PANEL_STACK;
/** @deprecated Use `PANEL_STACK_HEADER` instead */
exports.PANEL_STACK2_HEADER = exports.PANEL_STACK_HEADER;
/** @deprecated Use PANEL_STACK_HEADER_BACK instead */
exports.PANEL_STACK2_HEADER_BACK = exports.PANEL_STACK_HEADER_BACK;
/** @deprecated Use PANEL_STACK_VIEW instead */
exports.PANEL_STACK2_VIEW = exports.PANEL_STACK_VIEW;
exports.POPOVER = `${NS}-popover`;
exports.POPOVER_ARROW = `${exports.POPOVER}-arrow`;
exports.POPOVER_BACKDROP = `${exports.POPOVER}-backdrop`;
exports.POPOVER_CAPTURING_DISMISS = `${exports.POPOVER}-capturing-dismiss`;
exports.POPOVER_CONTENT = `${exports.POPOVER}-content`;
exports.POPOVER_CONTENT_PLACEMENT = `${exports.POPOVER}-placement`;
exports.POPOVER_CONTENT_SIZING = `${exports.POPOVER_CONTENT}-sizing`;
exports.POPOVER_DISMISS = `${exports.POPOVER}-dismiss`;
exports.POPOVER_DISMISS_OVERRIDE = `${exports.POPOVER_DISMISS}-override`;
exports.POPOVER_MATCH_TARGET_WIDTH = `${exports.POPOVER}-match-target-width`;
exports.POPOVER_OPEN = `${exports.POPOVER}-open`;
exports.POPOVER_POPPER_ESCAPED = `${exports.POPOVER}-popper-escaped`;
exports.POPOVER_REFERENCE_HIDDEN = `${exports.POPOVER}-reference-hidden`;
exports.POPOVER_TARGET = `${exports.POPOVER}-target`;
exports.POPOVER_TRANSITION_CONTAINER = `${exports.POPOVER}-transition-container`;
exports.POPOVER_MINIMAL_ANIMATION = `${exports.POPOVER}-minimal-animation`;
/** @deprecated, no longer used in Blueprint v5.x */
exports.POPOVER_WRAPPER = `${exports.POPOVER}-wrapper`;
exports.PROGRESS_BAR = `${NS}-progress-bar`;
exports.PROGRESS_METER = `${NS}-progress-meter`;
exports.PROGRESS_NO_STRIPES = `${NS}-no-stripes`;
exports.PROGRESS_NO_ANIMATION = `${NS}-no-animation`;
exports.PORTAL = `${NS}-portal`;
exports.SKELETON = `${NS}-skeleton`;
exports.SLIDER = `${NS}-slider`;
exports.SLIDER_AXIS = `${exports.SLIDER}-axis`;
exports.SLIDER_HANDLE = `${exports.SLIDER}-handle`;
exports.SLIDER_LABEL = `${exports.SLIDER}-label`;
exports.SLIDER_TRACK = `${exports.SLIDER}-track`;
exports.SLIDER_PROGRESS = `${exports.SLIDER}-progress`;
exports.START = `${NS}-start`;
exports.END = `${NS}-end`;
exports.SPINNER = `${NS}-spinner`;
exports.SPINNER_ANIMATION = `${exports.SPINNER}-animation`;
exports.SPINNER_HEAD = `${exports.SPINNER}-head`;
exports.SPINNER_NO_SPIN = `${NS}-no-spin`;
exports.SPINNER_TRACK = `${exports.SPINNER}-track`;
exports.SEGMENTED_CONTROL = `${NS}-segmented-control`;
exports.TAB = `${NS}-tab`;
exports.TAB_ICON = `${exports.TAB}-icon`;
exports.TAB_TAG = `${exports.TAB}-tag`;
exports.TAB_INDICATOR = `${exports.TAB}-indicator`;
exports.TAB_INDICATOR_WRAPPER = `${exports.TAB_INDICATOR}-wrapper`;
exports.TAB_LIST = `${exports.TAB}-list`;
exports.TAB_PANEL = `${exports.TAB}-panel`;
exports.TABS = `${exports.TAB}s`;
exports.TAG = `${NS}-tag`;
exports.TAG_REMOVE = `${exports.TAG}-remove`;
exports.COMPOUND_TAG = `${NS}-compound-tag`;
exports.COMPOUND_TAG_LEFT = `${exports.COMPOUND_TAG}-left`;
exports.COMPOUND_TAG_LEFT_CONTENT = `${exports.COMPOUND_TAG}-left-content`;
exports.COMPOUND_TAG_RIGHT = `${exports.COMPOUND_TAG}-right`;
exports.COMPOUND_TAG_RIGHT_CONTENT = `${exports.COMPOUND_TAG}-right-content`;
exports.TAG_INPUT = `${NS}-tag-input`;
exports.TAG_INPUT_ICON = `${exports.TAG_INPUT}-icon`;
exports.TAG_INPUT_VALUES = `${exports.TAG_INPUT}-values`;
exports.TOAST = `${NS}-toast`;
exports.TOAST_CONTAINER = `${exports.TOAST}-container`;
exports.TOAST_MESSAGE = `${exports.TOAST}-message`;
exports.TOOLTIP = `${NS}-tooltip`;
exports.TOOLTIP_INDICATOR = `${exports.TOOLTIP}-indicator`;
exports.TREE = `${NS}-tree`;
exports.TREE_NODE = `${NS}-tree-node`;
exports.TREE_NODE_CARET = `${exports.TREE_NODE}-caret`;
exports.TREE_NODE_CARET_CLOSED = `${exports.TREE_NODE_CARET}-closed`;
exports.TREE_NODE_CARET_NONE = `${exports.TREE_NODE_CARET}-none`;
exports.TREE_NODE_CARET_OPEN = `${exports.TREE_NODE_CARET}-open`;
exports.TREE_NODE_CONTENT = `${exports.TREE_NODE}-content`;
exports.TREE_NODE_EXPANDED = `${exports.TREE_NODE}-expanded`;
exports.TREE_NODE_ICON = `${exports.TREE_NODE}-icon`;
exports.TREE_NODE_LABEL = `${exports.TREE_NODE}-label`;
exports.TREE_NODE_LIST = `${exports.TREE_NODE}-list`;
exports.TREE_NODE_SECONDARY_LABEL = `${exports.TREE_NODE}-secondary-label`;
exports.TREE_NODE_SELECTED = `${exports.TREE_NODE}-selected`;
exports.TREE_ROOT = `${NS}-tree-root`;
exports.ICON = `${NS}-icon`;
exports.ICON_STANDARD = `${exports.ICON}-standard`;
exports.ICON_LARGE = `${exports.ICON}-large`;
exports.ICON_MUTED = `${exports.ICON}-muted`;
/**
 * Returns the namespace prefix for all Blueprint CSS classes.
 * Customize this namespace at build time by defining it with `webpack.DefinePlugin`.
 */
function getClassNamespace() {
    return NS;
}
/** Return CSS class for alignment. */
function alignmentClass(alignment) {
    switch (alignment) {
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        case alignment_1.Alignment.LEFT:
        case alignment_1.Alignment.START:
            return exports.ALIGN_LEFT;
        // eslint-disable-next-line @typescript-eslint/no-deprecated
        case alignment_1.Alignment.RIGHT:
        case alignment_1.Alignment.END:
            return exports.ALIGN_RIGHT;
        default:
            return undefined;
    }
}
function elevationClass(elevation) {
    if (elevation === undefined) {
        return undefined;
    }
    return `${NS}-elevation-${elevation}`;
}
function iconClass(iconName) {
    if (iconName == null) {
        return undefined;
    }
    return iconName.indexOf(`${NS}-icon-`) === 0 ? iconName : `${NS}-icon-${iconName}`;
}
function intentClass(intent) {
    if (intent == null || intent === intent_1.Intent.NONE) {
        return undefined;
    }
    return `${NS}-intent-${intent.toLowerCase()}`;
}
function positionClass(position) {
    if (position === undefined) {
        return undefined;
    }
    return `${NS}-position-${position}`;
}
function sizeClass(size, legacyProps) {
    if (size === "small") {
        return exports.SMALL;
    }
    if (size === "large") {
        return exports.LARGE;
    }
    const { large = false, small = false } = legacyProps;
    return {
        [exports.LARGE]: large,
        [exports.SMALL]: small,
    };
}
function variantClass(variant, legacyProps) {
    // variant takes precedence over minimal and outlined
    if (variant === "outlined") {
        return exports.OUTLINED;
    }
    if (variant === "minimal") {
        return exports.MINIMAL;
    }
    const { minimal = false, outlined = false } = legacyProps;
    return {
        [exports.MINIMAL]: minimal,
        [exports.OUTLINED]: outlined,
    };
}
//# sourceMappingURL=classes.js.map