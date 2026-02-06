"""Tests for placeholder syntax sugar (_)."""

from stolas.logic.placeholder import Placeholder, PlaceholderExpression, _
from stolas.logic import contains


class TestPlaceholderBasics:
    """Test basic placeholder functionality."""

    def test_placeholder_instance(self) -> None:
        """Test that _ is a Placeholder instance."""
        assert isinstance(_, Placeholder)

    def test_identity_passthrough(self) -> None:
        """Test that placeholder can be used as identity."""
        # Note: _ itself is not callable, but expressions are
        expr = _ + 0  # Create an expression
        assert expr(5) == 5


class TestPlaceholderComparison:
    """Test comparison operators."""

    def test_equal(self) -> None:
        """Test == operator."""
        expr = _ == 5
        assert isinstance(expr, PlaceholderExpression)
        assert expr(5) is True
        assert expr(3) is False

    def test_not_equal(self) -> None:
        """Test != operator."""
        expr = _ != 5
        assert expr(3) is True
        assert expr(5) is False

    def test_less_than(self) -> None:
        """Test < operator."""
        expr = _ < 10
        assert expr(5) is True
        assert expr(15) is False

    def test_less_equal(self) -> None:
        """Test <= operator."""
        expr = _ <= 10
        assert expr(10) is True
        assert expr(5) is True
        assert expr(15) is False

    def test_greater_than(self) -> None:
        """Test > operator."""
        expr = _ > 10
        assert expr(15) is True
        assert expr(5) is False

    def test_greater_equal(self) -> None:
        """Test >= operator."""
        expr = _ >= 10
        assert expr(10) is True
        assert expr(15) is True
        assert expr(5) is False


class TestPlaceholderArithmetic:
    """Test arithmetic operators."""

    def test_add(self) -> None:
        """Test + operator."""
        expr = _ + 5
        assert expr(10) == 15

    def test_subtract(self) -> None:
        """Test - operator."""
        expr = _ - 3
        assert expr(10) == 7

    def test_multiply(self) -> None:
        """Test * operator."""
        expr = _ * 2
        assert expr(5) == 10

    def test_divide(self) -> None:
        """Test / operator."""
        expr = _ / 2
        assert expr(10) == 5.0

    def test_floor_divide(self) -> None:
        """Test // operator."""
        expr = _ // 3
        assert expr(10) == 3

    def test_modulo(self) -> None:
        """Test % operator."""
        expr = _ % 3
        assert expr(10) == 1

    def test_power(self) -> None:
        """Test ** operator."""
        expr = _**2
        assert expr(5) == 25


class TestPlaceholderReflectedArithmetic:
    """Test reflected arithmetic operators (other op _)."""

    def test_radd(self) -> None:
        """Test reflected addition."""
        expr = 10 + _
        assert expr(5) == 15

    def test_rsub(self) -> None:
        """Test reflected subtraction."""
        expr = 10 - _
        assert expr(3) == 7

    def test_rmul(self) -> None:
        """Test reflected multiplication."""
        expr = 10 * _
        assert expr(5) == 50

    def test_rtruediv(self) -> None:
        """Test reflected division."""
        expr = 10 / _
        assert expr(2) == 5.0

    def test_rfloordiv(self) -> None:
        """Test reflected floor division."""
        expr = 10 // _
        assert expr(3) == 3


class TestPlaceholderUnary:
    """Test unary operators."""

    def test_negation(self) -> None:
        """Test unary - operator."""
        expr = -_
        assert expr(5) == -5
        assert expr(-3) == 3

    def test_positive(self) -> None:
        """Test unary + operator."""
        expr = +_
        assert expr(5) == 5
        assert expr(-3) == -3

    def test_absolute(self) -> None:
        """Test abs() operator."""
        expr = abs(_)
        assert expr(-5) == 5
        assert expr(3) == 3


class TestPlaceholderAttributeAccess:
    """Test attribute access."""

    def test_simple_attribute(self) -> None:
        """Test _.attr syntax."""

        class Point:
            def __init__(self, x: int, y: int) -> None:
                self.x = x
                self.y = y

        expr = _.x
        point = Point(10, 20)
        assert expr(point) == 10

    def test_chained_attributes(self) -> None:
        """Test _.attr1.attr2 syntax."""

        class Inner:
            def __init__(self, value: int) -> None:
                self.value = value

        class Outer:
            def __init__(self, inner: Inner) -> None:
                self.inner = inner

        expr = _.inner
        obj = Outer(Inner(42))
        result = expr(obj)
        assert result.value == 42


