import type { HotkeyConfig } from "../../hooks";
import { type DialogProps } from "../dialog/dialog";
export interface HotkeysDialogProps extends DialogProps {
    /**
     * This string displayed as the group name in the hotkeys dialog for all
     * global hotkeys.
     */
    globalGroupName?: string;
    hotkeys: readonly HotkeyConfig[];
}
export declare const HotkeysDialog: React.FC<HotkeysDialogProps>;
