"""Tests for immutable command/query DTO behavior."""

from dataclasses import FrozenInstanceError

import pytest

from app.application.commands.document_commands import AssignCompanySetCommand
from app.application.commands.version_commands import PublishApprovedVersionCommand
from app.application.dto import ActorContext
from app.application.queries.document_queries import GetDocumentQuery


def test_assign_company_set_command_normalizes_company_ids_to_immutable_tuple():
    requested_ids = [1, 2, 2]
    command = AssignCompanySetCommand(document_id=7, company_ids=requested_ids)

    requested_ids.append(99)

    assert command.company_ids == (1, 2, 2)
    assert isinstance(command.company_ids, tuple)


def test_assign_company_set_command_is_frozen():
    command = AssignCompanySetCommand(document_id=7, company_ids=[1, 2])

    with pytest.raises(FrozenInstanceError):
        command.document_id = 9


def test_publish_command_snapshots_user_as_actor_context(db, test_user):
    command = PublishApprovedVersionCommand(
        document_id=11,
        version_id=3,
        current_user=test_user,
    )

    assert isinstance(command.current_user, ActorContext)
    original_tenant_id = command.current_user.tenant_id

    test_user.tenant_id = 777
    test_user.is_active = False

    assert command.current_user.tenant_id == original_tenant_id
    assert command.current_user.is_active is True


def test_get_document_query_is_frozen():
    query = GetDocumentQuery(document_id=42)

    with pytest.raises(FrozenInstanceError):
        query.document_id = 99
