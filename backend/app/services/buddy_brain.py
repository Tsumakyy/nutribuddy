"""Conversa do Buddy.

Trocas de alimentos são conduzidas por uma pequena máquina de estados
determinística (refeição → item → opções → confirmação) que usa o
`substitution_engine` para calcular porções equivalentes. O estado fica salvo
no payload da última mensagem do Buddy, então a confirmação aplica exatamente
a proposta que o paciente viu. O modelo de linguagem só entra no papo livre e
nunca altera o plano.
"""
import random
import re

from . import ollama_service
from .substitution_engine import (
    evaluate,
    find_equivalents,
    food_tokens,
    match_score,
    normalize,
    parse_grams,
    portion_label,
    qty_like,
    resolve_food,
    tokens,
    catalog,
    FOOD_KEYWORD_ALIASES,
)
from .nutrition_catalog import HEALTHY_SUBSTITUTES_BY_GROUP

MEAL_ORDER = (
    "cafe", "lanche1", "almoco", "lanche2", "jantar",
    "pre_treino", "pos_treino", "pre_atividade", "pos_atividade",
)
MEAL_LABELS = {
    "cafe": "café da manhã",
    "lanche1": "lanche da manhã",
    "almoco": "almoço",
    "lanche2": "lanche da tarde",
    "jantar": "jantar",
    "pre_treino": "pré-treino",
    "pos_treino": "pós-treino",
    "pre_atividade": "pré-atividade",
    "pos_atividade": "pós-atividade",
}
MEAL_PATTERNS = (
    (r"lanche da manha|colacao", "lanche1"),
    (r"lanche da tarde|cafe da tarde|lanchinho da tarde", "lanche2"),
    (r"cafe da manha|desjejum|\b(?:no|o|meu|do) cafe\b", "cafe"),
    (r"\balmoc\w*", "almoco"),
    (r"\bjant\w*", "jantar"),
    (r"pre treino|antes do treino", "pre_treino"),
    (r"pos treino|depois do treino", "pos_treino"),
    (r"pre atividade", "pre_atividade"),
    (r"pos atividade", "pos_atividade"),
)

SWAP_RE = re.compile(
    r"\b(troc\w*|substitu\w*|mud\w*|alter\w*|outra coisa|no lugar|em vez|ao inves|"
    r"nao quero|nao tenho|acabou|enjoei|cansei|nao (?:to|estou) a fim|sem vontade|"
    r"nao gosto|nao curto|variar|diferente)\b"
)
YES_RE = re.compile(
    r"^(sim|s|confirmo|confirma|pode|bora|vamos|manda ver|manda|fechado|fechou|beleza|blz|"
    r"ok|okay|claro|isso|show|perfeito|aceito|top|demorou|com certeza|uhum|aham|quero|"
    r"faz|faca|aplica|troca|pode ser|yes)\b"
)
NO_RE = re.compile(r"^(nao|n|nem|melhor nao|deixa|cancela\w*|esquece|desisto|nope)\b")
MORE_RE = re.compile(r"\b(outras?|mais opc\w*|nenhum\w*|nao gostei|tem mais|ver outras)\b")
# "não quero carne", "sem azeite", "acabou a banana": o que vem depois é o que SAI.
NEGATION_RE = re.compile(
    r"\b(?:nao (?:quero|tenho|gosto|curto|como|aguento|tem|to a fim|estou a fim)|sem|tira|tirar|tire|"
    r"acabou|odeio|detesto|enjoei|cansei)\b(.*)"
)
NEGATION_END_RE = re.compile(r"\b(?:por|pelo|pela|no lugar|em vez|ao inves|mas|prefiro|quero|queria)\b|[,;.!?]")
PREFER_RE = re.compile(r"\b(?:prefiro|preferia|queria|quero|gosto de|pode ser|que tal|tem|bora de|manda)\b(.*)")
# "troca a proteína do almoço" → item do grupo proteína.
GROUP_WORDS = {
    "proteina": "protein", "carne": "protein", "carboidrato": "carb", "carbo": "carb",
    "fruta": "fruit", "gordura": "fat", "verdura": "vegetable", "legume": "vegetable",
    "vegetal": "vegetable", "salada": "vegetable", "leguminosa": "legume", "grao": "legume",
}
NOT_FOOD_WORDS = set(GROUP_WORDS) | {
    "trocar", "troca", "troco", "mudar", "muda", "substituir", "substitui", "alterar", "variar",
    "primeira", "primeiro", "segunda", "segundo", "terceira", "terceiro", "opcoes", "opcao", "item", "itens",
    "quero", "queria", "prefiro", "gosto", "pode", "tal", "comer", "hoje", "mais", "menos", "isso", "essa",
    "esse", "outra", "outro", "opcao", "coisa", "agora", "algo", "melhor", "entao", "porque", "para",
    "tambem", "almoco", "jantar", "cafe", "manha", "tarde", "lanche", "treino", "refeicao", "prato",
    "favor", "obrigado", "obrigada", "nenhuma", "nenhum", "dessa", "desse", "dela", "dele", "bem",
    "muito", "pouco", "nada", "tudo", "sim", "nao", "comida", "alguma", "algum", "dia", "vez", "ver",
    "pouquinho", "bastante", "uma", "umas", "uns", "mesmo", "aqui", "lugar",
}
ORDINALS = {
    "1": 0, "primeira": 0, "primeiro": 0, "um": 0, "uma": 0,
    "2": 1, "segunda": 1, "segundo": 1, "dois": 1, "duas": 1,
    "3": 2, "terceira": 2, "terceiro": 2, "tres": 2,
    "4": 3, "quarta": 3, "quarto": 3, "quatro": 3,
}
CLINICAL_RE = re.compile(
    r"\b(alergi\w*|alergic\w*|intoleran\w*|dor|dores|tontura|tont[oa]|desmai\w*|enjoo|nausea\w*|"
    r"vomit\w*|gravid\w*|gestante|diabet\w*|insulina|remedio\w*|medicament\w*|pressao alta|"
    r"hipertens\w*|sangr\w*|laxante\w*|purga\w*|febre|diarreia)\b"
)
COMPENSATION_RE = re.compile(
    r"\b(compens\w*|cortar carbo\w*|corte carbo\w*|reduzir carbo\w*|menos carbo\w*|"
    r"pular (?:a |uma )?refeic\w*|ficar sem comer|jejum)\b"
)
MISSED_RE = re.compile(r"\bnao consegui seguir\b|\bsai do plano\b|\bfugi d[aoe]\b|\bjaquei\b")
CHANGE_CLAIM_RE = re.compile(r"\b(troquei|substitu[ií]|apliquei|alterei|atualizei|mudei)\b", re.IGNORECASE)

