"""Collection helpers: chain, where, apply, count, first, last, pair, find, sort.

Also hosts the monad-collection combinators ``sequence``, ``traverse``,
``partition`` and the shared ``combine_all`` accumulator.
"""

from typing import Any, Callable, Iterable, TypeVar

from stolas.types.effect import Effect
from stolas.types.many import Many
from stolas.types.option import Nothing, Option, Some, _Nothing
from stolas.types.result import Error, Ok
from stolas.types.validated import Invalid, Valid

T = TypeVar("T")
U = TypeVar("U")

_KIND_FACTORIES: dict[str, Callable[[], Any]] = {
    "result": lambda: Ok(Many(())),
    "option": lambda: Some(Many(())),
    "validated": lambda: Valid(Many(())),
    "effect": lambda: Effect(lambda: Many(())),
}


def chain(
    func: Callable[[T], Iterable[U]] | Callable[[T], Many[U]],
) -> Callable[[Many[T]], Many[U]]:
    """FlatMap helper: maps function over Many items and flattens result.

    Usage: Many(...) >> chain(_.sub_items)
    """

    def wrapper(m: Many[T]) -> Many[U]:
        results: list[U] = []
        for x in m._items:
            res = func(x)
            if isinstance(res, Many):
                results.extend(res.items)
            elif isinstance(res, Iterable):
                results.extend(res)
            else:
                raise TypeError(f"Expected Iterable or Many, got {type(res)}")
        return Many(tuple(results))

    return wrapper


def where(predicate: Callable[[T], bool]) -> Callable[[Many[T]], Many[T]]:
    """Filter helper: keeps items matching predicate.

    Usage: Many(...) >> where(_ > 10)
    """

    def wrapper(m: Many[T]) -> Many[T]:
        return Many(tuple(x for x in m._items if predicate(x)))

    return wrapper


def apply(func: Callable[[T], U]) -> Callable[[Many[T]], Many[U]]:
    """Map helper: applies function to each item.

    Usage: Many(...) >> apply(_.upper())
    """

    def wrapper(m: Many[T]) -> Many[U]:
        return Many(tuple(func(x) for x in m._items))

    return wrapper


def count() -> Callable[[Many[T]], Some[int]]:
    """Return count of items wrapped in Some.

    Usage: Many(...) >> count()  # returns Some(N)
    """

    def wrapper(m: Many[T]) -> Some[int]:
        return Some(len(m._items))

    return wrapper


def first() -> Callable[[Many[T]], Option[T]]:
    """Return first item as Some, or Nothing if empty.

    Usage: Many(...) >> first()  # returns Some(x) or Nothing
    """

    def wrapper(m: Many[T]) -> Option[T]:
        if m._items:
            return Some(m._items[0])
        return Nothing

    return wrapper


def last() -> Callable[[Many[T]], Option[T]]:
    """Return last item as Some, or Nothing if empty.

    Usage: Many(...) >> last()  # returns Some(x) or Nothing
    """

    def wrapper(m: Many[T]) -> Option[T]:
        if m._items:
            return Some(m._items[-1])
        return Nothing

    return wrapper


def pair(other: Many[U]) -> Callable[[Many[T]], Many[tuple[T, U]]]:
    """Zip with another Many collection.

    Usage: Many([1,2]) >> pair(Many(['a','b']))  # Many([(1,'a'), (2,'b')])
    """

    def wrapper(m: Many[T]) -> Many[tuple[T, U]]:
        return Many(tuple(zip(m._items, other._items)))

    return wrapper


def find(predicate: Callable[[T], bool]) -> Callable[[Many[T]], Option[T]]:
    """Find first item matching predicate.

    Usage: Many(...) >> find(_ == 5)  # returns Some(5) or Nothing
    """

    def wrapper(m: Many[T]) -> Option[T]:
        for x in m._items:
            if predicate(x):
                return Some(x)
        return Nothing

    return wrapper


