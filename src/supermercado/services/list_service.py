"""Gestão de listas de compras e comparação por item."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from supermercado.matching.engine import ProductRef
from supermercado.persistence.models import ListItem, MarketProduct, Product, ShoppingList
from supermercado.services.search_service import RankedOffer, SearchService


@dataclass
class ComparedListItem:
    item: ListItem
    product: Product
    best: RankedOffer | None
    alternatives: list[RankedOffer]
    estimated_line_total: float | None


@dataclass
class ComparedList:
    shopping_list: ShoppingList
    lines: list[ComparedListItem]
    estimated_total: float
    errors: dict[str, str]


class ListService:
    def __init__(self, session: Session):
        self.session = session
        self.search = SearchService(session)

    def create_list(self, name: str, owner_id: str | None = None) -> ShoppingList:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("O nome da lista é obrigatório.")
        row = ShoppingList(name=cleaned, owner_id=owner_id, status="ativa")
        self.session.add(row)
        self.session.flush()
        return row

    def list_active(self) -> list[ShoppingList]:
        stmt = (
            select(ShoppingList)
            .where(ShoppingList.status == "ativa")
            .order_by(ShoppingList.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def get(self, list_id: str) -> ShoppingList | None:
        return self.session.get(ShoppingList, list_id)

    def archive(self, list_id: str) -> ShoppingList:
        row = self._require_list(list_id)
        row.status = "arquivada"
        self.session.flush()
        return row

    def add_item(
        self,
        list_id: str,
        *,
        name: str,
        brand: str | None = None,
        category: str | None = None,
        quantity_value: float | None = None,
        quantity_unit: str | None = None,
        pack_count: int = 1,
        ean: str | None = None,
        quantity_desired: float = 1.0,
        notes: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> ListItem:
        shopping_list = self._require_list(list_id)
        if shopping_list.status != "ativa":
            raise ValueError("Só é possível adicionar itens a listas activas.")
        if not name.strip():
            raise ValueError("O nome do produto é obrigatório.")
        if quantity_desired <= 0:
            raise ValueError("A quantidade desejada deve ser positiva.")

        product = Product(
            name=name.strip(),
            brand=(brand.strip() if brand else None),
            category=(category.strip() if category else None),
            quantity_value=quantity_value,
            quantity_unit=quantity_unit,
            pack_count=pack_count or 1,
            ean=(ean.strip() if ean else None),
            attributes_json=attributes,
            notes=notes,
        )
        self.session.add(product)
        self.session.flush()

        item = ListItem(
            list_id=list_id,
            product_id=product.id,
            quantity_desired=float(quantity_desired),
            notes=notes,
            status="pendente",
        )
        self.session.add(item)
        self.session.flush()
        return item

    def remove_item(self, item_id: str) -> None:
        item = self.session.get(ListItem, item_id)
        if item is None:
            raise ValueError("Item não encontrado.")
        self.session.delete(item)
        self.session.flush()

    def items_for(self, list_id: str) -> list[tuple[ListItem, Product]]:
        self._require_list(list_id)
        items = list(
            self.session.scalars(select(ListItem).where(ListItem.list_id == list_id))
        )
        out: list[tuple[ListItem, Product]] = []
        for item in items:
            product = self.session.get(Product, item.product_id)
            if product:
                out.append((item, product))
        return out

    def compare_list(self, list_id: str, persist: bool = True) -> ComparedList:
        shopping_list = self._require_list(list_id)
        lines: list[ComparedListItem] = []
        errors: dict[str, str] = {}
        estimated_total = 0.0

        for item, product in self.items_for(list_id):
            canonical = ProductRef(
                name=product.name,
                brand=product.brand,
                ean=product.ean,
                quantity_value=product.quantity_value,
                quantity_unit=product.quantity_unit,
                pack_count=product.pack_count or 1,
                attributes=product.attributes_json,
            )
            try:
                result = self.search.search(
                    text=product.name,
                    ean=product.ean,
                    canonical=canonical,
                    persist=persist,
                )
                for market, err in result.errors.items():
                    errors[f"{product.id}:{market}"] = err

                available = [r for r in result.ranked if r.offer.available]
                pool = available or result.ranked
                best = pool[0] if pool else None
                if best and best.market_product_id:
                    item.selected_market_product_id = best.market_product_id
                    item.status = "comparado" if best.offer.available else "indisponivel"
                line_total = None
                if best and best.offer.available:
                    # custo estimado = preço final da embalagem × quantidade desejada
                    line_total = best.offer.price_final * item.quantity_desired
                    estimated_total += line_total
                lines.append(
                    ComparedListItem(
                        item=item,
                        product=product,
                        best=best,
                        alternatives=pool[:5],
                        estimated_line_total=line_total,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors[product.id] = str(exc)
                lines.append(
                    ComparedListItem(
                        item=item,
                        product=product,
                        best=None,
                        alternatives=[],
                        estimated_line_total=None,
                    )
                )

        self.session.flush()
        return ComparedList(
            shopping_list=shopping_list,
            lines=lines,
            estimated_total=estimated_total,
            errors=errors,
        )

    def selected_offer_label(self, item: ListItem) -> str | None:
        if not item.selected_market_product_id:
            return None
        mp = self.session.get(MarketProduct, item.selected_market_product_id)
        if not mp:
            return None
        return f"{mp.market_id}: {mp.name}"

    def _require_list(self, list_id: str) -> ShoppingList:
        row = self.session.get(ShoppingList, list_id)
        if row is None:
            raise ValueError("Lista não encontrada.")
        return row