GROUP_ROLE = {
    "protein": "a proteína",
    "dairy_cheese": "o laticínio/recheio",
    "carb": "o carboidrato",
    "legume": "a leguminosa",
    "fruit": "a fruta",
    "fat": "a gordura boa",
    "dairy_drink": "o laticínio",
    "vegetable": "o vegetal",
}
GROUP_ROLE_OF = {
    "protein": "da proteína",
    "dairy_cheese": "do laticínio/recheio",
    "carb": "do carboidrato",
    "legume": "da leguminosa",
    "fruit": "da fruta",
    "fat": "da gordura boa",
    "dairy_drink": "do laticínio",
    "vegetable": "do vegetal",
}
PRIMARY_LABEL = {
    "protein_g": "a proteína", "carbs_g": "o carboidrato", "fat_g": "a gordura", "kcal": "as calorias",
}
PRIMARY_SHORT = {"protein_g": "P", "carbs_g": "C", "fat_g": "G"}
EMOJI_BY_TOKEN = {
    "frango": "🍗", "tilapia": "🐟", "salmao": "🐟", "atum": "🐟", "ovo": "🥚", "clara": "🥚",
    "patinho": "🥩", "alcatra": "🥩", "tofu": "🌱", "arroz": "🍚", "macarrao": "🍝",
    "batata": "🥔", "mandioca": "🥔", "pao": "🍞", "tapioca": "🫓", "aveia": "🥣",
    "cuscuz": "🌽", "quinoa": "🌾", "feijao": "🫘", "lentilha": "🫘", "grao": "🫘",
    "banana": "🍌", "mamao": "🍈", "maca": "🍎", "morango": "🍓", "laranja": "🍊", "melancia": "🍉",
    "pera": "🍐", "uva": "🍇", "abacate": "🥑", "azeite": "🫒", "amendoim": "🥜",
    "castanha": "🌰", "brocoli": "🥦", "cenoura": "🥕", "tomate": "🍅", "alface": "🥬",
    "queijo": "🧀", "ricota": "🧀", "cottage": "🧀", "leite": "🥛", "iogurte": "🥛",
}

# Restrições do perfil (objetivo cadastrado pelo nutricionista).
MEAT_WORDS = {"frango", "patinho", "alcatra", "carne", "tilapia", "salmao", "atum", "peixe", "bife", "boi", "file"}
ANIMAL_WORDS = MEAT_WORDS | {
    "ovo", "clara", "queijo", "ricota", "cottage", "requeijao", "mussarela", "leite", "iogurte", "whey",
}

_rng = random.Random()


def _pick(options: list[str]) -> str:
    return _rng.choice(options)


def _emoji(food_name: str) -> str:
    for tok in food_tokens(food_name) | set(tokens(food_name)):
        if tok in EMOJI_BY_TOKEN:
            return EMOJI_BY_TOKEN[tok]
    return "🍽️"


def _macro_line(values: dict) -> str:
    return (
        f"{values['kcal']:.0f} kcal · P {values['protein_g']:.0f}g · "
        f"C {values['carbs_g']:.0f}g · G {values['fat_g']:.0f}g"
    )


def _short_line(values: dict, primary: str) -> str:
    if primary in PRIMARY_SHORT:
        return f"{values['kcal']:.0f} kcal · {PRIMARY_SHORT[primary]} {values[primary]:.0f}g"
    return f"{values['kcal']:.0f} kcal"


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def _join(names: list[str]) -> str:
    names = [_lower_first(name) for name in names]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " e " + names[-1]


def _reply(message: str, state: dict | None = None, *, quick_replies=None,
           needs_nutritionist=False, awaiting=False, day_changes=None, ai_unavailable=False) -> dict:
    message = "\n".join(re.sub(r" {2,}", " ", line).strip() if not line.startswith("    ") else line
                        for line in message.split("\n"))
    message = re.sub(r"\n{3,}", "\n\n", message).strip()
    return {
        "message": message,
        "needs_nutritionist": needs_nutritionist,
        "awaiting_confirmation": awaiting,
        "day_changes": day_changes or [],
        "ai_unavailable": ai_unavailable,
        "quick_replies": quick_replies or [],
        "buddy_state": state or {},
    }


