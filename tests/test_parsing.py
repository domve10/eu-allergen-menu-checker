from src.main import extract_recipes_from_html, parse_menu_text


def test_menu_colon_and_dash():
    menu = """# Starters
Moules-frites: mussels, white wine, butter - 24 €
Tiramisu - savoiardi, mascarpone, eggs
Bruschetta (bread, tomato, garlic) €7.50

Soup of the day"""
    d = parse_menu_text(menu)
    assert [x['name'] for x in d] == ['Moules-frites', 'Tiramisu', 'Bruschetta', 'Soup of the day']
    assert d[0]['ingredients'] == 'mussels, white wine, butter'
    assert d[1]['ingredients'] == 'savoiardi, mascarpone, eggs'
    assert d[2]['ingredients'] == 'bread, tomato, garlic'
    assert d[3]['ingredients'] == ''


def test_jsonld_graph():
    html = """<html><head><script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[{"@type":"WebPage","name":"x"},
     {"@type":["Recipe"],"name":"Pasta &amp; Ceci","recipeIngredient":["200 g pasta","1 can chickpeas","rosemary"]}]}
    </script></head></html>"""
    r = extract_recipes_from_html(html)
    assert r == [{'name': 'Pasta & Ceci', 'ingredients': ['200 g pasta', '1 can chickpeas', 'rosemary']}]


def test_jsonld_list_and_invalid_blocks():
    html = """<script type="application/ld+json">{not json}</script>
    <script type='application/ld+json'>[{"@type":"Organization"},{"@type":"Recipe","name":"Pancakes",
    "recipeIngredient":"flour, milk, eggs"}]</script>"""
    r = extract_recipes_from_html(html)
    assert r[0]['name'] == 'Pancakes'


def test_no_recipe():
    assert extract_recipes_from_html('<html><body>No recipe</body></html>') == []