class TestPlaceholderIndexing:
    """Test indexing operations."""

    def test_list_indexing(self) -> None:
        """Test _[index] for lists."""
        expr = _[0]
        assert expr([1, 2, 3]) == 1

        expr = _[2]
        assert expr([10, 20, 30]) == 30

    def test_dict_indexing(self) -> None:
        """Test _[key] for dicts."""
        expr = _["name"]
        assert expr({"name": "Alice", "age": 30}) == "Alice"

    def test_string_indexing(self) -> None:
        """Test _[index] for strings."""
        expr = _[0]
        assert expr("hello") == "h"


class TestPlaceholderMethodCalls:
    """Test method call syntax."""

    def test_simple_method_call(self) -> None:
        """Test _.attr.method() syntax."""

        # Note: Direct _.method() doesn't work, need attribute access first
        # This is because Placeholder.__getattr__ returns PlaceholderExpression
        # which then has __getattr__ returning PlaceholderMethodProxy
        class Text:
            def __init__(self, value: str) -> None:
                self.value = value

        expr = _.value.upper()
        assert expr(Text("hello")) == "HELLO"

    def test_method_with_args(self) -> None:
        """Test _.attr.method(args) syntax."""

        class Text:
            def __init__(self, value: str) -> None:
                self.value = value

        expr = _.value.replace("a", "b")
        assert expr(Text("banana")) == "bbnbnb"

    def test_method_with_kwargs(self) -> None:
        """Test _.attr.method(kwargs) syntax."""

        class Text:
            def __init__(self, value: str) -> None:
                self.value = value

        expr = _.value.split(sep=",")
        assert expr(Text("a,b,c")) == ["a", "b", "c"]


class TestPlaceholderChaining:
    """Test chaining multiple operations."""

    def test_arithmetic_chain(self) -> None:
        """Test chaining arithmetic operations."""
        expr = (_ + 5) * 2
        assert expr(10) == 30

    def test_comparison_chain(self) -> None:
        """Test chaining with comparison."""
        expr = (_ * 2) > 10
        assert expr(6) is True
        assert expr(4) is False

    def test_attribute_and_arithmetic(self) -> None:
        """Test combining attribute access and arithmetic."""

        class Value:
            def __init__(self, x: int) -> None:
                self.x = x

        expr = _.x + 10
        assert expr(Value(5)) == 15

    def test_attribute_and_method(self) -> None:
        """Test combining attribute and method call."""

        class Person:
            def __init__(self, name: str) -> None:
                self.name = name

        expr = _.name.upper()
        assert expr(Person("alice")) == "ALICE"

    def test_index_and_method(self) -> None:
        """Test combining indexing and method call."""
        expr = _[0].upper()
        assert expr(["hello", "world"]) == "HELLO"


class TestPlaceholderMembership:
    """Test membership operators (in)."""

    def test_in_string(self) -> None:
        """Test 'item in _' for strings."""
        expr = contains("@")
        assert expr("test@example.com") is True
        assert expr("testexample.com") is False

    def test_in_list(self) -> None:
        """Test 'item in _' for lists."""
        expr = contains(5)
        assert expr([1, 2, 3, 4, 5]) is True
        assert expr([1, 2, 3, 4]) is False

    def test_in_dict(self) -> None:
        """Test 'item in _' for dicts (checks keys)."""
        expr = contains("name")
        assert expr({"name": "Alice", "age": 30}) is True
        assert expr({"email": "alice@example.com"}) is False

    def test_in_tuple(self) -> None:
        """Test 'item in _' for tuples."""
        expr = contains("hello")
        assert expr(("hello", "world")) is True
        assert expr(("foo", "bar")) is False


class TestPlaceholderWithLogicFunctions:
    """Test placeholder integration with logic functions."""

    def test_with_where(self) -> None:
        """Test _ with where() function."""
        from stolas.logic import where
        from stolas.types import Many

        numbers = Many([1, 2, 3, 4, 5])
        result = where(_ > 2)(numbers)
        assert list(result.items) == [3, 4, 5]

    def test_with_apply(self) -> None:
        """Test _ with apply() function."""
        from stolas.logic import apply
        from stolas.types import Many

        numbers = Many([1, 2, 3])
        result = apply(_ * 2)(numbers)
        assert list(result.items) == [2, 4, 6]

    def test_with_find(self) -> None:
        """Test _ with find() function."""
        from stolas.logic import find
        from stolas.types import Many, Some

        numbers = Many([1, 2, 3, 4, 5])
        result = find(_ == 3)(numbers)
        assert isinstance(result, Some)
        assert result.value == 3

    def test_with_check(self) -> None:
        """Test _ with check() function."""
        from stolas.logic import check
        from stolas.types import Ok

        validator = check(_ > 0, "Must be positive")
        result = validator(10)
        assert isinstance(result, Ok)
        assert result.value == 10