class _Turn:
    """Tudo o que o Buddy sabe sobre a mensagem atual."""

    def __init__(self, message: str, context: dict, state: dict | None):
        self.raw = message
        self.text = normalize(message)
        self.tokens = tokens(message)
        self.plan = {
            key: items for key, items in (context.get("effective_plan_for_today") or {}).items()
            if items
        }
        self.extra_foods = context.get("food_values") or {}
        goal = normalize(context.get("patient_goal_from_nutritionist") or "")
        if re.search(r"\bvegan", goal):
            self.restricted, self.restriction = set(ANIMAL_WORDS), "vegano"
        elif re.search(r"\bvegetarian", goal):
            self.restricted, self.restriction = set(MEAT_WORDS), "vegetariano"
        else:
            self.restricted, self.restriction = set(), ""
        self.state = dict(state or {})
        self.disliked = set(self.state.get("disliked", []))

        # Negação: termos negados nunca são o desejo do paciente.
        self.negated_text = ""
        match = NEGATION_RE.search(self.text)
        if match:
            self.negated_text = NEGATION_END_RE.split(match.group(1), maxsplit=1)[0]
        self.negated = set(tokens(self.negated_text))
        positive_text = self.text.replace(self.negated_text, " ") if self.negated_text else self.text
        self.positive = set(tokens(positive_text))
        self.negated_foods = self.foods_in(self.negated)
        # Mudou de ideia ("quero frango" depois de "não gosto de frango")
        self.disliked -= {tok for tok in self.positive if tok in _food_words()} - self.negated
        self.disliked |= _expand_food_words(self.negated)

    # ---------- memória curta ----------
    @property
    def avoid(self) -> set[str]:
        return self.disliked | self.restricted

    def negated_label(self) -> str:
        """Como o paciente chamou o que recusou: "ovo", e não "ovo cozido e ovo mexido"."""
        foods = self.negated_foods
        common = set.intersection(*(food_tokens(f["name"]) for f in foods)) if foods else set()
        if len(foods) > 1 and common:
            return sorted(common)[0]
        return _join([f["name"] for f in foods[:2]])

    def keep(self, **values) -> dict:
        new_state = {"disliked": sorted(self.disliked)}
        new_state.update(values)
        return new_state

    # ---------- interpretação ----------
    def meal_from_text(self, text: str | None = None) -> str | None:
        text = self.text if text is None else text
        for pattern, key in MEAL_PATTERNS:
            if re.search(pattern, text):
                return key
        if re.search(r"\blanche\b", text):
            snacks = [key for key in ("lanche1", "lanche2") if key in self.plan]
            if len(snacks) == 1:
                return snacks[0]
        return None

    def items_mentioned(self, meal_key: str, text_tokens: list[str]) -> list[int]:
        items = self.plan.get(meal_key, [])
        scored = [(match_score(item["food"], text_tokens), index) for index, item in enumerate(items)]
        best = max((score for score, _ in scored), default=0)
        if best:
            return [index for score, index in scored if score == best]
        groups = {GROUP_WORDS[tok] for tok in text_tokens if tok in GROUP_WORDS}
        if not groups:
            return []
        return [
            index for index, item in enumerate(items)
            if (food := resolve_food(item["food"], self.extra_foods)) and food["group"] in groups
        ]

    def catalog_mentioned(self, text_tokens: list[str], exclude: set[str]) -> list[dict]:
        scored = []
        for food in catalog():
            if normalize(food["name"]) in exclude:
                continue
            score = match_score(food["name"], text_tokens)
            if score:
                scored.append((score, food))
        best = max((score for score, _ in scored), default=0)
        return [food for score, food in scored if score == best]

    def foods_in(self, text_tokens) -> list[dict]:
        text_tokens = list(text_tokens)
        return self.catalog_mentioned(text_tokens, set()) if text_tokens else []

    def unknown_food_words(self) -> list[str]:
        """Palavras com cara de comida que não estão na tabela ("prefiro granola")."""
        match = PREFER_RE.search(self.text)
        if not match:
            return []
        words = [
            tok for tok in re.findall(r"[a-z]+", match.group(1))
            if len(tok) >= 4 and tok not in NOT_FOOD_WORDS and _singular_tok(tok) not in NOT_FOOD_WORDS
            and _singular_tok(tok) not in _food_words() and not SWAP_RE.search(tok)
            and not any(re.search(pattern, tok) for pattern, _ in MEAL_PATTERNS)
        ]
        return words[:2]

    def ordinal(self) -> int | None:
        if len(self.tokens) > 4:
            return None
        for tok in self.tokens:
            if tok in ORDINALS:
                return ORDINALS[tok]
        return None


def _singular_tok(tok: str) -> str:
    return tokens(tok)[0] if tokens(tok) else tok


_FOOD_WORDS: set[str] = set()


def _food_words() -> set[str]:
    if not _FOOD_WORDS:
        for food in catalog():
            _FOOD_WORDS.update(food_tokens(food["name"]))
        _FOOD_WORDS.update(FOOD_KEYWORD_ALIASES)
    return _FOOD_WORDS


def _expand_food_words(text_tokens) -> set[str]:
    words = {tok for tok in text_tokens if tok in _food_words()}
    for tok in list(words):
        words.update(FOOD_KEYWORD_ALIASES.get(tok, ()))
    return words


def _meal_list(turn: _Turn) -> str:
    return ", ".join(MEAL_LABELS[key] for key in MEAL_ORDER if key in turn.plan)


def _others_note(items: list[dict], target_index: int) -> str:
    others = [item["food"] for i, item in enumerate(items) if i != target_index]
    if not others:
        return ""
    return f"O resto do prato ({_join(others)}) fica igualzinho."


# ---------------------------------------------------------------- respostas

def _ask_meal(turn: _Turn, desired: list[str] | None = None) -> dict:
    if not turn.plan:
        return _reply(
            "Ainda não encontrei refeições no seu plano de hoje 🤔 "
            "Assim que seu nutricionista cadastrar, eu te ajudo com as trocas!",
            turn.keep(),
        )
    return _reply(
        _pick(["Bora! 🍽️", "Partiu variar! 🔄", "Deixa comigo! ✨"])
        + f" Qual refeição você quer mexer? Hoje tem: {_meal_list(turn)}.",
        turn.keep(stage="pick_meal", desired=desired or []),
        quick_replies=[MEAL_LABELS[key].capitalize() for key in MEAL_ORDER if key in turn.plan],
    )


