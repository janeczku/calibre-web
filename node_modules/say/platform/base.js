const childProcess = require('child_process')
const once = require('one-time')

class SayPlatformBase {
  constructor () {
    this.child = null
    this.baseSpeed = 0
  }

  /**
   * Uses system libraries to speak text via the speakers.
   *
   * @param {string} text Text to be spoken
   * @param {string|null} voice Name of voice to be spoken with
   * @param {number|null} speed Speed of text (e.g. 1.0 for normal, 0.5 half, 2.0 double)
   * @param {Function|null} callback A callback of type function(err) to return.
   */
  speak (text, voice, speed, callback) {
    if (typeof callback !== 'function') {
      callback = () => {}
    }

    callback = once(callback)

    if (!text) {
      return setImmediate(() => {
        callback(new TypeError('say.speak(): must provide text parameter'))
      })
    }

    let { command, args, pipedData, options } = this.buildSpeakCommand({ text, voice, speed })

    this.child = childProcess.spawn(command, args, options)

    this.child.stdin.setEncoding('ascii')
    this.child.stderr.setEncoding('ascii')

    if (pipedData) {
      this.child.stdin.end(pipedData)
    }

    this.child.stderr.once('data', (data) => {
      // we can't stop execution from this function
      callback(new Error(data))
    })

    this.child.addListener('exit', (code, signal) => {
      if (code === null || signal !== null) {
        return callback(new Error(`say.speak(): could not talk, had an error [code: ${code}] [signal: ${signal}]`))
      }

      this.child = null

      callback(null)
    })
  }

  /**
   * Uses system libraries to speak text via the speakers.
   *
   * @param {string} text Text to be spoken
   * @param {string|null} voice Name of voice to be spoken with
   * @param {number|null} speed Speed of text (e.g. 1.0 for normal, 0.5 half, 2.0 double)
   * @param {string} filename Path to file to write audio to, e.g. "greeting.wav"
   * @param {Function|null} callback A callback of type function(err) to return.
   */
  export (text, voice, speed, filename, callback) {
    if (typeof callback !== 'function') {
      callback = () => {}
    }

    callback = once(callback)

    if (!text) {
      return setImmediate(() => {
        callback(new TypeError('say.export(): must provide text parameter'))
      })
    }

    if (!filename) {
      return setImmediate(() => {
        callback(new TypeError('say.export(): must provide filename parameter'))
      })
    }

    try {
      var { command, args, pipedData, options } = this.buildExportCommand({ text, voice, speed, filename })
    } catch (error) {
      return setImmediate(() => {
        callback(error)
      })
    }

    this.child = childProcess.spawn(command, args, options)

    this.child.stdin.setEncoding('ascii')
    this.child.stderr.setEncoding('ascii')

    if (pipedData) {
      this.child.stdin.end(pipedData)
    }

    this.child.stderr.once('data', (data) => {
      // we can't stop execution from this function
      callback(new Error(data))
    })

    this.child.addListener('exit', (code, signal) => {
      if (code === null || signal !== null) {
        return callback(new Error(`say.export(): could not talk, had an error [code: ${code}] [signal: ${signal}]`))
      }

      this.child = null

      callback(null)
    })
  }

  /**
   * Stops currently playing audio. There will be unexpected results if multiple audios are being played at once
   *
   * TODO: If two messages are being spoken simultaneously, childD points to new instance, no way to kill previous
   *
   * @param {Function|null} callback A callback of type function(err) to return.
   */
  stop (callback) {
    if (typeof callback !== 'function') {
      callback = () => {}
    }

    callback = once(callback)

    if (!this.child) {
      return setImmediate(() => {
        callback(new Error('say.stop(): no speech to kill'))
      })
    }

    this.runStopCommand()

    this.child = null

    callback(null)
  }

  convertSpeed (speed) {
    return Math.ceil(this.baseSpeed * speed)
  }

  /**
   * Get Installed voices on system
   * @param {Function} callback A callback of type function(err,voices) to return.
   */
  getInstalledVoices (callback) {
    if (typeof callback !== 'function') {
      callback = () => {}
    }
    callback = once(callback)

    let { command, args } = this.getVoices()
    var voices = []
    this.child = childProcess.spawn(command, args)

    this.child.stdin.setEncoding('ascii')
    this.child.stderr.setEncoding('ascii')

    this.child.stderr.once('data', (data) => {
      // we can't stop execution from this function
      callback(new Error(data))
    })
    this.child.stdout.on('data', function (data) {
      voices += data
    })

    this.child.addListener('exit', (code, signal) => {
      if (code === null || signal !== null) {
        return callback(new Error(`say.getInstalledVoices(): could not get installed voices, had an error [code: ${code}] [signal: ${signal}]`))
      }
      if (voices.length > 0) {
        voices = voices.split('\r\n')
        voices = (voices[voices.length - 1] === '') ? voices.slice(0, voices.length - 1) : voices
      }
      this.child = null

      callback(null, voices)
    })

    this.child.stdin.end()
  }
}

module.exports = SayPlatformBase
