<img src="https://travis-ci.org/Marak/say.js.svg?branch=master" />

<img src="https://github.com/Marak/say.js/raw/master/logo.png" />

## Installing say.js

```bash
npm install say
```


## Usage

```javascript
// automatically pick platform
const say = require('say')

// or, override the platform
const Say = require('say').Say
const say = new Say('darwin' || 'win32' || 'linux')

// Use default system voice and speed
say.speak('Hello!')

// Stop the text currently being spoken
say.stop()

// More complex example (with an OS X voice) and slow speed
say.speak("What's up, dog?", 'Alex', 0.5)

// Fire a callback once the text has completed being spoken
say.speak("What's up, dog?", 'Good News', 1.0, (err) => {
  if (err) {
    return console.error(err)
  }

  console.log('Text has been spoken.')
});

// Export spoken audio to a WAV file
say.export("I'm sorry, Dave.", 'Cellos', 0.75, 'hal.wav', (err) => {
  if (err) {
    return console.error(err)
  }

  console.log('Text has been saved to hal.wav.')
})
```

### Methods

#### Speak:

* Speed: 1 = 100%, 0.5 = 50%, 2 = 200%, etc

```javascript
say.speak(text, voice || null, speed || null, callback || null)
```

#### Export Audio:

* MacOS / Windows Only
* Speed: 1 = 100%, 0.5 = 50%, 2 = 200%, etc

```javascript
say.export(text, voice || null, speed || null, filename, callback || null)
```

#### Stop Speaking:

```javascript
say.stop(callback || null)
```

#### Get List of Installed Voice(s):

```javascript
say.getInstalledVoices(callback)
```

## Feature Matrix

Unfortunately every feature isn't supported on every platform. PR's welcome!

Platform | Speak | Export | Stop | Speed | Voice | List
---------|-------|--------|------|-------|-------|-----
macOS    | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :no_entry_sign:
Linux    | :white_check_mark: | :no_entry_sign:    | :white_check_mark: | :white_check_mark: | :white_check_mark: | :no_entry_sign:
Windows  | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark:


## macOS Notes

Voices in macOS are associated with different localities. To a list of voices and their localities run the following command:

```sh
say -v "?"
```

As an example, the default voice is `Alex` and the voice used by Siri is `Samantha`.


## Windows Notes

None.

## Linux Notes

Linux support requires [Festival](http://www.cstr.ed.ac.uk/projects/festival/). As far as I can tell there is no sane way to get a list of available voices. The only voice that seems to work is `voice_kal_diphone`, which seems to be the default anyway.

The `.export()` method is not available.

Try the following command to install Festival with a default voice:

```shell
sudo apt-get install festival festvox-kallpc16k
```


## Requirements

* Mac OS X (comes with `say`)
* Linux with Festival installed
* Windows (comes with SAPI.SpVoice)
  * Needs to have Powershell installed and available in $PATH (see [issue #75](https://github.com/Marak/say.js/issues/75))