def _ask_item(turn: _Turn, meal_key: str, intro: str | None = None) -> dict:
    items = turn.plan[meal_key]
    label = MEAL_LABELS[meal_key]
    listing = "\n".join(f"{i + 1}) {item['food']} — {item['qty']}" for i, item in enumerate(items))
    intro = intro or _pick([
        f"Bora dar um tapa no {label}! ✨",
        f"Missão {label} novo aceita! 🕵️",
        f"Partiu variar o {label}! 🔄",
    ])
    return _reply(
        f"{intro} Ele tá assim hoje:\n\n{listing}\n\n"
        "Qual item você quer trocar? Manda o número, o nome, ou só me diz o que tá com vontade "
        "de comer que eu calculo a porção certinha 😋",
        turn.keep(stage="pick_item", meal_key=meal_key),
        quick_replies=[item["food"] for item in items][:4],
    )


def _cannot_calculate(turn: _Turn, meal_key: str, item: dict, unknown_food: bool) -> dict:
    if unknown_food:
        reason = f"ainda não tenho os dados nutricionais de {_lower_first(item['food'])} na minha tabela"
    else:
        reason = f"{_lower_first(item['food'])} tá numa medida caseira ({item['qty']}) e não em gramas"
    others = [i["food"] for i in turn.plan[meal_key] if i is not item]
    tip = f" Se quiser, troco outro item: {_join(others)}." if others else ""
    return _reply(
        f"Ih, {reason}, então não consigo garantir uma troca equivalente 😕{tip} "
        "Pra esse, vale confirmar com seu nutri.",
        turn.keep(stage="pick_item", meal_key=meal_key),
        needs_nutritionist=True,
    )


def _target_info(turn: _Turn, meal_key: str, index: int):
    item = turn.plan[meal_key][index]
    original = resolve_food(item["food"], turn.extra_foods)
    grams = parse_grams(item["qty"])
    return item, original, grams


def _offer_options(turn: _Turn, meal_key: str, index: int, intro: str = "",
                   shown: list[str] | None = None) -> dict:
    item, original, grams = _target_info(turn, meal_key, index)
    if not original or not grams:
        return _cannot_calculate(turn, meal_key, item, unknown_food=not original)

    meal_items = turn.plan[meal_key]
    exclude = {i["food"] for i in meal_items} | set(shown or [])
    options = find_equivalents(original, grams, meal_key, exclude, turn.avoid)
    exhausted = False
    if not options and shown:
        exhausted = True
        shown = []
        options = find_equivalents(original, grams, meal_key, {i["food"] for i in meal_items}, turn.avoid)
    if not options:
        no_oil = " sem azeite" if "azeite" in turn.disliked else ""
        return _reply(
            f"{intro + ' ' if intro else ''}Procurei bastante, mas não achei uma troca{no_oil} pra "
            f"{_lower_first(item['food'])} que mantenha calorias e macros parecidos 😕 "
            f"Se der, mantém {_lower_first(item['food'])} hoje — ou vale ver outras opções com seu nutri!",
            turn.keep(),
            needs_nutritionist=True,
        )

    primary = options[0]["primary"]
    listing = "\n".join(
        f"{n + 1}) {_emoji(opt['food'])} {opt['food']} — {portion_label(opt['food'], opt['grams'])}"
        + (f" + azeite {opt['extra']['grams']}g" if opt.get("extra") else "")
        + f" · {_short_line(opt['totals'], primary)}"
        for n, opt in enumerate(options)
    )
    intro = intro or _pick([
        "Bora variar! 🔄", "Missão troca aceita! 🕵️", "Deixa comigo! ✨", "Partiu cardápio novo! 🍽️",
    ])
    primary_text = "as calorias" if primary == "kcal" else f"as calorias e {PRIMARY_LABEL[primary]}"
    if exhausted:
        message = (
            f"Pra manter tudo equilibrado, essas são as únicas trocas que fecham a conta pra "
            f"{_lower_first(item['food'])} 😅\n\n{listing}\n\n"
            f"Se nenhuma agradar, tudo bem manter {_lower_first(item['food'])} hoje!"
        )
    else:
        message = (
        f"{intro} Pra substituir {_lower_first(item['food'])} ({item['qty']}) no {MEAL_LABELS[meal_key]}, "
        f"separei opções que batem {primary_text}:\n\n{listing}\n\n"
        f"📌 Original: {_short_line(options[0]['original_totals'], primary)}\n"
        f"{_others_note(meal_items, index)} Qual vai ser? 😄"
        )
    return _reply(
        message,
        turn.keep(
            stage="pick_option", meal_key=meal_key, index=index, target_food=item["food"],
            options=[opt["food"] for opt in options],
            shown=sorted(set(shown or []) | {opt["food"] for opt in options}),
        ),
        quick_replies=[opt["food"] for opt in options] + ["Outras opções"],
    )


def _propose(turn: _Turn, meal_key: str, index: int, result: dict, intro: str | None = None) -> dict:
    item = turn.plan[meal_key][index]
    new_items = [dict(food=i["food"], qty=i["qty"]) for i in turn.plan[meal_key]]
    new_items[index] = {"food": result["food"], "qty": qty_like(item["qty"], result["grams"])}
    extra = result.get("extra")
    extra_line = ""
    if extra:
        _add_extra(new_items, index, extra, item["qty"])
        extra_line = (
            f"\n✅ + {extra['food']} — {extra['grams']}g "
            f"(repõe a gordurinha boa {_of(item['food'])})"
        )
    name = result["food"]
    reaction = intro or _pick([
        f"{name}? Escolha de campeão! {_emoji(name)}",
        f"Hmm, {_lower_first(name)}… já tô com fome só de pensar {_emoji(name)}",
        f"Anotado: {_lower_first(name)} na área! {_emoji(name)}",
        f"Boa! {name} combina demais com esse prato {_emoji(name)}",
    ])
    fit = (
        "Praticamente gêmeos nutricionais! 👯"
        if result["kcal_diff"] <= 0.05
        else "Diferencinha mínima, dentro do esperado 👌"
    )
    message = (
        f"{reaction}\n\nFicaria assim no {MEAL_LABELS[meal_key]} de hoje:\n"
        f"❌ {item['food']} — {item['qty']}\n    {_macro_line(result['original_totals'])}\n"
        f"✅ {name} — {portion_label(name, result['grams'])}{extra_line}\n    {_macro_line(result['totals'])}\n\n"
        f"{fit} {_others_note(turn.plan[meal_key], index)}\n\n"
        "Fecho essa troca só pra hoje? O plano do seu nutri continua igualzinho 😉"
    )
    return _reply(
        message,
        turn.keep(
            stage="confirm", meal_key=meal_key, index=index, target_food=item["food"],
            choice=name, items=new_items,
            options=turn.state.get("options", []), shown=turn.state.get("shown", []),
        ),
        quick_replies=["Sim, troca! ✅", "Ver outras opções", "Deixa como está"],
        awaiting=True,
    )


