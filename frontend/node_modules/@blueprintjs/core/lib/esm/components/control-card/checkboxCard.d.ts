import { type ControlCardProps } from "./controlCard";
export type CheckboxCardProps = Omit<ControlCardProps, "controlKind">;
/**
 * Checkbox Card component.
 *
 * @see https://blueprintjs.com/docs/#core/components/control-card.checkbox-card
 */
export declare const CheckboxCard: React.FC<CheckboxCardProps>;
