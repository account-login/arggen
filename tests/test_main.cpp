#include <ostream>
#include "catch.hpp"

#include "test.h"


using namespace std;


inline ostream &operator <<(ostream &os, const MyOption &value) {
    os << value.to_string();
    return os;
}


TEST_CASE("Test parse args") {
    MyOption expected;
    expected.asdf = {"A1", "A2"};
    expected.bar = 456;
    expected.foo = true;
    expected.hahaha = "haha";
    expected.qwer = "abc";
    expected.verbose = 2;

    CHECK(MyOption::parse_args(
        {"--bar", "456", "-f", "-v", "-v", "--qwer", "abc", "haha", "A1", "A2"}
    ) == expected);
    CHECK(MyOption::parse_args(
        {"--bar", "456", "-vfv", "--qwer", "abc", "haha", "A1", "A2"}
    ) == expected);
    CHECK(MyOption::parse_args(
        {"--bar=456", "-vfv", "--qwer", "abc", "haha", "A1", "A2"}
    ) == expected);
    CHECK(MyOption::parse_args(
        {"-b456", "-vfv", "--qwer", "abc", "haha", "A1", "A2"}
    ) == expected);
    CHECK(MyOption::parse_args(
        {"-b", "456", "-vfv", "--qwer", "abc", "haha", "A1", "A2"}
    ) == expected);

    expected.bar = 123;
    CHECK(MyOption::parse_args(
        {"-vfv", "haha", "A1", "A2", "--qwer", "abc"}
    ) == expected);
}


TEST_CASE("Test parse_args fail") {
    CHECK_NOTHROW(MyOption::parse_args({
        "-b456", "-vfv", "--qwer", "abc", "asdf",
    }));

    // too few args
    CHECK_THROWS_AS(MyOption::parse_args({
        "-b456", "-vfv", "--qwer", "abc",
    }), ArgError);
    // expect args follow --qwer
    CHECK_THROWS_AS(MyOption::parse_args({
        "-b456", "-vfv", "--qwer",
    }), ArgError);
    // expect --qwer
    CHECK_THROWS_AS(MyOption::parse_args({
        "-b456", "-vfv", "asfd", "bbb",
    }), ArgError);

    // unknown option
    CHECK_THROWS_AS(MyOption::parse_args({
        "-b456", "-vfvz", "--qwer", "abc", "asdf",
    }), ArgError);
    CHECK_THROWS_AS(MyOption::parse_args({
        "-b456", "-vfv", "--bbb", "--qwer", "abc", "asdf",
    }), ArgError);

    // expect args follow --bar
    CHECK_THROWS_AS(MyOption::parse_args({
        "-vfv", "--qwer", "abc", "asdf", "--bar",
    }), ArgError);
    CHECK_THROWS_AS(MyOption::parse_args({
        "-vfv", "--qwer", "abc", "asdf", "--bar", "-v",
    }), ArgError);
    CHECK_THROWS_AS(MyOption::parse_args({
        "-vfv", "--qwer", "abc", "asdf", "-b", "-v",
    }), ArgError);
}
