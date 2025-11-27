# one-time

[![Made by unshift](https://img.shields.io/badge/made%20by-unshift-00ffcc.svg?style=flat-square)](http://unshift.io)[![Version npm](http://img.shields.io/npm/v/one-time.svg?style=flat-square)](http://browsenpm.org/package/one-time)[![Build Status](http://img.shields.io/travis/unshiftio/one-time/master.svg?style=flat-square)](https://travis-ci.org/unshiftio/one-time)[![Dependencies](https://img.shields.io/david/unshiftio/one-time.svg?style=flat-square)](https://david-dm.org/unshiftio/one-time)[![Coverage Status](http://img.shields.io/coveralls/unshiftio/one-time/master.svg?style=flat-square)](https://coveralls.io/r/unshiftio/one-time?branch=master)[![IRC channel](http://img.shields.io/badge/IRC-irc.freenode.net%23unshift-00a8ff.svg?style=flat-square)](http://webchat.freenode.net/?channels=unshift) 

Call the supplied function exactly one time. This prevents double callback
execution. This module can be used on both node and browsers using browserify.
No magical ES5/6 methods used unlike the `once` module does.

## Installation

```
npm install one-time
```

## Usage

Simply supply the function with the function that should only be called one
time:

```js
var one = require('one-time');

function load(file, fn) {
  fn = one(fn);

  eventemitter.once('load', fn);
  eventemitter.once('error', fn);

  // do stuff
  eventemitter.emit('error', new Error('Failed to load, but still finished'));
  eventemitter.emit('load');
}

function example(fn) {
  fn = one(fn);

  fn();
  fn('also receives all arguments');
  fn('it returns the same value') === 'bar';
  fn('never');
  fn('gonna');
  fn('give');
  fn('you');
  fn('up');
}

example(function () { 
  return 'bar'
});
```

### Why not `once`?

The main reason is that `once` cannot be used in a browser environment unless it's
ES5 compatible. For a module as simple as this I find that unacceptable. In addition
to that it super heavy on the dependency side. So it's totally not suitable to be
used in client side applications.

In addition to that we make sure that your code stays easy to debug as returned
functions are named in the same way as your supplied functions. Making heap
inspection and stacktraces easier to understand.

## License

MIT