def _of(food_name: str) -> str:
    """"do ovo cozido" / "da tilápia grelhada" — aproximação pelo gênero da primeira palavra."""
    first = normalize(food_name).split(" ")[0]
    feminine = first.endswith("a") or first in {"maca", "aveia", "tapioca", "carne"}
    return f"{'da' if feminine else 'do'} {_lower_first(food_name)}"


def _add_extra(items: list[dict], index: int, extra: dict, style_qty: str) -> None:
    """Soma o complemento a um item igual já em gramas, ou insere logo após o substituto."""
    for existing in items:
        grams = parse_grams(existing["qty"])
        if normalize(existing["food"]) == normalize(extra["food"]) and grams:
            existing["qty"] = qty_like(existing["qty"], grams + extra["grams"])
            return
    items.insert(index + 1, {"food": extra["food"], "qty": qty_like(style_qty, extra["grams"])})


def _try_desired(turn: _Turn, meal_key: str, index: int, desired: list[dict]) -> dict:
    """O paciente pediu um alimento específico: calcula a porção ou explica por que não dá."""
    item, original, grams = _target_info(turn, meal_key, index)
    if not original or not grams:
        return _cannot_calculate(turn, meal_key, item, unknown_food=not original)

    same_group = [food for food in desired if food["group"] == original["group"]]
    if not same_group:
        wish = desired[0]
        return _offer_options(
            turn, meal_key, index,
            intro=(
                f"{wish['name']} faz o papel {GROUP_ROLE_OF.get(wish['group'], 'de outro grupo')} e "
                f"{_lower_first(item['food'])} é {GROUP_ROLE.get(original['group'], 'outro grupo')} do prato, "
                "então essa troca desequilibraria a refeição ⚖️ Mas olha que trocas legais:"
            ),
        )

    preferred = {normalize(n) for n in HEALTHY_SUBSTITUTES_BY_GROUP.get(original["group"], [])}
    results = sorted(
        (evaluate(original, grams, food) for food in same_group),
        key=lambda r: (not r["ok"], r["error"] + (0 if normalize(r["food"]) in preferred else 0.03)),
    )
    good = [r for r in results if r.get("ok")]
    if good:
        return _propose(turn, meal_key, index, good[0])

    attempt = results[0]
    if attempt.get("reason") == "sem_dados":
        return _offer_options(turn, meal_key, index)
    primary = attempt["primary"]
    match = attempt["primary_match"]
    food_name = _lower_first(attempt["food"])
    if attempt.get("reason") == "porcao_grande":
        detail = f"seriam {match['grams']:.0f}g de {food_name} — um pratão! 😅"
    else:
        detail = (
            f"pra igualar {PRIMARY_LABEL[primary]} seriam {match['grams']:.0f}g de {food_name}, "
            f"com {match['totals']['kcal']:.0f} kcal, enquanto o original tem "
            f"{attempt['original_totals']['kcal']:.0f} kcal."
        )
    return _offer_options(
        turn, meal_key, index,
        intro=f"Hmm, {food_name} não fecha a conta aqui 🤔 {detail[0].upper()}{detail[1:]} Que tal uma dessas?",
    )


def _apply(turn: _Turn) -> dict:
    state = turn.state
    meal_key = state["meal_key"]
    label = MEAL_LABELS[meal_key]
    message = _pick([
        f"Feito! ✅ Seu {label} de hoje agora tem {_lower_first(state['choice'])} no lugar de "
        f"{_lower_first(state['target_food'])}. Bom apetite! 😋",
        f"Trocadíssimo! 🎉 {state['choice']} entrou no {label} de hoje. Aproveita! {_emoji(state['choice'])}",
        f"Prontinho! {_emoji(state['choice'])} {label.capitalize()} atualizado com {_lower_first(state['choice'])}. "
        "Já pode conferir na aba Meu dia!",
    ]) + " Amanhã o plano volta ao original, tá?"
    return _reply(
        message,
        turn.keep(),
        day_changes=[{"meal_key": meal_key, "items": state["items"]}],
    )


def _cancel(turn: _Turn) -> dict:
    return _reply(
        _pick([
            "Tranquilo, deixei tudo como estava 👍 Se bater vontade de outra coisa, é só chamar!",
            "Beleza, plano original mantido! 💪 Tô por aqui se precisar.",
            "Sem problema! Nada mudou 😉 Qualquer coisa, me chama.",
        ]),
        turn.keep(),
    )


# ---------------------------------------------------------------- fluxo

def _restriction_note(turn: _Turn, text: str) -> str:
    asked = [f["name"] for f in turn.foods_in(tokens(text)) if food_tokens(f["name"]) & turn.restricted]
    if not asked:
        return ""
    return (
        f"Seu plano é {turn.restriction}, então {_lower_first(asked[0])} fica de fora das minhas sugestões 🌱 "
        "(se quiser mudar isso, fala com seu nutri). "
    )


