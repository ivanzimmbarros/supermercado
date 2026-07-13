"""Testes unitários do ListService (validações e CRUD isolado)."""

from __future__ import annotations

import pytest

from supermercado.services.list_service import ListService


def test_create_list_requires_name(db_session):
    svc = ListService(db_session)
    with pytest.raises(ValueError, match="obrigatório"):
        svc.create_list("   ")


def test_add_item_and_remove(db_session):
    svc = ListService(db_session)
    lst = svc.create_list("Semana")
    item = svc.add_item(
        lst.id,
        name="Leite UHT",
        brand="Mimosa",
        quantity_value=1,
        quantity_unit="l",
        quantity_desired=2,
    )
    assert item.list_id == lst.id
    rows = svc.items_for(lst.id)
    assert len(rows) == 1
    assert rows[0][1].name == "Leite UHT"
    svc.remove_item(item.id)
    assert svc.items_for(lst.id) == []


def test_cannot_add_to_archived_list(db_session):
    svc = ListService(db_session)
    lst = svc.create_list("Temp")
    svc.archive(lst.id)
    with pytest.raises(ValueError, match="activas"):
        svc.add_item(lst.id, name="Arroz")
