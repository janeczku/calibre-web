import { jsx as _jsx } from "react/jsx-runtime";
import { AnchorButton } from "../button/buttons";
import { Tooltip } from "../tooltip/tooltip";
export function DialogStepButton({ tooltipContent, ...props }) {
    const button = _jsx(AnchorButton, { ...props });
    if (tooltipContent !== undefined) {
        return _jsx(Tooltip, { content: tooltipContent, children: button });
    }
    else {
        return button;
    }
}
//# sourceMappingURL=dialogStepButton.js.map