def _resolve_target(turn: _Turn, meal_key: str, desired: list[dict], target_tokens: list[str],
                    explicit_target: bool = False) -> dict:
    """Com a refeição definida, descobre qual item trocar."""
    meal_items = turn.plan.get(meal_key)
    if not meal_items:
        return _reply(
            f"Não achei {MEAL_LABELS[meal_key]} no seu plano de hoje 🤔 As refeições de hoje são: {_meal_list(turn)}.",
            turn.keep(stage="pick_meal", desired=[f["name"] for f in desired],
                      target_text=" ".join(target_tokens) if explicit_target else ""),
        )
    targets = turn.items_mentioned(meal_key, target_tokens)
    named = turn.foods_in(target_tokens) if explicit_target else []
    if not targets and named:
        # "Não quero aveia no café", mas a aveia está no lanche.
        food = named[0]["name"]
        elsewhere = [
            key for key in MEAL_ORDER
            if key in turn.plan and key != meal_key and turn.items_mentioned(key, target_tokens)
        ]
        if elsewhere:
            where = _join([MEAL_LABELS[k] for k in elsewhere])
            return _reply(
                f"Hmm, não achei {_lower_first(food)} no seu {MEAL_LABELS[meal_key]} de hoje 🤔 "
                f"Ela aparece no {where}. É lá que você quer trocar?",
                turn.keep(stage="pick_meal", target_text=" ".join(target_tokens), desired=[]),
                quick_replies=[MEAL_LABELS[k].capitalize() for k in elsewhere] + [MEAL_LABELS[meal_key].capitalize()],
            )
        return _ask_item(
            turn, meal_key,
            intro=f"Boa notícia: hoje nem tem {_lower_first(food)} no seu {MEAL_LABELS[meal_key]} 😄",
        )
    if len(targets) == 1:
        index = targets[0]
    elif desired:
        groups = {food["group"] for food in desired}
        same_role = [
            i for i, item in enumerate(meal_items)
            if (resolved := resolve_food(item["food"], turn.extra_foods)) and resolved["group"] in groups
        ]
        if len(same_role) != 1:
            names = _join([f["name"] for f in desired[:1]])
            return _ask_item(turn, meal_key, intro=f"Anotado, {names} {_emoji(desired[0]['name'])}!")
        index = same_role[0]
    else:
        return _ask_item(turn, meal_key)

    if desired:
        return _try_desired(turn, meal_key, index, desired)
    return _offer_options(turn, meal_key, index)


def _desired_foods(turn: _Turn, desired_text: str, meal_key: str | None) -> list[dict]:
    exclude = set()
    if meal_key:
        exclude = {normalize(item["food"]) for item in turn.plan.get(meal_key, [])}
        exclude |= {
            normalize(resolved["name"]) for item in turn.plan.get(meal_key, [])
            if (resolved := resolve_food(item["food"], turn.extra_foods))
        }
    desired_tokens = [tok for tok in tokens(desired_text) if tok not in turn.negated]
    if normalize(desired_text) == turn.text:
        # Sem "X por Y": termos que já nomeiam itens do plano descrevem o que sai, não o que entra.
        meals = [meal_key] if meal_key else list(turn.plan)
        plan_tokens = {tok for key in meals for item in turn.plan.get(key, []) for tok in food_tokens(item["food"])}
        desired_tokens = [tok for tok in desired_tokens if tok not in plan_tokens]
    desired = turn.catalog_mentioned(desired_tokens, exclude)
    return [food for food in desired if not (food_tokens(food["name"]) & turn.avoid)]


def _split_target_desired(text: str) -> tuple[str, str]:
    """"trocar X por Y" → (X, Y); "Y no lugar de X" → (X, Y)."""
    match = re.search(r"^(.*)\b(?:por|pelo|pela|pelos|pelas)\b(.*)$", text)
    if match:
        return match.group(1), match.group(2)
    match = re.search(r"^(.*)\b(?:em vez|no lugar|ao inves)\b(.*)$", text)
    if match:
        return match.group(2), match.group(1)
    return text, text


def _handle_swap_request(turn: _Turn) -> dict | None:
    target_text, desired_text = _split_target_desired(turn.text)
    explicit_target = target_text != desired_text or bool(turn.negated_foods)
    if turn.negated_foods:
        target_text = turn.negated_text
    meal_key = turn.meal_from_text()

    if meal_key is None:
        hits = [
            (key, index) for key in MEAL_ORDER if key in turn.plan
            for index in turn.items_mentioned(key, tokens(target_text))
        ]
        meals = sorted({key for key, _ in hits}, key=MEAL_ORDER.index)
        if len(meals) == 1:
            meal_key = meals[0]
        elif len(meals) > 1:
            food = turn.plan[hits[0][0]][hits[0][1]]["food"]
            return _reply(
                f"{_lower_first(food).capitalize()} aparece em mais de uma refeição hoje: "
                f"{_join([MEAL_LABELS[k] for k in meals])}. Qual delas você quer mexer? 🤔",
                turn.keep(stage="pick_meal", target_text=target_text, desired=[]),
                quick_replies=[MEAL_LABELS[k].capitalize() for k in meals],
            )

    desired = _desired_foods(turn, desired_text, meal_key)
    if meal_key is None:
        if not desired and not SWAP_RE.search(turn.text):
            return None
        return _ask_meal(turn, [food["name"] for food in desired])
    note = _restriction_note(turn, desired_text) if not desired else ""
    if note:
        target_index = turn.items_mentioned(meal_key, tokens(target_text))
        if len(target_index) == 1:
            return _offer_options(turn, meal_key, target_index[0], intro=note + "Olha o que fecha a conta:")
    unknown = [] if desired else turn.unknown_food_words()
    if unknown and not turn.items_mentioned(meal_key, tokens(target_text)):
        return _unknown_food(turn, unknown, None)
    return _resolve_target(turn, meal_key, desired, tokens(target_text), explicit_target)