def sort(
    key: Callable[[T], Any] | None = None, reverse: bool = False
) -> Callable[[Many[T]], Many[T]]:
    """Return sorted Many.

    Usage: Many(...) >> sort(key=_.age)
    """

    def wrapper(m: Many[T]) -> Many[T]:
        return Many(tuple(sorted(m._items, key=key, reverse=reverse)))  # type: ignore[arg-type,type-var]

    return wrapper


def combine_all(*vs: Any) -> Valid[tuple[Any, ...]] | Invalid[Any]:
    """Variadically combine Validated values into one flat Validated.

    All ``Valid`` -> a single ``Valid(tuple(values))`` (flat, never nested).
    Any ``Invalid`` -> ``Invalid`` with every error concatenated flat.

    This is the shared accumulate helper: ``sequence``'s Validated branch
    reuses the same flat-accumulate logic. It also avoids the nesting that
    ``Valid.combine`` produces (``Valid((1, 2)).combine(Valid(3))`` yields
    ``Valid(((1, 2), 3))``).

    Usage: combine_all(Valid(1), Valid(2), Valid(3))  # Valid((1, 2, 3))
    """
    values: list[Any] = []
    errors: list[Any] = []
    for v in vs:
        if isinstance(v, Valid):
            values.append(v._value)
        elif isinstance(v, Invalid):
            errors.extend(v._errors)
        else:
            raise ValueError(f"combine_all expected Validated, got {type(v)}")
    if errors:
        return Invalid(errors)
    return Valid(tuple(values))


def _success_of_empty(kind: str | None) -> Any:
    """Return the success-of-empty monad for a named kind, or raise."""
    if kind is None:
        raise ValueError("Cannot sequence an empty Many without a kind argument")
    factory = _KIND_FACTORIES.get(kind)
    if factory is None:
        raise ValueError(f"Unknown kind: {kind!r}")
    return factory()


def _sequence_result(items: Iterable[Any]) -> Ok[Many[Any]] | Error[Any]:
    """Fail-fast sequence over Result elements.

    Pulls ``items`` lazily so callers (``traverse``) can stop applying their
    mapping function past the first ``Error``.
    """
    values: list[Any] = []
    for x in items:
        if isinstance(x, Ok):
            values.append(x._value)
        elif isinstance(x, Error):
            return x
        else:
            raise ValueError(f"sequence expected Result, got {type(x)}")
    return Ok(Many(tuple(values)))


def _sequence_option(items: Iterable[Any]) -> Some[Many[Any]] | _Nothing:
    """Fail-fast sequence over Option elements.

    Pulls ``items`` lazily so callers (``traverse``) can stop applying their
    mapping function past the first ``Nothing``.
    """
    values: list[Any] = []
    for x in items:
        if isinstance(x, Some):
            values.append(x._value)
        elif isinstance(x, _Nothing):
            return Nothing
        else:
            raise ValueError(f"sequence expected Option, got {type(x)}")
    return Some(Many(tuple(values)))


def _sequence_validated(items: tuple[Any, ...]) -> Valid[Many[Any]] | Invalid[Any]:
    """Accumulating sequence over Validated elements."""
    for x in items:
        if not isinstance(x, (Valid, Invalid)):
            raise ValueError(f"sequence expected Validated, got {type(x)}")
    combined = combine_all(*items)
    if isinstance(combined, Invalid):
        return combined
    return Valid(Many(combined._value))


def _sequence_effect(items: tuple[Any, ...]) -> Effect[Many[Any]]:
    """Lazy sequence over Effect elements (no thunk runs now)."""
    for x in items:
        if not isinstance(x, Effect):
            raise ValueError(f"sequence expected Effect, got {type(x)}")

    def thunk() -> Many[Any]:
        return Many(tuple(x.run() for x in items))

    return Effect(thunk)


def _sequence_items(items: tuple[Any, ...], kind: str | None) -> Any:
    """Dispatch sequencing on the runtime monad type of the elements."""
    if not items:
        return _success_of_empty(kind)
    head = items[0]
    if isinstance(head, (Ok, Error)):
        return _sequence_result(items)
    if isinstance(head, (Some, _Nothing)):
        return _sequence_option(items)
    if isinstance(head, (Valid, Invalid)):
        return _sequence_validated(items)
    if isinstance(head, Effect):
        return _sequence_effect(items)
    raise ValueError(f"sequence expected a monad element, got {type(head)}")


