"""EU Allergen Checker for Menus & Recipes - Apify Actor entry point."""

from __future__ import annotations

import html
import json
import re
from typing import Any

import httpx
from apify import Actor

from .allergens import analyze_ingredients

CHARGE_EVENT = 'dish-analyzed'
USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/126.0 Safari/537.36 (compatible; EU-Allergen-Checker/0.1; +https://apify.com)'
)

_PRICE_RE = re.compile(r'\s*(?:[€$£]\s*\d+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?\s*(?:€|eur|euro|usd|\$|£|gbp))\s*$', re.I)
_DASH_SPLIT_RE = re.compile(r'\s+[-–—|]\s+')
_JSONLD_RE = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S
)


# --------------------------------------------------------------------------------------
# Input parsing
# --------------------------------------------------------------------------------------


def parse_menu_text(menu_text: str) -> list[dict[str, Any]]:
    """Parse free menu text: one dish per line.

    Supported line formats: ``Dish: ing, ing``, ``Dish - ing, ing`` (also en/em dash or |),
    ``Dish (ing, ing)``. A line without a separator is treated as a dish name only.
    Blank lines and lines starting with ``#`` are ignored; trailing prices are stripped.
    """
    dishes = []
    for raw in (menu_text or '').splitlines():
        line = raw.strip().lstrip('•*·').strip()
        if not line or line.startswith('#'):
            continue
        line = _PRICE_RE.sub('', line).strip().rstrip(' -–—|').strip()
        name, ingredients = line, ''
        if ':' in line:
            name, ingredients = line.split(':', 1)
        else:
            parts = _DASH_SPLIT_RE.split(line, maxsplit=1)
            if len(parts) == 2:
                name, ingredients = parts
            else:
                m = re.match(r'^(.*?)\s*\((.+)\)\s*$', line)
                if m:
                    name, ingredients = m.group(1), m.group(2)
        name = name.strip(' .-–—')
        ingredients = _PRICE_RE.sub('', ingredients.strip()).strip(' .-–—|')
        if name:
            dishes.append({'name': name, 'ingredients': ingredients})
    return dishes