def _continue_flow(turn: _Turn) -> dict | None:
    state = turn.state
    stage = state.get("stage")
    meal_key = state.get("meal_key")

    if stage in ("pick_item", "pick_option", "confirm") and meal_key not in turn.plan:
        return None
    if stage in ("pick_option", "confirm"):
        index = state.get("index", -1)
        items = turn.plan[meal_key]
        if not (0 <= index < len(items)) or items[index]["food"] != state.get("target_food"):
            return None  # o plano mudou desde a última mensagem

    if stage == "pick_meal":
        new_meal = turn.meal_from_text()
        if not new_meal:
            return None
        desired = [food for food in catalog() if food["name"] in state.get("desired", [])]
        desired += _desired_foods(turn, turn.text, new_meal)
        target_text = state.get("target_text", "")
        if target_text:
            return _resolve_target(turn, new_meal, desired, tokens(target_text), explicit_target=False)
        return _resolve_target(turn, new_meal, desired, turn.tokens)

    if stage == "pick_item":
        other_meal = turn.meal_from_text()
        if other_meal and other_meal != meal_key:
            return None
        ordinal = turn.ordinal()
        if ordinal is not None and ordinal < len(turn.plan[meal_key]):
            return _offer_options(turn, meal_key, ordinal)
        if NO_RE.search(turn.text):
            return _cancel(turn)
        target_text, desired_text = _split_target_desired(turn.text)
        if turn.negated_foods:
            target_text = turn.negated_text
        desired = _desired_foods(turn, desired_text, meal_key)
        if not desired and not turn.items_mentioned(meal_key, tokens(target_text)):
            unknown = turn.unknown_food_words()
            if unknown:
                return _unknown_food(turn, unknown, stage)
            if len(turn.tokens) <= 4 and not SWAP_RE.search(turn.text):
                return _nudge(turn, stage, [item["food"] for item in turn.plan[meal_key]])
            return None
        return _resolve_target(turn, meal_key, desired, tokens(target_text))

    if stage in ("pick_option", "confirm"):
        index = state["index"]
        options = state.get("options", [])
        other_meal = turn.meal_from_text()
        if other_meal and other_meal != meal_key:
            return None

        if turn.negated_foods:
            on_table = set(options) | {state.get("choice"), state.get("target_food")}
            on_table |= {i["food"] for i in state.get("items", [])}
            refused = {tok for name in on_table if name for tok in food_tokens(name)}
            if refused & _expand_food_words(turn.negated) or turn.items_mentioned(meal_key, list(turn.negated)):
                names = turn.negated_label()
                return _offer_options(
                    turn, meal_key, index,
                    intro=_pick([f"Anotado, sem {names}! 🙅", f"Xô, {names}! 🙅"]),
                )
            if any(turn.items_mentioned(key, list(turn.negated)) for key in turn.plan if key != meal_key):
                return None  # o paciente mudou de assunto para outra refeição

        if SWAP_RE.search(turn.text) and not turn.items_mentioned(meal_key, turn.tokens) and any(
            turn.items_mentioned(key, turn.tokens) for key in turn.plan if key != meal_key
        ):
            return None  # o paciente mudou de assunto para outra refeição

        if stage == "pick_option" and turn.negated_text:
            refused = [
                options[ORDINALS[tok]] for tok in tokens(turn.negated_text)
                if tok in ORDINALS and ORDINALS[tok] < len(options)
            ]
            if refused:
                for name in refused:
                    turn.disliked.update(food_tokens(name))
                return _offer_options(turn, meal_key, index,
                                      intro=f"Beleza, {_lower_first(refused[0])} tá fora! 🙅")

        note = _restriction_note(turn, turn.text)
        if note:
            return _offer_options(turn, meal_key, index, intro=note + "Olha o que fecha a conta:")

        ordinal = turn.ordinal()
        if stage == "pick_option" and ordinal is not None and ordinal < len(options):
            return _try_desired(turn, meal_key, index, [f for f in catalog() if f["name"] == options[ordinal]])

        desired = _desired_foods(turn, _split_target_desired(turn.text)[1], meal_key)
        is_yes = bool(YES_RE.search(turn.text) or "👍" in turn.raw)
        if desired:
            if stage == "confirm" and any(f["name"] == state.get("choice") for f in desired) and is_yes:
                return _apply(turn)
            # Prioriza o que já estava entre as opções mostradas.
            in_options = [f for f in desired if f["name"] in options]
            return _try_desired(turn, meal_key, index, in_options or desired)

        unknown = turn.unknown_food_words() if len(turn.tokens) > 1 else []
        if unknown and not MORE_RE.search(turn.text):
            return _unknown_food(turn, unknown, stage)
        if MORE_RE.search(turn.text):
            return _offer_options(
                turn, meal_key, index,
                intro=_pick(["Bora de mais opções! 🔍", "Tenho mais cartas na manga! 🃏"]),
                shown=state.get("shown", []),
            )
        if NO_RE.search(turn.text):
            return _cancel(turn)
        if stage == "confirm" and is_yes:
            return _apply(turn)
        if stage == "pick_option" and is_yes and len(options) == 1:
            return _try_desired(turn, meal_key, index, [f for f in catalog() if f["name"] == options[0]])
        if stage == "pick_option" and is_yes:
            return _reply(
                "Qual delas? Me manda o número ou o nome 😄",
                turn.keep(**{k: v for k, v in state.items() if k != "disliked"}),
                quick_replies=options + ["Outras opções"],
            )
        if len(turn.tokens) <= 6 and not SWAP_RE.search(turn.text):
            return _nudge(turn, stage, options)
    return None


