const SayPlatformBase = require('./base.js')

const BASE_SPEED = 175
const COMMAND = 'say'

class SayPlatformDarwin extends SayPlatformBase {
  constructor () {
    super()
    this.baseSpeed = BASE_SPEED
  }

  buildSpeakCommand ({ text, voice, speed }) {
    let args = []
    let pipedData = ''
    let options = {}

    if (!voice) {
      args.push(text)
    } else {
      args.push('-v', voice, text)
    }

    if (speed) {
      args.push('-r', this.convertSpeed(speed))
    }

    return { command: COMMAND, args, pipedData, options }
  }

  buildExportCommand ({ text, voice, speed, filename }) {
    let args = []
    let pipedData = ''
    let options = {}

    if (!voice) {
      args.push(text)
    } else {
      args.push('-v', voice, text)
    }

    if (speed) {
      args.push('-r', this.convertSpeed(speed))
    }

    if (filename) {
      args.push('-o', filename, '--data-format=LEF32@32000')
    }

    return { command: COMMAND, args, pipedData, options }
  }

  runStopCommand () {
    this.child.stdin.pause()
    this.child.kill()
  }

  getVoices () {
    throw new Error(`say.export(): does not support platform ${this.platform}`)
  }
}

module.exports = SayPlatformDarwin
