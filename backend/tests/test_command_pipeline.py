"""Tests for command handler pipeline orchestration."""

from app.application.commands.document_commands import (
    AssignCompanySetCommand,
    AssignCompanySetCommandHandler,
)
from app.application.commands.version_commands import (
    PublishApprovedVersionCommand,
    PublishApprovedVersionCommandHandler,
)
from app.application.pipeline import (
    CommandPipeline,
    FunctionCommandAuthorizer,
    FunctionCommandExecutor,
    FunctionCommandPublisher,
    FunctionCommandValidator,
)


def test_command_pipeline_runs_stages_in_order():
    stage_calls: list[str] = []

    def validate(context):
        stage_calls.append(f"validate:{context.command}")

    def authorize(context):
        stage_calls.append(f"authorize:{context.command}")

    def execute(context):
        stage_calls.append(f"execute:{context.command}")
        return f"done:{context.command}"

    def publish(context, result):
        stage_calls.append(f"publish:{context.command}:{result}")

    pipeline = CommandPipeline[str, str](
        validator=FunctionCommandValidator(validate),
        authorizer=FunctionCommandAuthorizer(authorize),
        executor=FunctionCommandExecutor(execute),
        publisher=FunctionCommandPublisher(publish),
    )

    run = pipeline.run("cmd-1")

    assert stage_calls == [
        "validate:cmd-1",
        "authorize:cmd-1",
        "execute:cmd-1",
        "publish:cmd-1:done:cmd-1",
    ]
    assert run.value == "done:cmd-1"
    assert run.trace.command_name == "str"
    assert run.trace.stage_order == ("validate", "authorize", "execute", "publish")


def test_assign_company_command_handler_records_pipeline_trace():
    class StubAssignUseCase:
        def assign_company_set(self, _document_id, company_ids):
            return len(set(company_ids))

    handler = AssignCompanySetCommandHandler(StubAssignUseCase())
    result = handler.execute(AssignCompanySetCommand(document_id=11, company_ids=[1, 1, 2]))

    assert result.is_ok
    assert result.value == 2
    assert handler.last_trace is not None
    assert handler.last_trace.command_name == "AssignCompanySetCommand"
    assert handler.last_trace.stage_order == ("validate", "authorize", "execute", "publish")


def test_publish_command_handler_records_pipeline_trace(test_user):
    class StubPublishUseCase:
        def publish_approved_version(self, _document_id, _version_id, _current_user):
            return {"id": 99, "published": True}

    handler = PublishApprovedVersionCommandHandler(StubPublishUseCase())
    result = handler.execute(
        PublishApprovedVersionCommand(document_id=3, version_id=7, current_user=test_user)
    )

    assert result.is_ok
    assert result.value["published"] is True
    assert handler.last_trace is not None
    assert handler.last_trace.command_name == "PublishApprovedVersionCommand"
    assert handler.last_trace.stage_order == ("validate", "authorize", "execute", "publish")
