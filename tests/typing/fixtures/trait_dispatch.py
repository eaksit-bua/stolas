"""Fixture: @trait dispatch reveals TraitDispatcher[R] and a call reveals R.

Validates trait.pyi: `@trait def describe(...) -> str` yields a
TraitDispatcher[str], and calling the dispatcher returns str. No trait.pyi gap
was needed for milestone 5; this fixture is the regression guard.
"""

from stolas.struct import trait


@trait
def describe(x: object) -> str:
    raise NotImplementedError


class Dog:
    name: str


@describe.impl(Dog)
def _describe_dog(animal: Dog) -> str:
    return animal.name


reveal_type(describe)
reveal_type(describe(Dog()))
