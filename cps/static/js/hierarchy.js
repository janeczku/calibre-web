/**
 * Hierarchical custom columns: collapse/expand state persistence.
 *
 * The open/closed state of every <details class="hierarchy-details"> node is
 * stored in sessionStorage (per column, keyed by the node's dotted path), so
 * the user's expansion survives page navigations within the session.
 * The active branch is additionally expanded server-side (URL-driven), which
 * takes precedence for the current path.
 *
 * Also wires the "Expand all" / "Collapse all" buttons on the tree page.
 */
(function ($) {
    'use strict';

    $(function () {
        var $tree = $('.hierarchy-tree');
        if (!$tree.length) {
            return;
        }
        var colId = $tree.data('col-id');
        var storageKey = 'cw-hierarchy-' + colId;
        var state = {};

        function loadState() {
            try {
                state = JSON.parse(sessionStorage.getItem(storageKey) || '{}') || {};
            } catch (e) {
                state = {};
            }
        }

        function saveState() {
            try {
                sessionStorage.setItem(storageKey, JSON.stringify(state));
            } catch (e) { /* storage unavailable (private mode etc.) */ }
        }

        loadState();

        // Restore previously toggled nodes (server-rendered "open" state for
        // the active path is only applied when no user preference exists).
        $tree.find('details.hierarchy-details[data-path]').each(function () {
            var path = $(this).data('path');
            if (Object.prototype.hasOwnProperty.call(state, path)) {
                this.open = !!state[path];
            }
        });

        $tree.on('toggle', 'details.hierarchy-details', function () {
            state[$(this).data('path')] = this.open;
            saveState();
        });

        $('#hierarchy-expand-all').on('click', function (e) {
            e.preventDefault();
            $tree.find('details.hierarchy-details').prop('open', true);
        });

        $('#hierarchy-collapse-all').on('click', function (e) {
            e.preventDefault();
            $tree.find('details.hierarchy-details').prop('open', false);
        });
    });
}(jQuery));
