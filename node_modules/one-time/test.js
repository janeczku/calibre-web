describe('one-time', function () {
  'use strict';

  var assume = require('assume')
    , one = require('./');

  it('is exported as a function', function () {
    assume(one).is.a('function');
  });

  it('only calls the supplied function once', function (next) {
    next = one(next);

    next();
    next();
    next();
    next();
  });

  it('returns the same value as the called function every single time', function () {
    var foo = one(function () {
      return 'bar';
    });

    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
    assume(foo()).equals('bar');
  });

  it('the returned function uses the same displayName as the given fn', function () {
    var foo = one(function banana() {
      return 'bar';
    });

    assume(foo.displayName).equals('banana');
  });
});
