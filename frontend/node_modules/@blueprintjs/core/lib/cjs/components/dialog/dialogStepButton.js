"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DialogStepButton = DialogStepButton;
const jsx_runtime_1 = require("react/jsx-runtime");
const buttons_1 = require("../button/buttons");
const tooltip_1 = require("../tooltip/tooltip");
function DialogStepButton({ tooltipContent, ...props }) {
    const button = (0, jsx_runtime_1.jsx)(buttons_1.AnchorButton, { ...props });
    if (tooltipContent !== undefined) {
        return (0, jsx_runtime_1.jsx)(tooltip_1.Tooltip, { content: tooltipContent, children: button });
    }
    else {
        return button;
    }
}
//# sourceMappingURL=dialogStepButton.js.map