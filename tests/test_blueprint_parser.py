import random

import pytest
import yaml

from focusgroup.blueprint_parser import BlueprintError, BlueprintParser, split_args

from .conftest import EXAMPLE


def parser(seed=0):
    return BlueprintParser(random.Random(seed))


def test_range_is_inclusive_int():
    values = {parser(s).parse("{{ range(1, 3) }}") for s in range(50)}
    assert values == {1, 2, 3}


def test_choice_accepts_quoted_and_bare_options():
    for s in range(20):
        assert parser(s).parse("{{ choice('Cat person', Dog_person, \"Fish\") }}") in {
            "Cat person",
            "Dog_person",
            "Fish",
        }


def test_choice_keeps_parentheses_inside_options():
    assert parser().parse("{{ choice(Salesforce (Overkill)) }}") == "Salesforce (Overkill)"


def test_weighted_respects_weights():
    p = parser(1)
    picks = [p.parse("{{ weighted(Common:0.9, Rare:0.1) }}") for _ in range(2000)]
    share = picks.count("Common") / len(picks)
    assert 0.86 < share < 0.94


def test_weighted_with_quoted_keys_and_bare_none_label():
    p = parser(2)
    picks = {p.parse("{{ weighted('Admin': 0.5, None: 0.5) }}") for _ in range(200)}
    assert picks == {"Admin", "None"}


def test_normal_and_bool_types():
    p = parser(3)
    assert isinstance(p.parse("{{ normal(100, 10) }}"), int)
    assert isinstance(p.parse("{{ bool(0.5) }}"), bool)
    assert p.parse("{{ bool(0) }}") is False
    assert p.parse("{{ bool(1) }}") is True


def test_embedded_templates_become_strings():
    out = parser().parse("Age {{ range(20, 20) }}, mood {{ choice(Sunny) }}")
    assert out == "Age 20, mood Sunny"


def test_trailing_whitespace_still_returns_typed_value():
    assert parser().parse("{{ range(5, 5) }} ") == 5


def test_seed_makes_skeletons_reproducible():
    blueprint = yaml.safe_load((EXAMPLE / "blueprint.yaml").read_text())
    assert parser(42).skeleton(blueprint) == parser(42).skeleton(blueprint)


def test_nested_blueprints_are_rolled():
    out = parser().skeleton({"stats": {"str": "{{ range(1, 1) }}"}, "fixed": 7})
    assert out == {"stats": {"str": 1}, "fixed": 7}


@pytest.mark.parametrize("bad", ["{{ explode(1) }}", "{{ not a call }}", "{{ weighted(A, B) }}"])
def test_bad_templates_raise(bad):
    with pytest.raises(BlueprintError):
        parser().parse(bad)


def test_no_code_execution():
    # The old parser used eval(); make sure expressions are treated as text.
    assert parser().parse("{{ choice(__import__('os').getcwd()) }}") == "__import__('os').getcwd()"


def test_split_args_respects_quotes():
    assert split_args("'a, b', c, (d, e)") == ["'a, b'", "c", "(d, e)"]


def test_example_blueprint_rolls_every_field():
    blueprint = yaml.safe_load((EXAMPLE / "blueprint.yaml").read_text())
    skeleton = parser(7).skeleton(blueprint)
    assert set(skeleton) == set(blueprint)
    assert not any("{{" in str(v) for v in skeleton.values())