def _unknown_food(turn: _Turn, words: list[str], stage: str | None) -> dict:
    """O paciente pediu algo que não está na tabela: diz isso em vez de "não entendi"."""
    name = " ".join(words)
    text = (
        f"Hmm, {name} ainda não tá na minha tabela nutricional 😅, então não consigo calcular "
        "uma porção equivalente com segurança."
    )
    keep = {k: v for k, v in turn.state.items() if k != "disliked"}
    if stage == "pick_option":
        options = turn.state.get("options", [])
        text += " Das que eu garanto, tenho: " + _join(options) + ". Alguma te agrada?"
        return _reply(text, turn.keep(**keep), quick_replies=options + ["Outras opções"])
    if stage == "confirm":
        text += f" Sigo com {_lower_first(turn.state.get('choice', ''))} ou quer ver outras opções?"
        return _reply(text, turn.keep(**keep), awaiting=True,
                      quick_replies=["Sim, troca! ✅", "Ver outras opções", "Deixa como está"])
    if stage == "pick_item":
        return _reply(text + " Me diz qual item do prato você quer trocar que eu te mostro o que dá 😉",
                      turn.keep(**keep), quick_replies=[i["food"] for i in turn.plan[keep["meal_key"]]][:4])
    return _reply(text + " Se quiser, me fala qual item quer trocar que eu te mostro as opções que fecham a conta 😉",
                  turn.keep())


def _nudge(turn: _Turn, stage: str, choices: list[str]) -> dict:
    keep = {k: v for k, v in turn.state.items() if k != "disliked"}
    if stage == "confirm":
        text = 'Não peguei essa 😅 Confirmo a troca? Responde "sim" pra trocar ou "não" pra deixar como está.'
        replies = ["Sim, troca! ✅", "Ver outras opções", "Deixa como está"]
    else:
        text = f"Não peguei essa 😅 Me manda o número (1 a {len(choices)}) ou o nome do alimento."
        replies = choices + (["Outras opções"] if stage == "pick_option" else [])
    return _reply(text, turn.keep(**keep), quick_replies=replies, awaiting=stage == "confirm")


# ---------------------------------------------------------------- respostas fixas

def _compensation() -> dict:
    return _reply(
        "Nada de compensar! 💚 Não precisa cortar carboidrato, pular refeição nem fazer jejum por causa "
        "de um doce. Retoma o plano na próxima refeição, do jeitinho que está — é a constância que conta, "
        "não um dia isolado 😉"
    )


def _clinical() -> dict:
    return _reply(
        "Opa, esse assunto é importante demais pra eu dar palpite 🩺 Fala com seu nutricionista ou médico, tá? "
        "Se for algo urgente ou intenso, procure atendimento de saúde agora mesmo.",
        needs_nutritionist=True,
    )


def _missed_meal() -> dict:
    return _reply(
        _pick([
            "Tá tudo bem, acontece com todo mundo! 💚 Um deslize não apaga seu progresso.",
            "Relaxa, ninguém é robô (só eu 🤖)! Um escorregão não muda sua caminhada 💚",
        ])
        + " Bora retomar na próxima refeição, sem compensar nem pular nada. "
        "Se quiser, me conta o que rolou — às vezes dá pra trocar algum item da próxima refeição pra ficar mais fácil 😉"
    )


def _chat_fallback(turn: _Turn) -> dict:
    if re.search(r"\b(oi|ola|eai|e ai|bom dia|boa tarde|boa noite|hey)\b", turn.text):
        text = _pick([
            "Oii! 👋 Tô aqui pra deixar seu dia mais gostoso. Quer trocar algum alimento de hoje? "
            "É só falar tipo \"quero trocar o arroz do almoço\" 😉",
            "E aí! 🐣 Bora cuidar do dia juntos? Se quiser variar alguma refeição, me chama!",
        ])
    elif re.search(r"\b(dica\w*|sugest\w*|ideia\w*)\b", turn.text):
        text = _pick([
            "Dica do Buddy: deixa uma garrafinha de água sempre à vista — o corpo agradece 💧",
            "Dica do Buddy: mastigar devagar ajuda a perceber a saciedade. Sem pressa! 😌",
            "Dica do Buddy: um prato bem colorido costuma ter mais variedade de nutrientes 🌈",
            "Dica do Buddy: deixa as frutas lavadas na geladeira, fica bem mais fácil lembrar delas 🍎",
            "Dica do Buddy: planejar as marmitas no domingo deixa a semana muito mais leve 🍱",
        ])
    elif re.search(r"\b(obrigad\w*|valeu|vlw|brigad\w*)\b", turn.text):
        text = _pick(["Imagina! 💚 Tamo junto!", "Por nada! Conta comigo sempre 🐣"])
    else:
        text = (
            "Hmm, nessa eu ainda não sei te ajudar direitinho 🙈 Mas trocas de alimento eu resolvo na hora! "
            "Experimenta: \"quero trocar a proteína do jantar\" ou \"posso comer frango no lugar do peixe?\""
        )
    return _reply(text, turn.keep(), ai_unavailable=True)


def respond(message: str, context: dict, state: dict | None, history: list[dict] | None = None,
            context_text: str = "") -> dict:
    turn = _Turn(message, context, state)

    if COMPENSATION_RE.search(turn.text):
        return {**_compensation(), "buddy_state": turn.keep()}
    if CLINICAL_RE.search(turn.text):
        return {**_clinical(), "buddy_state": turn.keep()}
    if MISSED_RE.search(turn.text):
        return {**_missed_meal(), "buddy_state": turn.keep()}

    continued = _continue_flow(turn)
    if continued:
        return continued
    if NO_RE.search(turn.text) and len(turn.tokens) <= 4 and not turn.negated_foods:
        return _cancel(turn)

    swap = _handle_swap_request(turn)
    if swap:
        return swap
    if turn.negated_foods:
        return _reply(
            f"Anotado, nada de {turn.negated_label()} nas minhas sugestões de hoje! 🙅 "
            "Quer trocar algum alimento?",
            turn.keep(),
        )

    text = ollama_service.chat_reply(history or [], message, context_text)
    if text and not CHANGE_CLAIM_RE.search(text):
        return _reply(text, turn.keep())
    return _chat_fallback(turn)
