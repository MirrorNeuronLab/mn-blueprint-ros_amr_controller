"""Record a completed Compose shutdown without issuing robot commands."""
from mn_sdk.blueprint.hooks import report_activity
from mn_sdk.blueprint.outputs import publish_artifact_bundle
from mn_sdk_common.publication import ArtifactWrite


def render_review(artifact):
    from mn_web_report_skill import render_report_html

    evidence = artifact["evidence"]
    return render_report_html({"title": "Warehouse simulation report", "identity": "Simulation only",
        "sections": [
            {"id": "assessment", "title": "Assessment", "blocks": [{"type": "paragraph", "text": artifact["assessment"]}]},
            {"id": "evidence", "title": "Shutdown evidence", "blocks": [{"type": "table",
                "columns": ["Service", "Workflow step", "Observed outcome", "Source"],
                "rows": [[artifact["service"], evidence["workflow_step"], evidence["observed_outcome"], "final_artifact.json"]]}]},
            {"id": "coverage", "title": "Coverage", "blocks": [{"type": "paragraph", "text": artifact["coverage"]}]},
        ]}).encode()


def record_stop(block, inputs):
    artifact = {"schema_version": "mn.turtlebot.service_result.v1", "status": "stopped", "service": "turtlebot-warehouse",
                "simulation_only": True, "assessment": "The warehouse simulation stopped.",
                "evidence": {"workflow_step": block.step_id, "observed_outcome": "Service shutdown completed"},
                "coverage": "This receipt establishes service shutdown only. Check navigation telemetry for route outcomes."}
    reference = block.store.commit("final_artifact.json", artifact, kind="service_result")
    try:
        receipt = publish_artifact_bundle(block, [
            ArtifactWrite("review", "report.html", lambda: render_review(artifact), kind="html",
                          required=False, revision=reference.sha256, mode=0o644),
        ], receipt_path=block.root + "/warehouse-review.json")
        if receipt["warnings"] or receipt["delivery_warnings"]:
            raise OSError("Warehouse review unavailable")
    except Exception:
        block.check()
        report_activity("The shutdown receipt was saved. The web report could not be published.",
                        kind="diagnostic", level="warning", run_dir=block.store.run_dir)
    report_activity("Warehouse navigation service stopped", kind="result", owner_blueprint="ros_amr_controller", step_id=block.step_id, run_dir=block.store.run_dir)
    return {**artifact, "artifact": reference.to_dict()}
