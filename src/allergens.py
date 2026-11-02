"""Rule-based detection of the 14 EU allergens (Regulation (EU) No 1169/2011, Annex II).

Pure Python, no external services. Text is normalised (lowercase, accents stripped,
punctuation -> spaces) and matched with word-boundary regular expressions built from
multilingual dictionaries (EN, IT, FR, NL, DE, ES).

Term syntax used in the dictionaries below:
    "egg"      -> whole word, with an optional English-style plural ("eggs", "eggs")
    "ei!"      -> whole word, exact (no plural suffix)
    "weizen*"  -> word starting with "weizen" (German/Dutch compounds: "weizenmehl")
    "*mehl"    -> word ending with "mehl" ("weizenmehl", "dinkelmehl")
    "*nuss*"   -> word containing "nuss" anywhere
Multi-word terms match across any whitespace.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable

DISCLAIMER = (
    'Automated draft based only on the ingredient text provided; not a legal allergen '
    'declaration. Verify against recipes and supplier specifications.'
)

LANGUAGES = ('en', 'it', 'fr', 'nl', 'de', 'es')

CONTAINS = 'contains'
CHECK = 'check'


# --------------------------------------------------------------------------------------
# Normalisation & pattern compilation
# --------------------------------------------------------------------------------------

_SPECIAL_CHARS = str.maketrans({'ß': 'ss', 'œ': 'oe', 'Œ': 'oe', 'æ': 'ae', 'Æ': 'ae', 'ø': 'o', 'Ø': 'o'})


def normalize(text: str) -> str:
    """Lowercase, strip accents, turn punctuation into spaces and collapse whitespace."""
    if not text:
        return ''
    text = text.translate(_SPECIAL_CHARS)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().translate(_SPECIAL_CHARS)
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _term_regex(term: str) -> str:
    term = term.strip()
    prefix = suffix = ''
    exact = False
    if term.startswith('*'):
        prefix, term = '[a-z]*', term[1:]
    if term.endswith('*'):
        suffix, term = '[a-z]*', term[:-1]
    elif term.endswith('!'):
        exact, term = True, term[:-1]
    if not suffix and not exact:
        suffix = '(?:s|es)?'
    body = r'\s+'.join(re.escape(part) for part in normalize(term).split())
    return rf'(?<![a-z0-9]){prefix}{body}{suffix}(?![a-z0-9])'


@lru_cache(maxsize=None)
def _compile(terms: tuple[str, ...]) -> re.Pattern[str] | None:
    if not terms:
        return None
    # Longer terms first so the most specific term is reported.
    ordered = sorted(set(terms), key=len, reverse=True)
    return re.compile('|'.join(f'(?:{_term_regex(t)})' for t in ordered))


def _mask(text: str, pattern: re.Pattern[str] | None) -> str:
    if pattern is None:
        return text
    return pattern.sub(lambda m: '#' * len(m.group(0)), text)


# --------------------------------------------------------------------------------------
# Allergen dictionaries
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Allergen:
    number: int
    id: str
    name: str
    short: str
    contains: dict[str, tuple[str, ...]]
    check: dict[str, tuple[str, ...]] = field(default_factory=dict)
    exclude: tuple[str, ...] = ()
    check_note: str = ''
    # Markers that, when present in the same ingredient, downgrade 'contains' to 'check'.
    free_markers: tuple[str, ...] = ()


_FLOUR_FREE = (
    'rice flour', 'corn flour', 'cornflour', 'maize flour', 'chickpea flour', 'gram flour', 'almond flour',
    'coconut flour', 'potato flour', 'tapioca flour', 'cassava flour', 'buckwheat flour', 'chestnut flour',
    'farina di riso', 'farina di mais', 'farina di ceci', 'farina di mandorle', 'farina di castagne',
    'farina di grano saraceno', 'farina di cocco', 'farina di patate',
    'farine de riz', 'farine de mais', 'farine de sarrasin', 'farine de pois chiches', 'farine de pois chiche',
    'farine d amande', 'farine d amandes', 'farine de chataigne', 'farine de coco',
    'rijstmeel', 'rijstebloem', 'maismeel', 'maizena', 'boekweitmeel', 'amandelmeel', 'kikkererwtenmeel',
    'aardappelmeel', 'reismehl', 'maismehl', 'buchweizenmehl', 'mandelmehl', 'kichererbsenmehl',
    'kartoffelmehl', 'kokosmehl', 'johannisbrotkernmehl', 'kastanienmehl',
    'harina de arroz', 'harina de maiz', 'harina de garbanzo', 'harina de almendra', 'harina de almendras',
    'harina de trigo sarraceno', 'harina de coco', 'harina de castana',
)

ALLERGENS: tuple[Allergen, ...] = (
    Allergen(
        1, 'gluten', 'Cereals containing gluten', 'Gluten',
        contains={
            'en': ('wheat', 'flour', 'bread', 'breadcrumb', 'bread crumb', 'panko', 'pasta', 'spaghetti', 'linguine',
                   'tagliatelle', 'fettuccine', 'pappardelle', 'penne', 'rigatoni', 'fusilli', 'farfalle', 'orecchiette',
                   'bucatini', 'paccheri', 'lasagne', 'lasagna', 'ravioli', 'tortellini', 'cannelloni', 'gnocchi',
                   'couscous', 'cous cous', 'bulgur', 'bulghur', 'barley', 'rye', 'oat', 'oatmeal', 'spelt',
                   'kamut', 'khorasan', 'farro', 'durum', 'semolina', 'seitan', 'malt', 'malted', 'beer', 'ale!',
                   'lager', 'stout', 'noodle', 'crouton', 'cracker', 'biscuit', 'cookie', 'cake', 'pastry',
                   'shortcrust', 'brioche', 'croissant', 'baguette', 'pizza', 'focaccia', 'pita', 'pitta', 'naan',
                   'crumble', 'roux', 'ladyfinger', 'lady finger', 'sponge', 'wafer', 'batter', 'tempura',
                   'dumpling', 'filo', 'phyllo', 'matzo', 'shortbread', 'gingerbread', 'flatbread', 'cornbread',
                   'sourdough', 'bun', 'muffin', 'scone', 'waffle', 'pancake', 'crepe', 'gluten', 'triticale',
                   'freekeh', 'emmer', 'einkorn', 'wholemeal', 'whole wheat', 'graham'),
            'it': ('frumento', 'grano', 'grano duro', 'farina', 'pane', 'pangrattato', 'pan grattato', 'semola',
                   'semolino', 'orzo', 'segale', 'avena', 'malto', 'birra', 'pasta sfoglia', 'pasta frolla',
                   'pasta brisee', 'biscotti', 'biscotto', 'savoiardi', 'savoiardo', 'crostini', 'crostino',
                   'grissini', 'piadina', 'pizzoccheri', 'tagliolini', 'maccheroni', 'vermicelli', 'bigoli',
                   'trofie', 'pici', 'strozzapreti', 'crespelle', 'panettone', 'pandoro', 'friselle', 'taralli',
                   'pastella', 'impanato', 'impanati', 'impanata'),
            'fr': ('ble!', 'bles!', 'farine', 'pain', 'chapelure', 'orge', 'seigle', 'avoine', 'epeautre', 'semoule',
                   'biere', 'pates!', 'pate feuilletee', 'pate brisee', 'pate sablee', 'pate a choux',
                   'pate a pizza', 'nouille', 'gaufre', 'galette', 'crepe', 'pain d epice', 'pain d epices',
                   'pain de mie', 'biscotte', 'boudoir'),
            'nl': ('tarwe*', 'bloem!', 'meel!', '*meel', 'brood', 'paneermeel', 'broodkruim*', 'gerst*', 'rogge*',
                   'haver*', 'spelt*', 'griesmeel', 'mout!', 'bier!', 'deeg!', 'bladerdeeg', 'koek', 'koekje',
                   'koekjes', 'beschuit', 'stokbrood', 'speculaas'),
            'de': ('weizen*', 'mehl!', '*mehl', '*brot', 'brot*', 'brotchen', 'paniermehl', 'semmelbrosel',
                   'gerste*', 'roggen*', 'hafer*', 'dinkel*', 'griess*', 'malz*', 'bier!', '*bier', '*nudel*',
                   '*teig', 'kekse', 'keks', 'spatzle', 'knodel', 'zwieback', 'lebkuchen', 'brezel', 'paniert'),
            'es': ('trigo', 'harina', 'pan!', 'panes!', 'pan rallado', 'cebada', 'centeno', 'avena', 'espelta',
                   'semola', 'malta', 'cerveza', 'fideo', 'fideos', 'galleta', 'galletas', 'hojaldre', 'rebozado',
                   'empanado', 'bizcocho', 'magdalena'),
        },
        check={
            'en': ('tortilla', 'fishcake', 'fish cake', 'sausage', 'gravy', 'granola', 'muesli', 'stock cube'),
            'it': ('dado', 'salsiccia'),
            'fr': ('saucisse', 'fond de veau'),
            'de': ('wurst', 'brueh*', 'bruh*'),
            'es': ('salchicha',),
        },
        exclude=(
            'buckwheat', 'grano saraceno', 'sarrasin', 'ble noir', 'boekweit*', 'buchweizen*', 'alforfon',
            'trigo sarraceno', 'rice noodle', 'rice noodles', 'rice vermicelli', 'glass noodle', 'glass noodles',
            'rice pasta', 'pasta di riso', 'corn tortilla', 'corn tortillas', 'rice cake', 'rice cakes',
            'reisnudel*', 'glasnudel*', 'pan fried', 'pan seared', 'pan roasted', 'pan juice', 'pan juices',
            'pan sauce', 'pan dulce', 'pasta di mandorle', 'pasta di nocciole', 'pasta di pistacchio',
            'pasta di acciughe', 'pasta d acciughe', 'pasta di olive', 'pasta di sesamo', 'pasta di arachidi',
            'pasta di zucchero', 'pasta di peperoncino', 'pasta de almendra', 'pasta de sesamo', 'pasta de dientes',
            'bloemkool', 'eetbare bloem*', 'gluten free', 'glutenfree', 'senza glutine', 'sans gluten', 'glutenvrij', 'glutenfrei', 'sin gluten', 'johannisbrot*', 'pate de campagne', 'grana padano', 'pain perdu',
            'sweet potato flour', 'cake pan', 'oyster cracker',
        ) + _FLOUR_FREE,
        check_note='Check the cereal source (wheat, rye, barley, oats, spelt, kamut) and supplier spec.',
        free_markers=('gluten free', 'senza glutine', 'sans gluten', 'glutenvrij', 'glutenfrei', 'sin gluten',
                      'glutenfri', 'gf!'),
    ),
    Allergen(
        2, 'crustaceans', 'Crustaceans', 'Crustaceans',
        contains={
            'en': ('crustacean', 'shrimp', 'prawn', 'lobster', 'langoustine', 'crab', 'crayfish', 'crawfish',
                   'scampi', 'krill', 'shrimp paste', 'bisque'),
            'it': ('crostacei', 'crostaceo', 'gambero', 'gamberi', 'gamberetto', 'gamberetti', 'gamberone',
                   'gamberoni', 'aragosta', 'aragoste', 'astice', 'astici', 'granchio', 'granchi', 'granseola',
                   'mazzancolla', 'mazzancolle', 'canocchia', 'canocchie', 'cicala di mare', 'cicale di mare'),
            'fr': ('crustace', 'crevette', 'homard', 'langouste', 'crabe', 'ecrevisse', 'gambas', 'tourteau',
                   'araignee de mer'),
            'nl': ('schaaldier*', 'garnaal', 'garnalen', 'kreeft', 'kreeften', 'krab', 'krabben', 'langoestine*',
                   'rivierkreeft*', 'noordzeekrab'),
            'de': ('krustentier*', 'garnele*', 'krabbe*', 'hummer*', 'languste*', 'kaisergranat', '*krebs', 'krebs*',
                   'shrimps', 'scampi'),
            'es': ('crustaceo', 'gamba', 'gambas', 'langostino', 'langostinos', 'camaron', 'camarones', 'langosta',
                   'bogavante', 'cangrejo', 'cigala', 'cigalas', 'quisquilla', 'centollo', 'necora', 'carabinero'),
        },
        check={
            'en': ('shellfish', 'seafood', 'surimi', 'kimchi', 'fish sauce', 'xo sauce'),
            'it': ('frutti di mare', 'frutto di mare'),
            'fr': ('fruits de mer', 'fruit de mer'),
            'nl': ('zeevruchten',),
            'de': ('meeresfrucht*',),
            'es': ('mariscos', 'marisco'),
        },
        exclude=('crab apple', 'crab apples', 'crabapple*'),
        check_note='Seafood mixes, surimi and some sauces may contain crustaceans.',
    ),
    Allergen(
        3, 'eggs', 'Eggs', 'Eggs',
        contains={
            'en': ('egg', 'egg yolk', 'yolk', 'egg white', 'albumen', 'albumin', 'meringue', 'eggnog', 'mayonnaise',
                   'mayo', 'aioli', 'hollandaise', 'bearnaise', 'custard', 'frittata', 'omelette', 'omelet',
                   'quiche', 'zabaglione', 'sabayon', 'carbonara'),
            'it': ('uovo', 'uova', 'tuorlo', 'tuorli', 'albume', 'albumi', 'maionese', 'meringa', 'meringhe',
                   'zabaione', 'crema pasticcera', 'pasta all uovo', 'frittata'),
            'fr': ('oeuf', 'jaune d oeuf', 'blanc d oeuf', 'mayonnaise', 'creme anglaise', 'creme patissiere'),
            'nl': ('ei!', 'eieren', 'eidooier*', 'eigeel', 'eierdooier', 'dooier*', 'eiwitten'),
            'de': ('ei!', 'eier*', 'eigelb', 'eidotter', 'eiklar', '*eier'),
            'es': ('huevo', 'huevos', 'yema', 'yemas', 'clara de huevo', 'claras de huevo', 'mayonesa', 'alioli',
                   'merengue', 'tortilla espanola', 'tortilla de patatas'),
        },
        check={
            'en': ('lecithin', 'fresh pasta', 'tempura', 'batter', 'brioche', 'gnocchi',
                   'surimi', 'nougat', 'remoulade', 'tartar sauce', 'tartare sauce', 'caesar dressing',
                   'ice cream', 'gelato', 'tagliatelle', 'fettuccine', 'pappardelle', 'tagliolini', 'ravioli',
                   'tortellini', 'lasagne', 'lasagna', 'cannelloni'),
            'nl': ('eiwit',),
            'de': ('eiweiss',),
            'fr': ('sauce tartare', 'remoulade'),
        },
        exclude=('eggplant', 'eggplants', 'egg plant', 'egg plants'),
        check_note='Fresh pasta, batters, glazes and some sauces often contain egg.',
        free_markers=('egg free', 'eggless', 'vegan', 'senza uova', 'sans oeuf', 'sans oeufs', 'zonder ei',
                      'ohne ei', 'sin huevo', 'plant based'),
    ),
    Allergen(
        4, 'fish', 'Fish', 'Fish',
        contains={
            'en': ('fish*', 'fish sauce', 'fishcake', 'anchovy', 'anchovies', 'tuna', 'salmon', 'cod', 'haddock',
                   'hake', 'sardine', 'mackerel', 'trout', 'sea bass', 'seabass', 'bass', 'sea bream', 'seabream',
                   'bream', 'sole', 'plaice', 'halibut', 'turbot', 'monkfish', 'swordfish', 'herring', 'pollock',
                   'pollack', 'tilapia', 'snapper', 'mullet', 'eel', 'caviar', 'roe', 'bottarga', 'colatura',
                   'garum', 'bonito', 'katsuobushi', 'dashi', 'catfish', 'dogfish', 'whitefish', 'kingfish',
                   'flatfish', 'skate', 'john dory', 'grouper', 'pike', 'perch', 'carp', 'zander', 'sprat', 'whiting',
                   'kipper', 'gravlax', 'lox', 'worcestershire', 'nam pla', 'nuoc mam', 'fumet', 'tonnato',
                   'smoked salmon', 'cuttlefish ink'),
            'it': ('pesce', 'pesci', 'acciuga', 'acciughe', 'alice', 'alici', 'tonno', 'salmone', 'merluzzo',
                   'baccala', 'stoccafisso', 'sardina', 'sardine', 'sgombro', 'trota', 'branzino', 'spigola', 'orata',
                   'sogliola', 'rombo', 'pesce spada', 'aringa', 'aringhe', 'nasello', 'rana pescatrice',
                   'coda di rospo', 'colatura di alici', 'cernia', 'dentice', 'triglia', 'triglie', 'ricciola',
                   'palamita', 'anguilla', 'pesce persico', 'luccio', 'bottarga'),
            'fr': ('poisson', 'anchois', 'thon', 'saumon', 'cabillaud', 'morue', 'maquereau', 'truite',
                   'loup de mer', 'dorade', 'daurade', 'turbot', 'lotte', 'espadon', 'hareng', 'colin', 'merlu',
                   'eglefin', 'raie', 'rouget', 'brochet', 'sandre', 'flétan', 'fletan', 'bar de ligne', 'sole meuniere'),
            'nl': ('vis!', 'vissen', '*vis!', 'vissaus', 'visfumet', 'ansjovis', 'tonijn', 'zalm', 'kabeljauw',
                   'makreel', 'forel', 'zeebaars', 'zeebrasem', 'zeetong', 'tarbot', 'zwaardvis', 'haring', 'schelvis',
                   'koolvis', 'paling', 'heilbot', 'stokvis', 'snoekbaars', 'wijting', 'rog'),
            'de': ('*fisch*', 'sardelle*', 'anchovis', 'lachs*', 'kabeljau', 'dorsch', 'makrele*', 'forelle*',
                   'barsch', 'seezunge*', 'steinbutt', 'hering*', 'seelachs', 'aal!', 'scholle', 'zander', 'hecht',
                   'karpfen', 'thunfisch*', 'rotbarsch', 'heilbutt'),
            'es': ('pescado', 'pescados', 'anchoa', 'anchoas', 'boqueron', 'boquerones', 'atun', 'salmon',
                   'bacalao', 'merluza', 'sardina', 'sardinas', 'caballa', 'trucha', 'lubina', 'dorada', 'lenguado',
                   'rodaballo', 'rape!', 'pez espada', 'arenque', 'mero', 'besugo', 'salmonete'),
        },
        check={
            'en': ('tapenade', 'caesar dressing', 'kimchi', 'seafood', 'surimi', 'xo sauce', 'puttanesca'),
            'it': ('frutti di mare', 'puttanesca'),
            'fr': ('fruits de mer', 'bouillabaisse'),
            'nl': ('zeevruchten',),
            'de': ('meeresfrucht*',),
            'es': ('mariscos',),
        },
        exclude=('shellfish', 'cuttlefish', 'jellyfish', 'crayfish', 'starfish', 'fish free', 'fishfree',
                 'tintenfisch*', '*fischer', 'sole proprietor', 'bass guitar',
                 'pike place', 'perch on', 'roe deer', 'alice springs'),
        check_note='Dressings and sauces (Caesar, tapenade, puttanesca) often contain anchovy.',
    ),
    Allergen(
        5, 'peanuts', 'Peanuts', 'Peanuts',
        contains={
            'en': ('peanut', 'peanut butter', 'peanut oil', 'groundnut', 'ground nut', 'monkey nut', 'arachis',
                   'satay'),
            'it': ('arachide', 'arachidi', 'burro di arachidi', 'noccioline americane', 'nocciolina americana'),
            'fr': ('arachide', 'cacahuete', 'cacahouete', 'beurre de cacahuete', 'beurre d arachide'),
            'nl': ('pinda*', 'aardnoot', 'aardnoten'),
            'de': ('erdnuss*', 'erdnusse*'),
            'es': ('cacahuete', 'cacahuetes', 'cacahuate', 'cacahuates', 'mani!', 'manies'),
        },
        check={
            'en': ('mole sauce', 'pad thai', 'gado gado'),
            'it': ('noccioline', 'nocciolina'),
        },
        check_note='Some Asian, African and Latin sauces/oils contain peanut.',
    ),
    Allergen(
        6, 'soybeans', 'Soybeans', 'Soy',
        contains={
            'en': ('soy', 'soya', 'soybean', 'soya bean', 'soy bean', 'soy sauce', 'tamari', 'tofu', 'tempeh',
                   'edamame', 'miso', 'natto', 'shoyu', 'soy lecithin', 'teriyaki', 'hoisin', 'yuba', 'tvp'),
            'it': ('soia', 'salsa di soia', 'lecitina di soia'),
            'fr': ('soja', 'sauce soja'),
            'nl': ('soja*',),
            'de': ('soja*', '*soja'),
            'es': ('soja', 'salsa de soja'),
        },
        check={
            'en': ('lecithin', 'oyster sauce', 'vegetable protein', 'chocolate', 'black bean sauce'),
            'it': ('lecitina', 'cioccolato'),
            'fr': ('lecithine', 'chocolat'),
            'nl': ('lecithine', 'chocolade'),
            'de': ('lecithin', 'schokolade'),
            'es': ('lecitina', 'chocolate'),
        },
        check_note='Lecithin (E322), chocolate and Asian sauces may be soy-based.',
    ),
    Allergen(
        7, 'milk', 'Milk', 'Milk',
        contains={
            'en': ('milk', 'butter', 'cream', 'cheese', 'yogurt', 'yoghurt', 'ghee', 'whey', 'casein', 'caseinate',
                   'lactose', 'buttermilk', 'mozzarella', 'parmesan', 'parmigiano', 'parmigiano reggiano', 'pecorino',
                   'grana padano', 'ricotta', 'mascarpone', 'gorgonzola', 'feta', 'cheddar', 'brie', 'camembert',
                   'emmental', 'emmentaler', 'gruyere', 'burrata', 'stracciatella', 'provolone', 'fontina',
                   'taleggio', 'scamorza', 'halloumi', 'paneer', 'creme fraiche', 'sour cream', 'ice cream', 'gelato',
                   'custard', 'bechamel', 'quark', 'kefir', 'skyr', 'comte', 'gouda', 'edam', 'raclette',
                   'reblochon', 'roquefort', 'stilton', 'manchego', 'asiago', 'caciocavallo', 'labneh', 'tzatziki',
                   'raita', 'hollandaise', 'bearnaise', 'buttercream', 'dulce de leche', 'curd', 'cottage cheese',
                   'cream cheese', 'mornay', 'alfredo', 'fondue', 'panna cotta', 'milk chocolate'),
            'it': ('latte', 'burro', 'panna', 'formaggio', 'formaggi', 'yogurt', 'besciamella', 'crema pasticcera',
                   'stracchino', 'crescenza', 'caciotta', 'fior di latte', 'latticini', 'siero di latte'),
            'fr': ('lait', 'beurre', 'creme', 'fromage', 'yaourt', 'lactoserum', 'petit lait', 'chantilly',
                   'creme anglaise', 'creme patissiere'),
            'nl': ('melk*', '*melk', 'boter', 'roomboter', 'room!', 'slagroom', 'zure room', 'kaas', '*kaas',
                   'karnemelk', 'zuivel', 'wei!', 'yoghurt', 'kwark'),
            'de': ('milch*', '*milch', 'butter*', '*butter', 'sahne*', '*sahne', 'kase*', '*kase', 'joghurt',
                   'quark', 'schmand', 'rahm*', '*rahm', 'molke', 'buttermilch', 'creme fraiche'),
            'es': ('leche', 'mantequilla', 'nata', 'queso', 'quesos', 'yogur', 'crema', 'requeson', 'suero de leche',
                   'bechamel'),
        },
        check={
            'en': ('chocolate', 'caramel', 'toffee', 'fudge', 'brioche', 'croissant', 'pesto', 'risotto',
                   'mashed potato', 'mash', 'nougat', 'puff pastry', 'shortcrust', 'ravioli', 'tortellini',
                   'pancake', 'crepe', 'batter', 'ragu', 'bolognese'),
            'it': ('cioccolato', 'caramello', 'pure', 'ragu'),
            'fr': ('chocolat', 'caramel', 'puree', 'pate feuilletee'),
            'nl': ('chocolade', 'karamel', 'bladerdeeg'),
            'de': ('schokolade', 'karamell', 'blatterteig'),
            'es': ('chocolate', 'caramelo', 'hojaldre'),
        },
        exclude=(
            'cream of tartar', 'creme de cassis', 'creme de menthe', 'creme de cacao', 'creme de mure',
            'butter bean', 'butter beans', 'butter lettuce', 'butterhead', 'butternut*', 'peanut butter',
            'nut butter', 'almond butter', 'cashew butter', 'cocoa butter', 'cacao butter', 'shea butter',
            'apple butter', 'beurre de cacao', 'burro di cacao', 'cacaoboter', 'kakaobutter', 'manteca de cacao',
            'room temperature', 'room temp', 'living room', 'mushroom*',
            'coconut milk', 'coconut cream', 'coconut yogurt', 'coconut yoghurt', 'coconut butter',
            'almond milk', 'oat milk', 'soy milk', 'soya milk', 'rice milk', 'cashew milk', 'hazelnut milk',
            'soy yogurt', 'soya yogurt', 'soy cream', 'oat cream', 'soy cheese', 'vegan cheese', 'vegan butter',
            'latte di cocco', 'latte di mandorla', 'latte di mandorle', 'latte di soia', 'latte di avena',
            'latte di riso', 'panna di soia', 'panna vegetale', 'lait de coco', 'lait d amande', 'lait de soja',
            'lait d avoine', 'lait de riz', 'creme de coco', 'creme de soja', 'kokosmelk', 'amandelmelk',
            'sojamelk', 'havermelk', 'rijstmelk', 'kokosmilch', 'mandelmilch', 'sojamilch', 'hafermilch',
            'reismilch', 'kokosnussmilch', 'sojasahne', 'hafersahne', 'leche de coco', 'leche de almendra',
            'leche de almendras', 'leche de soja', 'leche de avena', 'leche de arroz', 'crema de coco',
            'crema di balsamico', 'crema balsamica', 'crema de balsamico', 'creme de balsamique',
            'pindakaas', 'erdnussbutter', 'butterfly', 'butterflied',
            'milk thistle', 'kokosrahm', 'zuurkool',
        ),
        check_note='Chocolate, caramel, mash, risotto and pastry are often made with milk or butter.',
        free_markers=('dairy free', 'vegan', 'plant based', 'senza lattosio e latte', 'sans produits laitiers',
                      'zuivelvrij', 'milchfrei', 'sin lacteos'),
    ),
    Allergen(
        8, 'nuts', 'Nuts (tree nuts)', 'Nuts',
        contains={
            'en': ('nut', 'mixed nuts', 'tree nut', 'almond', 'hazelnut', 'filbert', 'cobnut', 'walnut', 'cashew',
                   'pecan', 'brazil nut', 'pistachio', 'macadamia', 'queensland nut', 'marzipan', 'frangipane',
                   'praline', 'gianduja', 'gianduia', 'nutella', 'amaretti', 'orgeat', 'nut oil', 'walnut oil',
                   'romesco', 'dukkah', 'baklava', 'pralin', 'nougatine'),
            'it': ('mandorla', 'mandorle', 'nocciola', 'nocciole', 'noce', 'noci', 'anacardo', 'anacardi',
                   'pistacchio', 'pistacchi', 'noci pecan', 'noci del brasile', 'noci di macadamia', 'marzapane',
                   'frutta secca', 'frutta a guscio', 'granella di nocciole', 'pasta di mandorle'),
            'fr': ('amande', 'noisette', 'noix', 'cajou', 'noix de cajou', 'pistache', 'noix de pecan',
                   'noix du bresil', 'massepain', 'praline', 'fruits a coque', 'fruits secs'),
            'nl': ('*noot', '*noten', 'noot', 'noten', 'amandel*', 'hazelnoot*', 'walnoot*', 'cashew*', 'pistache*',
                   'pecannoot*', 'paranoot*', 'marsepein', 'notenpasta'),
            'de': ('*nuss*', '*nusse*', 'mandel*', 'pistazie*', 'cashew*', 'pekannuss*', 'paranuss*', 'macadamia*',
                   'marzipan', 'krokant'),
            'es': ('almendra', 'almendras', 'avellana', 'avellanas', 'nuez', 'nueces', 'anacardo', 'anacardos',
                   'pistacho', 'pistachos', 'pacana', 'pacanas', 'nuez de brasil', 'nuez del brasil', 'mazapan',
                   'frutos secos'),
        },
        check={
            'en': ('coconut', 'pine nut', 'pine kernel', 'chestnut', 'nougat', 'amaretto', 'pesto', 'granola',
                   'muesli', 'chocolate'),
            'it': ('cocco', 'noce di cocco', 'pinoli', 'pinolo', 'castagna', 'castagne', 'marroni', 'torrone',
                   'noccioline', 'nocciolina', 'amaretto'),
            'fr': ('coco!', 'noix de coco', 'pignon', 'pignons de pin', 'chataigne', 'marron glace', 'nougat'),
            'nl': ('kokos*', 'kokosnoot', 'pijnboompit*', 'kastanje*'),
            'de': ('kokos*', 'kokosnuss*', 'pinienkern*', 'marone*', 'esskastanie*', 'kastanie*'),
            'es': ('coco!', 'pinon', 'pinones', 'castana', 'castanas', 'turron'),
        },
        exclude=(
            'nutmeg', 'noce moscata', 'noix de muscade', 'nootmuskaat', 'muskatnuss*', 'nuez moscada',
            'butternut*', 'water chestnut*', 'tiger nut*', 'kola nut*', 'betel nut*', 'doughnut*', 'donut*',
            'peanut*', 'ground nut*', 'groundnut*', 'monkey nut*', 'erdnuss*', 'pindanoot*', 'pindanoten',
            'aardnoot', 'aardnoten', 'nut free', 'nut-free', 'noce di burro', 'noix de beurre', 'noce di vitello',
            'noix de veau', 'beurre noisette', 'pommes noisette', 'noix de saint jacques', 'noix st jacques',
            'noccioline americane', 'nocciolina americana',
        ),
        check_note=('Only almonds, hazelnuts, walnuts, cashews, pecans, Brazil nuts, pistachios and macadamia '
                    'are Annex II nuts; coconut, pine nuts and chestnuts are not, but verify for allergic guests.'),
        free_markers=('nut free', 'senza frutta a guscio', 'sans fruits a coque', 'notenvrij', 'nussfrei',
                      'sin frutos secos'),
    ),
    Allergen(
        9, 'celery', 'Celery', 'Celery',
        contains={
            'en': ('celery', 'celeriac', 'celery salt', 'celery seed', 'soffritto', 'mirepoix'),
            'it': ('sedano', 'sedano rapa', 'battuto'),
            'fr': ('celeri', 'celeri rave', 'celeri branche'),
            'nl': ('*selder*', 'selder*'),
            'de': ('*sellerie*', 'suppengrun'),
            'es': ('apio', 'apionabo'),
        },
        check={
            'en': ('stock', 'broth', 'bouillon', 'stock cube', 'consomme', 'gravy', 'curry powder', 'bloody mary',
                   'ragu', 'bolognese', 'bisque', 'fumet', 'court bouillon', 'vegetable stock', 'demi glace', 'jus!'),
            'it': ('brodo', 'dado', 'ragu', 'fondo bruno'),
            'fr': ('fond', 'fond blanc', 'fond brun', 'fond de veau', 'bouillon', 'fumet'),
            'nl': ('bouillon', 'fond', 'soepgroente*', 'soep'),
            'de': ('bruhe', '*bruhe', 'fond', 'suppe'),
            'es': ('caldo', 'fondo', 'pastilla de caldo'),
        },
        exclude=('stock pot', 'stockpot', 'in stock', 'out of stock', 'fondue', 'fondant'),
        check_note='Stocks, broths, bouillon cubes, soups and spice mixes frequently contain celery.',
    ),
    Allergen(
        10, 'mustard', 'Mustard', 'Mustard',
        contains={
            'en': ('mustard', 'mustard seed', 'dijon', 'wholegrain mustard', 'piccalilli', 'honey mustard'),
            'it': ('senape', 'mostarda'),
            'fr': ('moutarde', 'moutarde de dijon'),
            'nl': ('mosterd*',),
            'de': ('*senf*',),
            'es': ('mostaza',),
        },
        check={
            'en': ('mayonnaise', 'mayo', 'aioli', 'vinaigrette', 'remoulade', 'curry powder', 'tartar sauce',
                   'tartare sauce', 'dressing', 'honey dressing', 'ketchup', 'pickle', 'pickles', 'salad cream'),
            'it': ('maionese',),
            'fr': ('vinaigrette', 'remoulade', 'sauce tartare'),
            'es': ('mayonesa', 'alioli'),
            'de': ('mayonnaise',),
            'nl': ('mayonaise',),
        },
        check_note='Mayonnaise, dressings, vinaigrettes and spice blends often contain mustard.',
    ),
    Allergen(
        11, 'sesame', 'Sesame seeds', 'Sesame',
        contains={
            'en': ('sesam*', 'tahini', 'tahina', 'gomasio', 'hummus', 'houmous', 'baba ganoush', 'baba ghanoush',
                   'benne seed', 'sesame oil'),
            'it': ('sesamo', 'tahina'),
            'fr': ('sesame', 'houmous'),
            'nl': ('sesam*',),
            'de': ('sesam*',),
            'es': ('sesamo', 'ajonjoli'),
        },
        check={
            'en': ('za atar', 'zaatar', 'dukkah', 'halva', 'halvah', 'furikake', 'hoisin', 'everything bagel'),
            'it': ('halva',),
        },
        check_note="Za'atar, halva, dukkah and some Asian sauces contain sesame.",
    ),
    Allergen(
        12, 'sulphites', 'Sulphur dioxide and sulphites', 'Sulphites',
        contains={
            'en': ('sulphite', 'sulfite', 'sulphur dioxide', 'sulfur dioxide', 'metabisulphite', 'metabisulfite',
                   'bisulphite', 'bisulfite', 'e220!', 'e221!', 'e222!', 'e223!', 'e224!', 'e226!', 'e227!', 'e228!',
                   'e 220!', 'e 221!', 'e 222!', 'e 223!', 'e 224!', 'e 226!', 'e 227!', 'e 228!'),
            'it': ('solfiti', 'solfito', 'anidride solforosa', 'metabisolfito'),
            'fr': ('sulfite', 'anhydride sulfureux', 'dioxyde de soufre'),
            'nl': ('sulfiet', 'sulfieten', 'zwaveldioxide'),
            'de': ('sulfit', 'sulfite', 'schwefeldioxid', 'geschwefelt'),
            'es': ('sulfitos', 'sulfito', 'dioxido de azufre', 'anhidrido sulfuroso'),
        },
        check={
            'en': ('wine', 'white wine', 'red wine', 'vinegar', 'balsamic', 'dried fruit', 'dried apricot',
                   'raisin', 'sultana', 'currant', 'prune', 'dried fig', 'dried figs', 'port!', 'sherry', 'marsala',
                   'vermouth', 'cider', 'beer', 'champagne', 'prosecco', 'pickle', 'gherkin', 'caper', 'cornichon',
                   'madeira', 'cognac', 'brandy', 'sausage', 'worcestershire', 'vinaigrette', 'lemon juice from concentrate',
                   'candied peel', 'glace cherr*', 'dried mango', 'dried cranberr*'),
            'it': ('vino', 'vini', 'aceto', 'aceto balsamico', 'uvetta', 'uva passa', 'uva sultanina',
                   'albicocche secche', 'prugne secche', 'fichi secchi', 'vin santo', 'vermut', 'capperi', 'cappero',
                   'canditi', 'sottaceti', 'frutta candita', 'spumante'),
            'fr': ('vin', 'vinaigre', 'raisins secs', 'abricots secs', 'pruneau', 'pruneaux', 'cidre', 'porto',
                   'xeres', 'cornichon', 'capre', 'fruits confits', 'cremant'),
            'nl': ('wijn*', '*wijn', 'azijn*', '*azijn', 'rozijn*', 'krent*', 'gedroogde', 'augurk*', 'kappertjes'),
            'de': ('wein!', '*wein', 'weisswein', 'rotwein', 'weinessig', 'essig*', '*essig', 'rosine*',
                   'sultanine*', 'trockenobst', 'trockenfrucht*', 'kapern', 'gewurzgurke*', 'sekt'),
            'es': ('vino', 'vinagre', 'pasas', 'uvas pasas', 'orejones', 'ciruelas pasas', 'jerez', 'alcaparras',
                   'pepinillos', 'cava!'),
        },
        exclude=('wine glass', 'port salut', 'weintraube*'),
        check_note='Wine, vinegar, dried fruit, pickles and some cured meats commonly contain sulphites (>10 mg/kg).',
    ),
    Allergen(
        13, 'lupin', 'Lupin', 'Lupin',
        contains={
            'en': ('lupin*', 'lupine flour', 'lupin flour'),
            'it': ('lupini', 'lupino', 'farina di lupino'),
            'fr': ('lupin', 'farine de lupin'),
            'nl': ('lupine*',),
            'de': ('lupine*', 'lupinen*', 'lupinenmehl'),
            'es': ('altramuz', 'altramuces', 'chocho', 'chochos'),
        },
        check_note='Lupin flour is sometimes used in gluten-free bakery products.',
    ),
    Allergen(
        14, 'molluscs', 'Molluscs', 'Molluscs',
        contains={
            'en': ('mollusc', 'mollusk', 'mussel', 'clam', 'oyster', 'scallop', 'squid', 'calamari', 'calamares',
                   'octopus', 'cuttlefish', 'snail', 'escargot', 'whelk', 'cockle', 'abalone', 'periwinkle',
                   'razor clam', 'oyster sauce', 'squid ink', 'cuttlefish ink', 'winkle'),
            'it': ('molluschi', 'mollusco', 'cozza', 'cozze', 'vongola', 'vongole', 'ostrica', 'ostriche',
                   'capasanta', 'capesante', 'cappasanta', 'cappesante', 'calamaro', 'calamari', 'polpo', 'polipo',
                   'polpi', 'seppia', 'seppie', 'moscardino', 'moscardini', 'lumaca', 'lumache', 'nero di seppia',
                   'telline', 'fasolari', 'datteri di mare', 'totano', 'totani', 'cannolicchi', 'murici',
                   'lumachine di mare'),
            'fr': ('mollusque', 'moule', 'palourde', 'huitre', 'coquille saint jacques', 'coquilles saint jacques',
                   'saint jacques', 'st jacques', 'noix de saint jacques', 'calmar', 'encornet', 'poulpe', 'seiche',
                   'escargot', 'bulot', 'coque', 'petoncle', 'praire', 'bigorneau', 'supion', 'chipiron'),
            'nl': ('weekdier*', 'mossel*', 'oester*', 'sint jakobsschelp*', 'jakobsschelp*', 'coquille*',
                   'inktvis*', 'pijlinktvis*', 'octopus*', 'slak', 'slakken', 'kokkel*', 'venusschelp*', 'alikruik*',
                   'wulk*', 'zeekat'),
            'de': ('weichtier*', '*muschel*', 'auster*', 'tintenfisch*', 'kalmar*', 'krake*', 'oktopus*', 'pulpo',
                   'sepia', 'schnecke*', '*schnecke', 'herzmuschel*', 'jakobsmuschel*'),
            'es': ('molusco', 'moluscos', 'mejillon', 'mejillones', 'almeja', 'almejas', 'ostra', 'ostras', 'vieira',
                   'vieiras', 'calamar', 'calamares', 'pulpo', 'sepia', 'chipiron', 'chipirones', 'caracol',
                   'caracoles', 'berberecho', 'berberechos', 'chirla', 'chirlas', 'zamburina', 'zamburinas',
                   'navaja', 'navajas', 'tinta de calamar', 'choco'),
        },
        check={
            'en': ('shellfish', 'seafood', 'xo sauce', 'paella'),
            'it': ('frutti di mare', 'frutto di mare'),
            'fr': ('fruits de mer', 'fruit de mer', 'couteau', 'couteaux'),
            'nl': ('zeevruchten', 'schelpdier*'),
            'de': ('meeresfrucht*',),
            'es': ('mariscos', 'marisco'),
        },
        exclude=('zimtschnecke*', 'nussschnecke*', 'puddingschnecke*', 'schneckennudel*', 'moule a gateau',
                 'moule a tarte', 'scalloped potato*', 'scalloped edge*',
                 'oyster mushroom*', 'pleurote', 'austernpilz*', 'oesterzwam*', 'coque de chocolat',
                 'oeuf a la coque', 'oeufs a la coque', 'a la coque', 'coquillettes'),
        check_note='Seafood mixes and some sauces (oyster sauce, XO) contain molluscs.',
    ),
)

ALLERGENS_BY_ID = {a.id: a for a in ALLERGENS}


# --------------------------------------------------------------------------------------
# Hidden allergen hints for compound ingredients (language-agnostic)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Hint:
    terms: tuple[str, ...]
    effects: tuple[tuple[str, str], ...]  # (allergen id, confidence)
    note: str


HINTS: tuple[Hint, ...] = (
    Hint(('pesto', 'pesto alla genovese', 'pesto genovese'), (('milk', CONTAINS), ('nuts', CHECK)),
         'Pesto: contains cheese (milk); traditional pine nuts are not an Annex II nut, but many pestos use '
         'cashews or walnuts - check the recipe/label.'),
    Hint(('worcestershire', 'worcester sauce', 'salsa worcester', 'sauce worcestershire'),
         (('fish', CONTAINS), ('gluten', CHECK), ('sulphites', CHECK)),
         'Worcestershire sauce contains anchovies (fish); malt vinegar may add gluten and sulphites.'),
    Hint(('stock', 'broth', 'bouillon', 'brodo', 'fond', 'fumet', 'caldo', 'bruhe', 'consomme', 'demi glace',
          'fondo bruno', 'fond de veau', 'soep'),
         (('celery', CHECK),),
         'Stock/broth/bouillon: verify celery in the stock or bouillon used.'),
    Hint(('stock cube', 'bouillon cube', 'dado', 'dado da brodo', 'cube de bouillon', 'bouillonblokje',
          'bruhwurfel', 'pastilla de caldo', 'avecrem'),
         (('celery', CHECK), ('gluten', CHECK)),
         'Stock cubes: frequently contain celery and wheat - check the label.'),
    Hint(('mayonnaise', 'mayo', 'maionese', 'mayonesa', 'mayonaise', 'aioli', 'alioli', 'remoulade',
          'tartar sauce', 'tartare sauce', 'sauce tartare'),
         (('eggs', CONTAINS), ('mustard', CHECK)),
         'Mayonnaise/aioli: contains egg; many recipes and commercial versions also contain mustard.'),
    Hint(('hollandaise', 'bearnaise', 'sauce hollandaise', 'sauce bearnaise'),
         (('eggs', CONTAINS), ('milk', CONTAINS), ('sulphites', CHECK)),
         'Hollandaise/bearnaise: egg yolks and butter; reduction may contain wine/vinegar (sulphites).'),
    Hint(('soy sauce', 'salsa di soia', 'sauce soja', 'sojasaus', 'sojasosse', 'salsa de soja', 'shoyu',
          'teriyaki'),
         (('soybeans', CONTAINS), ('gluten', CONTAINS)),
         'Soy sauce is usually brewed with wheat (gluten) unless labelled gluten-free tamari.'),
    Hint(('tamari', 'miso'), (('soybeans', CONTAINS), ('gluten', CHECK)),
         'Tamari/miso: soy; some varieties contain wheat or barley.'),
    Hint(('hoisin',), (('soybeans', CONTAINS), ('gluten', CHECK), ('sesame', CHECK)),
         'Hoisin sauce: soy-based; check wheat and sesame.'),
    Hint(('oyster sauce',), (('molluscs', CONTAINS), ('gluten', CHECK), ('soybeans', CHECK)),
         'Oyster sauce: molluscs; often contains wheat and soy.'),
    Hint(('fish sauce', 'nam pla', 'nuoc mam', 'colatura', 'colatura di alici', 'garum'),
         (('fish', CONTAINS), ('crustaceans', CHECK)),
         'Fish sauce: fish; some brands also contain shrimp.'),
    Hint(('caesar dressing', 'caesar sauce', 'caesar salad'),
         (('fish', CHECK), ('eggs', CONTAINS), ('milk', CONTAINS), ('mustard', CHECK)),
         'Caesar dressing: egg and parmesan; classic versions contain anchovy and mustard.'),
    Hint(('pasta', 'pates', 'spaghetti', 'linguine', 'penne', 'rigatoni', 'fusilli', 'noodle', 'noodles',
          'nudeln', 'fideos', 'nouilles'),
         (('gluten', CONTAINS), ('eggs', CHECK)),
         'Pasta/noodles: wheat (gluten); fresh and egg pasta also contain egg.'),
    Hint(('tagliatelle', 'fettuccine', 'pappardelle', 'tagliolini', 'lasagne', 'lasagna', 'cannelloni',
          'pasta all uovo', 'fresh pasta', 'egg pasta', 'egg noodles'),
         (('gluten', CONTAINS), ('eggs', CHECK)),
         'Egg pasta shapes are typically made with wheat flour and egg.'),
    Hint(('ravioli', 'tortellini', 'tortelloni', 'agnolotti', 'cappelletti'),
         (('gluten', CONTAINS), ('eggs', CHECK), ('milk', CHECK)),
         'Filled pasta: wheat + usually egg dough; fillings often contain cheese.'),
    Hint(('breadcrumbs', 'breadcrumb', 'bread crumbs', 'panko', 'pangrattato', 'chapelure', 'paneermeel',
          'paniermehl', 'pan rallado'),
         (('gluten', CONTAINS), ('milk', CHECK)),
         'Breadcrumbs: wheat (gluten); some contain milk.'),
    Hint(('bechamel', 'besciamella', 'white sauce', 'mornay'),
         (('milk', CONTAINS), ('gluten', CONTAINS)),
         'Bechamel: milk, butter and wheat-flour roux.'),
    Hint(('custard', 'crema pasticcera', 'creme patissiere', 'creme anglaise', 'zabaglione', 'zabaione',
          'sabayon'),
         (('milk', CONTAINS), ('eggs', CONTAINS)),
         'Custards/creams: milk and egg yolks.'),
    Hint(('ladyfinger', 'ladyfingers', 'lady fingers', 'savoiardi', 'boudoirs', 'biscuits a la cuillere'),
         (('gluten', CONTAINS), ('eggs', CONTAINS)),
         'Ladyfingers/savoiardi: wheat flour and eggs.'),
    Hint(('brioche',), (('gluten', CONTAINS), ('eggs', CONTAINS), ('milk', CONTAINS)),
         'Brioche: wheat, eggs and butter.'),
    Hint(('croissant', 'puff pastry', 'pasta sfoglia', 'pate feuilletee', 'bladerdeeg', 'blatterteig', 'hojaldre'),
         (('gluten', CONTAINS), ('milk', CHECK), ('eggs', CHECK)),
         'Laminated pastry: wheat; butter (milk) unless made with margarine; egg wash common.'),
    Hint(('shortcrust', 'pasta frolla', 'pate sablee', 'pate brisee', 'murbeteig'),
         (('gluten', CONTAINS), ('milk', CHECK), ('eggs', CHECK)),
         'Shortcrust: wheat and butter; sweet versions contain egg.'),
    Hint(('crepe', 'crepes', 'crespelle', 'pancake', 'pancakes', 'pfannkuchen', 'pannenkoek', 'batter',
          'pastella'),
         (('gluten', CONTAINS), ('eggs', CHECK), ('milk', CHECK)),
         'Batters/crepes: wheat flour, usually egg and milk.'),
    Hint(('tempura',), (('gluten', CONTAINS), ('eggs', CHECK)), 'Tempura batter: wheat flour, often egg.'),
    Hint(('gnocchi',), (('gluten', CONTAINS), ('eggs', CHECK)), 'Gnocchi: usually wheat flour, sometimes egg.'),
    Hint(('meringue', 'meringa', 'merengue'), (('eggs', CONTAINS),), 'Meringue: egg whites.'),
    Hint(('marzipan', 'marzapane', 'massepain', 'marsepein', 'mazapan', 'frangipane'),
         (('nuts', CONTAINS),), 'Marzipan/frangipane: almonds.'),
    Hint(('praline', 'pralin', 'gianduja', 'gianduia', 'nutella', 'nougatine', 'krokant'),
         (('nuts', CONTAINS), ('milk', CHECK)), 'Praline/gianduja: hazelnuts or almonds; often milk.'),
    Hint(('nougat', 'torrone', 'turron'), (('nuts', CHECK), ('eggs', CHECK), ('peanuts', CHECK)),
         'Nougat/torrone: usually almonds or hazelnuts and egg white; some contain peanuts.'),
    Hint(('amaretti', 'amaretto'), (('nuts', CHECK), ('eggs', CHECK)),
         'Amaretti/amaretto: almond or apricot kernel; amaretti contain egg white.'),
    Hint(('tahini', 'tahina', 'hummus', 'houmous', 'baba ganoush', 'baba ghanoush'), (('sesame', CONTAINS),),
         'Tahini/hummus: sesame paste.'),
    Hint(('satay', 'satay sauce'), (('peanuts', CONTAINS), ('soybeans', CHECK)), 'Satay: peanut sauce.'),
    Hint(('dashi', 'katsuobushi', 'bonito flakes'), (('fish', CONTAINS),), 'Dashi: bonito (fish) stock.'),
    Hint(('surimi', 'crab sticks', 'seafood sticks'),
         (('fish', CONTAINS), ('crustaceans', CHECK), ('eggs', CHECK), ('gluten', CHECK)),
         'Surimi: fish; often egg white, wheat starch and crab flavouring.'),
    Hint(('seafood', 'shellfish', 'frutti di mare', 'fruits de mer', 'zeevruchten', 'meeresfruchte',
          'mariscos'),
         (('crustaceans', CHECK), ('molluscs', CHECK)),
         'Seafood/shellfish: specify which species (crustaceans and/or molluscs).'),
    Hint(('soffritto', 'mirepoix', 'battuto', 'suppengrun', 'soepgroente'), (('celery', CONTAINS),),
         'Soffritto/mirepoix: onion, carrot and celery.'),
    Hint(('ragu', 'bolognese', 'ragu alla bolognese'),
         (('celery', CHECK), ('milk', CHECK), ('sulphites', CHECK)),
         'Ragu: soffritto (celery), often milk and wine.'),
    Hint(('curry powder', 'currypulver', 'poudre de curry', 'curry in polvere'),
         (('mustard', CHECK), ('celery', CHECK)), 'Curry powders may contain mustard and celery.'),
    Hint(('vinaigrette', 'salad dressing', 'dressing'), (('mustard', CHECK), ('sulphites', CHECK)),
         'Dressings/vinaigrettes: often mustard and vinegar (sulphites).'),
    Hint(('beer', 'birra', 'biere', 'bier', 'cerveza', 'ale!', 'lager', 'stout'),
         (('gluten', CONTAINS), ('sulphites', CHECK)), 'Beer: barley malt (gluten).'),
    Hint(('chocolate', 'cioccolato', 'chocolat', 'chocolade', 'schokolade'),
         (('milk', CHECK), ('soybeans', CHECK), ('nuts', CHECK)),
         'Chocolate: check milk, soy lecithin and nut traces on the label.'),
    Hint(('ice cream', 'gelato', 'glace'), (('milk', CONTAINS), ('eggs', CHECK)),
         'Ice cream/gelato: milk; custard bases contain egg.'),
    Hint(('granola', 'muesli'), (('gluten', CONTAINS), ('nuts', CHECK)), 'Granola/muesli: oats; often nuts.'),
    Hint(('sausage', 'salsiccia', 'saucisse', 'wurst', 'salchicha', 'worst'),
         (('gluten', CHECK), ('sulphites', CHECK), ('milk', CHECK), ('mustard', CHECK)),
         'Sausages may contain rusk/wheat, sulphites, milk powder or mustard.'),
    Hint(('gravy', 'jus!', 'demi glace'), (('gluten', CHECK), ('celery', CHECK), ('sulphites', CHECK)),
         'Gravy/jus: check flour, stock (celery) and wine.'),
    Hint(('lecithin', 'lecitina', 'lecithine', 'e322!'), (('soybeans', CHECK), ('eggs', CHECK)),
         'Lecithin (E322) is usually from soy or egg - check the source.'),
    Hint(('kimchi',), (('fish', CHECK), ('crustaceans', CHECK)), 'Kimchi often contains fish sauce or shrimp.'),
    Hint(('xo sauce',), (('crustaceans', CONTAINS), ('fish', CONTAINS), ('molluscs', CONTAINS)),
         'XO sauce: dried shrimp, scallop and fish.'),
    Hint(('tapenade',), (('fish', CHECK),), 'Tapenade often contains anchovies.'),
    Hint(('puttanesca',), (('fish', CHECK),), 'Puttanesca usually contains anchovies.'),
    Hint(('dukkah', 'za atar', 'zaatar'), (('sesame', CONTAINS), ('nuts', CHECK)),
         "Dukkah/za'atar: sesame; dukkah often contains hazelnuts."),
    Hint(('carbonara',), (('eggs', CONTAINS), ('milk', CONTAINS), ('gluten', CHECK)),
         'Carbonara: egg yolks and Pecorino/Parmigiano; served with wheat pasta.'),
    Hint(('tiramisu',), (('eggs', CONTAINS), ('milk', CONTAINS), ('gluten', CONTAINS)),
         'Tiramisu: mascarpone, eggs, savoiardi (wheat).'),
    Hint(('panna cotta',), (('milk', CONTAINS),), 'Panna cotta: cream (milk).'),
    Hint(('wine', 'vino', 'vin', 'wijn', 'wein!', 'marsala', 'sherry', 'vermouth', 'port!', 'porto', 'madeira'),
         (('sulphites', CHECK),), 'Wine and fortified wines almost always contain sulphites (>10 mg/l).'),
    Hint(('vinegar', 'aceto', 'vinaigre', 'azijn', 'essig', 'vinagre', 'balsamic'), (('sulphites', CHECK),),
         'Vinegar (esp. wine and balsamic vinegar) may contain sulphites.'),
    Hint(('dried fruit', 'dried apricot', 'dried apricots', 'raisin', 'raisins', 'sultana', 'sultanas',
          'uvetta', 'uva passa', 'raisins secs', 'rozijnen', 'rosinen', 'pasas', 'prunes', 'prugne secche',
          'albicocche secche', 'abricots secs', 'orejones', 'candied peel', 'canditi'),
         (('sulphites', CHECK),), 'Dried fruit is often preserved with sulphites.'),
)


# --------------------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------------------


def _terms(by_lang: dict[str, tuple[str, ...]], languages: tuple[str, ...]) -> tuple[str, ...]:
    out: list[str] = []
    for lang, terms in by_lang.items():
        if lang in languages:
            out.extend(terms)
    return tuple(out)


def resolve_languages(languages: Iterable[str] | None) -> tuple[str, ...]:
    """Return the dictionaries to use. English is always included; unknown codes are ignored."""
    if not languages:
        return LANGUAGES
    wanted = {str(l).strip().lower()[:2] for l in languages if str(l).strip()}
    wanted = {l for l in wanted if l in LANGUAGES}
    if not wanted:
        return LANGUAGES
    wanted.add('en')
    return tuple(l for l in LANGUAGES if l in wanted)


@dataclass
class _Hit:
    confidence: str
    contains_terms: list[str] = field(default_factory=list)
    check_terms: list[str] = field(default_factory=list)

    def add(self, term: str, confidence: str) -> None:
        bucket = self.contains_terms if confidence == CONTAINS else self.check_terms
        padded = f' {term} '
        if not any(padded in f' {t} ' for t in bucket):
            # Drop shorter terms that are part of the new, more specific one ("wine" vs "white wine").
            bucket[:] = [t for t in bucket if f' {t} ' not in padded]
            bucket.append(term)
        if confidence == CONTAINS:
            self.confidence = CONTAINS

    @property
    def terms(self) -> list[str]:
        return self.contains_terms if self.confidence == CONTAINS else self.check_terms


def split_ingredients(ingredients: str | list | tuple | None) -> list[str]:
    """Split an ingredient list (string or array) into individual ingredient strings.

    Commas/semicolons/newlines/bullets separate ingredients, except inside parentheses.
    """
    if ingredients is None:
        return []
    if isinstance(ingredients, (list, tuple)):
        items: list[str] = []
        for part in ingredients:
            if part is None:
                continue
            items.extend(split_ingredients(str(part)) if isinstance(part, str) and ('\n' in part) else [str(part)])
        return [i.strip() for i in items if i and str(i).strip()]
    text = str(ingredients)
    items, buf, depth = [], [], 0
    for ch in text:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth = max(0, depth - 1)
        if depth == 0 and ch in ',;\n•·|':
            items.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    items.append(''.join(buf))
    return [i.strip(' \t-*') for i in items if i.strip(' \t-*')]


def analyze_ingredients(
    ingredients: str | list | tuple | None,
    *,
    languages: Iterable[str] | None = None,
    name_only: str | None = None,
) -> dict:
    """Analyse ingredients and return allergens + checks.

    If no ingredients are given, ``name_only`` (the dish name) is analysed instead and every
    finding is downgraded to 'check'.
    """
    langs = resolve_languages(languages)
    items = split_ingredients(ingredients)
    checks: list[str] = []
    fallback = False
    if not items and name_only:
        items = [name_only]
        fallback = True
        checks.append('No ingredient list provided: analysis is based on the dish name only. '
                      'Provide ingredients for a reliable result.')

    hits: dict[str, _Hit] = {}

    def record(allergen_id: str, term: str, confidence: str) -> None:
        if fallback:
            confidence = CHECK
        hit = hits.get(allergen_id)
        if hit is None:
            hit = hits[allergen_id] = _Hit(confidence=confidence)
        hit.add(term, confidence)

    for raw in items:
        text = normalize(raw)
        if not text:
            continue
        for allergen in ALLERGENS:
            excl = _compile(allergen.exclude)
            check_pat = _compile(_terms(allergen.check, langs))
            contains_pat = _compile(_terms(allergen.contains, langs))
            free_pat = _compile(allergen.free_markers)
            base = _mask(text, excl)
            is_free = bool(free_pat and free_pat.search(text))
            found_contains = False
            if contains_pat is not None:
                # Check-only terms ("pine nuts", "coconut") are masked so they cannot trigger 'contains'.
                for m in contains_pat.finditer(_mask(base, check_pat)):
                    found_contains = True
                    record(allergen.id, m.group(0), CHECK if is_free else CONTAINS)
            if check_pat is not None:
                for m in check_pat.finditer(base):
                    term = m.group(0)
                    record(allergen.id, term, CHECK)
            if is_free and found_contains:
                checks.append(f'{allergen.short}: "{raw.strip()}" is labelled free-from - verify the product '
                              'specification and cross-contamination.')

        for hint in HINTS:
            pat = _compile(hint.terms)
            m = pat.search(text) if pat else None
            if not m:
                continue
            applied = False
            for allergen_id, confidence in hint.effects:
                allergen = ALLERGENS_BY_ID[allergen_id]
                excl = _compile(allergen.exclude)
                if excl is not None and excl.search(text) and not pat.search(_mask(text, excl)):
                    continue
                free_pat = _compile(allergen.free_markers)
                if free_pat and free_pat.search(text):
                    confidence = CHECK
                record(allergen_id, m.group(0), confidence)
                applied = True
            if applied and hint.note not in checks:
                checks.append(hint.note)

    allergens_out = []
    for allergen in ALLERGENS:
        hit = hits.get(allergen.id)
        if not hit:
            continue
        allergens_out.append({
            'number': allergen.number,
            'id': allergen.id,
            'name': allergen.name,
            'matchedTerms': hit.terms,
            'confidence': hit.confidence,
        })
        if hit.confidence == CHECK and allergen.check_note:
            note = f'{allergen.short} (check): matched {", ".join(repr(t) for t in hit.terms)}. {allergen.check_note}'
            checks.append(note)

    contains_names = [ALLERGENS_BY_ID[a['id']].short for a in allergens_out if a['confidence'] == CONTAINS]
    check_names = [ALLERGENS_BY_ID[a['id']].short for a in allergens_out if a['confidence'] == CHECK]
    line = 'Contains: ' + ', '.join(contains_names) if contains_names else \
        'Contains: none of the 14 EU allergens detected'
    return {
        'ingredientsAnalyzed': items,
        'allergens': allergens_out,
        'allergenCount': len(contains_names),
        'containsAllergens': contains_names,
        'checkAllergens': check_names,
        'euAllergenLine': line,
        'checks': _dedupe(checks),
        'disclaimer': DISCLAIMER,
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out
