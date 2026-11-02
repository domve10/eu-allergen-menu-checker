import pytest

from src.allergens import CHECK, CONTAINS, DISCLAIMER, analyze_ingredients, normalize, split_ingredients


def found(text, **kw):
    """Return {allergen_id: confidence}."""
    return {a['id']: a['confidence'] for a in analyze_ingredients(text, **kw)['allergens']}


def contains(text, **kw):
    return {k for k, v in found(text, **kw).items() if v == CONTAINS}


# ---- normalisation / splitting -------------------------------------------------------

def test_normalize_strips_accents_and_ligatures():
    assert normalize('Crème Fraîche, Œufs & Grieß') == 'creme fraiche oeufs griess'


def test_split_respects_parentheses():
    assert split_ingredients('flour (wheat, rye), eggs; milk') == ['flour (wheat, rye)', 'eggs', 'milk']


def test_split_array():
    assert split_ingredients(['a', ' b ', '']) == ['a', 'b']


# ---- tricky false positives ----------------------------------------------------------

def test_coconut_is_check_not_tree_nut():
    assert found('coconut') == {'nuts': CHECK}
    assert found('noix de coco') == {'nuts': CHECK}
    assert found('Kokosnuss') == {'nuts': CHECK}


def test_coconut_milk_is_not_milk():
    assert 'milk' not in found('coconut milk')
    assert 'milk' not in found('lait de coco')


@pytest.mark.parametrize('text', ['nutmeg', 'noce moscata', 'noix de muscade', 'Muskatnuss', 'nootmuskaat', 'nuez moscada'])
def test_nutmeg_is_not_a_nut(text):
    assert found(text) == {}


@pytest.mark.parametrize('text', ['buckwheat', 'grano saraceno', 'farine de sarrasin', 'Buchweizenmehl', 'boekweit'])
def test_buckwheat_is_not_gluten(text):
    assert 'gluten' not in found(text)


def test_peanut_does_not_trigger_tree_nuts():
    assert found('peanuts') == {'peanuts': CONTAINS}
    assert found('peanut butter') == {'peanuts': CONTAINS}
    assert found('Erdnüsse') == {'peanuts': CONTAINS}
    assert found('pindakaas') == {'peanuts': CONTAINS}


def test_butternut_squash_is_not_nuts():
    assert found('butternut squash') == {}


def test_cream_of_tartar_is_not_milk():
    assert found('cream of tartar') == {}


def test_eggplant_is_not_egg():
    assert found('eggplant') == {}
    assert found('grilled eggplants') == {}


def test_fishcake_is_fish():
    assert found('fishcake')['fish'] == CONTAINS
    assert found('fishcakes')['fish'] == CONTAINS


def test_pine_nuts_are_check_only():
    assert found('pine nuts') == {'nuts': CHECK}
    assert found('pinoli') == {'nuts': CHECK}


def test_chef_phrases_not_nuts():
    assert 'nuts' not in found('noce di burro')       # knob of butter
    assert 'nuts' not in found('beurre noisette')     # brown butter
    assert found('noix de Saint-Jacques') == {'molluscs': CONTAINS}


def test_pan_seared_not_gluten():
    assert found('pan-seared salmon') == {'fish': CONTAINS}


def test_room_temperature_not_milk():
    assert found('eggs at room temperature') == {'eggs': CONTAINS}


def test_moutarde_not_malt():
    assert 'gluten' not in found('moutarde')


def test_plain_ingredients_no_allergens():
    assert found('sea salt, extra virgin olive oil, garlic, tomato, basil') == {}


# ---- multilingual -------------------------------------------------------------------

def test_italian_basic():
    assert contains('farina 00, uova, burro') == {'gluten', 'eggs', 'milk'}


def test_french_basic():
    assert contains('crème fraîche, moutarde de Dijon') == {'milk', 'mustard'}


def test_dutch_shrimp():
    assert found('garnalen') == {'crustaceans': CONTAINS}


def test_german_celery():
    assert found('Sellerie') == {'celery': CONTAINS}
    assert found('Knollensellerie') == {'celery': CONTAINS}


def test_german_compounds():
    assert contains('Weizenmehl, Haselnüsse, Sahne, Senf') == {'gluten', 'nuts', 'milk', 'mustard'}


def test_spanish():
    assert contains('harina de trigo, huevos, leche, almendras, gambas') == {
        'gluten', 'eggs', 'milk', 'nuts', 'crustaceans'}


def test_spanish_rice_flour_not_gluten():
    assert 'gluten' not in found('harina de arroz')


def test_french_oeufs_ligature():
    assert found('Œufs') == {'eggs': CONTAINS}


def test_all_fourteen():
    text = ('wheat flour, prawns, eggs, anchovies, peanuts, soy sauce, milk, almonds, celery, mustard, '
            'sesame seeds, sodium metabisulphite, lupin flour, mussels')
    result = analyze_ingredients(text)
    assert [a['number'] for a in result['allergens']] == list(range(1, 15))
    assert all(a['confidence'] == CONTAINS for a in result['allergens'])


# ---- hidden allergen hints ----------------------------------------------------------

def test_pesto_hint():
    f = found('pesto')
    assert f['milk'] == CONTAINS and f['nuts'] == CHECK


def test_worcestershire_hint():
    assert found('Worcestershire sauce')['fish'] == CONTAINS


def test_stock_hint_is_celery_check():
    assert found('chicken stock') == {'celery': CHECK}
    assert found('brodo vegetale') == {'celery': CHECK}


def test_mayonnaise_hint():
    f = found('mayonnaise')
    assert f['eggs'] == CONTAINS and f['mustard'] == CHECK


def test_soy_sauce_hint():
    assert contains('soy sauce') == {'soybeans', 'gluten'}


def test_wine_vinegar_dried_fruit_sulphites_check():
    for t in ('white wine', 'balsamic vinegar', 'raisins', 'vino rosso', 'dried apricots'):
        assert found(t).get('sulphites') == CHECK, t


def test_pasta_hint():
    f = found('pasta')
    assert f['gluten'] == CONTAINS and f['eggs'] == CHECK


def test_breadcrumbs():
    assert found('breadcrumbs')['gluten'] == CONTAINS


def test_gluten_free_downgrades():
    assert found('gluten-free pasta')['gluten'] == CHECK


def test_vegan_mayo_downgrades_egg():
    assert found('vegan mayonnaise')['eggs'] == CHECK


# ---- output shape ------------------------------------------------------------------

def test_output_shape_and_line():
    r = analyze_ingredients('spaghetti, guanciale, egg yolks, Pecorino Romano, black pepper')
    assert r['euAllergenLine'] == 'Contains: Gluten, Eggs, Milk'
    assert r['allergenCount'] == 3
    assert r['disclaimer'] == DISCLAIMER
    eggs = next(a for a in r['allergens'] if a['id'] == 'eggs')
    assert eggs['matchedTerms'] == ['egg yolks'] and eggs['number'] == 3


def test_name_only_fallback_is_check():
    r = analyze_ingredients(None, name_only='Moules-frites')
    assert r['allergens'][0]['id'] == 'molluscs' and r['allergens'][0]['confidence'] == CHECK
    assert r['allergenCount'] == 0


def test_languages_restriction():
    assert found('garnalen', languages=['it']) == {}
    assert found('garnalen', languages=['nl']) == {'crustaceans': CONTAINS}