def sequence(kind: str | None = None) -> Callable[[Many[Any]], Any]:
    """Turn a ``Many`` of monads into one monad of a ``Many``.

    Dispatches on the runtime monad type of the elements:

    - ``Result``: fail-fast; first ``Error`` short-circuits, else ``Ok(Many)``.
    - ``Option``: fail-fast; first ``Nothing`` -> ``Nothing``, else ``Some(Many)``.
    - ``Validated``: accumulating; all ``Invalid`` errors are concatenated flat.
    - ``Effect``: lazy; one ``Effect`` whose thunk runs each element on ``.run()``.

    An empty ``Many`` requires ``kind`` (``"result"``/``"option"``/
    ``"validated"``/``"effect"``) and yields the success-of-empty for it;
    without ``kind`` it raises ``ValueError``. Heterogeneous or non-monad
    elements also raise ``ValueError``.

    Usage: Many([Ok(1), Ok(2)]) >> sequence()  # Ok(Many([1, 2]))
    """

    def wrapper(m: Many[Any]) -> Any:
        return _sequence_items(m._items, kind)

    return wrapper


def traverse(
    func: Callable[[Any], Any], kind: str | None = None
) -> Callable[[Many[Any]], Any]:
    """Map ``func`` over a ``Many`` then sequence the results.

    Short-circuits for fail-fast monads: for ``Result``/``Option`` ``func`` is
    NOT called on elements past the first failure. For ``Validated`` ``func``
    is called on every element (errors accumulate). Empty/``kind``/``ValueError``
    rules match ``sequence``.

    Usage: Many([1, 2]) >> traverse(lambda x: Ok(x + 1))  # Ok(Many([2, 3]))
    """

    def wrapper(m: Many[Any]) -> Any:
        items = m._items
        if not items:
            return _success_of_empty(kind)
        head = func(items[0])
        rest = items[1:]
        if isinstance(head, (Ok, Error)):
            return _traverse_fail_fast(head, rest, func, _sequence_result)
        if isinstance(head, (Some, _Nothing)):
            return _traverse_fail_fast(head, rest, func, _sequence_option)
        mapped = (head, *(func(x) for x in rest))
        if isinstance(head, (Valid, Invalid)):
            return _sequence_validated(mapped)
        if isinstance(head, Effect):
            return _sequence_effect(mapped)
        raise ValueError(f"traverse expected a monad result, got {type(head)}")

    return wrapper


def _traverse_fail_fast(
    head: Any,
    rest: tuple[Any, ...],
    func: Callable[[Any], Any],
    seq: Callable[[Iterable[Any]], Any],
) -> Any:
    """Lazily apply ``func`` to ``rest`` only until ``seq`` short-circuits."""

    def lazy() -> Iterable[Any]:
        yield head
        for x in rest:
            yield func(x)

    return seq(lazy())


def partition() -> Callable[[Many[Any]], tuple[Many[Any], Many[Any]]]:
    """Split a ``Many`` of ``Result`` into ``(Many[oks], Many[errors])``.

    Order is preserved within each side. A non-``Result`` element raises
    ``ValueError``. Returns a plain 2-tuple of ``Many`` (not a monad).

    Usage: Many([Ok(1), Error("x")]) >> partition()  # (Many([1]), Many(["x"]))
    """

    def wrapper(m: Many[Any]) -> tuple[Many[Any], Many[Any]]:
        oks: list[Any] = []
        errors: list[Any] = []
        for x in m._items:
            if isinstance(x, Ok):
                oks.append(x._value)
            elif isinstance(x, Error):
                errors.append(x._error)
            else:
                raise ValueError(f"partition expected Result, got {type(x)}")
        return Many(tuple(oks)), Many(tuple(errors))

    return wrapper
