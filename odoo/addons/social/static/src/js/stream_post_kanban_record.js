import { KanbanRecord } from '@web/views/kanban/kanban_record';

export const CANCEL_GLOBAL_CLICK = ["a", ".o_social_subtle_btn", "img"].join(",");
const DEFAULT_COMMENT_COUNT = 20;

export class StreamPostKanbanRecord extends KanbanRecord {
    //---------------------------------------
    // Handlers
    //---------------------------------------

    /**
     * @override
     */
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        this.rootRef.el.querySelector('.o_social_comments').click();
    }

    //---------------------------------------
    // Private
    //---------------------------------------

    /**
     * TODO: remove in master.
     */
    async _updateLikesCount(userLikeField, likesCountField, record = null) {
    }

    /**
     * TODO: remove in master.
     */
    _prepareLikeAdditionnalValues(likesCount, userLikes) {
        return {};
    }

    //---------
    // Getters
    //---------

    get commentCount() {
        return this.props.commentCount || DEFAULT_COMMENT_COUNT;
    }
}