def _is_recipe(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    t = node.get('@type')
    types = t if isinstance(t, list) else [t]
    return any(isinstance(x, str) and x.split('/')[-1].lower() == 'recipe' for x in types)


def _walk(node: Any):
    if isinstance(node, list):
        for item in node:
            yield from _walk(item)
    elif isinstance(node, dict):
        yield node
        for key in ('@graph', 'mainEntity', 'mainEntityOfPage', 'itemListElement', 'item', 'hasPart'):
            if key in node:
                yield from _walk(node[key])


def extract_recipes_from_html(page_html: str) -> list[dict[str, Any]]:
    """Extract schema.org Recipe objects (name + recipeIngredient) from JSON-LD blocks."""
    recipes = []
    for block in _JSONLD_RE.findall(page_html or ''):
        block = block.strip()
        block = re.sub(r'^\s*(?:<!--|//\s*<!\[CDATA\[)|(?:-->|//\s*\]\]>)\s*$', '', block).strip()
        try:
            data = json.loads(block, strict=False)
        except json.JSONDecodeError:
            try:
                data = json.loads(html.unescape(block), strict=False)
            except json.JSONDecodeError:
                continue
        for node in _walk(data):
            if not _is_recipe(node):
                continue
            ingredients = node.get('recipeIngredient') or node.get('ingredients') or []
            if isinstance(ingredients, str):
                ingredients = [ingredients]
            ingredients = [html.unescape(re.sub(r'<[^>]+>', ' ', str(i))).strip() for i in ingredients if i]
            name = node.get('name') or node.get('headline') or 'Untitled recipe'
            if isinstance(name, list):
                name = name[0] if name else 'Untitled recipe'
            recipes.append({'name': html.unescape(str(name)).strip(), 'ingredients': ingredients})
    return recipes


def _normalise_dish(d: Any) -> dict[str, Any] | None:
    if isinstance(d, str):
        parsed = parse_menu_text(d)
        return parsed[0] if parsed else None
    if not isinstance(d, dict):
        return None
    name = str(d.get('name') or d.get('dishName') or '').strip()
    ingredients = d.get('ingredients', d.get('recipeIngredient', ''))
    if not name and not ingredients:
        return None
    return {'name': name or 'Unnamed dish', 'ingredients': ingredients}


# --------------------------------------------------------------------------------------
# Actor
# --------------------------------------------------------------------------------------


def build_item(dish: dict[str, Any], source: str, languages: list[str] | None) -> dict[str, Any]:
    result = analyze_ingredients(dish.get('ingredients'), languages=languages, name_only=dish.get('name'))
    return {'dishName': dish.get('name'), 'source': source, **result}


class ChargeLimitReached(Exception):
    pass


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        languages = actor_input.get('languages') or None
        dishes_in = actor_input.get('dishes') or []
        menu_text = actor_input.get('menuText') or ''
        recipe_urls = actor_input.get('recipeUrls') or []

        charging = Actor.get_charging_manager()
        stats = {'analyzed': 0, 'errors': 0}

        def limit_reached() -> bool:
            remaining = charging.calculate_max_event_charge_count_within_limit(CHARGE_EVENT)
            return remaining is not None and remaining <= 0

        async def emit(dish: dict[str, Any], source: str) -> None:
            if limit_reached():
                raise ChargeLimitReached
            await Actor.push_data(build_item(dish, source, languages))
            stats['analyzed'] += 1
            charge_result = await Actor.charge(event_name=CHARGE_EVENT, count=1)
            if charge_result.event_charge_limit_reached:
                raise ChargeLimitReached

        try:
            for d in dishes_in:
                dish = _normalise_dish(d)
                if dish:
                    await emit(dish, 'dishes')
                else:
                    Actor.log.warning(f'Skipping invalid dish entry: {d!r}')

            for dish in parse_menu_text(menu_text):
                await emit(dish, 'menuText')

            if recipe_urls:
                async with httpx.AsyncClient(
                    headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml'},
                    follow_redirects=True,
                    timeout=30,
                ) as client:
                    for entry in recipe_urls:
                        url = (entry.get('url') if isinstance(entry, dict) else str(entry or '')).strip()
                        if not url:
                            continue
                        recipes, error = [], None
                        try:
                            resp = await client.get(url)
                            resp.raise_for_status()
                            recipes = extract_recipes_from_html(resp.text)
                            if not recipes:
                                error = 'No schema.org Recipe (JSON-LD) found on the page.'
                        except httpx.HTTPError as exc:
                            error = f'Could not fetch page: {exc.__class__.__name__}: {exc}'
                        if error:
                            # Error items are informational and are NOT charged.
                            if limit_reached():
                                raise ChargeLimitReached
                            Actor.log.warning(f'{url}: {error}')
                            stats['errors'] += 1
                            await Actor.push_data({
                                'dishName': None, 'source': url, 'error': error, 'ingredientsAnalyzed': [],
                                'allergens': [], 'allergenCount': 0, 'containsAllergens': [],
                                'checkAllergens': [], 'euAllergenLine': None, 'checks': [], 'disclaimer': None,
                            })
                            continue
                        for recipe in recipes:
                            await emit(recipe, url)
        except ChargeLimitReached:
            Actor.log.warning(
                'The maximum total charge set for this run has been reached - stopping. '
                f'Dishes analysed: {stats["analyzed"]}. Increase the run\'s max charge to process more.'
            )

        if stats['analyzed'] == 0 and stats['errors'] == 0:
            Actor.log.warning('No dishes found in the input. Provide "dishes", "menuText" or "recipeUrls".')
        Actor.log.info(f'Done. Dishes analysed: {stats["analyzed"]}, URL errors: {stats["errors"]}.')
