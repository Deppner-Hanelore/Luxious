"""Contract checks for the field survey workspace and action policy."""

from ui.workflow_controller import Operation, WorkflowController, Workspace, WorkflowSnapshot


def test_workspace_permissions_and_edit_return_context():
    workflow = WorkflowController()
    workflow.select_point("P3")

    assert workflow.allows(Operation.RECORD_READING)
    assert not workflow.allows(Operation.CHANGE_POINT)
    workflow.enter_review()
    assert workflow.workspace == Workspace.REVIEW
    assert not workflow.allows(Operation.RECORD_READING)
    assert workflow.allows(Operation.SAVE)

    workflow.enter_edit()
    assert workflow.workspace == Workspace.EDIT
    assert workflow.allows(Operation.CORRECT_READING)
    assert workflow.allows(Operation.IMPORT_READINGS)
    assert workflow.leave_edit({"P1", "P3"}) == "P3"
    assert workflow.workspace == Workspace.REVIEW


def test_edit_return_clears_deleted_selection_and_reconciles_stale_points():
    workflow = WorkflowController()
    workflow.select_point("P2")
    workflow.enter_edit()

    assert workflow.leave_edit({"P1", "P3"}) is None
    assert workflow.workspace == Workspace.SURVEY
    assert workflow.reconcile_points({"P1", "P3"}) is None


def test_next_pending_never_wraps_when_every_point_is_measured():
    workflow = WorkflowController()
    workflow.select_point("P3")

    assert workflow.next_pending(["P1", "P2", "P3"], {"P1", "P2", "P3"}) is None
    assert workflow.next_pending(["P1", "P2", "P3"], {"P1", "P3"}) == "P2"
    assert workflow.next_pending([], set()) is None


def test_snapshot_restores_workspace_and_only_valid_point_ids():
    workflow = WorkflowController()
    snapshot = WorkflowSnapshot(Workspace.REVIEW, "P2")

    workflow.restore(snapshot, {"P1", "P2"})
    assert workflow.workspace == Workspace.REVIEW
    assert workflow.selected_point_id == "P2"

    workflow.restore(snapshot, {"P1"})
    assert workflow.selected_point_id is None