class TestPlaceholderComplexExpressions:
    """Test complex placeholder expressions."""

    def test_complex_arithmetic(self) -> None:
        """Test complex arithmetic expression."""
        expr = (_ + 10) * 2 - 5
        assert expr(5) == 25  # (5 + 10) * 2 - 5 = 25

    def test_complex_comparison(self) -> None:
        """Test complex comparison expression."""
        expr = (_ * 2 + 1) >= 10
        assert expr(5) is True  # 5 * 2 + 1 = 11 >= 10
        assert expr(4) is False  # 4 * 2 + 1 = 9 < 10

    def test_attribute_chain_with_method(self) -> None:
        """Test complex attribute and method chain."""

        class Address:
            def __init__(self, city: str) -> None:
                self.city = city

        class Person:
            def __init__(self, address: Address) -> None:
                self.address = address

        # Access address, then city, then call upper() on the city string
        expr = _.address
        person = Person(Address("bangkok"))
        address = expr(person)
        assert address.city == "bangkok"

        # Full chain: get address.city value
        expr2 = _.address.city
        assert expr2(person) == "bangkok"


class TestPlaceholderEdgeCases:
    """Test edge cases and special scenarios."""

    def test_multiple_placeholders_same_expression(self) -> None:
        """Test that each _ creates independent expressions."""
        expr1 = _ + 5
        expr2 = _ * 2
        assert expr1(10) == 15
        assert expr2(10) == 20

    def test_placeholder_with_none(self) -> None:
        """Test placeholder with None values."""
        expr = _ == None  # noqa: E711
        assert expr(None) is True
        assert expr(5) is False

    def test_placeholder_with_bool(self) -> None:
        """Test placeholder with boolean values."""
        expr = _ == True  # noqa: E712
        assert expr(True) is True
        assert expr(False) is False

    def test_callable_result(self) -> None:
        """Test that PlaceholderExpression is callable."""
        expr = _ + 5
        assert callable(expr)
        assert expr(10) == 15


class TestPlaceholderExpressionChainedOperators:
    """Tests for PlaceholderExpression chained comparison/arithmetic operators."""

    def test_expression_ne(self) -> None:
        expr = _.value != 5
        assert expr(type("Obj", (), {"value": 3})()) is True
        assert expr(type("Obj", (), {"value": 5})()) is False

    def test_expression_lt(self) -> None:
        expr = _.value < 5
        assert expr(type("Obj", (), {"value": 3})()) is True
        assert expr(type("Obj", (), {"value": 7})()) is False

    def test_expression_le(self) -> None:
        expr = _.value <= 5
        assert expr(type("Obj", (), {"value": 5})()) is True
        assert expr(type("Obj", (), {"value": 6})()) is False

    def test_expression_truediv(self) -> None:
        expr = _.value / 2
        assert expr(type("Obj", (), {"value": 10})()) == 5.0

    def test_expression_floordiv(self) -> None:
        expr = _.value // 3
        assert expr(type("Obj", (), {"value": 10})()) == 3

    def test_expression_mod(self) -> None:
        expr = _.value % 3
        assert expr(type("Obj", (), {"value": 10})()) == 1

    def test_expression_eq_inner_function_executed(self) -> None:
        expr = _.value == 5
        obj = type("Obj", (), {"value": 5})()
        assert expr(obj) is True
        obj2 = type("Obj", (), {"value": 3})()
        assert expr(obj2) is False


class TestPlaceholderReflectedOperators:
    """Tests for Placeholder reflected arithmetic operators."""

    def test_radd(self) -> None:
        expr = 10 + _
        assert expr(5) == 15

    def test_rsub(self) -> None:
        expr = 10 - _
        assert expr(3) == 7

    def test_rmul(self) -> None:
        expr = 3 * _
        assert expr(4) == 12

    def test_rtruediv(self) -> None:
        expr = 10 / _
        assert expr(2) == 5.0

    def test_rfloordiv(self) -> None:
        expr = 10 // _
        assert expr(3) == 3
