"""Contract checks for the field survey workspace state."""

from ui.workflow_controller import WorkflowController, Workspace, WorkflowSnapshot


def test_controller_has_no_edit_workspace():
    assert [w.value for w in Workspace] == ["survey", "review"]
    workflow = WorkflowController()
    assert not hasattr(workflow, "allows")
    assert not hasattr(workflow, "enter_edit")
    workflow.enter_review()
    assert workflow.workspace == Workspace.REVIEW
    workflow.enter_survey()
    assert workflow.workspace == Workspace.SURVEY


def test_reconcile_clears_deleted_selection():
    workflow = WorkflowController()
    workflow.select_point("P2")
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
