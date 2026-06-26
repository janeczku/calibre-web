export interface HTMLTableProps extends React.TableHTMLAttributes<HTMLTableElement>, React.RefAttributes<HTMLTableElement> {
    /** Enable borders between rows and cells. */
    bordered?: boolean;
    /** Use compact appearance with less padding. */
    compact?: boolean;
    /** Enable hover styles on rows. */
    interactive?: boolean;
    /** Use an alternate background color on odd-numbered rows. */
    striped?: boolean;
}
/**
 * HTML table component.
 *
 * @see https://blueprintjs.com/docs/#core/components/html-table
 */
export declare const HTMLTable: React.FC<HTMLTableProps>;
